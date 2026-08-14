# edengrove-website

Public site for **Eden Grove**, a luxury team at Compass (Middle Tennessee).
Served by GitHub Pages at `edengrovetennessee.com`.

## Current state — draft, not finished

Two sections: a full-bleed hero and a featured-properties block. No build step,
no dependencies; `index.html` is the whole site.

**`<meta name="robots" content="noindex, nofollow">` is set on purpose.** The
featured listings are invented — real Middle Tennessee street names with made-up
prices, square footage and `MLS # 0000000`. That must not be indexed, and it must
not be public-facing marketing. Remove the noindex tag only once every listing on
the page is real.

## Still missing before launch

Compass compliance furniture is deliberately absent while the design is settled:

- **Compass firm name in type equal to or larger than "Eden Grove"** — Tenn. Comp.
  R. & Regs. 1260-02-.12. This is the violation that gets teams cited.
- The office's **registered firm name and telephone number** exactly as filed with TREC
- **Equal Housing Opportunity** and **Realtor®** logos
- Compass's current **legal disclaimers**
- Team **licence numbers**

The principal broker approves the site **before** launch, not after.

Listings beyond the team's own require an **IDX agreement** with Realtracs plus
Compass authorisation. Until then, only our own listings with our own photography.

## Structure

| | |
|---|---|
| `index.html` | Entire site — markup, CSS and JS in one file |
| `media/hero.jpg` | Hero slot, 2400 × 1350. Swap `<img class="hero__media">` for `<video>` and no CSS changes |
| `media/prop-lead.jpg` | Lead property, 2400 × 960 (5:2) |
| `media/prop-1.jpg`, `prop-2.jpg` | Secondary properties, 1200 × 1000 (6:5) |
| `CNAME` | Custom domain. Written by GitHub — leave it |

All images are labelled placeholders.

## Design notes

Cormorant Garamond for display, Jost for interface. Ink `#14170F`, paper
`#F4F1EC`, and one warm accent — brass `#B6A97C` — used only for status badges,
hairline rules and the single call to action.

Property cards show the address at rest and reveal price, square footage and MLS
number on hover. Because hover does not exist on touch, any device that cannot
hover shows those numbers permanently; keyboard users get them on focus.

## DNS

Four A records at `@` → `185.199.108–111.153`, CNAME `www` →
`edengrovetennessee.github.io`. All **DNS only / grey cloud** in Cloudflare, or
GitHub cannot issue its TLS certificate.
