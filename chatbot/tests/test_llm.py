"""DeepSeek client and the Gemini -> DeepSeek fallback (no keys or network needed)."""
import asyncio
import json

import httpx
import pytest

import llm
from gemini_client import GeminiBlocked, GeminiError


def deepseek(handler, model="deepseek-v4-flash"):
    d = llm.DeepSeek("ds-key", model)
    d.http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return d


def ds_reply(obj, finish="stop"):
    return httpx.Response(200, json={"choices": [{"finish_reason": finish,
                                                  "message": {"content": json.dumps(obj) if obj is not None else ""}}]})


def test_deepseek_request_and_parse():
    seen = {}

    def handler(req):
        seen["url"], seen["auth"], seen["body"] = str(req.url), req.headers["authorization"], json.loads(req.content)
        return ds_reply({"in_scope": True, "answer": "Hi", "source_urls": []})

    out = asyncio.run(deepseek(handler).answer("RULES", [("user", "q1"), ("model", "a1")], "q2"))
    assert out["answer"] == "Hi"
    b = seen["body"]
    assert seen["url"] == llm.DEEPSEEK_API and seen["auth"] == "Bearer ds-key"
    assert b["model"] == "deepseek-v4-flash" and b["response_format"] == {"type": "json_object"}
    assert b["messages"][0]["role"] == "system" and "json" in b["messages"][0]["content"]
    assert [m["role"] for m in b["messages"]] == ["system", "user", "assistant", "user"]
    assert "<visitor_message>" in b["messages"][1]["content"] and "<visitor_message>" in b["messages"][3]["content"]
    assert "tools" not in b
    assert b["thinking"] == {"type": "disabled"}          # thinking is on by default and only slows replies


def test_deepseek_classify():
    assert asyncio.run(deepseek(lambda r: ds_reply({"category": "OFF_TOPIC"})).classify("SYS", "weather")) == "OFF_TOPIC"


def test_deepseek_content_filter_is_a_block():
    with pytest.raises(GeminiBlocked):
        asyncio.run(deepseek(lambda r: ds_reply({}, finish="content_filter")).classify("SYS", "x"))


def test_deepseek_empty_json_and_errors():
    with pytest.raises(GeminiError):
        asyncio.run(deepseek(lambda r: ds_reply(None)).classify("SYS", "x"))          # known empty-content issue
    with pytest.raises(GeminiError):
        asyncio.run(deepseek(lambda r: httpx.Response(402, text="Insufficient Balance")).classify("SYS", "x"))
    d = deepseek(lambda r: ds_reply({}))
    d.api_key = ""
    with pytest.raises(GeminiError):
        asyncio.run(d.classify("SYS", "x"))


class Stub:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result, error, 0

    async def classify(self, *a):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result

    answer = classify

    async def close(self):
        pass


def test_fallback_switches_and_cools_down():
    g, d = Stub(error=GeminiError("HTTP 402: credits depleted")), Stub(result="ON_TOPIC")
    f = llm.Fallback([("gemini", g), ("deepseek", d)], cooldown=300)
    assert asyncio.run(f.classify("S", "m")) == "ON_TOPIC"
    assert (g.calls, d.calls) == (1, 1)
    asyncio.run(f.classify("S", "m"))                  # within cooldown: Gemini skipped
    assert (g.calls, d.calls) == (1, 2)
    f.down_until["gemini"] = 0                         # cooldown over: Gemini tried first again
    asyncio.run(f.classify("S", "m"))
    assert g.calls == 2


def test_safety_block_is_not_retried_on_backup():
    g, d = Stub(error=GeminiBlocked("SAFETY")), Stub(result="ON_TOPIC")
    with pytest.raises(GeminiBlocked):
        asyncio.run(llm.Fallback([("gemini", g), ("deepseek", d)]).answer("S", [], "m"))
    assert d.calls == 0


def test_both_down_raises_error():
    f = llm.Fallback([("gemini", Stub(error=GeminiError("a"))), ("deepseek", Stub(error=GeminiError("b")))])
    with pytest.raises(GeminiError):
        asyncio.run(f.classify("S", "m"))


def test_make_uses_configured_providers():
    assert [n for n, _ in llm.make("g", "m", "m", "", "").providers] == ["gemini"]
    assert [n for n, _ in llm.make("", "m", "m", "d", "deepseek-flash").providers] == ["deepseek"]
    assert [n for n, _ in llm.make("g", "m", "m", "d", "deepseek-flash").providers] == ["gemini", "deepseek"]


def _sequence(*replies):
    calls = []

    def handler(req):
        calls.append(1)
        return replies[min(len(calls), len(replies)) - 1]
    return handler, calls


def test_deepseek_blank_retried_twice_then_succeeds():
    blank = httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": "      "}}]})
    handler, calls = _sequence(blank, blank, ds_reply({"category": "ON_TOPIC"}))
    assert asyncio.run(deepseek(handler).classify("SYS", "x")) == "ON_TOPIC"
    assert len(calls) == 3


def test_deepseek_blank_three_times_gives_error_and_stops():
    blank = httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": ""}}]})
    handler, calls = _sequence(blank)
    with pytest.raises(llm.DeepSeekEmpty):
        asyncio.run(deepseek(handler).classify("SYS", "x"))
    assert len(calls) == 3                                   # 1 try + max 2 retries


def test_blank_reply_does_not_bench_deepseek():
    g, d = Stub(error=GeminiError("HTTP 402")), Stub(error=llm.DeepSeekEmpty("blank"))
    f = llm.Fallback([("gemini", g), ("deepseek", d)])
    with pytest.raises(GeminiError):
        asyncio.run(f.classify("S", "m"))
    assert "gemini" in f.down_until and "deepseek" not in f.down_until
