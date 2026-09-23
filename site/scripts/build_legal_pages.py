#!/usr/bin/env python3
"""
Builds /privacy and /terms from the fragments produced by convert_legal.py.

Both pages share one template so the nav, footer and head stay identical to
each other and to the main site. Re-run after convert_legal.py.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent
LEGAL = SITE / "assets" / "legal"

SITE_URL = "https://capraecapital.com"

PAGES = [
    {"key": "privacy", "dir": "privacy", "title": "Privacy Policy",
     "eyebrow": "LEGAL",
     "desc": "How Caprae Capital collects, uses, and protects your personal information."},
    {"key": "terms", "dir": "terms", "title": "Terms & Conditions",
     "eyebrow": "LEGAL",
     "desc": "The legal terms governing your use of the Caprae Capital website and services."},
]

NAV_TABS = [("Home", "/"), ("Services", "/services/"), ("Branding", "/services/branding/"),
            ("How It Works", "/how-it-works/"), ("Results", "/results/"), ("Pricing", "/pricing/")]

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-JNPTWTS723"></script>
    <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', 'G-JNPTWTS723');
    </script>
    <title>{title} - Caprae Capital</title>
    <meta name="description" content="{desc}">
    <link rel="canonical" href="{site}/{dir}/">
    <meta name="robots" content="index, follow">
    <meta name="theme-color" content="#0A0A0A">
    <link rel="icon" type="image/png" href="/assets/logo/caprae-logo.png">

    <meta property="og:type" content="website">
    <meta property="og:url" content="{site}/{dir}/">
    <meta property="og:title" content="{title} - Caprae Capital">
    <meta property="og:description" content="{desc}">
    <meta property="og:image" content="{site}/assets/logo/caprae-logo.png">
    <meta property="og:site_name" content="Caprae Capital Services">

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="/assets/legal.css?v=2">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ background: #0A0A0A; color: #B0B0B0; font-family: 'Inter', sans-serif;
               -webkit-font-smoothing: antialiased; }}
        .site-nav {{ position: fixed; top: 0; left: 0; right: 0; z-index: 1000; background: rgba(10,10,10,.94);
              backdrop-filter: blur(10px); border-bottom: 1px solid #1F1F1F; }}
        .nav-container {{ max-width: 1240px; margin: 0 auto; padding: 16px 24px; display: flex;
              align-items: center; justify-content: space-between; gap: 24px; }}
        .logo {{ display: flex; align-items: center; gap: 10px; color: #FFFFFF; text-decoration: none;
              font-family: 'Cormorant Garamond', serif; font-size: 17px; letter-spacing: 2px; }}
        .logo-img {{ height: 28px; width: auto; }}
        .nav-links {{ display: flex; gap: 30px; list-style: none; }}
        .nav-links a {{ color: #E0E0E0; text-decoration: none; font-size: 13.5px; font-weight: 500;
              letter-spacing: .3px; transition: color .25s ease; }}
        .nav-links a:hover {{ color: #F9D360; }}
        .cta-button {{ background: #F9D360; color: #0A0A0A; padding: 9px 20px; text-decoration: none;
              font-size: 13px; font-weight: 700; letter-spacing: .4px; white-space: nowrap; }}
        .cta-button:hover {{ background: #FFFFFF; }}
        @media (max-width: 900px) {{ .nav-links {{ display: none; }} }}
    </style>
</head>
<body>
    <nav class="site-nav">
        <div class="nav-container">
            <a href="/" class="logo">
                <img src="/assets/logo/caprae-logo.png" alt="Caprae Capital" class="logo-img">
                CAPRAE CAPITAL
            </a>
            <ul class="nav-links">{navlinks}
            </ul>
            <a href="/contact/" class="cta-button">Contact Us</a>
        </div>
    </nav>

    <div class="legal-wrap">
        <div class="legal-container">
            <header class="legal-head">
                <p class="legal-eyebrow">{eyebrow}</p>
                <h1>{title}</h1>
                <p class="legal-sub">Caprae Capital LLC · <a href="/" style="color:#B0B0B0">capraecapital.com</a></p>
            </header>

            <div class="legal-layout">
                <aside class="legal-toc">
                    <div class="legal-toc-title">On this page</div>
                    <nav>{toc}
                    </nav>
                </aside>

                <article class="legal-doc">
{body}
                </article>
            </div>

            <div class="legal-foot">
                <span>&copy; <span id="yr">2026</span> Caprae Capital LLC</span>
                <a href="/privacy/">Privacy Policy</a>
                <a href="/terms/">Terms &amp; Conditions</a>
                <a href="mailto:partners@capraecapital.com">partners@capraecapital.com</a>
                <a href="/">← Back to Caprae Capital</a>
            </div>
        </div>
    </div>
    <script>document.getElementById('yr').textContent = new Date().getFullYear();</script>
</body>
</html>
"""


def main():
    navlinks = "".join(
        f'\n                <li><a href="{path}">{label}</a></li>' for label, path in NAV_TABS)
    for p in PAGES:
        body = (LEGAL / f"{p['key']}.html").read_text(encoding="utf-8")
        toc = json.loads((LEGAL / f"{p['key']}.toc.json").read_text(encoding="utf-8"))
        toc_html = "".join(
            f'\n                        <a href="#{t["id"]}">{t["text"]}</a>' for t in toc)
        out = TEMPLATE.format(title=p["title"], desc=p["desc"], dir=p["dir"],
                              eyebrow=p["eyebrow"], site=SITE_URL,
                              navlinks=navlinks, toc=toc_html, body=body)
        d = SITE / p["dir"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(out, encoding="utf-8", newline="\n")
        print(f"  {p['dir']}/index.html  {len(out):,} bytes | {len(toc)} toc entries")


if __name__ == "__main__":
    main()
