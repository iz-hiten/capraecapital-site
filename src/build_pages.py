#!/usr/bin/env python3
"""
Builds every page of the main site from src/template.html.

The site used to be one index.html whose nav switched hidden "tabs". Each
section now has its own URL (/services/, /pricing/, /services/ai-readiness/ …)
so every page gets its own title, description, canonical and social tags,
and crawlers see only that page's content.

    python src/build_pages.py

Edit src/template.html (layout, copy, styles, scripts) and the PAGES table
below (URLs and meta), then re-run. Never edit the generated
site/**/index.html files by hand — the next build overwrites them.
Also regenerates site/sitemap.xml.
"""
import html
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "src" / "template.html"
SITE = ROOT / "site"
SITE_URL = "https://capraecapital.com"

# Heading promoted to the page's <h1> (the home hero already has one).
H1_SECTION_HEADING = r'<h2 class="(section-heading[^"]*)"([^>]*)>(.*?)</h2>'
H1_BRANDING = r'<h2 class="(branding-h1)"()>(.*?)</h2>'
H1_TESTIMONIALS = r'<h2 class="(fade-in-element)"()>(Client Testimonials)</h2>'

# nav       — nav item marked active
# section   — which <section id> the page shows
# card      — service pages: the single service card to show
PAGES = [
    {"path": "/", "section": "home", "nav": "home", "h1": None,
     "title": "Caprae Capital Services - End-to-End Private Equity Services",
     "description": "Completely white-labeled, fully outsourced private equity services. Search as a Service, deal sourcing, diligence, and execution support at 30-60% less than traditional providers.",
     "twitter_description": "Completely white-labeled, fully outsourced private equity services at 30-60% less than traditional providers.",
     "crumbs": [], "priority": "1.0"},

    {"path": "/services/", "section": "services", "nav": "services", "h1": H1_SECTION_HEADING,
     "title": "Private Equity Services | Deal Sourcing to Growth | Caprae",
     "description": "End-to-end private equity services, from deal sourcing to post-acquisition growth: Search as a Service, fractional ops, AI-readiness, and tech development.",
     "crumbs": [("Services", "/services/")], "priority": "0.9"},

    {"path": "/services/search-as-a-service/", "section": "services", "nav": "services",
     "card": "search-as-a-service", "name": "Search as a Service",
     "title": "Search as a Service | Deal Sourcing Starting at $1,250/mo",
     "description": "Complete deal sourcing tailored to your criteria. lead generation, email list cleansing, cold calling campaigns, and email automation. Starting at $1,250/mo.",
     "crumbs": [("Services", "/services/"), ("Search as a Service", None)], "priority": "0.8"},

    {"path": "/services/entrepreneurship-as-a-service/", "section": "services", "nav": "services",
     "card": "entrepreneurship-as-a-service", "name": "Entrepreneurship as a Service",
     "title": "Entrepreneurship | Fractional Ops for Founders | Capraecapital",
     "description": "Fractional operations for growth-stage entrepreneurs cold calling, LinkedIn outreach, social media management, and marketing support to scale your business faster.",
     "crumbs": [("Services", "/services/"), ("Entrepreneurship as a Service", None)], "priority": "0.8"},

    {"path": "/services/ai-readiness/", "section": "services", "nav": "services",
     "card": "ai-readiness", "name": "AI-Readiness as a Service",
     "title": "AI-Readiness | Tech Strategy & Due Diligence | Capraecapital",
     "description": "Prepare your business for the AI era technology due diligence, ROI optimization, AI-driven automation, and team training & adoption. Custom pricing.",
     "crumbs": [("Services", "/services/"), ("AI-Readiness", None)], "priority": "0.8"},

    {"path": "/services/tech-development/", "section": "services", "nav": "services",
     "card": "tech-development", "name": "Tech Development",
     "title": "Tech Development | MVP to Full-Stack Platforms | Capraecapital",
     "description": "From MVP to full-stack platforms built with modern frameworks digital marketing tools, project management, and quality assurance. Project-based pricing.",
     "crumbs": [("Services", "/services/"), ("Tech Development", None)], "priority": "0.8"},

    {"path": "/services/post-acquisition-strategy/", "section": "services", "nav": "services",
     "card": "post-acquisition-strategy", "name": "Post-Acquisition Strategy",
     "title": "Post-Acquisition Strategy | Growth Programs and Advisory",
     "description": "Scale acquired businesses with hands-on growth programs fractional CXO services, operational optimization, and performance metrics. Custom pricing.",
     "crumbs": [("Services", "/services/"), ("Post-Acquisition Strategy", None)], "priority": "0.8"},

    {"path": "/services/branding/", "section": "branding", "nav": "branding", "h1": H1_BRANDING,
     "service_name": "Branding as a Service",
     "title": "Branding as a Service | LinkedIn Ghostwriting for Finance",
     "description": "Become a category-defining voice in finance. 10 ghostwritten LinkedIn posts a month by an award-winning journalist, plus brand strategy. $1,250/mo.",
     "crumbs": [("Services", "/services/"), ("Branding", None)], "priority": "0.8"},

    {"path": "/how-it-works/", "section": "how", "nav": "how", "h1": H1_SECTION_HEADING,
     "title": "How It Works | 7-Step Deal Sourcing Process | Caprae Capital",
     "description": "A seven-step process refined through hundreds of deals: define your criteria, we source off-market deals and run outreach, and you meet owners by week 3.",
     "crumbs": [("How It Works", None)], "priority": "0.7"},

    {"path": "/results/", "section": "results", "nav": "results", "h1": H1_TESTIMONIALS,
     "title": "Results | $110M+ in Deals Closed | Caprae Capital",
     "description": "$110M+ in deals closed in 2026 YTD, $50M+ sourced and diligenced in 2025, and 10-20 owner engagements a month. See what our clients say.",
     "crumbs": [("Results", None)], "priority": "0.7"},

    {"path": "/pricing/", "section": "pricing", "nav": "pricing", "h1": H1_SECTION_HEADING,
     "title": "Pricing | Search as a Service from $1,250/mo | Caprae",
     "description": "Transparent pricing, 30-60% less than traditional providers. Search as a Service from $1,250/mo + 2% success fee, or custom plans for larger teams.",
     "crumbs": [("Pricing", None)], "priority": "0.7"},

    {"path": "/contact/", "section": "contact", "nav": "contact", "h1": H1_SECTION_HEADING,
     "title": "Contact Us | Caprae Capital Services",
     "description": "Tell us about your search, your business, or what you're working on. The Caprae Capital team gets back to you within 24 hours.",
     "crumbs": [("Contact", None)], "priority": "0.6"},
]

# Legal pages are built by site/scripts/build_legal_pages.py; listed here for the sitemap.
EXTRA_SITEMAP = [("/privacy/", "yearly", "0.3"), ("/terms/", "yearly", "0.3")]

SECTION_RE = re.compile(r'    <!-- [A-Z ]+ SECTION -->\n    <section id="(\w+)">\n(.*?)\n    </section>\n', re.S)
CARD_RE = re.compile(r'                <!--@card:([\w-]+)-->\n(.*?)                <!--@/card-->\n', re.S)


def attr(v):
    return html.escape(v, quote=True)


def head_meta(p):
    url = SITE_URL + p["path"]
    return "\n".join([
        f'    <title>{html.escape(p["title"], quote=False)}</title>',
        f'    <meta name="description" content="{attr(p["description"])}">',
        f'    <link rel="canonical" href="{url}">',
        f'    <meta property="og:type" content="website">',
        f'    <meta property="og:url" content="{url}">',
        f'    <meta property="og:title" content="{attr(p["title"])}">',
        f'    <meta property="og:description" content="{attr(p["description"])}">',
        f'    <meta name="twitter:title" content="{attr(p["title"])}">',
        f'    <meta name="twitter:description" content="{attr(p.get("twitter_description", p["description"]))}">',
    ])


def jsonld(obj):
    body = json.dumps(obj, indent=2, ensure_ascii=False).replace("\n", "\n    ")
    return f'    <script type="application/ld+json">\n    {body}\n    </script>'


def page_jsonld(p):
    blocks = []
    if p["crumbs"]:
        items = [{"@type": "ListItem", "position": 1, "name": "Home", "item": SITE_URL + "/"}]
        for i, (name, path) in enumerate(p["crumbs"], start=2):
            items.append({"@type": "ListItem", "position": i, "name": name,
                          "item": SITE_URL + (path or p["path"])})
        blocks.append(jsonld({"@context": "https://schema.org", "@type": "BreadcrumbList",
                              "itemListElement": items}))
    name = p.get("name") or p.get("service_name")
    if name:
        blocks.append(jsonld({
            "@context": "https://schema.org", "@type": "Service",
            "name": name, "description": p["description"], "url": SITE_URL + p["path"],
            "areaServed": "Worldwide",
            "provider": {"@type": "Organization", "name": "Caprae Capital", "url": SITE_URL + "/"},
        }))
    return "\n".join(blocks)


def promote_h1(section, pattern):
    new, n = re.subn(pattern, r'<h1 class="\1"\2>\3</h1>', section, count=1, flags=re.S)
    assert n == 1, f"no heading matching {pattern!r}"
    return new


def service_page(section, p):
    """The services section, narrowed to one card, headed by the service name."""
    cards = dict(CARD_RE.findall(section))
    card = cards[p["card"]]
    card = re.sub(r'\n *<a class="service-link"[^\n]*', "", card)  # no "Learn more" to itself
    start = section.index('            <div class="services-grid">')
    last = list(CARD_RE.finditer(section))[-1]
    grid_close = section.index("            </div>\n", last.end())
    new = (section[:start]
           + '            <div class="services-grid single">\n' + card
           + "            </div>\n"
           + '            <div class="service-page-ctas">\n'
           + '                <a href="/contact/" class="button-primary">Talk to us</a>\n'
           + '                <a href="/services/" class="button-secondary">All services</a>\n'
           + "            </div>\n"
           + section[grid_close + len("            </div>\n"):])
    new = re.sub(H1_SECTION_HEADING,
                 lambda m: f'<h1 class="{m.group(1)}"{m.group(2)}>{html.escape(p["name"], quote=False)}</h1>',
                 new, count=1, flags=re.S)
    new = re.sub(r'(<p class="section-subtitle[^"]*">)(.*?)(</p>)',
                 r"\1Part of Caprae Capital's end-to-end services, from deal sourcing to post-acquisition growth\3",
                 new, count=1, flags=re.S)
    return new


def build(p, sections, prefix, suffix):
    section = sections[p["section"]]
    if p.get("card"):
        section = service_page(section, p)
    elif p.get("h1"):
        section = promote_h1(section, p["h1"])
    # strip build markers left in the services grid
    section = re.sub(r" *<!--@/?card[^>]*-->\n", "", section)

    head = prefix.replace("    <!--@PAGE_META-->", head_meta(p), 1)
    jl = page_jsonld(p)
    head = head.replace("    <!--@PAGE_JSONLD-->\n", jl + "\n" if jl else "", 1)
    head = head.replace(f'data-nav="{p["nav"]}"', f'data-nav="{p["nav"]}" class="active"', 1)

    out = (head
           + f'    <section id="{p["section"]}" class="active">\n{section}\n    </section>\n'
           + suffix)
    assert "<!--@" not in out, f"unreplaced marker in {p['path']}"
    return out


def main():
    template = TEMPLATE.read_text(encoding="utf-8")
    matches = list(SECTION_RE.finditer(template))
    sections = {m.group(1): m.group(2) for m in matches}
    assert set(sections) == {"home", "services", "branding", "how", "results", "pricing", "contact"}, sections.keys()
    prefix, suffix = template[:matches[0].start()], template[matches[-1].end():]

    for p in PAGES:
        for field, limit in (("title", 60), ("description", 160)):
            if len(p[field]) > limit:
                print(f"  note: {p['path']} {field} is {len(p[field])} chars (> {limit})")
        out_file = SITE / p["path"].strip("/") / "index.html"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(build(p, sections, prefix, suffix), encoding="utf-8", newline="\n")
        print(f"wrote {out_file.relative_to(ROOT)}")

    today = date.today().isoformat()
    urls = [(p["path"], "weekly" if p["path"] == "/" else "monthly", p["priority"]) for p in PAGES] + EXTRA_SITEMAP
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, freq, prio in urls:
        sitemap += ["  <url>", f"    <loc>{SITE_URL}{path}</loc>", f"    <lastmod>{today}</lastmod>",
                    f"    <changefreq>{freq}</changefreq>", f"    <priority>{prio}</priority>", "  </url>"]
    sitemap.append("</urlset>")
    (SITE / "sitemap.xml").write_text("\n".join(sitemap) + "\n", encoding="utf-8", newline="\n")
    print("wrote site/sitemap.xml")


if __name__ == "__main__":
    main()
