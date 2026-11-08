import shapefile, glob, json, math, re

# ---- the frame -------------------------------------------------------------
LAT0, LAT1 = 35.675, 36.370
LON0, LON1 = -87.075, -86.600
K = math.cos(math.radians((LAT0+LAT1)/2))        # x compression at this latitude

Wp = (LON1-LON0)*K
Hp = (LAT1-LAT0)
VB_W = 1000.0
VB_H = VB_W*Hp/Wp
def proj(lon, lat):
    x = (lon-LON0)*K/Wp*VB_W
    y = (LAT1-lat)/Hp*VB_H
    return x, y

print(f'frame {LAT0}-{LAT1} N, {LON0}-{LON1} W  ->  viewBox 0 0 {VB_W:.0f} {VB_H:.1f}  (w:h 1:{VB_H/VB_W:.2f})')

def inframe(lon,lat): return LON0-0.2<lon<LON1+0.2 and LAT0-0.2<lat<LAT1+0.2

def simplify(pts, tol):
    """Ramer-Douglas-Peucker."""
    if len(pts)<3: return pts
    def rdp(p):
        if len(p)<3: return p
        (x0,y0),(x1,y1)=p[0],p[-1]
        dx,dy=x1-x0,y1-y0; m=math.hypot(dx,dy)
        best,bi=-1,0
        for i in range(1,len(p)-1):
            x,y=p[i]
            d = abs(dy*x-dx*y+x1*y0-y1*x0)/m if m else math.hypot(x-x0,y-y0)
            if d>best: best,bi=d,i
        if best>tol:
            return rdp(p[:bi+1])[:-1]+rdp(p[bi:])
        return [p[0],p[-1]]
    import sys; sys.setrecursionlimit(10000)
    return rdp(pts)

def path(parts, tol=1.2, close=False):
    out=[]
    for pts in parts:
        pts=[proj(x,y) for x,y in pts]
        pts=simplify(pts, tol)
        if len(pts)<2: continue
        d='M'+' L'.join(f'{x:.1f},{y:.1f}' for x,y in pts)
        if close: d+=' Z'
        out.append(d)
    return ' '.join(out)

geo={'viewBox':f'0 0 {VB_W:.0f} {VB_H:.1f}','w':VB_W,'h':round(VB_H,1),
     'frame':dict(lat0=LAT0,lat1=LAT1,lon0=LON0,lon1=LON1,k=K)}

# ---- counties --------------------------------------------------------------
r=shapefile.Reader(glob.glob('tiger/cb_2023_us_county_500k/*.shp')[0])
flds=[f[0] for f in r.fields[1:]]
counties=[]
for sr in r.iterShapeRecords():
    rec=dict(zip(flds, sr.record))
    if rec['STATEFP']!='47': continue
    bx=sr.shape.bbox
    if bx[2]<LON0-0.2 or bx[0]>LON1+0.2 or bx[3]<LAT0-0.2 or bx[1]>LAT1+0.2: continue
    pts=sr.shape.points; parts=list(sr.shape.parts)+[len(pts)]
    rings=[pts[parts[i]:parts[i+1]] for i in range(len(parts)-1)]
    rings=[rr for rr in rings if len(rr)>8]
    d=path(rings, tol=1.1, close=True)
    xs=[float(m) for m in re.findall(r'(-?\d+\.\d)(?=,)', d)]
    ys=[float(m) for m in re.findall(r',(-?\d+\.\d)', d)]
    if not xs or min(xs)>VB_W or max(xs)<0 or min(ys)>VB_H or max(ys)<0: continue
    counties.append(dict(name=rec['NAME'], d=d))
geo['counties']=counties
print('counties:', ', '.join(c['name'] for c in counties))

# ---- interstates -----------------------------------------------------------
r=shapefile.Reader(glob.glob('tiger/tl_2023_47_prisecroads/*.shp')[0])
flds=[f[0] for f in r.fields[1:]]
roads={}
for sr in r.iterShapeRecords():
    rec=dict(zip(flds, sr.record))
    if rec['RTTYP']!='I': continue
    bx=sr.shape.bbox
    if bx[2]<LON0 or bx[0]>LON1 or bx[3]<LAT0 or bx[1]>LAT1: continue
    nm=(rec['FULLNAME'] or '').strip()
    roads.setdefault(nm, []).append(sr.shape.points)
geo['roads']=[dict(name=k, d=path(v, tol=1.6)) for k,v in sorted(roads.items())]
print('interstates:', ', '.join(k for k in sorted(roads)))

# ---- rivers ----------------------------------------------------------------
want=('cumberland','harpeth')
rivers={}
for shp in glob.glob('tiger/tl_2023_*_linearwater/*.shp'):
    r=shapefile.Reader(shp); flds=[f[0] for f in r.fields[1:]]
    for sr in r.iterShapeRecords():
        rec=dict(zip(flds, sr.record))
        nm=(rec['FULLNAME'] or '')
        low=nm.lower()
        if not any(w in low for w in want): continue
        if 'branch' in low or ' br' == low[-3:]: continue
        bx=sr.shape.bbox
        if bx[2]<LON0 or bx[0]>LON1 or bx[3]<LAT0 or bx[1]>LAT1: continue
        key='Cumberland River' if 'cumberland' in low else 'Harpeth River'
        rivers.setdefault(key, []).append(sr.shape.points)
geo['rivers']=[dict(name=k, d=path(v, tol=1.0)) for k,v in sorted(rivers.items())]
print('rivers:', {k:len(v) for k,v in rivers.items()})

# ---- the pins --------------------------------------------------------------
pts=json.load(open('points.json'))
for p in pts:
    x,y=proj(p['lon'],p['lat']); p['x']=round(x,1); p['y']=round(y,1)
geo['points']=pts
json.dump(geo, open('geo.json','w'))
tot=sum(len(c['d']) for c in counties)+sum(len(r['d']) for r in geo['roads'])+sum(len(r['d']) for r in geo['rivers'])
print(f'\npath payload ~{tot/1024:.1f} KB')
print('pin x range %.0f-%.0f  y range %.0f-%.0f  (viewBox %s)'%(
   min(p["x"] for p in pts),max(p["x"] for p in pts),
   min(p["y"] for p in pts),max(p["y"] for p in pts), geo['viewBox']))
