"""Builds the detailed basemap for neighborhoods.html.

THE FRAME IS NOT NEGOTIABLE. It is identical to data/map-build-geo.py, so
every pin, every label box and every listing coordinate already solved
stays exactly where it is. Only what sits underneath them changes.
"""
import glob, json, math, sys
import shapefile

import os
T = os.environ.get("TIGER", os.path.join(os.path.dirname(os.path.abspath(__file__)), "tiger"))
LAT0, LAT1 = 35.675, 36.370
LON0, LON1 = -87.075, -86.600
K  = math.cos(math.radians((LAT0 + LAT1) / 2))
Wp, Hp = (LON1 - LON0) * K, (LAT1 - LAT0)
VB_W = 1000.0
VB_H = VB_W * Hp / Wp
PAD  = 0.03                                     # degrees of slop outside the frame

def proj(lon, lat):
    return ((lon - LON0) * K / Wp * VB_W, (LAT1 - lat) / Hp * VB_H)

def in_frame(bbox):
    x0, y0, x1, y1 = bbox
    return not (x1 < LON0 - PAD or x0 > LON1 + PAD or y1 < LAT0 - PAD or y0 > LAT1 + PAD)

sys.setrecursionlimit(100000)
def rdp(p, tol):
    if len(p) < 3: return p
    (x0, y0), (x1, y1) = p[0], p[-1]
    dx, dy = x1 - x0, y1 - y0
    m = math.hypot(dx, dy)
    best, bi = -1.0, 0
    for i in range(1, len(p) - 1):
        x, y = p[i]
        d = abs(dy*x - dx*y + x1*y0 - y1*x0)/m if m else math.hypot(x-x0, y-y0)
        if d > best: best, bi = d, i
    if best > tol:
        return rdp(p[:bi+1], tol)[:-1] + rdp(p[bi:], tol)
    return [p[0], p[-1]]

def length(pts):
    return sum(math.hypot(pts[i+1][0]-pts[i][0], pts[i+1][1]-pts[i][1])
               for i in range(len(pts)-1))

def parts_of(shape):
    idx = list(shape.parts) + [len(shape.points)]
    return [shape.points[idx[i]:idx[i+1]] for i in range(len(idx)-1)]

def path(parts, tol, close=False, min_len=0.0, dec=1):
    """dec=0 for the faint layers. A tenth of a map unit is a seventh of a
       pixel at the size this renders; carrying it costs 20% of the file and
       buys nothing the eye can see."""
    fmt = "{:.0f},{:.0f}" if dec == 0 else "{:.1f},{:.1f}"
    out, kept, last = [], 0, None
    for pts in parts:
        q = [proj(x, y) for x, y in pts]
        q = rdp(q, tol)
        if len(q) < 2: continue
        if min_len and length(q) < min_len: continue
        s = [fmt.format(x, y) for x, y in q]
        if dec == 0:                       # drop points the rounding merged
            s = [v for i, v in enumerate(s) if i == 0 or v != s[i-1]]
            if len(s) < 2: continue
        d = "M" + " ".join(s)
        if close: d += "Z"
        out.append(d); kept += 1
    return " ".join(out), kept

def read(name):
    g = glob.glob(f"{T}/{name}/*.shp")
    if not g: return None
    return shapefile.Reader(g[0])

layers = {}
def emit(key, d, kept, note=""):
    layers[key] = d
    print(f"  {key:16s} {len(d):>8,} chars  {kept:>5} parts  {note}")

print(f"frame -> viewBox 0 0 {VB_W:.0f} {VB_H:.1f}\n")

# ---- counties --------------------------------------------------------------
r = read("cb_county")
flds = [f[0] for f in r.fields[1:]]
parts = []
for sr in r.iterShapeRecords():
    rec = dict(zip(flds, sr.record))
    if rec["STATEFP"] != "47" or not in_frame(sr.shape.bbox): continue
    parts += parts_of(sr.shape)
emit("county", *path(parts, 1.4, close=True))

# ---- city limits -----------------------------------------------------------
r = read("tl_2023_47_place")
flds = [f[0] for f in r.fields[1:]]
parts, names = [], []
for sr in r.iterShapeRecords():
    rec = dict(zip(flds, sr.record))
    if rec["STATEFP"] != "47": continue
    x0, y0, x1, y1 = sr.shape.bbox
    cx, cy = (x0+x1)/2, (y0+y1)/2
    if not (LON0-0.05 < cx < LON1+0.05 and LAT0-0.05 < cy < LAT1+0.05): continue
    parts += parts_of(sr.shape)
    names.append(rec["NAME"])
emit("place", *path(parts, 1.7, close=True, dec=0), note=", ".join(sorted(names)[:9]))

# ---- water: lakes and river polygons ---------------------------------------
parts = []
for c in ("47037", "47187", "47021", "47119"):
    r = read(f"tl_2023_{c}_areawater")
    if not r: continue
    flds = [f[0] for f in r.fields[1:]]
    for sr in r.iterShapeRecords():
        rec = dict(zip(flds, sr.record))
        if not in_frame(sr.shape.bbox): continue
        if rec["AWATER"] < 40000: continue          # drop farm ponds
        parts += parts_of(sr.shape)
emit("waterarea", *path(parts, 0.7, close=True))

# ---- water: rivers and creeks ----------------------------------------------
parts = []
for c in ("47037", "47187"):
    r = read(f"tl_2023_{c}_linearwater")
    if not r: continue
    flds = [f[0] for f in r.fields[1:]]
    for sr in r.iterShapeRecords():
        rec = dict(zip(flds, sr.record))
        if not in_frame(sr.shape.bbox): continue
        if rec["MTFCC"] not in ("H3010", "H3013", "H3020"): continue
        parts += parts_of(sr.shape)
emit("waterline", *path(parts, 1.1, min_len=14.0, dec=0))

# ---- roads -----------------------------------------------------------------
r = read("tl_2023_47_prisecroads")
flds = [f[0] for f in r.fields[1:]]
prim, sec = [], []
for sr in r.iterShapeRecords():
    rec = dict(zip(flds, sr.record))
    if not in_frame(sr.shape.bbox): continue
    (prim if rec["MTFCC"] == "S1100" else sec).extend(parts_of(sr.shape))
emit("primary",   *path(prim, 0.55))
emit("secondary", *path(sec,  1.0, dec=0))

local = []
for c in ("47037", "47187"):
    r = read(f"tl_2023_{c}_roads")
    flds = [f[0] for f in r.fields[1:]]
    for sr in r.iterShapeRecords():
        rec = dict(zip(flds, sr.record))
        if rec["MTFCC"] != "S1400" or not in_frame(sr.shape.bbox): continue
        local += parts_of(sr.shape)
emit("local", *path(local, 1.8, min_len=8.0, dec=0), note="the city texture")

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "map-basemap.json")
json.dump({"viewBox": f"0 0 {VB_W:.0f} {VB_H:.1f}", "layers": layers}, open(out, "w"))
total = sum(len(v) for v in layers.values())
print(f"\n  TOTAL {total:,} chars of path data")
