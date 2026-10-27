"""Model providers: Gemini first, DeepSeek as the backup.

If Gemini fails (no credit, outage, timeout, bad reply) the same request is retried on DeepSeek,
and Gemini is skipped for a cooldown period so visitors don't wait on a failing provider.
A safety block from Gemini is NOT retried elsewhere: that message is refused, so the backup can't
be used to get around a block. Every answer, from either provider, still goes through the same
checks in app.py.
"""
import json
import logging
import time

import httpx

import usage

from gemini_client import Gemini, GeminiBlocked, GeminiError, LoopSafeHTTP

log = logging.getLogger("chatbot")

DEEPSEEK_API = "https://api.deepseek.com/chat/completions"

# DeepSeek has no response schema, so the JSON shape is spelled out in the instructions (its JSON mode
# also requires the word "json" in the prompt).
CLASSIFY_FORMAT = ('\n\nRespond in json only, exactly like {"category": "ON_TOPIC"}, where category is one of '
                   'ON_TOPIC, GREETING, OFF_TOPIC, ADVICE, INJECTION, ABUSE.')
ANSWER_FORMAT = ('\n\nRespond in json only, exactly like {"in_scope": true, "answer": "...", '
                 '"source_urls": ["https://capraecapital.com/pricing/"]}.')


class DeepSeekEmpty(GeminiError):
    """DeepSeek kept returning blank or non-JSON content (a documented JSON-mode issue). Only that
    message fails; DeepSeek itself is not taken out of rotation."""


class DeepSeek(LoopSafeHTTP):
    """DeepSeek chat completions (OpenAI-compatible), JSON mode, same interface as Gemini."""

    def __init__(self, api_key, model, timeout=25.0):
        self.api_key, self.model = api_key, model or "deepseek-flash"
        self.timeout = timeout

    async def _chat(self, system, messages, max_tokens, temperature):
        if not self.api_key:
            raise GeminiError("DEEPSEEK_API_KEY is not set")
        body = {"model": self.model, "messages": [{"role": "system", "content": system}] + messages,
                "response_format": {"type": "json_object"}, "max_tokens": max_tokens,
                "temperature": temperature, "stream": False,
                "thinking": {"type": "disabled"}}          # on (effort high) by default: slow, not needed here
        last = None
        server_tries, empty_tries = 0, 0
        while True:
            try:
                r = await self.http.post(DEEPSEEK_API, json=body, headers={"Authorization": f"Bearer {self.api_key}"})
            except httpx.HTTPError as e:
                last, server_tries = e, server_tries + 1
                if server_tries > 1:                       # one retry on network error
                    raise GeminiError(f"DeepSeek request failed: {last}")
                continue
            if r.status_code in (429, 500, 502, 503, 504):
                last, server_tries = GeminiError(f"DeepSeek HTTP {r.status_code}"), server_tries + 1
                if server_tries > 1:                       # one retry on rate limit / server error
                    raise GeminiError(f"DeepSeek request failed: {last}")
                continue
            if r.status_code != 200:
                raise GeminiError(f"DeepSeek HTTP {r.status_code}: {r.text[:200]}")
            try:
                data = r.json()
                usage.from_deepseek(self.model, "classify" if max_tokens <= 256 else "answer", data.get("usage"))
                choice = data["choices"][0]
                if choice.get("finish_reason") == "content_filter":
                    raise GeminiBlocked("DeepSeek content_filter")
                return json.loads(choice["message"]["content"] or "")
            except GeminiBlocked:
                raise
            except (ValueError, KeyError, IndexError, TypeError):
                # Documented: "the API may occasionally return empty content" in JSON mode.
                # Retry a blank or broken reply at most 2 times, then give up on this message only.
                empty_tries += 1
                if empty_tries > 2:
                    raise DeepSeekEmpty("DeepSeek returned empty content 3 times")
                log.info("provider=deepseek returned empty content; retry %d of 2", empty_tries)

    async def classify(self, system, message, previous_reply=""):
        prompt = (f"PREVIOUS ASSISTANT REPLY:\n{previous_reply[:600] or '(none)'}\n\n"
                  f"VISITOR MESSAGE:\n<visitor_message>\n{message}\n</visitor_message>")
        out = await self._chat(system + CLASSIFY_FORMAT, [{"role": "user", "content": prompt}],
                               max_tokens=256, temperature=0)
        return out.get("category") if isinstance(out, dict) else None

    async def answer(self, system, history, message):
        msgs = [{"role": "user", "content": f"<visitor_message>\n{t}\n</visitor_message>"} if r == "user"
                else {"role": "assistant", "content": t} for r, t in history]
        msgs.append({"role": "user", "content": f"<visitor_message>\n{message}\n</visitor_message>"})
        return await self._chat(system + ANSWER_FORMAT, msgs, max_tokens=1024, temperature=0.2)


class Fallback:
    """Try providers in order; skip one for `cooldown` seconds after it fails."""

    def __init__(self, providers, cooldown=300):
        self.providers = [(name, p) for name, p in providers if p is not None]
        self.cooldown = cooldown
        self.down_until = {}

    async def close(self):
        for _, p in self.providers:
            await p.close()

    async def _run(self, method, *args):
        now = time.time()
        live = [(n, p) for n, p in self.providers if self.down_until.get(n, 0) <= now] or self.providers
        last = None
        for name, p in live:
            try:
                return await getattr(p, method)(*args)
            except GeminiBlocked:
                raise                                  # a safety block is final, never retried elsewhere
            except GeminiError as e:
                last = e
                if not isinstance(e, DeepSeekEmpty):       # a blank reply isn't an outage: don't bench DeepSeek
                    self.down_until[name] = time.time() + self.cooldown
                log.info("provider=%s failed (%s); switching to the next provider", name, str(e)[:120])
        raise last or GeminiError("no provider configured")

    async def classify(self, system, message, previous_reply=""):
        return await self._run("classify", system, message, previous_reply)

    async def answer(self, system, history, message):
        return await self._run("answer", system, history, message)


def make(gemini_key, gemini_model, guard_model, deepseek_key, deepseek_model):
    providers = [("gemini", Gemini(gemini_key, gemini_model, guard_model) if gemini_key else None),
                 ("deepseek", DeepSeek(deepseek_key, deepseek_model) if deepseek_key else None)]
    if not any(p for _, p in providers):
        providers = [("gemini", Gemini("", gemini_model, guard_model))]   # fails closed with a clear error
    return Fallback(providers)
