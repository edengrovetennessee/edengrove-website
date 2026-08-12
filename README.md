# edengrove-website

Public holding page for **Eden Grove**, a luxury team at Compass (Middle Tennessee).

Served by GitHub Pages at `edengrovetennessee.com`.

## What this is right now

A single static page: the Eden Grove wordmark debossed into a plaster ground,
plus one link to the internal dashboard. Nothing else. It exists so the domain
is not dead while Compass compliance answers the co-branding questions.

## Before this becomes a real marketing site

The full site cannot launch until compliance confirms:

- the office's **exact registered firm name and telephone number** as filed with TREC
- the approved **Compass co-branding lockup**
- the current **required legal disclaimers**

Tennessee Rule 1260-02-.12 requires the firm name to appear in type **equal to or
larger than** the team name in all advertising, alongside the registered firm name
and phone. Also required on a marketing site: Equal Housing Opportunity logo,
Realtor® logo, and team licence numbers.

The principal broker approves the site **before** launch, not after.

## Files

| File | Purpose |
|---|---|
| `index.html` | The whole page. Self-contained — no build step. |
| `CNAME` | Custom domain for GitHub Pages. Written by GitHub; leave it. |

## Editing

The dashboard link is the only line intended to change:

```html
<a class="dash" href="https://dashboard.edengrovetennessee.com">Company dashboard</a>
```

## DNS

Four A records at `@` → `185.199.108–111.153`, CNAME `www` → `edengrovetennessee.github.io`.
All **DNS only / grey cloud** in Cloudflare, or GitHub cannot issue the TLS certificate.
