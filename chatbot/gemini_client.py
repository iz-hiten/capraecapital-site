"""Minimal Gemini API client (REST, paid tier).

No tools are ever sent, so the model cannot search the web or open URLs: it only
sees the text we pass in. Safety filters are set explicitly because they are off
by default on current Gemini models.
"""
import asyncio
import json

import httpx

import usage

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SAFETY = [{"category": c, "threshold": "BLOCK_MEDIUM_AND_ABOVE"} for c in (
    "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH",
    "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT")]

CLASSIFY_SCHEMA = {
    "type": "OBJECT",
    "properties": {"category": {"type": "STRING",
                                "enum": ["ON_TOPIC", "GREETING", "OFF_TOPIC", "ADVICE", "INJECTION", "ABUSE"]}},
    "required": ["category"],
}
ANSWER_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "in_scope": {"type": "BOOLEAN"},
        "answer": {"type": "STRING"},
        "source_urls": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": ["in_scope", "answer", "source_urls"],
}


class LoopSafeHTTP:
    """An httpx client per event loop. Serverless hosts (and test clients) may run each request in a
    new loop, and a client bound to a closed loop fails. Assigning `.http` pins a client (tests)."""
    timeout = 20.0
    _pinned = None
    _client = None
    _loop = None

    @property
    def http(self):
        if self._pinned is not None:
            return self._pinned
        loop = asyncio.get_running_loop()
        if self._client is None or self._loop is not loop:
            self._client, self._loop = httpx.AsyncClient(timeout=self.timeout), loop
        return self._client

    @http.setter
    def http(self, client):
        self._pinned = client

    async def close(self):
        client = self._pinned or self._client
        if client is not None:
            await client.aclose()


class GeminiError(Exception):
    pass


class GeminiBlocked(Exception):
    """Gemini's own safety filter blocked the prompt or the reply."""


class Gemini(LoopSafeHTTP):
    def __init__(self, api_key, model, guard_model, timeout=20.0):
        self.api_key, self.model, self.guard_model = api_key, model, guard_model
        self.timeout = timeout

    async def _generate(self, model, system, contents, schema, max_tokens, temperature):
        if not self.api_key:
            raise GeminiError("GEMINI_API_KEY is not set")
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": contents,
            "safetySettings": SAFETY,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json",
                "responseSchema": schema,
            },
        }
        last = None
        for _ in range(2):  # one retry on rate limit / server error
            try:
                r = await self.http.post(API.format(model=model), json=body,
                                         headers={"x-goog-api-key": self.api_key})
            except httpx.HTTPError as e:
                last = e
                continue
            if r.status_code in (429, 500, 502, 503, 504):
                last = GeminiError(f"HTTP {r.status_code}")
                continue
            if r.status_code != 200:
                raise GeminiError(f"HTTP {r.status_code}: {r.text[:200]}")
            data = r.json()
            usage.from_gemini(model, "classify" if schema is CLASSIFY_SCHEMA else "answer", data.get("usageMetadata"))
            if data.get("promptFeedback", {}).get("blockReason"):
                raise GeminiBlocked(data["promptFeedback"]["blockReason"])
            cands = data.get("candidates") or []
            if not cands:
                raise GeminiError("no candidates")
            cand = cands[0]
            if cand.get("finishReason") in ("SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "RECITATION"):
                raise GeminiBlocked(cand["finishReason"])
            text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []) if not p.get("thought"))
            try:
                return json.loads(text)
            except (ValueError, TypeError):
                raise GeminiError("reply was not valid JSON")
        raise GeminiError(f"request failed: {last}")

    async def classify(self, system, message, previous_reply=""):
        prompt = (f"PREVIOUS ASSISTANT REPLY:\n{previous_reply[:600] or '(none)'}\n\n"
                  f"VISITOR MESSAGE:\n<visitor_message>\n{message}\n</visitor_message>")
        out = await self._generate(self.guard_model, system, [{"role": "user", "parts": [{"text": prompt}]}],
                                   CLASSIFY_SCHEMA, max_tokens=256, temperature=0)
        return out.get("category")

    async def answer(self, system, history, message):
        contents = [{"role": "user", "parts": [{"text": f"<visitor_message>\n{text}\n</visitor_message>"}]}
                    if role == "user" else {"role": "model", "parts": [{"text": text}]}
                    for role, text in history]
        contents.append({"role": "user", "parts": [{"text": f"<visitor_message>\n{message}\n</visitor_message>"}]})
        return await self._generate(self.model, system, contents, ANSWER_SCHEMA, max_tokens=1024, temperature=0.2)
