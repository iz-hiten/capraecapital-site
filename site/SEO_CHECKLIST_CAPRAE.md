# Caprae Capital Services — SEO Readiness Checklist

Compulsory SEO elements for a production website. Status reflects the current state of `capraecapital.com` as of 2026-07-08.

---

## 1. Core Meta (in `<head>`)

| Element | Status | Impact |
|---|---|---|
| `<title>` (unique per page, ≤ 60 chars) | Present — home 58 chars; Field Notes posts have unique titles | High. Truncated in SERPs; every page shows the same snippet. |
| `<meta name="description">` (≤ 155 chars, unique) | Present — unique per Field Notes post | High. Directly affects CTR from search results. |
| `<meta charset="UTF-8">` | Present | Critical. Encoding correctness. |
| `<meta name="viewport">` | Present | Critical. Mobile-friendliness ranking factor. |
| `<html lang="en">` | Present | Medium. Signals language to Google. |
| `<link rel="canonical">` | Present — self-referential per page | High. Prevents duplicate-content penalty on aliased routes. |
| `<meta name="robots">` (per-page index/noindex) | Present (`index, follow, max-image-preview:large`) | High. Auth/checkout pages should be `noindex`. |
| `<meta name="theme-color">` | Present (`#0A0A0A`) | Low. Mobile browser chrome color. |
| `<meta name="keywords">` | Absent (correct) | None. Deprecated by Google — do not add. |

## 2. Social & Sharing (Open Graph + Twitter Card)

| Element | Status | Impact |
|---|---|---|
| `og:title` | Present | High. Controls LinkedIn / Slack / iMessage / FB preview title. |
| `og:description` | Present | High. Preview subtitle. |
| `og:image` (1200×630 PNG) | Partial — uses 400×410 logo, not a 1200×630 share image | High. Small square logo renders as a cramped thumbnail on LinkedIn/Slack. |
| `og:url` | Present | Medium. Canonical share URL. |
| `og:type` (`website` / `article` / `product`) | Present — `website` on home, `article` on Field Notes posts | Medium. |
| `og:site_name` | Present | Low. |
| `twitter:card` (`summary_large_image`) | Present — but paired with a square logo image | High. `summary_large_image` expects a wide image; supply a 1200×630. |
| `twitter:title` / `twitter:description` / `twitter:image` | Present | High. |

## 3. Crawl & Indexing

| Element | Status | Impact |
|---|---|---|
| `robots.txt` | Present (`Allow: /`, points to sitemap) | Critical. Controls crawlers and points to sitemap. |
| `sitemap.xml` | Present — homepage only (correct; this is a single-page site, all sections are `#anchor` routes) | Critical. Should list only canonical URLs of this site. |
| Field Notes on this domain | Mirror only — `sync.js` copies partners' Field Notes into `/field-notes/`, but every page `canonical`s back to `capraecapitalpartners.com`. Correctly **excluded** from this sitemap; nav links to the partners copy | — Field Notes is a partners feature; these mirrors must not be indexed here (avoids duplicate content). |
| `noindex` on private routes | N/A — marketing site, no private routes | — |
| Google Search Console verification | Present (`googled90b83ade46def6e.html`) — deploy required to go live | Critical. Cannot monitor coverage, submit sitemap, or see queries. |
| Bing Webmaster verification | Missing | Medium. |

## 4. Structured Data (JSON-LD)

| Element | Status | Impact |
|---|---|---|
| `Organization` schema | Present | High. Enables knowledge panel + logo in SERPs. |
| `WebSite` schema (with `SearchAction`) | Present — `WebSite`; verify `SearchAction` present | Medium. Enables sitelinks searchbox. |
| `ProfessionalService` + `Service` + `Offer` / `OfferCatalog` | Present — rich service/offer graph on home | High. Service rich results; strong entity signal. |
| `Article` schema on Field Notes posts | Present — `Article` + `ImageObject` + `WebPage` per post | Medium. Article rich results. |
| `BreadcrumbList` schema | Present — Home › Private Equity Services | Medium. Rich breadcrumb display in SERPs. |
| `FAQPage` schema on service pages | Present — 6 Q&As + matching visible `#faq` section | Medium. FAQ rich results. |
| `sameAs` on Organization (LinkedIn, X) | Verify — confirm `sameAs` array populated | Medium. Links entity to social profiles. |

## 5. Performance & Technical (Core Web Vitals)

| Element | Status | Impact |
|---|---|---|
| HTTPS + valid certificate | Present | Critical. Ranking factor. |
| Mobile responsive | Present | Critical. Mobile-first indexing. |
| LCP < 2.5 s | Unmeasured | High. Core Web Vital. |
| CLS < 0.1 | Unmeasured | High. Core Web Vital. |
| INP < 200 ms | Unmeasured | High. Core Web Vital (replaced FID). |
| Font preloading / `font-display: swap` | Partial — Google Fonts `preconnect` + `display=swap` | Medium. |
| Image lazy loading (`loading="lazy"`) | Unaudited | Medium. |
| Image alt text on all `<img>` | Present — 13/13 images have `alt` | High. Accessibility + image search. |
| Static pre-rendered HTML for social scrapers | Present — static HTML, no client-only SPA | High. Scrapers read `<head>` directly. |
| Compression (gzip / brotli) | Assumed via host | Medium. |

## 6. On-Page Content

| Element | Status | Impact |
|---|---|---|
| Single `<h1>` per page | Present — 1 per page | High. |
| Logical `<h2>` / `<h3>` hierarchy | Present | Medium. |
| Descriptive internal link anchor text | Present | Medium. |
| URL slugs (readable, hyphenated) | Present — Field Notes posts use readable slugs | Medium. |
| 404 page | Present — branded `404.html`, wired via nginx `error_page 404` | Medium. Broken links serve host default instead of a branded page. |
| Field Notes link in nav | Present — points to `capraecapitalpartners.com/field-notes/` (the canonical home) | Low. Correct cross-link; not a local page. |

## 7. Analytics & Monitoring

| Element | Status | Impact |
|---|---|---|
| Google Analytics 4 | Present (`G-JNPTWTS723`) | Critical. |
| Search Console coverage monitoring | Available — GSC verification added (see §3); deploy + Verify, then submit sitemap & monitor | High. |
| Server logs / crawler tracking | Present — nginx `access_log` + `error_log` at `/var/log/nginx/capraecapital.com.*` | Medium. |

## 8. Trust & E-E-A-T Signals

| Element | Status | Impact |
|---|---|---|
| Public About / team page | Present (`assets/team`) | High. Trust signal. |
| Testimonials / portfolio proof | Present (`assets/testimonials`, `assets/portfolio`) | High. Social proof. |
| Contact details | Verify | High. |
| Terms + Privacy pages | Verify | Critical. Required for commercial trust + Google Ads eligibility. |
| Named authors / bylines on content | Partial — Field Notes attributed to org, not named authors | Medium. |
| Organizational schema with `sameAs` (LinkedIn, X) | Verify (see §4) | Medium. |

---

## Priority summary

- **Critical (do now):** Confirm Google Search Console verification (`googled90b83ade46def6e.html`) is the correct token for this property, deploy, and submit the (homepage) sitemap. (Field Notes is **not** a services page — it mirrors from partners and canonicalizes there; leave it out of this sitemap.)
- **High (next):** Produce a proper 1200×630 `og:image` / `twitter:image` share card (currently the 400×410 logo). Add a branded `404.html`. Baseline Core Web Vitals (LCP/CLS/INP).
- **Medium (later):** confirm `WebSite` `SearchAction`, Bing Webmaster verification. (`BreadcrumbList` + `FAQPage`, 404 page, and server logs now done.)
