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

# nav       — nav items marked active (a page inside Resources marks both)
# section   — which <section id> the page shows
# h1        — heading promoted to <h1>; None when the section already has its own <h1>
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

    {"path": "/services/", "section": "services-overview", "nav": ["services"], "h1": None,
     "title": "Our Services | Deal Sourcing to Post-Acquisition Growth",
     "description": "End-to-end coverage for every stage. Search as a Service, Entrepreneurship as a Service, AI-Readiness, Tech Development, and Post-Acquisition Strategy.",
     "crumbs": [("Services", "/services/")], "priority": "0.9"},

    {"path": "/services/search-as-a-service/", "section": "search-as-a-service", "nav": ["services"],
     "h1": None, "name": "Search as a Service",
     "title": "Search as a Service | Deal Sourcing Starting at $1,250/mo",
     "description": "Complete deal sourcing tailored to your criteria. lead generation, email list cleansing, cold calling campaigns, and email automation. Starting at $1,250/mo.",
     "crumbs": [("Services", "/services/"), ("Search as a Service", None)], "priority": "0.8"},

    {"path": "/services/entrepreneurship-as-a-service/", "section": "entrepreneurship-as-a-service", "nav": ["services"],
     "h1": None, "name": "Entrepreneurship as a Service",
     "title": "Entrepreneurship | Fractional Ops for Founders | Capraecapital",
     "description": "Fractional operations for growth-stage entrepreneurs cold calling, LinkedIn outreach, social media management, and marketing support to scale your business faster.",
     "crumbs": [("Services", "/services/"), ("Entrepreneurship as a Service", None)], "priority": "0.8"},

    {"path": "/services/ai-readiness/", "section": "ai-readiness", "nav": ["services"],
     "h1": None, "name": "AI-Readiness as a Service",
     "title": "AI-Readiness | Tech Strategy & Due Diligence | Capraecapital",
     "description": "Prepare your business for the AI era technology due diligence, ROI optimization, AI-driven automation, and team training & adoption. Custom pricing.",
     "crumbs": [("Services", "/services/"), ("AI-Readiness", None)], "priority": "0.8"},

    {"path": "/services/tech-development/", "section": "tech-development", "nav": ["services"],
     "h1": None, "name": "Tech Development",
     "title": "Tech Development | MVP to Full-Stack Platforms | Capraecapital",
     "description": "From MVP to full-stack platforms built with modern frameworks digital marketing tools, project management, and quality assurance. Project-based pricing.",
     "crumbs": [("Services", "/services/"), ("Tech Development", None)], "priority": "0.8"},

    {"path": "/services/post-acquisition-strategy/", "section": "post-acquisition-strategy", "nav": ["services"],
     "h1": None, "name": "Post-Acquisition Strategy",
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

    # Results and case studies share one page
    {"path": "/case-study/", "section": "case-study", "nav": ["resources", "case-study"], "h1": H1_SECTION_HEADING,
     "title": "Case Studies | Client Results with Caprae Capital",
     "description": "How clients used Caprae Capital: a $20M+ first acquisition in six months, two advanced meetings in two months, and 10-20 owner engagements a month.",
     "crumbs": [("Case Studies", None)], "priority": "0.7"},

    {"path": "/faq/", "section": "faq", "nav": ["resources", "faq"], "h1": H1_SECTION_HEADING,
     "title": "FAQ | Common Questions About Caprae Capital Services",
     "description": "Answers to common questions about Search as a Service, pricing, engagement timelines, and how Caprae Capital supports PE professionals.",
     "crumbs": [("FAQ", None)], "priority": "0.5"},

    {"path": "/blog/", "section": "blog", "nav": ["resources", "blog"], "h1": H1_SECTION_HEADING,
     "title": "Blog | Caprae Capital Services",
     "description": "",
     "crumbs": [("Blog", None)], "priority": "0.5"},
]

# Meta for /team/<slug>/ pages. Anyone not listed gets "<Name> | <Role> | Caprae Capital"
# and no description until one is written.
TEAM_META = {
    "kevin-hong": {
        "title": "Kevin Hong | Founder | Caprae Capital",
        "description": "Kevin Hong, Founder of Caprae Capital, scaled two startups to $31M and $7M ARR, raised $8M+ VC, and is a Chicago Booth MBA and Amazon bestselling author."},
    "hereford-johnson": {
        "title": "Hereford Johnson | Principal | Caprae Capital",
        "description": "Hereford Johnson, Principal at Caprae Capital, closed acquisitions in 11 and 6 months. Northwestern Kellogg MBA, former Deloitte Consulting."},
    "zackary-beckham": {
        "title": "Zackary Beckham | Founder | Caprae Capital",
        "description": "Zackary Beckham, Founder of Caprae Capital, is a self-funded searcher who closed an MSP, with 10+ years of tech and AI implementation experience."},
    "jeff-blacklock": {
        "title": "Jeff Blacklock | Deal Advisor | Caprae Capital",
        "description": "Jeff Blacklock, Deal Advisor at Caprae Capital, is a former searcher and President of ValWell Technologies in the oil and gas industry."},
    "mitchell-vermet": {
        "title": "Mitch Vermet, CFA, CAIA | Caprae Capital",
        "description": "Mitch Vermet, Capital Adviser at Caprae Capital, is Managing Partner at Bankers Edge, having helped manage $30B+ in institutional capital. CFA, CAIA."},
    "richard-consul": {
        "title": "Richard Consul, CFA | Caprae Capital",
        "description": "Richard Consul, Capital Adviser at Caprae Capital, is Founder and Managing Partner of Bankers Edge with 20+ years of buy-side experience. CFA."},
    "eric-nehrlich": {
        "title": "Eric Nehrlich | Executive Coach | Caprae Capital",
        "description": "Eric Nehrlich, Executive Coach at Caprae Capital, is a former Chief of Staff at Google who now prepares operators for the CEO seat. MIT, Columbia, Stanford."},
}

# Body of each /team/<slug>/ page: a short bio (from the person's meta description and
# facts already on the site) and their profile links.
TEAM_PROFILES = {
    "kevin-hong": {
        "bio": [
            "Kevin Hong is the Founder of Caprae Capital. Before founding the firm, he spent seven years as a business journalist, then scaled two startups to $31M and $7M in annual recurring revenue and raised more than $8M in venture capital.",
            'He holds an MBA from Chicago Booth and is the author of the Amazon bestseller <em>The Outlier Approach</em>. At Caprae he oversees <a href="/services/entrepreneurship-as-a-service/">Entrepreneurship as a Service</a> and reviews the firm\'s <a href="/services/search-as-a-service/">Search as a Service</a> work.',
        ],
        "links": [("LinkedIn", "https://www.linkedin.com/in/kevinhshong/"),
                  ("Searchfunder", "https://searchfunder.com/profile/kevin-hong")],
    },
    "hereford-johnson": {
        "bio": [
            "Hereford Johnson is a Principal at Caprae Capital. As a buyer, he closed acquisitions in 11 and 6 months, so he advises clients from first-hand experience of getting deals to close.",
            'He holds an MBA from Northwestern\'s Kellogg School of Management and previously worked at Deloitte Consulting. He reviews Caprae\'s <a href="/services/post-acquisition-strategy/">Post-Acquisition Strategy</a> work and brings a buyer\'s view to <a href="/services/search-as-a-service/">Search as a Service</a>.',
        ],
        "links": [("LinkedIn", "https://www.linkedin.com/in/hereford/")],
    },
    "zackary-beckham": {
        "bio": [
            "Zackary Beckham is a Founder of Caprae Capital. He is a self-funded searcher who acquired a managed IT services business (MSP), which he runs today.",
            'With more than 10 years of technology and AI implementation experience, he leads Caprae\'s <a href="/services/ai-readiness/">AI-Readiness</a> assessments and oversees <a href="/services/tech-development/">Tech Development</a>.',
        ],
        "links": [("LinkedIn", "https://www.linkedin.com/in/zackarybeckham/"),
                  ("Searchfunder", "https://searchfunder.com/profile/zackary-beckham")],
    },
    "jeff-blacklock": {
        "bio": [
            "Jeff Blacklock is a Deal Advisor at Caprae Capital. He is a former searcher and the President of ValWell Technologies, a company in the oil and gas industry.",
            'Jeff first worked with Caprae as a client, when the program secured two advanced meetings in Houston within two months. Read the <a href="/case-study/">Valwell case study</a>.',
        ],
        "links": [("LinkedIn", "https://www.linkedin.com/in/jeffblacklock/")],
    },
    "mitchell-vermet": {
        "bio": [
            "Mitch Vermet is a Capital Adviser at Caprae Capital. He is a Managing Partner at Bankers Edge and has helped manage more than $30B in institutional capital.",
            "He holds both the Chartered Financial Analyst (CFA) and Chartered Alternative Investment Analyst (CAIA) designations.",
        ],
        "links": [("LinkedIn", "https://www.linkedin.com/in/mitch-vermet-cfa-caia-5472b880/")],
    },
    "richard-consul": {
        "bio": [
            "Richard Consul is a Capital Adviser at Caprae Capital. He is the Founder and Managing Partner of Bankers Edge and brings more than 20 years of buy-side experience.",
            "He is a Chartered Financial Analyst (CFA) charterholder.",
        ],
        "links": [("LinkedIn", "https://www.linkedin.com/in/richard-consul-cfa/")],
    },
    "eric-nehrlich": {
        "bio": [
            "Eric Nehrlich is an Executive Coach at Caprae Capital. He is a former Chief of Staff at Google and now prepares operators for the CEO seat.",
            'He studied at MIT, Columbia and Stanford, and provides search fund CEO coaching as part of Caprae\'s <a href="/services/post-acquisition-strategy/">Post-Acquisition Strategy</a> service.',
        ],
        "links": [("LinkedIn", "https://www.linkedin.com/in/nehrlich/")],
    },
}

# <meta name="keywords"> per page, from the finalized SEO keyword sheet (2026-09-28).
# Only these pages get the tag. Exact duplicates are written once.
KEYWORDS = {
    "/": [
        "ETA", "entrepreneurship through acquisition", "private equity consulting services",
        "private equity consulting firms", "private equity due diligence consulting",
        "private equity outsourcing", "business broker lead generation", "private equity deal sourcing",
        "off market businesses for sale", "deal sourcing services", "buy side deal sourcing.",
        "off market deal sourcing", "independent sponsor deal sourcing", "lower middle market deal sourcing",
        "acquisition entrepreneur support services", "affordable private equity services",
        "white label private equity services", "white-labeled deal sourcing firm",
        "best outsourced private equity partner", "affordable private equity services",
        "independent sponsor services", "outsourced deal sourcing", "outsourced private equity analysts",
        "outsourced private equity services", "search fund services", "self funded search support",
        "sell side M&A advisory small business", "white label M&A services", "search fund support services",
        "outsourced M&A support",
    ],
    "/services/": [
        "sell side advisory", "buy side M&A advisory", "M&A due diligence services",
        "business acquisition consulting", "m&a deal advisory", "deal advisory services",
        "advisory services for mergers and acquisitions", "acquisition support services",
        "deal advisory for private equity", "acquisition advisory services", "deal structuring advisory",
        "M&A research services", "capital raising for independent sponsors",
        "best outsourced deal sourcing companies", "deal sourcing and advisory services",
        "what services do search fund providers offer", "white label PE service packages",
        "buy side advisory business", "buy side advisory small business", "financial modeling for acquisitions",
        "market research for acquisitions", "SBA acquisition advisory",
    ],
    "/services/search-as-a-service/": [
        "fractional CMO", "B2B lead generation agency", "appointment setting services",
        "outsourced lead generation", "outsourced sales and marketing", "search as a service", "outsourced SDR",
        "cold calling agency", "outsourced business development", "AI automation for small business",
        "outsourced cold calling", "LinkedIn outreach service", "proprietary deal flow", "fractional sales team",
        "cold calling business owners", "proprietary deal sourcing", "AI consulting for private equity",
        "acquisition target identification", "search fund deal sourcing", "handwritten letter marketing",
        "search as a service reviews", "search as a service vs in house sourcing", "business owner outreach",
        "buy box sourcing", "cold calling for search funds", "deal sourcing for search funds",
        "how to find off market businesses to buy", "off market business acquisition",
        "search fund lead generation", "search fund outsourcing", "entrepreneurship as a service",
        "fractional growth team", "outsourced linkedin services",
    ],
    "/services/entrepreneurship-as-a-service/": [  # "EaaS" in the sheet
        "fractional business development", "growth as a service", "outsourced business operations",
        "fractional operations support", "business growth consulting for acquisitions",
        "done for you business growth", "entrepreneurship as a service vs hiring in house",
        "fractional executive team", "fractional team vs full time hires",
        "growth support for small business owners", "outsourced growth strategy", "outsourced growth team",
        "outsourced operations for small business", "outsourced team for acquired business",
        "post acquisition growth support", "support for first time business owners",
        "support for new business acquirers", "turnkey business operations support",
        "what is entrepreneurship as a service",
    ],
    "/services/ai-readiness/": [
        "ai readiness assessment", "AI readiness audit", "AI enablement services", "AI readiness consulting",
        "AI implementation for small business", "AI readiness assessment tool", "small business AI consulting",
        "AI automation consulting for small business", "AI readiness checklist for business",
        "AI readiness assessment for businesses", "AI readiness consulting cost",
        "AI readiness for small business owners", "AI strategy consulting for acquired companies",
        "AI due diligence M&A", "AI for private equity portfolio companies",
        "technology due diligence for acquisitions",
    ],
    "/services/post-acquisition-strategy/": [  # sheet: /services/Post-acquisition-strategy
        "fractional COO", "buy and build strategy", "fractional CFO for small business",
        "value creation plan private equity", "fractional CXO services", "post acquisition integration strategy",
        "post acquisition strategy", "post acquisition value creation", "post acquisition integration consulting",
        "100 day plan after acquisition", "first 100 days after buying a business", "first time CEO coaching",
        "post acquisition support", "what to do after buying a business",
        "acquisition entrepreneur post close support", "business transition consulting after acquisition",
        "post acquisition growth strategy", "post acquisition leadership support", "add-on acquisition strategy",
        "growing a business after acquisition", "operational improvement after acquisition",
        "portfolio company operations support", "search fund CEO coaching", "search fund CEO support",
    ],
    "/services/branding/": [
        "social media management agency", "financial services marketing agency", "press release service",
        "personal branding agency", "LinkedIn content strategy", "executive branding", "newsletter writing service",
        "LinkedIn ghostwriter", "LinkedIn profile management", "m&a branding agency",
        "social media management for financial services", "founder branding", "outsourced CMO for small business",
        "PR for private equity firms", "branding as a service", "LinkedIn content management",
        "LinkedIn management service", "ghostwriter for executives", "LinkedIn ghostwriting service",
        "personal branding for finance professionals", "thought leadership ghostwriting",
        "private equity marketing services", "brand identity after acquisition",
        "brand messaging service for small business", "brand positioning service for acquired companies",
        "brand refresh service for acquired business", "brand strategy consulting for search funds",
        "branding agency for private equity portfolio companies", "branding service for acquisition entrepreneurs",
        "branding services for small business acquisitions", "B2B content marketing for finance",
        "LinkedIn ghostwriting for finance", "branding for search funds", "thought leadership for private equity",
    ],
    "/services/tech-development/": [
        "custom software development", "web app development", "MVP development", "AI app development",
        "CRM development", "SaaS development agency", "startup MVP development",
        "website development for small business", "full stack development agency", "startup website design",
        "website design for private equity firms", "website for search funds",
    ],
    "/pricing/": [
        "lead generation pricing", "M&A advisory fees", "buy side advisory fees", "M&A success fee",
        "deal sourcing pricing", "LinkedIn ghostwriting pricing", "search fund services pricing",
        "search fund cost", "outsourced deal sourcing cost", "outsourced cold calling pricing",
        "deal sourcing cost", "affordable deal sourcing", "affordable M&A advisory",
    ],
}

# Legal pages are built by site/scripts/build_legal_pages.py; listed here for the sitemap.
EXTRA_SITEMAP = [("/privacy/", "yearly", "0.3"), ("/terms/", "yearly", "0.3")]

SECTION_RE = re.compile(r'    <!-- [A-Z ]+ SECTION -->\n    <section id="([\w-]+)">\n(.*?)\n    </section>\n', re.S)
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
    keywords = list(dict.fromkeys(KEYWORDS.get(p["path"], [])))  # drop exact repeats, keep order
    if keywords:
        lines.append(f'    <meta name="keywords" content="{attr(", ".join(keywords))}">')
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
        person = {
            "@context": "https://schema.org", "@type": "Person",
            "name": m["alt"], "jobTitle": m["role"], "image": SITE_URL + m["img"],
            "url": SITE_URL + p["path"],
            "worksFor": {"@type": "Organization", "name": "Caprae Capital", "url": SITE_URL + "/"},
        }
        if p["description"]:
            person["description"] = p["description"]
        links = [url for _, url in TEAM_PROFILES.get(m["slug"], {}).get("links", [])]
        if links:
            person["sameAs"] = links
        blocks.append(jsonld(person))
    return "\n".join(blocks)


def promote_h1(section, pattern):
    new, n = re.subn(pattern, r'<h1 class="\1"\2>\3</h1>', section, count=1, flags=re.S)
    assert n == 1, f"no heading matching {pattern!r}"
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
    profile = TEAM_PROFILES.get(m["slug"])
    if profile:
        paras = "\n".join(f"                    <p>{p}</p>" for p in profile["bio"])
        links = "\n".join(f'                    <a href="{attr(url)}" target="_blank" rel="noopener">{e(label)} <span aria-hidden="true">&#8599;</span></a>'
                          for label, url in profile["links"])
        body = (f'                <div class="profile-bio">\n{paras}\n                </div>\n'
                f'                <div class="related-links" role="navigation" aria-label="{attr(m["alt"])} elsewhere">\n{links}\n                </div>\n')
    else:
        body = '                <p class="profile-note">Full profile coming soon.</p>\n'
    return f"""        <div class="container profile-section">
            <a class="profile-back" href="/team/">&larr; Meet our team</a>
            <div class="profile-card">
                <img src="{m['img']}" alt="{attr(m['alt'])}" class="profile-photo">
                <h1 class="profile-name">{e(m['name'])}</h1>
                <p class="profile-role">{e(m['role'])}</p>
{body}                <div class="service-page-ctas">
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
        if p.get("h1"):
            section = promote_h1(section, p["h1"])

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
    expected = {"home", "services-overview", "search-as-a-service", "entrepreneurship-as-a-service", "ai-readiness", "tech-development", "post-acquisition-strategy", "branding", "how", "pricing", "contact",
                "about", "team", "faq", "blog", "case-study"}
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
    unknown = set(KEYWORDS) - {p["path"] for p in pages}
    assert not unknown, f"KEYWORDS for pages that don't exist: {unknown}"
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
