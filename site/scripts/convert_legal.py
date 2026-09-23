#!/usr/bin/env python3
"""
Termly HTML -> clean, theme-able HTML fragments for capraecapital.com.

Source of truth: the two documents in the repo root. This script NEVER edits
them. They arrive from Termly with a hardcoded light theme in !important inline
styles, which would render as a white Arial page inside the dark site.

Presentation is stripped; wording is preserved. The script then VERIFIES that
the visible text of the output equals the visible text of the source
(whitespace-normalised) and refuses to write anything on drift, so we can prove
the legal wording was not altered.

The two documents are NOT marked up the same way:
  - Privacy: heading classes sit on <span>
  - Terms:   heading classes sit on <div> wrapping a real <h2>, and Termly's own
             in-page TOC links point at ids like #ip, which must survive.

Usage:  python3 scripts/convert_legal.py [--check]
"""
import html
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent
ROOT = SITE.parent

DOCS = [
    ("privacy", ROOT / "Caprae Privacy Policy.txt", "Privacy Policy"),
    ("terms",   ROOT / "Caprae Terms and Conditions.txt", "Terms & Conditions"),
]

KEEP = {"div", "p", "ul", "ol", "li", "table", "thead", "tbody", "tr", "td", "th",
        "strong", "b", "em", "i", "u", "a", "br", "sup", "sub"}
VOID = {"br"}
ATTRS = {"a": {"href", "target", "rel"}, "td": {"colspan", "rowspan"}, "th": {"colspan", "rowspan"}}
HEADING_MAP = {"title": "h1", "heading_1": "h2", "heading_2": "h3"}

BLOCK = {"div", "p", "ul", "ol", "li", "table", "thead", "tbody", "tr", "td", "th",
         "h1", "h2", "h3", "h4", "h5", "h6", "br", "section", "article", "header",
         "footer", "blockquote", "hr"}


def slug(t):
    s = re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")
    return re.sub(r"-{2,}", "-", s)[:70] or "section"


class Converter(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.toc, self.stack = [], [], []
        self.skip = 0
        self._ids = set()
        self._h = None          # {"tag","buf","id"} while capturing a heading

    def _uid(self, base):
        s, n = base, 2
        while s in self._ids:
            s, n = f"{base}-{n}", n + 1
        self._ids.add(s)
        return s

    def emit(self, s):
        if self.skip == 0 and self._h is None:
            self.out.append(s)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        style = (a.get("style") or "").replace(" ", "").lower()

        if tag == "style" or "display:none" in style or "base64," in style:
            self.skip += 1
            self.stack.append(("__skip__", tag))
            return
        if self.skip:
            self.stack.append(("__skip__", tag))
            return

        # Inside a heading we keep only text, but remember Termly's anchor id.
        if self._h is not None:
            if a.get("id"):
                self._h["id"] = self._h["id"] or a["id"]
            self.stack.append((None, tag))
            return

        cls = a.get("data-custom-class", "")
        if cls in HEADING_MAP:
            self._h = {"tag": HEADING_MAP[cls], "buf": [], "id": a.get("id") or ""}
            self.stack.append(("__heading__", tag))
            return
        if cls == "subtitle":
            self.emit('<p class="legal-updated">')
            self.stack.append(("p", tag))
            return

        if tag not in KEEP:                       # span, bdt, font ... -> unwrap
            self.stack.append((None, tag))
            return

        kept = {k: v for k, v in a.items() if k in ATTRS.get(tag, set()) and v}
        if a.get("id"):                           # keep anchor targets
            kept["id"] = a["id"]
        if tag == "a" and kept.get("href", "").startswith("http"):
            kept.setdefault("target", "_blank")
            kept.setdefault("rel", "noopener")
        attr_s = "".join(f' {k}="{html.escape(v, quote=True)}"' for k, v in kept.items())

        self.emit(f"<{tag}{attr_s}>")
        self.stack.append((None if tag in VOID else tag, tag))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][1] != tag:
                continue
            for emitted, _ in reversed(self.stack[i:]):
                if emitted == "__skip__":
                    self.skip = max(0, self.skip - 1)
                elif emitted == "__heading__":
                    h, self._h = self._h, None
                    text = re.sub(r"\s+", " ", "".join(h["buf"])).strip()
                    if text:
                        hid = self._uid(h["id"] or slug(text))
                        self.out.append(f'<{h["tag"]} id="{hid}">{html.escape(text, quote=False)}</{h["tag"]}>')
                        if h["tag"] == "h2":
                            self.toc.append({"id": hid, "text": text})
                elif emitted and emitted not in VOID:
                    self.emit(f"</{emitted}>")
            del self.stack[i:]
            return

    def finish(self):
        """Termly's HTML leaves tags unclosed. Flush whatever is still open so
        the fragment is balanced -- otherwise the browser auto-nests it and the
        page layout collapses."""
        for emitted, _ in reversed(self.stack):
            if emitted == "__skip__":
                self.skip = max(0, self.skip - 1)
            elif emitted == "__heading__":
                self._h = None
            elif emitted and emitted not in VOID:
                self.out.append(f"</{emitted}>")
        self.stack.clear()

    def handle_data(self, data):
        # Always emit. Collapsing to a single space preserves word boundaries
        # that would otherwise be lost when the surrounding span is unwrapped.
        text = re.sub(r"\s+", " ", data)
        if not text:
            return
        if self._h is not None:
            self._h["buf"].append(text)
        elif self.skip == 0:
            self.out.append(html.escape(text, quote=False))


def visible_text(markup):
    """Text a reader sees. Block tags become a space, inline tags vanish -
    otherwise unwrapping an inline <span> would look like lost whitespace."""
    s = re.sub(r"<style[^>]*>.*?</style>", " ", markup, flags=re.S | re.I)
    s = re.sub(r"<(\w+)[^>]*style=\"[^\"]*display:\s*none[^\"]*\"[^>]*>.*?</\1>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<\s*(/?)(\w+)([^>]*)>", lambda m: " " if m.group(2).lower() in BLOCK else "", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def tidy(f):
    # Termly wraps headings in <strong>, which puts a block element inside an
    # inline one. Hoist the heading out.
    for h in ("h1", "h2", "h3"):
        f = re.sub(rf"<(strong|b|em|i)>\s*(<{h}[^>]*>.*?</{h}>)\s*</\1>", r"\2", f, flags=re.S)
    f = re.sub(r"<(div|p)[^>]*>\s*</\1>", "", f)
    # Runs of empty <div><br></div> spacers; vertical rhythm is the CSS's job.
    f = re.sub(r"(<div>\s*<br>\s*</div>\s*){2,}", "<div><br></div>", f)
    f = re.sub(r"(<br>\s*){3,}", "<br><br>", f)
    return re.sub(r"\s{2,}", " ", f).strip()


def main():
    check = "--check" in sys.argv
    outdir = SITE / "assets" / "legal"
    outdir.mkdir(parents=True, exist_ok=True)
    bad = 0
    for key, path, title in DOCS:
        raw = path.read_text(encoding="utf-8", errors="replace")
        c = Converter(); c.feed(raw); c.close(); c.finish()
        frag = tidy("".join(c.out))
        s_txt, o_txt = visible_text(raw), visible_text(frag)
        ok = s_txt == o_txt
        print(f"{key:8} {len(frag):>7,} bytes | {len(c.toc):>2} sections | parity: {'OK' if ok else 'MISMATCH'}")
        if not ok:
            bad += 1
            for i, (x, y) in enumerate(zip(s_txt, o_txt)):
                if x != y:
                    print(f"    diverges at char {i}\n      src: ...{s_txt[max(0,i-80):i+80]}...\n      out: ...{o_txt[max(0,i-80):i+80]}...")
                    break
            else:
                n = min(len(s_txt), len(o_txt))
                print(f"    length differs: src {len(s_txt)} vs out {len(o_txt)}\n      tail: ...{(s_txt if len(s_txt)>len(o_txt) else o_txt)[n:n+160]}...")
        elif not check:
            (outdir / f"{key}.html").write_text(frag, encoding="utf-8")
            (outdir / f"{key}.toc.json").write_text(json.dumps(c.toc, indent=1), encoding="utf-8")
    if bad:
        print(f"\nFAILED: {bad} document(s) diverged. Nothing written.")
        return 1
    print("\nAll documents match their source text exactly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
