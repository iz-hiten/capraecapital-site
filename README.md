# capraecapital.com — independent static copy

Snapshot of the live site taken 2026-09-23 from the production web root
`/home/ubuntu/caprae-site/caprae-capital-services` (served by nginx as `capraecapital.com`).

## What's inside

    site/                     the entire web root — this IS the website
      index.html              the whole one-page site (~115 KB)
      privacy/  terms/        legal pages
      field-notes/            blog index + posts + rss.xml
      assets/                 images, logos, portfolio, team, testimonials, legal.css
      404.html  robots.txt  sitemap.xml
      scripts/                python helpers used to build the legal pages (not needed to run)
    deploy/
      nginx-capraecapital.com.conf   the production nginx server config

No build step, no backend, no database. Pure static HTML/CSS/images.

## Run it locally

Do NOT double-click index.html. A few paths are root-relative (`/assets/logo/...`,
`/privacy/`, `/terms/`) and only resolve when served from a web root.

    cd site
    python3 -m http.server 8000

Then open http://localhost:8000

Any static server works equally well (`npx serve`, `php -S`, VS Code Live Server, etc.).

## Deploy it somewhere real

Drop the contents of `site/` into any static host — nginx, Apache, Netlify,
Vercel, Cloudflare Pages, S3 + CloudFront. Point the web root at `site/`.

If you use nginx, start from `deploy/nginx-capraecapital.com.conf`. That file
holds things that are NOT in the site folder and would otherwise be lost:

- ~20 301 redirects for legacy URLs Google still has indexed
  (`/book`, `/services`, `/team`, `/careers`, `/post/*`, …)
- the `404.html` error-page mapping
- the `www` → bare-domain redirect
- cache headers for `/assets/` (30 days) and the security/SEO headers
- Certbot SSL block (the cert paths are for the original server — replace them)

The file also contains the server blocks for `capraecapitalpartners.com`
(a different site, running a Node app on :8080). Delete those blocks unless you
need them.

## Notes / gotchas

- **Needs internet to look right.** Google Fonts, Termly (cookie consent),
  Google Tag Manager, and YouTube embeds load from remote hosts. Offline it
  still renders, just with fallback fonts and no consent banner.
- **Analytics and consent are wired to the original property.** Before putting
  this on a new domain, replace the Google Tag Manager container ID and the
  Termly IDs in `index.html`, or strip them.
- **`googled90b83ade46def6e.html`** is a Google Search Console verification file
  for the original domain. Delete it on a new domain.
- **Absolute links stay pointed at the original sites.** `index.html` links out
  to `capraecapitalpartners.com` and `capraecapitalpartners.substack.com`, and a
  handful of canonical/OG tags hardcode `https://capraecapital.com`. Update those
  if this copy becomes the canonical site.
- **No git history.** The `.git` repo lives one level up in `caprae-site/` and
  covers the corporate site too, so it was left out.
- Stale `index.html.bak.*` backups were excluded.
