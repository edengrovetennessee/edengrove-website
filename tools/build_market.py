#!/usr/bin/env python3
"""
Write the figures in data/market.json into the site's HTML.

The output is static. A visitor with JavaScript off, and a crawler, both see the
real number — which is the whole reason this is a build step rather than a fetch
in the browser. It also means a figure and its as-at date can never drift apart,
because one pass writes both.

Markup this looks for:
  <span data-fig="lux.brentwood.median" ...>$1,800,000</span>
      inner text replaced; if the element also carries data-count (the animated
      stat tiles), that attribute is rewritten too.
  <tbody data-table="luxzips"> ... </tbody>
      contents replaced wholesale.
  <span data-asof="luxzips">September 2026</span>
      replaced with the period the data is for.

Refuses to write, and exits non-zero, if a key is missing or a figure is past its
max age. A stale median on a brokerage page is a claim, not a statistic.

Usage:  python3 tools/build_market.py [--check]
        --check reports what would change and writes nothing.
"""
import datetime, io, json, os, re, sys

ROOT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA  = os.path.join(ROOT, "data", "market.json")
PAGES = ["sellers.html", "buyers.html"]

MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]


def fail(msg):
    print("BUILD FAILED: " + msg, file=sys.stderr)
    sys.exit(1)


def money(n):
    return "${:,.0f}".format(n)


def fmt(value, kind):
    if kind == "usd0":
        return money(value)
    if kind == "days":
        return "{:,.0f}".format(value)
    if kind == "times":
        return "{:.1f}×".format(value)
    if kind == "pct":
        return "{:.1f}%".format(value)
    return "{:,.0f}".format(value)


def count_attrs(value, kind):
    """(data-count, data-pre, data-suf, data-dec) for the animated stat tiles."""
    if kind == "usd0":
        return ("%d" % round(value), "$", "", "0")
    if kind == "days":
        return ("%d" % round(value), "", "", "0")
    if kind == "times":
        return ("%s" % value, "", "×", "1")
    if kind == "pct":
        return ("%s" % value, "", "%", "1")
    return ("%s" % value, "", "", "0")


def month_name(as_of):
    y, m = as_of.split("-")
    return "%s %s" % (MONTHS[int(m) - 1], y)


def month_end(as_of):
    y, m = int(as_of[:4]), int(as_of[5:7])
    return (datetime.date(y + (m == 12), (m % 12) + 1, 1) - datetime.timedelta(days=1))


def check_age(key, fig, today):
    as_of = fig.get("asOf")
    cap = fig.get("maxAgeDays")
    if not as_of or not cap:
        return
    age = (today - month_end(as_of)).days
    if age > cap:
        fail("%s is %d days past its %s period, over the %d-day limit. "
             "Run tools/fetch_market.py, or widen maxAgeDays if the source itself "
             "has stopped publishing." % (key, age, as_of, cap))


def build_rows(rows):
    out = []
    for r in rows:
        psf = money(r["psf"]) if r.get("psf") else "&mdash;"
        dom = "{:,.0f}".format(r["dom"]) if r.get("dom") else "&mdash;"
        act = "{:,.0f}".format(r["active"]) if r.get("active") else "&mdash;"
        tail = "{:.1f}×".format(r["tail"]) if r.get("tail") else "&mdash;"
        out.append(
            "        <tr><td>%s<small>%s</small></td>"
            "<td class=\"w-price\">%s</td><td>%s</td><td>%s</td>"
            "<td>%s</td><td>%s</td></tr>"
            % (r["area"], r["zip"], money(r["median"]), money(r["average"]),
               tail, psf, dom))
    return "\n".join(out)


def main():
    check_only = "--check" in sys.argv
    if not os.path.exists(DATA):
        fail("data/market.json not found. Run tools/fetch_market.py first.")
    with io.open(DATA, encoding="utf-8") as f:
        data = json.load(f)

    today = datetime.date.today()
    figures = dict(data.get("figures", {}))
    figures.update(data.get("manual", {}))        # hand-entered wins
    tables = data.get("tables", {})

    changed, touched, wrote = 0, 0, []

    for page in PAGES:
        path = os.path.join(ROOT, page)
        if not os.path.exists(path):
            print("skip %s (not present)" % page, file=sys.stderr)
            continue
        src = io.open(path, encoding="utf-8").read()
        orig = src

        # ---- single figures ---------------------------------------------------
        def sub_fig(m):
            nonlocal changed, touched
            whole, attrs, inner = m.group(0), m.group(1), m.group(2)
            key = re.search(r'data-fig="([^"]+)"', attrs).group(1)
            if key not in figures:
                fail("%s wants data-fig=\"%s\" and market.json has no such key." % (page, key))
            fig = figures[key]
            check_age(key, fig, today)
            text = fmt(fig["value"], fig.get("fmt", "num"))
            c, pre, suf, dec = count_attrs(fig["value"], fig.get("fmt", "num"))
            a = attrs
            if 'data-count="' in a:
                a = re.sub(r'data-count="[^"]*"', 'data-count="%s"' % c, a)
                a = re.sub(r'data-pre="[^"]*"', 'data-pre="%s"' % pre, a)
                a = re.sub(r'data-suf="[^"]*"', 'data-suf="%s"' % suf, a)
                a = re.sub(r'data-dec="[^"]*"', 'data-dec="%s"' % dec, a)
            touched += 1
            new = "<span%s>%s</span>" % (a, text)
            if new != whole:
                changed += 1
            return new

        src = re.sub(r'<span([^>]*\bdata-fig="[^"]+"[^>]*)>(.*?)</span>',
                     sub_fig, src, flags=re.S)

        # ---- as-at labels -----------------------------------------------------
        def sub_asof(m):
            nonlocal changed, touched
            attrs = m.group(1)
            key = re.search(r'data-asof="([^"]+)"', attrs).group(1)
            src_as_of = (tables.get(key) or {}).get("asOf") or (figures.get(key) or {}).get("asOf")
            if not src_as_of:
                fail("%s wants data-asof=\"%s\" and market.json has no period for it." % (page, key))
            touched += 1
            new = "<span%s>%s</span>" % (attrs, month_name(src_as_of))
            if new != m.group(0):
                changed += 1
            return new

        src = re.sub(r'<span([^>]*\bdata-asof="[^"]+"[^>]*)>.*?</span>',
                     sub_asof, src, flags=re.S)

        # ---- tables -----------------------------------------------------------
        def sub_table(m):
            nonlocal changed, touched
            attrs = m.group(1)
            key = re.search(r'data-table="([^"]+)"', attrs).group(1)
            t = tables.get(key)
            if not t:
                fail("%s wants data-table=\"%s\" and market.json has no such table." % (page, key))
            check_age(key, {"asOf": t["asOf"], "maxAgeDays": 75}, today)
            touched += 1
            new = "<tbody%s>\n%s\n      </tbody>" % (attrs, build_rows(t["rows"]))
            if new != m.group(0):
                changed += 1
            return new

        src = re.sub(r'<tbody([^>]*\bdata-table="[^"]+"[^>]*)>.*?</tbody>',
                     sub_table, src, flags=re.S)

        if src != orig:
            wrote.append(page)
            if not check_only:
                io.open(path, "w", encoding="utf-8").write(src)

    verb = "would update" if check_only else "updated"
    print("%s %d of %d marked slots across %s"
          % (verb, changed, touched, ", ".join(wrote) if wrote else "nothing"))
    if data.get("refused"):
        print("NOTE: %d figure(s) are holding their previous value: %s"
              % (len(data["refused"]), ", ".join(data["refused"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
