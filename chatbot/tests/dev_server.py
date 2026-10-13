"""Local preview: the real site + the real API on one port.

    cd chatbot && python tests/dev_server.py          ->  http://localhost:8091/  (fake Gemini, no key needed)
    cd chatbot && python tests/dev_server.py --real   ->  http://localhost:8091/  (real Gemini, key from .env)

Never deploy this file.
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:8091")

import uvicorn  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

import app as chatapp  # noqa: E402

ANSWERS = {
    "search as a service": ("Search as a Service is our outsourced deal sourcing program. We build target lists from "
                            "your buy box and reach owners by phone, email, LinkedIn and handwritten mail. It starts at "
                            "$1,250/month plus a 2% success fee, and clients typically see 10 to 20 owner engagements "
                            "a month. Details: https://capraecapital.com/services/search-as-a-service/",
                            ["https://capraecapital.com/services/search-as-a-service/", "https://capraecapital.com/pricing/"]),
    "cost": ("Our main plans:\n- Search as a Service: $1,250/month + 2% success fee\n- Entrepreneurship as a Service: "
             "$1,000/month\n- Branding as a Service: $1,250/month\nAI-Readiness and Post-Acquisition Strategy are custom "
             "priced, and Tech Development is project-based.", ["https://capraecapital.com/pricing/"]),
}


class FakeGemini:
    async def classify(self, system, message, previous=""):
        m = message.lower()
        if any(w in m for w in ("weather", "recipe", "bitcoin")):
            return "OFF_TOPIC"
        if "should i buy" in m or "invest" in m:
            return "ADVICE"
        if m.strip(" !.") in ("hi", "hello", "hey", "thanks"):
            return "GREETING"
        return "ON_TOPIC"

    async def answer(self, system, history, message):
        m = message.lower()
        for key, (text, src) in ANSWERS.items():
            if key in m or (key == "cost" and ("price" in m or "much" in m)):
                return {"in_scope": True, "answer": text, "source_urls": src}
        if "invented" in m:  # demo: an answer with a made-up price gets replaced
            return {"in_scope": True, "answer": "It costs $777 a month.", "source_urls": []}
        return {"in_scope": True, "answer": "Hi! I can answer questions about Caprae Capital: our services, pricing, "
                                            "process and team. You can also book a call at https://capraecapital.com/contact/.",
                "source_urls": ["https://capraecapital.com/contact/"]}

    async def close(self):
        pass


if "--real" not in sys.argv:
    os.environ["GEMINI_API_KEY"] = "fake"
    chatapp.gemini = FakeGemini()
chatapp.app.mount("/", StaticFiles(directory=HERE.parent.parent / "site", html=True), name="site")

if __name__ == "__main__":
    uvicorn.run(chatapp.app, host="127.0.0.1", port=8091)
