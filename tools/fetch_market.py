#!/usr/bin/env python3
"""
Pull the Nashville luxury market figures from Realtor.com Research and write
data/market.json.

Why this source and not a scraper: Realtor.com publishes these as plain CSV on a
stable public URL, built to be consumed by machine. A scraper pointed at a
consumer property site breaks the first time that site redesigns, and gets
IP-blocked from CI besides. This file has not changed shape in years and the
column names are part of its contract.

What it is NOT: these are LISTING-side figures — what is being asked across
active inventory — not closed sales. Every page that prints them says so. Closed
sale data lives in RealTracs and has to be entered by hand; those figures live
under "manual" in market.json and this script never touches them.

Usage:  python3 tools/fetch_market.py [--dry-run]
Exit 0 = market.json written (or already current). Exit 1 = refused to write.
"""
import csv, io, json, os, sys, urllib.request, datetime, copy

ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT    = os.path.join(ROOT, "data", "market.json")

COUNTY_URL = "https://econdata.s3-us-west-2.amazonaws.com/Reports/Core/RDC_Inventory_Core_Metrics_County.csv"
ZIP_URL    = "https://econdata.s3-us-west-2.amazonaws.com/Reports/Core/RDC_Inventory_Core_Metrics_Zip.csv"

ATTRIB = {
    "name": "Realtor.com® Research Data",
    "url":  "https://www.realtor.com/research/data/",
    "note": "Active-listing metrics. Asking prices across inventory on the market, not closed sales.",
}

# The luxury ZIPs, in the order they appear on the page. Keep this list short and
# deliberate: every row is a claim that this is a market Eden Grove works in.
LUX_ZIPS = [
    ("37046", "College Grove"),
    ("37014", "Arrington"),
    ("37027", "Brentwood"),
    ("37220", "Oak Hill"),
    ("37215", "Green Hills &amp; Forest Hills"),
    ("37205", "Belle Meade &amp; West Meade"),
    ("37069", "Franklin, north"),
    ("37064", "Franklin, south"),
]
COUNTIES = {"47037": "Davidson", "47187": "Williamson"}

# A figure that moves more than this month-over-month is almost certainly a bad
# parse or a source revision, not the market. Refuse rather than publish it.
MAX_MOM_SWING = 0.40


def log(msg):
    print(msg, file=sys.stderr)


def get(url, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": "edengrove-market/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8-sig", "replace")


def rows(text):
    return list(csv.DictReader(io.StringIO(text)))


def num(rec, key):
    v = rec.get(key)
    if v in (None, "", "NaN", "nan"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def load_previous():
    if not os.path.exists(OUT):
        return None
    try:
        with io.open(OUT, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log("WARN: could not read existing market.json (%s); treating as first run" % e)
        return None


def sane(key, new, prev):
    """True if the new value is publishable. Keeps the old one if not."""
    if new is None:
        log("GUARD %s: source had no value" % key)
        return False
    if new <= 0:
        log("GUARD %s: non-positive (%r)" % (key, new))
        return False
    if prev:
        old = prev.get("value")
        if isinstance(old, (int, float)) and old > 0:
            swing = abs(new - old) / old
            if swing > MAX_MOM_SWING:
                log("GUARD %s: %.0f%% swing (%s -> %s) exceeds %.0f%%"
                    % (key, swing * 100, old, new, MAX_MOM_SWING * 100))
                return False
    return True


def main():
    dry = "--dry-run" in sys.argv
    today = datetime.date.today().isoformat()
    prev = load_previous()
    prev_figs = (prev or {}).get("figures", {})

    log("fetching county metrics ...")
    county = rows(get(COUNTY_URL))
    log("fetching zip metrics ...")
    zips = rows(get(ZIP_URL))
    if not county or not zips:
        log("ABORT: a source returned no rows")
        return 1

    period = str(county[0]["month_date_yyyymm"])            # e.g. 202609
    as_of  = "%s-%s" % (period[:4], period[4:6])
    zperiod = str(zips[0]["month_date_yyyymm"])
    if zperiod != period:
        log("NOTE: county period %s, zip period %s — using each as given" % (period, zperiod))
    zas_of = "%s-%s" % (zperiod[:4], zperiod[4:6])

    by_zip = {str(r["postal_code"]).zfill(5): r for r in zips}
    by_fips = {str(r["county_fips"]).zfill(5): r for r in county}

    figures, table, refused = {}, [], []

    def put(key, value, fmt, as_of_, label):
        p = prev_figs.get(key)
        if not sane(key, value, p):
            refused.append(key)
            if p:
                figures[key] = copy.deepcopy(p)   # keep the last good one
                figures[key]["stale"] = True
            return
        figures[key] = {"value": value, "fmt": fmt, "asOf": as_of_,
                        "source": "realtor_research", "label": label,
                        "cadence": "monthly", "maxAgeDays": 75}

    # ---- the luxury ZIP table -------------------------------------------------
    for z, area in LUX_ZIPS:
        r = by_zip.get(z)
        if not r:
            log("GUARD zip %s (%s): absent from this month's file" % (z, area))
            refused.append("zip.%s" % z)
            continue
        med = num(r, "median_listing_price")
        avg = num(r, "average_listing_price")
        psf = num(r, "median_listing_price_per_square_foot")
        dom = num(r, "median_days_on_market")
        act = num(r, "active_listing_count")
        if med is None or avg is None:
            log("GUARD zip %s (%s): median or average missing" % (z, area))
            refused.append("zip.%s" % z)
            continue
        table.append({
            "zip": z, "area": area,
            "median": int(med), "average": int(avg),
            "psf": int(psf) if psf else None,
            "dom": int(dom) if dom else None,
            "active": int(act) if act else None,
            "tail": round(avg / med, 2) if med else None,
        })

    if len(table) < len(LUX_ZIPS) - 1:
        log("ABORT: only %d of %d luxury ZIPs resolved — the source shape may have changed"
            % (len(table), len(LUX_ZIPS)))
        return 1

    # ---- headline figures -----------------------------------------------------
    bw = by_zip.get("37027")
    if bw:
        put("lux.brentwood.median", num(bw, "median_listing_price"), "usd0", zas_of,
            "Brentwood median asking")
        put("lux.brentwood.dom", num(bw, "median_days_on_market"), "days", zas_of,
            "Brentwood median days on market")
    bm = by_zip.get("37205")
    if bm:
        m, a = num(bm, "median_listing_price"), num(bm, "average_listing_price")
        if m and a:
            put("lux.bellemeade.tail", round(a / m, 2), "times", zas_of,
                "Belle Meade average against median")

    for fips, name in COUNTIES.items():
        r = by_fips.get(fips)
        if not r:
            continue
        k = name.lower()
        put("county.%s.median" % k, num(r, "median_listing_price"), "usd0", as_of,
            "%s median asking" % name)
        put("county.%s.dom" % k, num(r, "median_days_on_market"), "days", as_of,
            "%s median days on market" % name)
        put("county.%s.psf" % k, num(r, "median_listing_price_per_square_foot"), "usd0", as_of,
            "%s price per square foot" % name)

    doc = {
        "generated": datetime.datetime.now(datetime.timezone.utc)
                        .replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "fetched": today,
        "sources": {"realtor_research": dict(ATTRIB, asOf=zas_of)},
        "figures": figures,
        "tables": {"luxzips": {"asOf": zas_of, "source": "realtor_research", "rows": table}},
        # Hand-entered figures survive every fetch. Closed-sale and luxury-tier
        # numbers come from RealTracs and cannot be pulled from a public file.
        "manual": (prev or {}).get("manual", {}),
        "refused": refused,
    }

    if refused:
        log("NOTE: %d figure(s) kept at their previous value: %s" % (len(refused), ", ".join(refused)))

    if dry:
        log("--dry-run: not writing")
        print(json.dumps(doc, indent=2)[:1200])
        return 0

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")
    log("wrote %s — %d figures, %d table rows, period %s"
        % (os.path.relpath(OUT, ROOT), len(figures), len(table), zas_of))
    return 0


if __name__ == "__main__":
    sys.exit(main())
