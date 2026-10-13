"""Input and output checks for the site assistant.

Everything here is deterministic (no AI calls), so it can be unit-tested and
cannot be talked out of its rules.
"""
import re
import unicodedata

from pages import ALLOWED_EXTERNAL, CONTACT_EMAIL, CONTACT_PHONE, PAGES, SITE

# ---------------------------------------------------------------- canned replies
BOOK = "You can book a call or send a message through our Contact page."
REPLY_OFF_TOPIC = ("I can only help with questions about Caprae Capital: our services, pricing, "
                   "process and team. " + BOOK)
REPLY_INJECTION = ("I can't help with that. I'm here to answer questions about Caprae Capital's "
                   "services, pricing, process and team.")
REPLY_ADVICE = ("I can't give investment, legal, tax or accounting advice, and Caprae Capital doesn't "
                "provide it. For your situation, please speak with a licensed adviser. If you'd like "
                "to discuss how our services could support your search or deal, " + BOOK)
REPLY_UNSURE = ("I don't want to give you a wrong answer, and I couldn't confirm that from our website. "
                + BOOK)
REPLY_ERROR = "Sorry, the assistant is unavailable right now. Please try again shortly, or " \
              "email partners@capraecapital.com."
REPLY_LIMIT = "You've reached the limit for this chat. To keep talking, " + BOOK
REPLY_RATE = "You're sending messages too quickly. Please wait a moment and try again."

# ---------------------------------------------------------------- input checks
_CONTROL = re.compile(r"[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f​-‏‪-‮⁠-⁯﻿]")


def clean_message(text, max_chars):
    """Normalise visitor text. Returns (clean_text, error) where error is None when OK."""
    if not isinstance(text, str):
        return "", "empty"
    text = unicodedata.normalize("NFKC", text)
    text = _CONTROL.sub("", text)
    text = re.sub(r"[ \t]+", " ", text).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    if not text:
        return "", "empty"
    if len(text) > max_chars:
        return "", "too_long"
    return text, None


# Phrases that only appear in attempts to change the assistant's behaviour or to use
# it as a general-purpose AI. A match is refused before any AI call is made.
_INJECTION_PATTERNS = [
    r"\b(ignore|disregard|forget|override|bypass)\b.{0,40}\b(instruction|rule|prompt|guideline|polic|above|previous|prior|earlier|everything)",
    r"\b(system|developer|hidden|initial|original)\s+(prompt|message|instruction)",
    r"\b(reveal|show|print|repeat|output|display|leak|tell me)\b.{0,30}\b(your|the)\b.{0,15}\b(prompt|instructions|rules|guidelines|configuration)",
    r"\byou are now\b|\bfrom now on,? you\b|\bact as\b|\bpretend (to be|you)\b|\broleplay\b|\brole-play\b",
    r"\bjailbreak|\bDAN\b|\bdeveloper mode\b|\bgod mode\b|\bunfiltered\b|\buncensored\b",
    r"\bnew (instructions|rules|persona)\b|\bsimulate\b.{0,20}\b(ai|assistant|model|terminal)",
    r"<\s*/?\s*(system|assistant|site_content|visitor_message|instructions)\s*>",
    r"\[\s*(system|inst)\s*\]|###\s*(system|instruction)",
    r"```|\b(base64|rot13|hex encode|decode this)\b",
    r"\b(write|generate|create|give me|produce|debug|fix|complete)\b.{0,30}\b(code|script|program|function|sql|regex|html|css|javascript|python|java|c\+\+|essay|poem|song|story|joke|recipe|homework)\b",
    r"\b(translate|summari[sz]e)\b.{0,20}\b(this|the following|text|article)\b",
    r"\btranslat(e|ion)\b",
    r"\b(repeat|print|output|list|recite)\b.{0,30}\b(everything above|the above|your rules|rules you follow|instructions|marker)",
    r"\b(internal|secret|hidden)\s+(marker|code|token|key|word|instructions?)\b",
    r"\b(unrestricted|no (rules|restrictions|limits)|without (any )?(rules|restrictions|filters)|drop your|your restrictions)\b",
    r"\blet'?s play\b|\bplay a game\b",
    r"\b(what|which)\s+(ai\s+|language\s+|llm\s+)?model\s+(are you|is this|do you (use|run)|powers)\b|\bwho (made|built|created|trained|programmed) you\b",
    r"\b(hack|malware|exploit|phish|scam|ransomware|keylogger|ddos)\w*",
]
_INJECTION_RE = [re.compile(p, re.I | re.S) for p in _INJECTION_PATTERNS]

# Requests for advice the firm doesn't give: answered with the advice disclaimer, not by the AI.
_ADVICE_RE = [re.compile(p, re.I | re.S) for p in [
    r"\b(stock|crypto|bitcoin|share)\s*(tips?|picks?|recommendations?)\b|\bwhat should i invest\b|\bwhich stocks?\b",
    r"\b(valuation|ebitda)\s+multiple\b|\bwhat is .{0,30}\bworth\b|\bhow much is my (business|company) worth\b",
    r"\b(my|our) (taxes|tax return|tax bill)\b|\bstructure my taxes\b|\btax (advice|planning)\b",
    r"\blegally binding\b|\breview (my|this|the) (loi|contract|agreement|nda)\b|\blegal advice\b",
    r"\bshould i (buy|sell|acquire|invest in) (this|that|a|an|the|my) (business|company|stock|deal|shares?)\b",
]]

_ABUSE_RE = re.compile(r"\b(stupid|idiot|useless|dumb|moron|shut up|f+u+c+k\w*|sh[i1]t\w*|bitch\w*)\b|"
                       r"\b(home address|personal (phone|number|email|address)|where does \w+ live)\b", re.I)

_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})


def _variants(text):
    """The message, plus a copy with leetspeak undone and s p a c e d letters joined."""
    flat = text.lower().translate(_LEET)
    flat = re.sub(r"\b(\w) (?=\w\b)", r"\1", flat)
    return (text, flat)


def prefilter(text):
    """Fixed-rule check before any AI call. Returns None, 'INJECTION', 'ADVICE' or 'ABUSE'."""
    for t in _variants(text):
        if any(r.search(t) for r in _INJECTION_RE):
            return "INJECTION"
    if _ABUSE_RE.search(text):
        return "ABUSE"
    if any(r.search(text) for r in _ADVICE_RE):
        return "ADVICE"
    return None


def looks_like_injection(text):
    return prefilter(text) == "INJECTION"


# ---------------------------------------------------------------- output checks
_URL_RE = re.compile(r"https?://[^\s<>\"')\]]+|\bwww\.[^\s<>\"')\]]+", re.I)
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
_CODE_RE = re.compile(r"```|<\s*script|\bdef \w+\(|\bfunction\s*\w*\s*\(|\bconsole\.log|\bimport \w+|;\s*}\s*$|SELECT .+ FROM", re.I | re.M)
_NUMBER_RE = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?(?:\s?[KMB]\b)?\+?|\b\d+(?:\.\d+)?\s?%|\b\d{1,3}(?:,\d{3})+\b")


def _norm_url(url):
    url = url.rstrip(".,;:!?")
    if url.lower().startswith("www."):
        url = "https://" + url
    return url


def url_allowed(url):
    u = _norm_url(url)
    if u.startswith(SITE + "/") or u == SITE:
        path = u[len(SITE):] or "/"
        path = path.split("#")[0].split("?")[0]
        return path in PAGES
    return any(u == a or u.startswith(a) for a in ALLOWED_EXTERNAL)


_LINK = (r"(?:https?://|www\.)[^\s<>\"')\]]*[^\s<>\"')\].,;:!?]"          # full URL, minus trailing punctuation
         r"|(?<![\w@.])/(?:[a-z0-9-]+/)+")                                    # bare site path like /pricing/
_LINK_PHRASE_RE = re.compile(
    r"(?:[ \t]*\b(?:at|via|on|see|visit|here|details|more details|learn more|read more|more info)\b[ \t]*:?)?"
    r"[ \t]*\(?(?:" + _LINK + r")\)?"
    r"(?:[ \t]+for (?:more|details|full details|more details|more information)\b)?", re.I)


def strip_all_links(text):
    """Answers carry no links at all: remove every URL or site path with its joining words, then tidy up."""
    text = _LINK_PHRASE_RE.sub("", text)
    text = re.sub(r"[ \t]+([.,;:!?])", r"\1", text)              # space before punctuation
    text = re.sub(r"([.!?])[ \t]*[.,;:]+", r"\1", text)           # "month.." / "month.:" leftovers
    text = re.sub(r",[ \t]*(or|and)?[ \t]*([.!?])", r"\2", text)   # ", or ." leftovers
    text = re.sub(r"(^|[.!?][ \t]+|\n)[ \t]*[,;][ \t]*(?:(?:or|and)[ \t]+)?(\w)",   # ", or book..." at a sentence start
                  lambda m: m.group(1) + m.group(2).upper(), text)
    text = re.sub(r"([.!?][ \t]+)(and|or)[ \t]+(\w)", lambda m: m.group(1) + m.group(3).upper(), text)
    text = re.sub(r":[ \t]*$", ".", text.strip())                  # dangling "Details:" at the end
    text = "\n".join(l.rstrip() for l in text.split("\n"))
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def strip_unknown_links(text):
    """Remove any URL, email or phone number that isn't one of ours."""
    text = _URL_RE.sub(lambda m: m.group(0) if url_allowed(m.group(0)) else "", text)
    text = _EMAIL_RE.sub(lambda m: m.group(0) if m.group(0).lower() == CONTACT_EMAIL else "", text)
    text = _PHONE_RE.sub(_keep_our_phone, text)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def _digits(s):
    return re.sub(r"\D", "", s)


def _keep_our_phone(m):
    digits = _digits(m.group(0))
    if len(digits) < 10:          # not a phone number (e.g. "2025-2026")
        return m.group(0)
    return m.group(0) if digits == _digits(CONTACT_PHONE) else ""


def looks_like_code(text):
    return bool(_CODE_RE.search(text))


def _norm_num(s):
    return s.replace(" ", "").replace(",", "").rstrip("+")


def unverified_numbers(answer, knowledge):
    """Money amounts, percentages and large numbers in the answer that don't appear in the knowledge."""
    known = {_norm_num(m) for m in _NUMBER_RE.findall(knowledge)}
    known_text = knowledge.replace(",", "")
    bad = []
    for m in _NUMBER_RE.findall(answer):
        n = _norm_num(m)
        if n not in known and n not in known_text:
            bad.append(m)
    return bad


def clean_sources(urls):
    """Keep only our own page URLs, de-duplicated, max 3, as (title, url)."""
    out, seen = [], set()
    for u in urls or []:
        if not isinstance(u, str):
            continue
        u = _norm_url(u.strip())
        if u.startswith("/"):
            u = SITE + u
        if not u.startswith(SITE):
            continue
        path = (u[len(SITE):] or "/").split("#")[0].split("?")[0]
        if not path.endswith("/"):
            path += "/"
        if path in PAGES and path not in seen:
            seen.add(path)
            out.append({"title": PAGES[path], "url": SITE + path})
    return out[:3]


def trim(text, limit):
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind(".\n"))
    return (cut[:end + 1] if end > limit // 2 else cut.rstrip() + "...")


_MASK_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_MASK_PHONE = re.compile(r"\+?\d[\d\s().-]{7,}\d")


def mask_pii(text):
    """For logs only: hide emails and phone numbers visitors type."""
    return _MASK_PHONE.sub("[phone]", _MASK_EMAIL.sub("[email]", text or ""))
