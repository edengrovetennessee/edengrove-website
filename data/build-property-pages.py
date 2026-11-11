"""
Generates a page for every property in properties.json that has not got one
by hand.

WHY A GENERATOR. There are fourteen of these and they are the same page with
different blanks. Hand-writing fourteen means fourteen places to fix the day
the follow-the-build endpoint changes, and the fourteenth will be missed.

WHAT IS DELIBERATE HERE

  The blanks are printed. The older preliminary pages left a fact out
  entirely when it was unknown, on the grounds that a heading with nothing
  under it is worse than no heading. Ryan reversed that on 11 Nov and he is
  right for these: a visitor looking at a house that does not exist yet
  wants to see that square footage is a question nobody has answered, not
  wonder whether we forgot to say. An unknown prints a rule, not a zero and
  not a guess.

  The chrome is not retyped. Head, nav and footer are lifted out of a donor
  page at build time, so these fourteen follow the rest of the site when the
  nav or the footer changes rather than drifting away from it.

  A property with no agent gets no signup form. The point of the form is
  that the lead lands in somebody's book; with agent null there is nobody
  to land it with, so the page offers the team's number instead of
  collecting an address it cannot route. Fill agent in, re-run, the form
  appears.

RUN IT from the repo root:
    python3 data/build-property-pages.py            # writes every page
    python3 data/build-property-pages.py 735-clematis   # just one
"""
import json, os, re, sys, urllib.parse

ROOT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DONOR = os.path.join(ROOT, "property/1211-jefferson-davis/index.html")
DATA  = os.path.join(ROOT, "data/properties.json")

# Where a follow-the-build signup goes. One constant, fourteen pages: when
# this moves from the contact endpoint to the CRM one, it moves here only.
FOLLOW_ENDPOINT = "https://dashboard.edengrovetennessee.com/__contact"

def esc(s): return (s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                     .replace('"',"&quot;"))

def chrome():
    """head, the nav bar, and everything from the footer down, from the donor."""
    h = open(DONOR, encoding="utf-8").read()
    head  = h[:h.index("<body")]
    bar   = h[h.index('<header class="bar"'): h.index("</header>") + len("</header>")]
    tail  = h[h.index('<footer class="foot"'):]
    return head, bar, tail

def head_for(p, head):
    """Retitle the donor's head for this property. Everything else - the
       stylesheet, the fonts, the favicons - is shared and left alone."""
    full = p["address"] + (f', {p["town"]} {p["state"]} {p["zip"]}' if p["town"] else "")
    url  = f'https://edengrovetennessee.com/property/{p["slug"]}/'
    desc = (f'{p["address"]} &mdash; a Private Exclusive coming to '
            f'{p["town"]}.' if p["town"] else
            f'{p["address"]} &mdash; a Private Exclusive. Register interest.')
    out = head
    out = re.sub(r"<title>.*?</title>", f"<title>{esc(full)} | Eden Grove</title>", out, flags=re.S)
    out = re.sub(r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{url}">', out)
    out = re.sub(r'(<meta property="og:url" content=")[^"]*(">)', rf'\g<1>{url}\g<2>', out)
    for k in ("og:title", "twitter:title"):
        tag = "property" if k.startswith("og") else "name"
        out = re.sub(rf'(<meta {tag}="{k}" content=")[^"]*(">)',
                     rf'\g<1>{esc(full)} | Eden Grove\g<2>', out)
    for k in ("og:description", "twitter:description"):
        tag = "property" if k.startswith("og") else "name"
        out = re.sub(rf'(<meta {tag}="{k}" content=")[^"]*(">)', rf'\g<1>{desc}\g<2>', out)
    return out + VEIL_CSS

VEIL_CSS = '''<style>
/* ================== COMING SOON: THE VEILED HERO ========================
   A house that does not exist yet has no photograph of itself. The frame
   still has to hold the top of the page, so it holds a veil: the image
   pushed far out of focus, darkened, and scaled up so no blurred edge
   shows inside the frame, with the status over the middle of it.

   Blur is a filter, not a crop, so the edges of the element go soft and
   let the page through unless the image is scaled past the blur radius.
   28px of blur needs about 8% of scale to cover; 1.12 is comfortable.

   WITH NO IMAGE AT ALL the frame falls back to a ground rather than a
   stand-in photograph of somebody else's house. A blurred picture of the
   wrong building is still a picture of the wrong building. */
.p-hero--veil .hero__media{
  filter:blur(28px) saturate(.68) brightness(.52);
  transform:scale(1.12);
}
.p-hero--veil .hero__scrim{background:
  radial-gradient(120% 90% at 50% 45%, rgba(20,23,15,.35) 0%, rgba(20,23,15,.78) 70%),
  linear-gradient(180deg, rgba(20,23,15,.86) 0%, rgba(20,23,15,.3) 26%, rgba(20,23,15,.9) 100%);
}
.p-hero--veil.p-hero--noimg{
  background:
    radial-gradient(130% 80% at 50% 38%, #23271d 0%, #171a12 55%, #0f1209 100%);
}
.p-hero--noimg .hero__media{display:none}
.p-hero__soon{
  display:block;margin:0 0 clamp(1.2rem,3vh,1.8rem);
  font-family:var(--ui);font-weight:300;
  font-size:clamp(.66rem,.6rem + .3vw,.86rem);
  letter-spacing:.46em;text-indent:.46em;text-transform:uppercase;
  color:var(--w1);
}
/* The hero body is left aligned on every property page, so the rule under
   the words is too. Centring it put a stray brass dash out in the middle
   of the frame with nothing above it. */
.p-hero__soon::after{
  content:"";display:block;width:2.6rem;height:1px;
  background:var(--brass);margin:clamp(1rem,2.4vh,1.4rem) 0 0;
}

/* ---- the facts, blanks included ----
   A dash is not decoration. It is the page saying this is a real question
   with no answer yet, which is different from the page forgetting. */
.p-facts{
  max-width:52rem;margin:clamp(2.2rem,5vh,3.2rem) auto 0;padding:0;
  display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 clamp(1.6rem,4vw,3rem);
}
@media (max-width:620px){ .p-facts{grid-template-columns:1fr;max-width:26rem} }
.p-facts > div{
  display:flex;align-items:baseline;justify-content:space-between;gap:1rem;
  border-top:1px solid var(--line);padding:.95rem 0;
}
.p-facts dt{
  font-family:var(--ui);font-weight:400;
  font-size:clamp(.58rem,.55rem + .14vw,.66rem);
  letter-spacing:.24em;text-transform:uppercase;color:var(--warm);
}
.p-facts dd{
  margin:0;font-family:var(--ui);font-weight:300;color:var(--t1);
  font-size:clamp(.86rem,.82rem + .2vw,.98rem);letter-spacing:.08em;
}
.p-facts dd.tbc{color:var(--t2);letter-spacing:.3em}

/* ---- follow the build ---- */
.p-follow{
  max-width:40rem;margin:clamp(2.2rem,5vh,3rem) auto 0;
  border:1px solid var(--line);padding:clamp(1.8rem,4.5vh,2.8rem) var(--gutter);
}
.p-follow__h{
  margin:0;text-align:center;font-family:var(--ui);font-weight:300;color:var(--t1);
  font-size:clamp(.96rem,.9rem + .3vw,1.14rem);
  letter-spacing:.16em;text-indent:.16em;text-transform:uppercase;
}
.p-follow__p{
  margin:1.1rem 0 0;text-align:center;font-weight:300;
  font-size:clamp(.84rem,.8rem + .18vw,.94rem);line-height:1.85;color:var(--t2);
}
.p-follow form{margin:clamp(1.6rem,3.5vh,2.2rem) 0 0;display:grid;gap:1.1rem}
.p-follow input{
  width:100%;background:none;border:0;border-bottom:1px solid var(--line);
  color:#fff;font-family:var(--ui);font-weight:300;font-size:.92rem;
  padding:.85rem .2rem;transition:border-color .4s var(--rise);
}
.p-follow input:focus{outline:none;border-bottom-color:var(--brass)}
.p-follow input::placeholder{color:var(--t3)}
.p-follow button{
  justify-self:center;margin-top:.6rem;background:none;border:0;cursor:pointer;
  padding:0 0 .5rem;border-bottom:1px solid var(--brass);
  font-family:var(--ui);font-weight:400;
  font-size:clamp(.64rem,.6rem + .14vw,.72rem);
  letter-spacing:.28em;text-indent:.28em;text-transform:uppercase;color:var(--t1);
  transition:color .4s var(--rise);
}
.p-follow button:hover,.p-follow button:focus-visible{color:var(--brass);outline:none}
.p-follow__fine{
  margin:1.4rem 0 0;text-align:center;font-weight:300;
  font-size:clamp(.7rem,.68rem + .12vw,.78rem);line-height:1.8;color:var(--warm);
}
/* Off screen, not display:none - some bots skip anything that is hidden
   outright, and a honeypot nothing fills in catches nothing. */
.p-follow__pot{position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden}
</style>
'''

FACTS = [("Status","status"),("Price","price"),("Square Feet","sqft"),
         ("Bedrooms","beds"),("Bathrooms","baths"),("Acreage","acres"),
         ("MLS","mls"),("Completion","completion")]

def facts_block(p):
    rows = []
    for label, key in FACTS:
        v = p.get(key)
        if v:
            rows.append(f'    <div><dt>{label}</dt><dd>{esc(str(v))}</dd></div>')
        else:
            rows.append(f'    <div><dt>{label}</dt><dd class="tbc">&mdash;</dd></div>')
    return "\n".join(rows)

def page(p, agents, head, bar, tail):
    A = agents.get(p["agent"]) if p["agent"] else None
    full = p["address"] + (f', {p["town"]}, {p["state"]} {p["zip"]}' if p["town"] else "")
    h1 = (f'{esc(p["address"])}<br>{esc(p["town"])}, {p["state"]} {p["zip"]}'
          if p["town"] else esc(p["address"]))
    hero_cls = "p-hero p-hero--veil" + ("" if p["hero"] else " p-hero--noimg")
    hero_img = (f'\n  <img class="hero__media" src="../../media/{p["hero"]}" alt="" aria-hidden="true">'
                if p["hero"] else "")

    # --- the parts that only exist when we know something -------------------
    loc = ""
    if p["town"]:
        q = urllib.parse.quote(full)
        hood_link = ""
        if p["hood"]:
            slug = p["hood"].lower().replace(" ", "-").replace("'", "")
            hood_link = (f'\n    <p><a class="prop__cta" href="../../neighborhood/{slug}/">Explore {esc(p["hood"])}'
                         '\n      <svg viewBox="0 0 8 8" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true">'
                         '\n        <path d="M2 1l3 3-3 3"/></svg></a></p>')
        loc = f'''
<!-- ================================ LOCATION ============================== -->
<section class="p-sec" aria-labelledby="hood-h">
  <h2 class="p-eyebrow" id="hood-h">{esc(p["hood"] or p["town"])}</h2>
  <div class="p-lede">{hood_link}
  </div>
  <div class="p-map">
    <p class="p-map__addr">{esc(full)}</p>
    <div class="p-map__frame">
      <iframe title="Map &mdash; {esc(full)}"
        src="https://www.google.com/maps?q={q}&amp;output=embed"
        loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>
    </div>
  </div>
</section>
'''

    builder = ""
    if p["builder"] == "liebo":
        builder = '''
<!-- ============================ BEHIND THE BUILD ========================== -->
<section class="p-sec p-sec--tight" aria-labelledby="build-h">
  <h2 class="p-eyebrow" id="build-h">Behind the Build</h2>
  <div class="p-lede">
    <p>Built by <strong>Liebo&nbsp;Builders</strong> &mdash; a Los&nbsp;Angeles
       design&ndash;build firm with more than twenty years and $250M in
       delivered work, now building in Middle&nbsp;Tennessee.</p>
    <p><a class="prop__cta" href="../../developer/liebo-builders/">Liebo Builders
      <svg viewBox="0 0 8 8" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true">
        <path d="M2 1l3 3-3 3"/></svg></a></p>
  </div>
</section>
'''

    # --- follow the build ---------------------------------------------------
    if p["follow"] and A:
        follow = f'''
<!-- ============================ FOLLOW THE BUILD ==========================
     Posts to the shared endpoint, which is rate limited and strips the
     honeypot server side. topic is what routes it: it carries the address
     so the signup lands against this property and with {esc(A["name"])}. -->
<section class="p-sec p-sec--tight" aria-labelledby="fol-h">
  <h2 class="p-eyebrow" id="fol-h">Follow the Build</h2>
  <div class="p-follow">
    <p class="p-follow__h">Watch it go up</p>
    <p class="p-follow__p">One email a week while this house is being built
       &mdash; a room, a drawing, or what changed on site. Nothing else, and
       you can stop any time.</p>
    <form id="folForm" novalidate>
      <label class="visually-hidden" for="folName">Name</label>
      <input id="folName" name="name" placeholder="Name" autocomplete="name" required>
      <label class="visually-hidden" for="folEmail">Email</label>
      <input id="folEmail" name="email" type="email" placeholder="Email" autocomplete="email" required>
      <div class="p-follow__pot" aria-hidden="true">
        <label for="folWebsite">Leave this empty</label>
        <input id="folWebsite" name="website" type="text" tabindex="-1" autocomplete="off">
      </div>
      <button type="submit">Follow this build</button>
    </form>
    <p class="p-follow__fine" id="folNote" role="status">Weekly build updates for
       {esc(p["address"])} only. We do not sell or share your address.</p>
  </div>
</section>
'''
        follow_js = f'''
<script>
/* The follow-the-build signup. One endpoint for every property; the topic
   is what says which house and therefore whose book the lead lands in. */
(() => {{
  const f = document.getElementById("folForm");
  if (!f) return;
  const note = document.getElementById("folNote");
  const rest = note.textContent;
  f.addEventListener("submit", async e => {{
    e.preventDefault();
    const d = new FormData(f);
    if (d.get("website")) return;                 // a bot filled the honeypot
    const name = (d.get("name") || "").trim(), email = (d.get("email") || "").trim();
    if (!name || !/^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$/.test(email)) {{
      note.textContent = "A name and an email address, please."; return;
    }}
    note.textContent = "Sending\\u2026";
    try {{
      const r = await fetch({json.dumps(FOLLOW_ENDPOINT)}, {{
        method: "POST", headers: {{ "content-type": "application/json" }},
        body: JSON.stringify({{
          name, email, website: "",
          topic: {json.dumps(p["address"] + " build updates")},
          message: {json.dumps("Follow the build signup - " + full + ". Listing agent: " + (A["name"] if A else "unassigned") + ".")}
        }})
      }});
      note.textContent = r.ok
        ? "You are on the list. The first update comes the next time there is something to show."
        : "That did not send. Call or text {esc(A["name"])} at {A["tel"][:3]}.{A["tel"][3:6]}.{A["tel"][6:]}.";
    }} catch {{
      note.textContent = "That did not send. Call or text {esc(A["name"])} at {A["tel"][:3]}.{A["tel"][3:6]}.{A["tel"][6:]}.";
    }}
    setTimeout(() => {{ note.textContent = rest; }}, 9000);
  }});
}})();
</script>
'''
    else:
        follow = '''
<!-- ============================ FOLLOW THE BUILD ==========================
     NO FORM ON PURPOSE. This property has no listing agent set in
     data/properties.json, so a signup has nobody to land with. Rather than
     collect an address the site cannot route, the page says who to call.
     Set "agent" and re-run the generator and the form appears. -->
<section class="p-sec p-sec--tight" aria-labelledby="fol-h">
  <h2 class="p-eyebrow" id="fol-h">Follow the Build</h2>
  <div class="p-lede">
    <p>Weekly updates on this build go out as it goes up. To be added, call or
       text <a href="tel:+16158120066">(615)&nbsp;812-0066</a> or email
       <a href="mailto:connect@edengrovetennessee.com">connect@edengrovetennessee.com</a>.</p>
  </div>
</section>
'''
        follow_js = ""

    # --- presented by -------------------------------------------------------
    if A:
        tel = f'({A["tel"][:3]}) {A["tel"][3:6]}-{A["tel"][6:]}'
        presented = f'''
<!-- =============================== PRESENTED ============================== -->
<section class="p-sec p-sec--tight" aria-labelledby="agents-h">
  <h2 class="p-eyebrow" id="agents-h">Presented By</h2>
  <div class="p-agents p-agents--1">
    <div class="p-agent">
      <div class="p-agent__photo">
        <img src="../../media/{A["photo"]}" alt="{esc(A["name"])}" loading="lazy" decoding="async">
      </div>
      <p class="p-agent__name">{esc(A["name"])}</p>
      <ul>
        <li>Eden Grove at Compass</li>
        <li><a href="tel:+1{A["tel"]}">{tel}</a></li>
        <li><a href="mailto:{A["email"]}">{A["email"]}</a></li>
        <li><a href="../../team.html">edengrovetennessee.com</a></li>
      </ul>
    </div>
  </div>
</section>
'''
    else:
        presented = '''
<!-- =============================== PRESENTED ==============================
     PENDING: no listing agent set for this property. -->
<section class="p-sec p-sec--tight" aria-labelledby="agents-h">
  <h2 class="p-eyebrow" id="agents-h">Presented By</h2>
  <div class="p-lede">
    <p>Eden Grove at Compass &mdash;
       <a href="tel:+16158120066">(615)&nbsp;812-0066</a>,
       <a href="mailto:connect@edengrovetennessee.com">connect@edengrovetennessee.com</a>.</p>
  </div>
</section>
'''

    body = f'''<body>

<!-- ==========================================================================
     {full.upper()}

     GENERATED. Do not hand-edit: run data/build-property-pages.py, which
     rebuilds this from data/properties.json and the chrome of the donor
     page. Anything typed in here is lost on the next run.

     Every fact this page has not got prints a rule rather than being left
     out, so the gap is visible and someone can fill it.
     ========================================================================== -->

<section class="{hero_cls}" id="top">{hero_img}
  <div class="hero__scrim"></div>
{bar}

  <div class="p-hero__body">
    <div class="reveal" style="animation-delay:.5s">
      <span class="p-hero__soon">Coming Soon</span>
      <span class="p-hero__status">{esc(p["status"])}</span>
      <h1>{h1}</h1>
      <a class="p-hero__cta" href="#inquire">Register Interest</a>
    </div>
  </div>
</section>

<!-- ============================== THE RESIDENCE =========================== -->
<section class="p-sec" aria-labelledby="res-h">
  <h2 class="p-eyebrow" id="res-h">The Residence</h2>
  <div class="p-story">
    <p>It is early here. What is settled is on this page; what is not is shown
       as a blank rather than guessed at, and fills in as the house does.</p>
  </div>

  <dl class="p-facts">
{facts_block(p)}
  </dl>
</section>
{builder}{loc}{follow}{presented}
<!-- ================================ INQUIRE =============================== -->
<section class="p-sec p-sec--tight" id="inquire" aria-labelledby="enq-h">
  <h2 class="p-eyebrow" id="enq-h">Inquiries</h2>
  <div class="p-lede">
    <p>This is a Private Exclusive and is not on the open market. To ask about
       it, call or text <a href="tel:+16158120066">(615)&nbsp;812-0066</a> or
       email <a href="mailto:connect@edengrovetennessee.com?subject={urllib.parse.quote(p["address"])}">connect@edengrovetennessee.com</a>.</p>
  </div>
</section>

'''
    return head_for(p, head) + body + tail.replace("</body>", follow_js + "</body>")

def main():
    cfg = json.load(open(DATA, encoding="utf-8"))
    head, bar, tail = chrome()
    want = sys.argv[1:] or None
    n = 0
    for p in cfg["properties"]:
        if want and p["slug"] not in want: continue
        d = os.path.join(ROOT, "property", p["slug"])
        os.makedirs(d, exist_ok=True)
        html = page(p, cfg["agents"], head, bar, tail)
        open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(html)
        flags = []
        if not p["agent"]: flags.append("no agent -> no signup form")
        if not p["hero"]:  flags.append("no image -> veil falls back to a ground")
        if not p["town"]:  flags.append("no town published -> no map")
        print(f'  property/{p["slug"]}/  {len(html):>7,}  {"; ".join(flags) or "complete"}')
        n += 1
    print(f"\n{n} page(s)")

if __name__ == "__main__":
    main()
