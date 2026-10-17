# Market data

The figures on `sellers.html` and `buyers.html` are not typed into the HTML. They
are written into it by a build step, so one file is the source of truth and a
number can never drift away from the date it belongs to.

```
data/market.json          every figure: value, format, source, as-at date, max age
tools/fetch_market.py     pulls the public sources, writes market.json
tools/build_market.py     writes market.json into the HTML
.github/workflows/market.yml   runs both on the 8th of each month and commits
```

## To change a number by hand

Edit `data/market.json`, then run `python3 tools/build_market.py`. Figures under
`"manual"` are never overwritten by the fetcher — that is where anything from
RealTracs belongs, because closed-sale and price-tier data is not published in any
machine-readable public file.

## To add a figure to a page

1. Add the key to `data/market.json`.
2. In the HTML, write `<span data-fig="your.key">a placeholder</span>`. On the
   animated stat tiles, keep the existing `data-count` / `data-pre` / `data-suf` /
   `data-dec` attributes — the build rewrites them too.
3. Run `python3 tools/build_market.py`.

`--check` reports what would change and writes nothing.

## Why Realtor.com and not a scraper

Realtor.com Research publishes county and ZIP metrics as plain CSV on a stable
public URL, meant to be read by machine. A scraper pointed at a consumer property
site breaks the first time that site is redesigned, and gets its CI IP blocked
besides. Greater Nashville REALTORS, which has the figures we would most like,
sits behind a bot check that returns 429 to everything.

**These are listing-side metrics** — asking prices across active inventory, not
closed sales. Every page that prints them says so. Attribution to Realtor.com is
required and is part of the source line, not optional decoration.

## When it fails

A failed run emails the repo owner and changes nothing on the live site. The
usual causes, in order of likelihood:

- **A figure is past its max age.** The source has not published, or the build has
  not run in a while. Run the fetcher.
- **A guard tripped.** A figure moved more than 40% in a month. Almost always a
  source revision rather than the market. Check `"refused"` in market.json; those
  keys are holding their previous value and are marked `"stale": true`.
- **The CSV changed shape.** Column names are part of this source's contract and
  have been stable for years, but if `fetch_market.py` aborts on resolving fewer
  than seven of the eight luxury ZIPs, that is what has happened.
