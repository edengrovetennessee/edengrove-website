import json, math, html
g=json.load(open('geo.json')); pts=g['points']
W,H=g['w'],g['h']

# ---- 1. separate coincident dots ------------------------------------------
MIN=18.0
moved=[]
for _ in range(60):
    hit=False
    for i in range(len(pts)):
        for j in range(i+1,len(pts)):
            a,b=pts[i],pts[j]
            dx,dy=b['x']-a['x'], b['y']-a['y']
            d=math.hypot(dx,dy)
            if d>=MIN: continue
            if d<0.01: dx,dy,d=1.0,0.0,1.0
            push=(MIN-d)/2
            ux,uy=dx/d,dy/d
            a['x']-=ux*push; a['y']-=uy*push
            b['x']+=ux*push; b['y']+=uy*push
            hit=True
            if {a['name'],b['name']} not in [set(m) for m in moved]: moved.append((a['name'],b['name']))
    if not hit: break
for p in pts: p['x']=round(p['x'],1); p['y']=round(p['y'],1)
print('separated:', moved)

# ---- 2. place the labels -------------------------------------------------
# Greedy candidate placement. Vertical nudging alone could not solve the
# Brentwood cluster - Annandale, Cielo, Harlan and Brentwood itself inside
# forty units - because with four labels in that space the only way out is
# sideways. Each label gets eight candidate positions and takes the cheapest
# one that is still free, neighbourhoods first so the places win over the
# subdivisions.
CH, LHT = 7.6, 26.0          # char width, line height
R = 13.0                     # a dot plus its ring
CAND = [                     # (dx, dy, anchor, penalty)
    ( 16,   5, 'start', 0), (-16,   5, 'end',   1),
    ( 16, -17, 'start', 3), (-16, -17, 'end',   4),
    ( 16,  27, 'start', 3), (-16,  27, 'end',   4),
    (  0, -22, 'middle',6), (  0,  32, 'middle',6),
]
def bbox(p, dx, dy, anc):
    w = len(p['name'])*CH
    x = p['x']+dx
    if anc=='start': x0,x1 = x, x+w
    elif anc=='end': x0,x1 = x-w, x
    else:            x0,x1 = x-w/2, x+w/2
    y = p['y']+dy
    return x0, x1, y-LHT*0.55, y+LHT*0.45

def overlap(A,B):
    return max(0, min(A[1],B[1])-max(A[0],B[0])) * max(0, min(A[3],B[3])-max(A[2],B[2]))

placed=[]
for p in sorted(pts, key=lambda q:(q['kind']!='neighborhood', q['y'])):
    best=None
    for dx,dy,anc,pen in CAND:
        B=bbox(p,dx,dy,anc)
        cost=pen*40.0
        if B[0]<4 or B[1]>W-4 or B[2]<12 or B[3]>H-6: cost+=12000
        for q in pts:                       # never sit on a pin
            if q is p: continue
            if B[0]-R < q['x'] < B[1]+R and B[2]-R < q['y'] < B[3]+R: cost += 2600
        for Q in placed: cost += overlap(B,Q)*5
        if best is None or cost<best[0]: best=(cost,dx,dy,anc,B)
    cost,dx,dy,anc,B = best
    p['dx'],p['dy'],p['anchor'],p['cost']=dx,dy,anc,round(cost,1)
    placed.append(B)

bad=[(p['name'],p['cost']) for p in pts if p['cost']>500]
print('labels still fighting:', bad or 'none')
print('max cost %.0f' % max(p['cost'] for p in pts))

# ---- 3. emit ---------------------------------------------------------------
HREF={'neighborhood':'neighborhood/{}/','development':'development/{}/'}
L=[f'<svg class="mp__svg" viewBox="{g["viewBox"]}" role="group" aria-labelledby="mp-title mp-desc" preserveAspectRatio="xMidYMid meet">',
   '  <title id="mp-title">Middle Tennessee</title>',
   '  <desc id="mp-desc">Twelve neighbourhoods and fourteen developments, each at its true position '
   'between Joelton and Spring Hill. Every one is a link to its page.</desc>',
   '  <g class="mp__land" aria-hidden="true">']
for c in g['counties']: L.append(f'    <path class="mp__county" d="{c["d"]}"/>')
for r in g['rivers']:   L.append(f'    <path class="mp__river" d="{r["d"]}"/>')
for r in g['roads']:    L.append(f'    <path class="mp__road" d="{r["d"]}"/>')
L.append('  </g>')
L.append('  <g class="mp__pins">')
order=sorted(pts,key=lambda p:(p['kind']!='neighborhood',p['name']))
for i,p in enumerate(order):
    href=HREF[p['kind']].format(p['slug'])
    cls='mp__pin mp__pin--dev' if p['kind']=='development' else 'mp__pin'
    nm=html.escape(p['name']); kind='development' if p['kind']=='development' else 'neighbourhood'
    L+= [f'    <a class="{cls}" href="{href}" style="--d:{(i*0.23)%3.0:.2f}s" aria-label="{nm}, {kind}">',
         f'      <title>{nm} &#8212; {kind}</title>',
         f'      <circle class="mp__ring" cx="{p["x"]}" cy="{p["y"]}" r="7"/>',
         f'      <circle class="mp__dot"  cx="{p["x"]}" cy="{p["y"]}" r="6"/>',
         f'      <text class="mp__lbl" x="{p["x"]+p["dx"]}" y="{p["y"]+round(p["dy"],1)}" text-anchor="{p["anchor"]}">{nm}</text>',
         f'      <circle class="mp__hit" cx="{p["x"]}" cy="{p["y"]}" r="26"/>',
         '    </a>']
L.append('  </g>\n</svg>')
open('pins.svg','w').write('\n'.join(L))
json.dump(g, open('geo.json','w'))
print('svg written')
