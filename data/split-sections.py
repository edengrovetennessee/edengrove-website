"""Splits the listings grid on properties.html into New Construction and Resale.

Ryan, 12 Nov: two resale listings, 2502 9th Ave S and 4303A Utah Ave;
everything else is new construction.

The two axes are independent and stay that way. New construction vs resale
is what the house IS; Active vs Private Exclusive is where it is in its
life. A new build can be actively listed, so the status plate on the card
is untouched and only the grouping is new.

A card whose address is not in the roster stops the run rather than being
dropped into a section on a guess.
"""
import re, sys

import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = OUT = os.path.join(ROOT, "properties.html")   # rewrites in place

RESALE = {"2502 9th Ave S", "4303A Utah Ave"}

h = open(SRC, encoding="utf-8").read()

OPEN = '<section class="listings" aria-label="Listings">\n  <div class="listings__grid">'
assert h.count(OPEN) == 1, "grid opener"
start = h.index(OPEN)
end = h.index("\n  </div>\n</section>", start)
inner = h[start + len(OPEN):end]

# A card is the <a> plus whatever sits above it, because several carry a
# comment explaining why that one has no price or no city. Splitting them
# off would file the explanation under the wrong house.
spans = [(m.start(), m.end()) for m in
         re.finditer(r'<a class="prop(?: prop--pe)?".*?\n    </a>', inner, re.S)]
assert spans, "no cards found"
cards, prev = [], 0
for s, e in spans:
    cards.append(inner[prev:e])
    prev = e
tail = inner[prev:].strip()
assert not tail, f"markup after the last card: {tail[:200]}"

new, res, unknown = [], [], []
for c in cards:
    m = re.search(r'class="prop__addr">(.*?)<', c, re.S)
    assert m, "card with no address"
    addr = re.sub(r"\s+", " ", m.group(1)).strip()
    (res if addr in RESALE else new).append((addr, c))

print(f"{len(cards)} cards -> {len(new)} new construction, {len(res)} resale")
assert len(res) == len(RESALE), (
    f"expected {len(RESALE)} resale, matched {len(res)}: {[a for a,_ in res]}")

def group(title, note, cards, first=False):
    return (f'''\n
  <div class="listings__head{' listings__head--first' if first else ''}">
    <h2 class="listings__h">{title}</h2>
    <p class="listings__n">{note}</p>
  </div>
  <div class="listings__grid">'''
            + "".join(c for _, c in cards) + "\n  </div>")

body = (group("New Construction",
              "Built with our own builders. Most are Private Exclusives and "
              "never reach the open market.", new, first=True)
        + group("Resale", "On the market now.", res))

h = h[:start] + '<section class="listings" aria-label="Listings">' + body + h[end + len("\n  </div>"):]

CSS = '''
/* ---- two sections, not one run ----
   New construction and resale are different things to be shopping for, and
   the page was asking a buyer to tell them apart from the photograph. The
   status plate still says Active or Private Exclusive, because that is a
   different question - where the house is in its life, not what it is. */
.listings__head{
  max-width:72rem;margin:clamp(3.2rem,7vh,5rem) auto clamp(1.4rem,3vh,2rem);
  padding:0 clamp(.5rem,1vw,1.1rem);text-align:center;
}
.listings__head--first{margin-top:0}
.listings__h{
  margin:0;font-family:var(--ui);font-weight:300;color:var(--t1,#F4F1EC);
  font-size:clamp(.82rem,.76rem + .26vw,1rem);
  letter-spacing:.3em;text-indent:.3em;text-transform:uppercase;
}
.listings__n{
  max-width:34rem;margin:.9rem auto 0;font-weight:300;
  font-size:clamp(.78rem,.75rem + .16vw,.86rem);
  line-height:1.8;color:var(--warm,#A7947C);
}
'''
anchor = "@media (max-width:760px){\n  .listings__grid{grid-template-columns:1fr}"
assert h.count(anchor) == 1, "css anchor"
h = h.replace(anchor, CSS + anchor, 1)

open(OUT, "w", encoding="utf-8").write(h)
print(f"wrote {OUT}  {len(h):,} chars")
for a, _ in res:
    print(f"  resale: {a}")
