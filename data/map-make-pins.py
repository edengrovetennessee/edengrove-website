"""One pin file for the tile map, and the frame each county map opens on.

WHY THE TRUE POSITIONS, NOT THE ONES ON THE DRAWN MAP. Four listing pins
were nudged off their address - 515 Shenandoah by 1,723ft, Deer Meadow by
1,812ft - to get out from under a neighbour's label. That nudge only ever
existed because the drawn map's labels are fixed and cannot move. A tile
map places its own labels and zooms, so the nudge is not just unnecessary,
it is wrong. This reads x0/y0, which is where each pin actually is.
"""
import json, math, glob, shapefile

import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
U = os.path.join(ROOT, "data")
LAT0, LAT1, LON0, LON1 = 35.675, 36.370, -87.075, -86.600
K = math.cos(math.radians((LAT0 + LAT1) / 2))
Wp, Hp = (LON1 - LON0) * K, (LAT1 - LAT0)
VBW = 1000.0
VBH = VBW * Hp / Wp

def unproj(x, y):
    return (x / VBW * Wp / K + LON0, LAT1 - y / VBH * Hp)

# ---- counties, for grouping and for the frames ------------------------------
r = shapefile.Reader(glob.glob(os.path.join(U, "tiger", "cb_2023_us_county_500k", "*.shp"))[0])
flds = [f[0] for f in r.fields[1:]]
counties = []
for sr in r.iterShapeRecords():
    rec = dict(zip(flds, sr.record))
    if rec["STATEFP"] != "47":
        continue
    idx = list(sr.shape.parts) + [len(sr.shape.points)]
    counties.append((rec["NAME"], sr.shape.bbox,
                     [sr.shape.points[idx[i]:idx[i+1]] for i in range(len(idx)-1)]))

def in_ring(x, y, ring):
    c = False
    for i in range(len(ring)):
        x1, y1 = ring[i]; x2, y2 = ring[(i+1) % len(ring)]
        if (y1 > y) != (y2 > y) and x < (x2-x1)*(y-y1)/(y2-y1) + x1:
            c = not c
    return c

def county_of(lon, lat):
    for name, bb, rings in counties:
        if bb[0] <= lon <= bb[2] and bb[1] <= lat <= bb[3]:
            if any(in_ring(lon, lat, ring) for ring in rings):
                return name
    return None

pins = []
for p in json.load(open(f"{U}/map-points.json")):
    pins.append({
        "kind": "community" if p["kind"] == "development" else "neighborhood",
        "label": p["name"], "lat": round(p["lat"], 6), "lon": round(p["lon"], 6),
        "href": ("development/" if p["kind"] == "development" else "neighborhood/")
                + p["slug"] + "/",
        "precision": p.get("precision"), "county": county_of(p["lon"], p["lat"]),
    })

for q in json.load(open(f"{U}/map-listings.json")):
    lon, lat = unproj(q["x0"], q["y0"])          # true, not nudged
    pins.append({
        "kind": "listing", "label": q["label"],
        "lat": round(lat, 6), "lon": round(lon, 6),
        "href": q["href"], "count": q["n"],
        "members": [m["label"] for m in q["members"]],
        "county": county_of(lon, lat),
    })

# ---- the frame each map opens on --------------------------------------------
# Firefly is the only pin in Maury and sits just over the Williamson line in
# Spring Hill, so it rides with Williamson rather than getting a map of its
# own. Recorded here rather than left for someone to rediscover.
GROUP = {"Davidson": "Davidson", "Williamson": "Williamson", "Maury": "Williamson"}
frames = {}
for p in pins:
    g = GROUP.get(p["county"])
    assert g, f"{p['label']} is in {p['county']}, which has no map"
    f = frames.setdefault(g, {"n": 0, "w": 180.0, "s": 90.0, "e": -180.0, "n_": -90.0})
    f["n"] += 1
    f["w"] = min(f["w"], p["lon"]); f["e"] = max(f["e"], p["lon"])
    f["s"] = min(f["s"], p["lat"]); f["n_"] = max(f["n_"], p["lat"])

PAD = 0.012                                       # ~0.8 mi of air around the edge pins
out = {}
for g, f in frames.items():
    out[g] = {"pins": f["n"],
              "bounds": [[round(f["w"]-PAD, 4), round(f["s"]-PAD, 4)],
                         [round(f["e"]+PAD, 4), round(f["n_"]+PAD, 4)]]}
    mi_w = (f["e"]-f["w"]+2*PAD) * 69.05 * K
    mi_h = (f["n_"]-f["s"]+2*PAD) * 69.05
    print(f"  {g:11s} {f['n']:>2} pins   {mi_w:5.1f} x {mi_h:5.1f} miles")

json.dump({"_note": "True positions. The drawn map nudges four listing pins "
                    "off their address to clear labels; a tile map must not.",
           "frames": out, "pins": pins},
          open(os.path.join(U, "map-pins.json"), "w"), indent=1)

from collections import Counter
print("\n ", Counter(p["kind"] for p in pins))
print(f"  {len(pins)} pins -> data/map-pins.json")
