"""
THE GREEN LAYER on neighborhoods.html.

The white and brass pins are places and they do not move; they are built once
by map-build-geo.py and placed by map-finalise.py. The green pins are stock,
and stock turns over, so they get their own script and their own run.

WHAT IT DOES
  1. reads the addresses straight out of properties.html, so the map can
     never disagree with the grid;
  2. geocodes each one (US Census first, Nominatim as a fallback);
  3. gives every street ONE pin - 715, 706 and 607 Davis Drive are one dot
     carrying the number three, not three dots on top of each other;
  4. pushes a pin out of any existing dot or any existing LABEL it has
     landed in, which is the part that is easy to forget: a green dot that
     eats the word "Cielo" is worse than one that is four hundred yards out;
  5. prints the <g class="mp__pins--list"> block and the panel rows.

WHAT IT WILL NOT DO
  It skips the six register-interest listings. Those cards deliberately
  publish no city and no price, and a pin at an exact address would hand
  over more than the card does. If one of them is ever given a town on
  properties.html it will start being mapped; until then it is not ours
  to place.

RUN IT  from the repo root, after a listing changes:
    python3 data/map-listings.py          # prints the two blocks to paste
"""
import json, math, re, ssl, time, urllib.parse, urllib.request

ROOT = __file__.rsplit("/data/", 1)[0]
UA = {"User-Agent": "eden-grove-map-build/1.0"}

# ---- the frame, identical to map-build-geo.py ------------------------------
LAT0, LAT1 = 35.675, 36.370
LON0, LON1 = -87.075, -86.600
K  = math.cos(math.radians((LAT0 + LAT1) / 2))
Wp, Hp = (LON1 - LON0) * K, (LAT1 - LAT0)
VB_W = 1000.0
VB_H = VB_W * Hp / Wp
UNIT_FT = (LAT1 - LAT0) * 69.05 * 5280 / VB_H      # ~140 ft per map unit

def proj(lon, lat):
    return ((lon - LON0) * K / Wp * VB_W, (LAT1 - lat) / Hp * VB_H)

# ---- 1. the addresses, from the page itself --------------------------------
def read_properties():
    h = open(f"{ROOT}/properties.html", encoding="utf-8").read()
    cuts = [m.start() for m in re.finditer(r'class="prop(?: prop--pe)?"', h)] + [len(h)]
    out = []
    for i in range(len(cuts) - 1):
        seg = h[cuts[i]:cuts[i + 1]]
        href = re.search(r'href="([^"]+)"', seg)
        addr = re.search(r'class="prop__addr">(.*?)<', seg, re.S)
        place = re.search(r'class="prop__place">(.*?)<', seg, re.S)
        if not addr:
            continue
        street = addr.group(1).strip()
        # the register-interest cards carry no town - see WHAT IT WILL NOT DO
        if place:
            city, zp = place.group(1).split(",")[0].strip(), ""
        else:
            # The town has to be the card's own, so look only at the short
            # run of markup straight after the address. Searching the whole
            # segment picks up the footer and maps a card that publishes no
            # town at all.
            tail = seg[addr.end():addr.end() + 200]
            m = re.search(r'([A-Z][a-z]+(?: [A-Z][a-z]+)?), TN (\d{5})', tail)
            if not m:
                print(f"  skipping (no town published): {street}")
                continue
            city, zp = m.group(1), m.group(2)
        link = href.group(1) if href and href.group(1).startswith("property/") else "properties.html"
        out.append({"street": street, "city": city, "zip": zp, "href": link})
    return out

# ---- 2. geocoding ----------------------------------------------------------
def _get(url):
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45,
                                context=ctx) as f:
        return json.loads(f.read().decode())

# Addresses neither gazetteer knows. A pin here is the town, not the house,
# and it is recorded as such - the same compromise Laurelbrooke already
# lives with on the white layer. Replace an entry the moment the real
# coordinates turn up.
MANUAL = {
    "2495 Deer Meadow Ln": (35.8676656, -86.7096095, "Arrington town centre", "area"),
}

def geocode(p):
    if p["street"] in MANUAL:
        return MANUAL[p["street"]]
    q = urllib.parse.urlencode({"street": p["street"], "city": p["city"], "state": "TN",
                                "zip": p["zip"], "benchmark": "Public_AR_Current",
                                "format": "json"})
    try:
        m = _get("https://geocoding.geo.census.gov/geocoder/locations/address?" + q) \
            .get("result", {}).get("addressMatches", [])
        if m:
            c = m[0]["coordinates"]
            return float(c["y"]), float(c["x"]), "census", "exact"
    except Exception as e:
        print("  census:", p["street"], e)
    time.sleep(1.2)
    try:
        d = _get("https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
            {"q": f'{p["street"]}, {p["city"]}, TN {p["zip"]}', "format": "json",
             "limit": 1, "countrycodes": "us"}))
        if d:
            return float(d[0]["lat"]), float(d[0]["lon"]), "nominatim", "street"
    except Exception as e:
        print("  nominatim:", p["street"], e)
    return None

# ---- 3. one pin per street -------------------------------------------------
def cluster(pts):
    by = {}
    for p in pts:
        by.setdefault((p["city"], " ".join(p["street"].split()[1:])), []).append(p)
    pins = []
    for (city, street), g in by.items():
        x = sum(p["x"] for p in g) / len(g)
        y = sum(p["y"] for p in g) / len(g)
        one = len(g) == 1
        pins.append({
            "x": x, "y": y, "x0": x, "y0": y, "n": len(g), "city": city,
            "label": g[0]["street"] if one else street,
            "href":  g[0]["href"]   if one else "properties.html",
            "members": sorted(({"label": p["street"], "href": p["href"]} for p in g),
                              key=lambda m: m["label"]),
        })
    return pins

# ---- 4. out of other people's dots AND other people's names ----------------
def obstacles():
    """Dot centres and label boxes already in the svg, in user units.

    The label boxes are measured once with a headless browser (the font
    decides the width) and cached next to this file. Re-measure after any
    change to the label set:  node data/map-label-boxes.js
    """
    return json.load(open(f"{ROOT}/data/map-obstacles.json"))

def place(pins, ob, dot_min=13.0, pad=6.0, self_min=15.0):
    dots, lbls = ob["dots"], ob["labels"]
    for _ in range(600):
        moved = False
        for a in pins:
            fx = fy = 0.0
            for b in lbls:
                x0, y0 = b["x"] - pad, b["y"] - pad
                x1, y1 = b["x"] + b["w"] + pad, b["y"] + b["h"] + pad
                if x0 < a["x"] < x1 and y0 < a["y"] < y1:
                    m, (ux, uy) = min([(a["x"]-x0, (-1, 0)), (x1-a["x"], (1, 0)),
                                       (a["y"]-y0, (0, -1)), (y1-a["y"], (0, 1))],
                                      key=lambda t: t[0])
                    fx += ux * (m + 0.5); fy += uy * (m + 0.5)
            for o in dots:
                d = math.hypot(a["x"]-o["x"], a["y"]-o["y"])
                if 1e-6 < d < dot_min:
                    k = (dot_min-d)/d; fx += (a["x"]-o["x"])*k; fy += (a["y"]-o["y"])*k
            for b in pins:
                if b is a: continue
                d = math.hypot(a["x"]-b["x"], a["y"]-b["y"])
                if 1e-6 < d < self_min:
                    k = (self_min-d)/d*0.5
                    fx += (a["x"]-b["x"])*k; fy += (a["y"]-b["y"])*k
            if abs(fx) > .01 or abs(fy) > .01:
                a["x"] += fx*0.35; a["y"] += fy*0.35; moved = True
        if not moved:
            break
    for a in pins:
        a["moved_ft"] = round(math.hypot(a["x"]-a["x0"], a["y"]-a["y0"]) * UNIT_FT)
    return pins

# ---- 5. the markup ---------------------------------------------------------
WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}

def emit(pins):
    svg = []
    for i, q in enumerate(sorted(pins, key=lambda z: (z["y"], z["x"]))):
        x, y = q["x"], q["y"]
        r = 7.5 if q["n"] > 1 else 6.0
        many = " mp__dot--many" if q["n"] > 1 else ""
        left = x > 700
        lx, anc = (x - 16, "end") if left else (x + 16, "start")
        if q["n"] > 1:
            txt = f'{q["label"]} &#183; {q["n"]} listings'
            aria = f'{q["label"]}, {WORDS[q["n"]]} listings'
            ttl = f'{q["label"]}, {q["city"]} &#8212; {WORDS[q["n"]]} listings'
        else:
            txt, aria = q["label"], f'{q["label"]}, {q["city"]}'
            ttl = f'{q["label"]}, {q["city"]} &#8212; Eden Grove listing'
        svg.append(
f'''    <a class="mp__pin mp__pin--list" href="{q["href"]}" style="--d:{(i*0.29)%3.0:.2f}s" aria-label="{aria}">
      <title>{ttl}</title>
      <circle class="mp__ring" cx="{x:.1f}" cy="{y:.1f}" r="{r+1.5:.1f}"/>
      <circle class="mp__dot{many}"  cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}"/>
      <text class="mp__lbl mp__lbl--list" x="{lx:.1f}" y="{y+5:.1f}" text-anchor="{anc}">{txt}</text>
      <circle class="mp__hit"  cx="{x:.1f}" cy="{y:.1f}" r="26"/>
    </a>''')
    rows = {}
    for q in pins:
        for m in q["members"]:
            rows.setdefault(q["city"], []).append((m["label"], m["href"]))
    panel = []
    for city in sorted(rows, key=lambda c: (-len(rows[c]), c)):
        panel.append(f'    <p class="mp__now__city">{city}</p>')
        panel.append('    <ul class="mp__now__list">')
        for label, href in sorted(rows[city]):
            panel.append(f'      <li><a href="{href}">{label}</a></li>')
        panel.append('    </ul>')
    return "\n".join(svg), "\n".join(panel)

if __name__ == "__main__":
    pts = read_properties()
    print(f"{len(pts)} mappable listings on properties.html")
    keep = []
    for p in pts:
        g = geocode(p)
        if not g:
            print(f"  NOT PLACED: {p['street']} - leave it off the map and say so")
            continue
        p["lat"], p["lon"], p["src"], p["precision"] = g
        p["x"], p["y"] = proj(p["lon"], p["lat"])
        keep.append(p)
        time.sleep(0.4)
    pins = place(cluster(keep), obstacles())
    for q in sorted(pins, key=lambda z: z["y"]):
        tag = f'x{q["n"]}' if q["n"] > 1 else "  "
        print(f'  {q["label"]:24s} {q["city"]:10s} ({q["x"]:6.1f},{q["y"]:7.1f}) {tag}'
              f'  moved {q["moved_ft"]:5d} ft')
    svg, panel = emit(pins)
    open(f"{ROOT}/data/map-listings.json", "w").write(json.dumps(pins, indent=1))
    print("\n--- paste into <g class=\"mp__pins mp__pins--list\"> ---\n" + svg)
    print("\n--- paste into .mp__now ---\n" + panel)
