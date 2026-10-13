"""The real Gemini client, run against a mocked Google API (no key or network needed)."""
import asyncio
import json

import httpx
import pytest

from gemini_client import Gemini, GeminiBlocked, GeminiError


def make(handler):
    g = Gemini("k-123", "gemini-3.5-flash-lite", "gemini-3.5-flash-lite")
    g.http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return g


def reply(obj, finish="STOP"):
    return httpx.Response(200, json={"candidates": [{"finishReason": finish,
                                                      "content": {"parts": [{"text": json.dumps(obj)}]}}]})


def test_request_shape_and_parse():
    seen = {}

    def handler(req):
        seen["url"] = str(req.url)
        seen["key"] = req.headers.get("x-goog-api-key")
        seen["body"] = json.loads(req.content)
        return reply({"in_scope": True, "answer": "Hi", "source_urls": []})

    g = make(handler)
    out = asyncio.run(g.answer("SYSTEM", [("user", "q1"), ("model", "a1")], "q2"))
    assert out["answer"] == "Hi"
    assert seen["url"].endswith("/models/gemini-3.5-flash-lite:generateContent")
    assert seen["key"] == "k-123"
    b = seen["body"]
    assert b["systemInstruction"]["parts"][0]["text"] == "SYSTEM"
    assert "tools" not in b                                     # no web search / URL tools
    assert {s["threshold"] for s in b["safetySettings"]} == {"BLOCK_MEDIUM_AND_ABOVE"}
    assert len(b["safetySettings"]) == 4
    assert b["generationConfig"]["responseMimeType"] == "application/json"
    roles = [c["role"] for c in b["contents"]]
    assert roles == ["user", "model", "user"]
    assert "<visitor_message>" in b["contents"][0]["parts"][0]["text"]
    assert "<visitor_message>" in b["contents"][2]["parts"][0]["text"]


def test_classify():
    g = make(lambda req: reply({"category": "OFF_TOPIC"}))
    assert asyncio.run(g.classify("SYS", "weather?")) == "OFF_TOPIC"


def test_safety_block_raises():
    g = make(lambda req: reply({}, finish="SAFETY"))
    with pytest.raises(GeminiBlocked):
        asyncio.run(g.classify("SYS", "x"))
    g = make(lambda req: httpx.Response(200, json={"promptFeedback": {"blockReason": "SAFETY"}}))
    with pytest.raises(GeminiBlocked):
        asyncio.run(g.classify("SYS", "x"))


def test_retry_then_error():
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(503, text="busy")

    with pytest.raises(GeminiError):
        asyncio.run(make(handler).classify("SYS", "x"))
    assert len(calls) == 2


def test_invalid_json_and_missing_key():
    g = make(lambda req: httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "not json"}]}}]}))
    with pytest.raises(GeminiError):
        asyncio.run(g.classify("SYS", "x"))
    g.api_key = ""
    with pytest.raises(GeminiError):
        asyncio.run(g.classify("SYS", "x"))


def test_thought_parts_ignored():
    def handler(req):
        return httpx.Response(200, json={"candidates": [{"finishReason": "STOP", "content": {"parts": [
            {"text": "thinking...", "thought": True}, {"text": json.dumps({"category": "GREETING"})}]}}]})
    assert asyncio.run(make(handler).classify("SYS", "hi")) == "GREETING"
