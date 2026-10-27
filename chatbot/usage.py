"""Record token usage of every AI call, one JSON line per call, in a daily file.

    chatbot/usage/2026-10-13.jsonl   (UTC date)

After each AI call, cost-alert/cost-alert.js is started in the background: it adds up the day's spend
and emails an alert once if it passes the limit.
Only token counts are stored, never visitor text. Recording can never break a chat.
"""
import json
import os
import subprocess
import time
from pathlib import Path

USAGE_DIR = Path(os.environ.get("USAGE_DIR") or Path(__file__).resolve().parent / "usage")


COST_ALERT = Path(__file__).resolve().parent / "cost-alert" / "cost-alert.js"
_check = None   # the running `node cost-alert.js`, if any


def record(provider, model, step, input_tokens=0, cached_tokens=0, output_tokens=0):
    try:
        USAGE_DIR.mkdir(parents=True, exist_ok=True)
        line = {"ts": int(time.time()), "provider": provider, "model": model, "step": step,
                "input": int(input_tokens or 0), "cached": int(cached_tokens or 0), "output": int(output_tokens or 0)}
        day = time.strftime("%Y-%m-%d", time.gmtime())
        with open(USAGE_DIR / f"{day}.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(line) + "\n")
        _start_cost_check(day)
    except Exception:
        pass


def _start_cost_check(day):
    """Run the JS cost check in the background after each AI call. It adds up today's spend and emails
    once if it is over the limit. Nothing runs between requests; nothing waits for it. Skipped when a
    check is already running or today's alert has already been sent."""
    global _check
    if os.environ.get("COST_ALERT", "on").lower() == "off" or not COST_ALERT.exists():
        return
    if (USAGE_DIR / f".cost-alert-sent-{day}").exists():
        return
    if _check is not None and _check.poll() is None:
        return
    env = {**os.environ, "USAGE_DIR": str(USAGE_DIR)}
    _check = subprocess.Popen([os.environ.get("NODE_BIN", "node"), str(COST_ALERT)], cwd=str(COST_ALERT.parent),
                              env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def from_gemini(model, step, meta):
    """Gemini usageMetadata: thinking tokens are billed as output."""
    meta = meta or {}
    record("gemini", model, step, meta.get("promptTokenCount"), meta.get("cachedContentTokenCount"),
           (meta.get("candidatesTokenCount") or 0) + (meta.get("thoughtsTokenCount") or 0))


def from_deepseek(model, step, usage):
    """DeepSeek usage: completion_tokens already include reasoning tokens."""
    usage = usage or {}
    record("deepseek", model, step, usage.get("prompt_tokens"), usage.get("prompt_cache_hit_tokens"),
           usage.get("completion_tokens"))
