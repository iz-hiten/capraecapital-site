# Site assistant (Gemini)

A chat widget on every page that answers questions **only** from `knowledge.md`.

## How it works

```
Browser widget (site/assets/chat/chat.js) → nginx /api/chat → app.py (127.0.0.1:8090) → Gemini API
```

**Files**

| File | What it does |
|---|---|
| `knowledge.md` | Everything the bot knows: the site's content, de-duplicated. Edit it when the site changes. |
| `app.py` | The API: limits, checks, the two Gemini calls, and output checks. |
| `guard.py` | Fixed rules that don't use AI: injection patterns, link, email and phone allow-lists, the number check, canned replies. |
| `prompts.py` | The classifier and answer instructions. |
| `gemini_client.py` | Calls the Gemini REST API. No tools, so it can't use the web; safety filters are on. |
| `llm.py` | Gemini first, DeepSeek as the backup. If Gemini fails, the same request goes to DeepSeek, and Gemini is skipped for 5 minutes. Safety blocks are never retried. |
| `pages.py` | The only pages and links the bot may show. |
| `usage.py` | Writes every AI call's token counts to `usage/YYYY-MM-DD.jsonl` (no visitor text). |
| `cost-alert/` | Node.js script: emails once a day when AI spend passes $1. It never stops the bot. Run `node cost-alert.js --dry-run` to see today's cost. |

**Security layers, in order** (any one of them can stop a message):
1. Only our domains can call the API (Origin check).
2. Message limits: size limit; 8 per minute and 60 per day per IP; 12 messages per chat; 2,000 a day site-wide.
3. Optional Cloudflare Turnstile bot check on the first message.
4. Pattern filter: obvious injection, "write code" and role-play attempts are refused before any AI call.
5. A separate Gemini classifier. Only `ON_TOPIC` and `GREETING` messages pass; off-topic, advice, injection and abuse get fixed replies.
6. The answer call:
   - Site content only, strict rules, and safety filters on.
   - Its JSON reply has three fields: `in_scope`, `answer` and `source_urls`.
   - Chat history is kept on the server, so the browser can't rewrite it.
7. Output checks before anything is shown:
   - Out-of-scope answers are replaced.
   - Leaking the instructions (caught by a secret marker), or replying with code, gets a refusal.
   - Any price or percentage not found in `knowledge.md` gets the "can't confirm" reply.
   - Unknown links, emails and phone numbers are removed.
   - Sources must be our own pages.
8. The widget shows replies as plain text. Only our own links become clickable.

If Gemini is down, DeepSeek answers instead, through the same checks. If both are down, the bot fails closed: visitors get a "temporarily unavailable" message, not an unchecked answer.

## Run locally

```bash
cd chatbot
pip install -r requirements.txt
python -m pytest -q tests        # 62 tests, no API key needed
python tests/dev_server.py       # site + API with a FAKE Gemini → http://localhost:8091/
```

With your key, to try real answers:
1. Put `GEMINI_API_KEY` in `.env`, and add `http://localhost:8091` to `ALLOWED_ORIGINS`.
2. Start the API with `uvicorn app:app --port 8090`.
3. Run `python redteam.py`. Every line should say PASS.

## Deploy (Ubuntu server)

```bash
cd /home/ubuntu/dev-caprae-site && git pull
cd chatbot && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env && nano .env            # paste GEMINI_API_KEY (use a PAID Gemini tier)
sudo cp ../deploy/caprae-chatbot.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now caprae-chatbot
sudo cp ../deploy/nginx-dev-caprae.saasquatchleads.com.conf /etc/nginx/sites-available/dev-caprae.saasquatchleads.com
sudo nginx -t && sudo systemctl reload nginx
curl https://dev-caprae.saasquatchleads.com/api/chat/health   # {"ok":true,...,"key_set":true}
```

**After deploying:**
- Logs are in `chatbot/chatbot.log`. They hold hashed IPs, with emails and phone numbers masked. Review flagged chats weekly.
- Set a budget alert in Google Cloud Billing.
- **Keep `knowledge.md` in sync with the site**: whenever page content changes, update it, then run `sudo systemctl restart caprae-chatbot`.
