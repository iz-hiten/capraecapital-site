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

Team member pages (/team/<name>/) are generated from the team block on the
home page: add, remove or rename someone there and their page follows.
Their meta lives in TEAM_META.
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

# nav       — nav items marked active (a page inside Resources marks both)
# section   — which <section id> the page shows
# card      — service pages: the single service card to show
# description may be "" — the description tags are then left out
PAGES = [
    {"path": "/", "section": "home", "nav": ["home"], "h1": None,
     "title": "Caprae Capital Services | End-to-End Private Equity Services",
     "description": "White-labeled, fully outsourced PE services deal sourcing, diligence & execution at 30-60% less than traditional providers. $110M+ deals closed.",
     "crumbs": [], "priority": "1.0"},

    {"path": "/about/", "section": "about", "nav": ["about"], "h1": H1_SECTION_HEADING,
     "title": "About Caprae Capital | Operators Who've Been in Your Shoes",
     "description": "Meet the team behind Caprae Capital deep expertise across private equity, startups, and transaction management, built to support searchers and PE firms.",
     "crumbs": [("About", None)], "priority": "0.8"},

    {"path": "/services/", "section": "services", "nav": ["services"], "h1": H1_SECTION_HEADING,
     "title": "Our Services | Deal Sourcing to Post-Acquisition Growth",
     "description": "End-to-end coverage for every stage. Search as a Service, Entrepreneurship as a Service, AI-Readiness, Tech Development, and Post-Acquisition Strategy.",
     "crumbs": [("Services", "/services/")], "priority": "0.9"},

    {"path": "/services/search-as-a-service/", "section": "services", "nav": ["services"],
     "card": "search-as-a-service", "name": "Search as a Service",
     "title": "Search as a Service | Deal Sourcing Starting at $1,250/mo",
     "description": "Complete deal sourcing tailored to your criteria. lead generation, email list cleansing, cold calling campaigns, and email automation. Starting at $1,250/mo.",
     "crumbs": [("Services", "/services/"), ("Search as a Service", None)], "priority": "0.8"},

    {"path": "/services/entrepreneurship-as-a-service/", "section": "services", "nav": ["services"],
     "card": "entrepreneurship-as-a-service", "name": "Entrepreneurship as a Service",
     "title": "Entrepreneurship | Fractional Ops for Founders | Capraecapital",
     "description": "Fractional operations for growth-stage entrepreneurs cold calling, LinkedIn outreach, social media management, and marketing support to scale your business faster.",
     "crumbs": [("Services", "/services/"), ("Entrepreneurship as a Service", None)], "priority": "0.8"},

    {"path": "/services/ai-readiness/", "section": "services", "nav": ["services"],
     "card": "ai-readiness", "name": "AI-Readiness as a Service",
     "title": "AI-Readiness | Tech Strategy & Due Diligence | Capraecapital",
     "description": "Prepare your business for the AI era technology due diligence, ROI optimization, AI-driven automation, and team training & adoption. Custom pricing.",
     "crumbs": [("Services", "/services/"), ("AI-Readiness", None)], "priority": "0.8"},

    {"path": "/services/tech-development/", "section": "services", "nav": ["services"],
     "card": "tech-development", "name": "Tech Development",
     "title": "Tech Development | MVP to Full-Stack Platforms | Capraecapital",
     "description": "From MVP to full-stack platforms built with modern frameworks digital marketing tools, project management, and quality assurance. Project-based pricing.",
     "crumbs": [("Services", "/services/"), ("Tech Development", None)], "priority": "0.8"},

    {"path": "/services/post-acquisition-strategy/", "section": "services", "nav": ["services"],
     "card": "post-acquisition-strategy", "name": "Post-Acquisition Strategy",
     "title": "Post-Acquisition Strategy | Growth Programs and Advisory",
     "description": "Scale acquired businesses with hands-on growth programs fractional CXO services, operational optimization, and performance metrics. Custom pricing.",
     "crumbs": [("Services", "/services/"), ("Post-Acquisition Strategy", None)], "priority": "0.8"},

    {"path": "/services/branding/", "section": "branding", "nav": ["branding"], "h1": H1_BRANDING,
     "service_name": "Branding as a Service",
     "title": "Branding as a Service | LinkedIn Ghostwriting for Finance",
     "description": "Turn finance professionals into category-defining voices on LinkedIn. Ghostwritten content by an award-winning journalist. $1,250/month.",
     "crumbs": [("Services", "/services/"), ("Branding", None)], "priority": "0.8"},

    {"path": "/how-it-works/", "section": "how", "nav": ["how"], "h1": H1_SECTION_HEADING,
     "title": "How It Works | Caprae Capital's 7-Step Process",
     "description": "A proven, seven-step methodology from defining your criteria to sourcing, outreach, and connecting you with off-market deal opportunities.",
     "crumbs": [("How It Works", None)], "priority": "0.7"},

    {"path": "/pricing/", "section": "pricing", "nav": ["pricing"], "h1": H1_SECTION_HEADING,
     "title": "Pricing | Transparent, Value-Driven PE Services",
     "description": "Search as a Service from $1,250/mo, Entrepreneurship as a Service from $1,000/mo — 30-60% less than traditional advisors. See full pricing.",
     "crumbs": [("Pricing", None)], "priority": "0.7"},

    {"path": "/contact/", "section": "contact", "nav": ["contact"], "h1": H1_SECTION_HEADING,
     "title": "Contact Caprae Capital | Get Started Today",
     "description": "Tell us what you're working on we'll get back to you within 24 hours. Reach out to discuss deal sourcing, branding, or PE support.",
     "crumbs": [("Contact", None)], "priority": "0.6"},

    # ── Resources ──
    {"path": "/team/", "section": "team", "nav": ["resources", "team"], "h1": None,
     "title": "Meet Our Team | Kevin Hong, Hereford Johnson & More",
     "description": "Get to know Caprae Capital founders, principal advisers, deal advisers, and capital advisors driving results across $110M+ in closed deals.",
     "crumbs": [("Our Team", None)], "priority": "0.7"},

    {"path": "/results/", "section": "results", "nav": ["resources", "results"], "h1": H1_TESTIMONIALS,
     "title": "Our Results | $110M+ in Deals Closed",
     "description": "See the numbers behind Caprae Capital $110M+ deals closed, 8 countries serviced, and 10-20 engagements per month for our clients.",
     "crumbs": [("Results", None)], "priority": "0.7"},

    {"path": "/case-study/", "section": "case-study", "nav": ["resources", "case-study"], "h1": H1_SECTION_HEADING,
     "title": "Case Studies | Client Results with Caprae Capital",
     "description": "How clients used Caprae Capital: a $20M+ first acquisition in six months, two advanced meetings in two months, and 10-20 owner engagements a month.",
     "crumbs": [("Case Studies", None)], "priority": "0.7"},

    {"path": "/faq/", "section": "faq", "nav": ["resources", "faq"], "h1": H1_SECTION_HEADING,
     "title": "FAQ | Common Questions About Caprae Capital Services",
     "description": "Answers to common questions about Search as a Service, pricing, engagement timelines, and how Caprae Capital supports PE professionals.",
     "crumbs": [("FAQ", None)], "priority": "0.5"},
]

# Meta for /team/<slug>/ pages. Anyone not listed gets "<Name> | <Role> | Caprae Capital"
# and no description until one is written.
TEAM_META = {
    "kevin-hong": {"title": "Kevin Hong | Founder | Caprae Capital", "description": ""},
}

# Legal pages are built by site/scripts/build_legal_pages.py; listed here for the sitemap.
EXTRA_SITEMAP = [("/privacy/", "yearly", "0.3"), ("/terms/", "yearly", "0.3")]

SECTION_RE = re.compile(r'    <!-- [A-Z ]+ SECTION -->\n    <section id="([\w-]+)">\n(.*?)\n    </section>\n', re.S)
CARD_RE = re.compile(r'                <!--@card:([\w-]+)-->\n(.*?)                <!--@/card-->\n', re.S)
TEAM_RE = re.compile(r'        <!--@team-->\n(.*?)        <!--@/team-->\n', re.S)
MEMBER_RE = re.compile(
    r'<h3 class="team-subgroup-heading[^"]*">(?P<group>.*?)</h3>'
    r'|<a class="team-member-link" href="/team/(?P<slug>[a-z-]+)/">\s*'
    r'<img src="(?P<img>[^"]+)" alt="(?P<alt>[^"]+)" class="member-photo">\s*'
    r'<h4>(?P<name>.*?)</h4>(?:\s*<p>(?P<role>.*?)</p>)?', re.S)


def attr(v):
    # attributes are double-quoted, so apostrophes can stay as-is
    return html.escape(v, quote=False).replace('"', "&quot;")


def head_meta(p):
    url = SITE_URL + p["path"]
    desc = p["description"]
    lines = [f'    <title>{html.escape(p["title"], quote=False)}</title>']
    if desc:
        lines.append(f'    <meta name="description" content="{attr(desc)}">')
    lines += [
        f'    <link rel="canonical" href="{url}">',
        f'    <meta property="og:type" content="{p.get("og_type", "website")}">',
        f'    <meta property="og:url" content="{url}">',
        f'    <meta property="og:title" content="{attr(p["title"])}">',
    ]
    if desc:
        lines.append(f'    <meta property="og:description" content="{attr(desc)}">')
    lines.append(f'    <meta name="twitter:title" content="{attr(p["title"])}">')
    if desc:
        lines.append(f'    <meta name="twitter:description" content="{attr(desc)}">')
    return "\n".join(lines)


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
    if p.get("person"):
        m = p["person"]
        blocks.append(jsonld({
            "@context": "https://schema.org", "@type": "Person",
            "name": m["alt"], "jobTitle": m["role"], "image": SITE_URL + m["img"],
            "url": SITE_URL + p["path"],
            "worksFor": {"@type": "Organization", "name": "Caprae Capital", "url": SITE_URL + "/"},
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


def team_members(block):
    """(slug, img, alt, name, role) for everyone in the team block, in page order.
    Someone without a role line takes their subgroup heading (e.g. Capital Advisor)."""
    members, group = [], None
    for m in MEMBER_RE.finditer(block):
        if m.group("group"):
            group = html.unescape(m.group("group")).strip()
            continue
        role = html.unescape(m.group("role") or group or "").strip()
        members.append({"slug": m.group("slug"), "img": m.group("img"), "alt": m.group("alt"),
                        "name": html.unescape(m.group("name")).strip(), "role": role})
    return members


def profile_section(m):
    e = lambda v: html.escape(v, quote=False)
    return f"""        <div class="container profile-section">
            <a class="profile-back" href="/team/">&larr; Meet our team</a>
            <div class="profile-card">
                <img src="{m['img']}" alt="{attr(m['alt'])}" class="profile-photo">
                <h1 class="profile-name">{e(m['name'])}</h1>
                <p class="profile-role">{e(m['role'])}</p>
                <p class="profile-note">Full profile coming soon.</p>
                <div class="service-page-ctas">
                    <a href="/contact/" class="button-primary">Talk to our team</a>
                </div>
            </div>
        </div>"""


def profile_pages(members):
    pages = []
    for m in members:
        meta = TEAM_META.get(m["slug"], {})
        pages.append({
            "path": f"/team/{m['slug']}/", "section": "team-profile", "nav": ["resources", "team"],
            "html": profile_section(m), "person": m, "og_type": "profile",
            "title": meta.get("title", f"{m['name']} | {m['role']} | Caprae Capital"),
            "description": meta.get("description", ""),
            "crumbs": [("Our Team", "/team/"), (m["alt"], None)], "priority": "0.5",
        })
    return pages


def build(p, sections, prefix, suffix):
    if "html" in p:
        section = p["html"]
    else:
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
    for key in p["nav"]:
        marker = f'data-nav="{key}"'
        assert marker in head, f"no nav item {marker} for {p['path']}"
        head = head.replace(marker, f'{marker} class="active"', 1)

    out = (head
           + f'    <section id="{p["section"]}" class="active">\n{section}\n    </section>\n'
           + suffix)
    assert "<!--@" not in out, f"unreplaced marker in {p['path']}"
    return out


def main():
    template = TEMPLATE.read_text(encoding="utf-8")
    matches = list(SECTION_RE.finditer(template))
    sections = {m.group(1): m.group(2) for m in matches}
    expected = {"home", "services", "branding", "how", "results", "pricing", "contact",
                "about", "team", "faq", "case-study"}
    assert set(sections) == expected, sorted(sections)
    prefix, suffix = template[:matches[0].start()], template[matches[-1].end():]

    # The team block is written once, on the home page; /team/ reuses it with its own <h1>.
    team = TEAM_RE.search(sections["home"])
    assert team, "team block markers missing from the home section"
    block = team.group(1)
    sections["home"] = TEAM_RE.sub(lambda m: m.group(1), sections["home"])
    team_block = re.sub(r'<h2 class="(team-heading[^"]*)">.*?</h2>',
                        r'<h1 class="\1">Meet Our Team</h1>', block, count=1, flags=re.S)
    assert sections["team"].strip() == "<!--@TEAM_BLOCK-->", "team section should hold only the placeholder"
    sections["team"] = team_block.rstrip("\n")

    pages = PAGES + profile_pages(team_members(block))
    for p in pages:
        if not p["description"]:
            print(f"  note: {p['path']} has no meta description")
        for field, limit in (("title", 60), ("description", 160)):
            if len(p[field]) > limit:
                print(f"  note: {p['path']} {field} is {len(p[field])} chars (> {limit})")
        out_file = SITE / p["path"].strip("/") / "index.html"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(build(p, sections, prefix, suffix), encoding="utf-8", newline="\n")
        print(f"wrote {out_file.relative_to(ROOT)}")

    today = date.today().isoformat()
    urls = [(p["path"], "weekly" if p["path"] == "/" else "monthly", p["priority"]) for p in pages] + EXTRA_SITEMAP
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
