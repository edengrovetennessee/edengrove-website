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
    # STATUS DRIVES THE WORDING. This used to say "a Private Exclusive" for
    # every property, which was true of the fourteen that existed when it was
    # written and false the moment one of them went Active: the meta
    # description and the link preview both told the market a listed house
    # was off market. An unrecognised status falls back to the old phrasing
    # rather than to a blank.
    st = (p.get("status") or "").strip()
    LEAD  = {"Private Exclusive": "a Private Exclusive coming to",
             "Coming Soon":       "coming soon to",
             "Active":            "now on the market in"}
    PHASE = {"Private Exclusive": "a Private Exclusive",
             "Coming Soon":       "coming soon",
             "Active":            "now on the market"}
    lead  = LEAD.get(st,  "a Private Exclusive coming to")
    phase = PHASE.get(st, "a Private Exclusive")
    desc = (f'{p["address"]} &mdash; {lead} '
            f'{p["town"]}.' if p["town"] else
            f'{p["address"]} &mdash; {phase}. Register interest.')
    kind = {"new": "New construction", "resale": "A resale"}.get(p.get("kind") or "", "A property")
    where = f' in {p["town"]}' if p["town"] else ""
    desc_plain = (f'{kind}{where} at {p["address"]}, {phase} with '
                  f'Eden Grove at Compass. Follow the build or register interest.')
    out = head
    out = re.sub(r"<title>.*?</title>", f"<title>{esc(full)} | Eden Grove</title>", out, flags=re.S)
    # The donor's own description names Shepherd Group and Chase Pasternak.
    # Lifted wholesale with the rest of the head, it put that sentence in the
    # search result of fourteen properties they have nothing to do with -
    # including Liebo's. Anything in the head that names a person or a firm
    # has to be rewritten, not inherited.
    out = re.sub(r'<meta name="description" content="[^"]*">',
                 f'<meta name="description" content="{desc_plain}">', out)
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
/* A SHARP HERO HAS TO CARRY THE NAV BY ITSELF, AND ONLY THE NAV.

   First attempt washed the top 40% of the picture, which protected the
   links and cost the photograph: Ryan, twice, that it was too dark. The
   wash was solving a problem that lives in the top 160 pixels by darkening
   a third of the image.

   So: a band, measured in pixels because that is where the nav is,
   whatever the hero's height. The middle of the picture is left alone.
   Swept on all three unveiled heroes, worst case of the three:

     wash .72, top 40%     nav 5.04   sky 0.224
     band 160px, a .92     nav 6.77   sky 0.311   +39% brighter

   Lighter picture and better legibility at the same time, because the ink
   is where the type is instead of spread thin over the whole frame.

   The foot is shortened too, .84 to nothing by 42% rather than 60%, which
   is all the headline and the Register Interest button need: measured at
   8.07 against a 4.5 floor.

   Only unveiled heroes need any of this, and only these generated pages
   have it. */
.p-hero:not(.p-hero--veil) .hero__scrim{
  background:
    linear-gradient(180deg, rgba(8,10,7,.92) 0px, rgba(8,10,7,.64) 85px,
                    rgba(8,10,7,0) 160px),
    linear-gradient(to top, rgba(8,10,7,.84) 0%, rgba(8,10,7,.52) 18%,
                    rgba(8,10,7,0) 42%);
}
/* WHOSE CROP IS THIS? The donor page these pages borrow their chrome from
   carries a phone rule tuned to its own hero: object-position 34%, chosen
   because 515 Shenandoah is a 2.17 panorama and dead centre landed on a run
   of windows that could be any elevation. Every generated page inherited
   it, so a portrait phone has been cropping each rendering by a rule
   written for a different photograph.

   The middle is the right default for a hero that is composed around its
   own centre, which most elevations are. A hero that wants another point
   sets "focus" in properties.json and it arrives as a custom property on
   the image itself. */
@media (max-aspect-ratio:1/1){
  .p-hero:not(.p-hero--veil) .hero__media{object-position:var(--hero-focus,50% 50%)}
}
/* ---- the figures, under the address ----
   Lifted from the hand-built property pages, which all carry this and
   which is what "built like the other pages" means at the top of one.
   The donor's stylesheet had the separator rule for this class and not
   the class itself, so a generated page that tried to use it got
   unstyled text. */
.p-hero__price{
  margin:1.5rem 0 0;padding:1rem 0;
  border-top:1px solid var(--wline);border-bottom:1px solid var(--wline);
  font-size:clamp(.66rem,.6rem + .24vw,.8rem);
  letter-spacing:.2em;text-indent:.2em;text-transform:uppercase;
  color:var(--w1);text-shadow:0 1px 20px rgba(0,0,0,.5);
}
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

/* ---- the film ----
   THE SAME FILM THE HAND-BUILT PAGES HAVE, lifted out of 715 Davis so a
   generated page can carry one too. Difference: that one is a YouTube
   embed, this is the file itself, because what Liebo send is an mp4 and
   putting it through a third party to play it back is a round trip for
   nothing. preload="none" so the weight is only paid by somebody who
   presses play; the poster is what loads. */
.p-film{max-width:58rem;margin:clamp(2.2rem,5vh,3.2rem) auto 0}
.p-film__frame{position:relative;aspect-ratio:16/9;background:#1b1f19;overflow:hidden}
.p-film__frame video{
  position:absolute;inset:0;width:100%;height:100%;object-fit:cover;border:0;display:block}
.p-film__play{
  position:absolute;inset:0;z-index:2;display:grid;place-items:center;
  border:0;background:rgba(20,23,15,.3);cursor:pointer;color:#fff;
  transition:background .3s var(--rise)}
.p-film__play[hidden]{display:none}
.p-film__play:hover,.p-film__play:focus-visible{background:rgba(20,23,15,.14);outline:none}
.p-film__play span{
  display:grid;place-items:center;width:4.2rem;height:4.2rem;border-radius:50%;
  border:1px solid var(--w2);background:rgba(20,23,15,.32);
  transition:border-color .3s var(--rise),background .3s var(--rise)}
.p-film__play:hover span{border-color:var(--brass);background:rgba(20,23,15,.5)}
.p-film__play svg{width:1.15rem;height:1.15rem;fill:currentColor;margin-left:.18rem}
/* The caption is the second way in: a visitor who does not read a bare
   circle as a control reads words. */
.p-film__cap{
  display:flex;align-items:center;justify-content:center;gap:.7rem;
  width:fit-content;margin:1.15rem auto 0;padding:0 0 .55rem;
  border:0;background:none;cursor:pointer;
  border-bottom:1px solid var(--brass);
  font-family:var(--ui);font-weight:300;
  font-size:clamp(.74rem,.7rem + .18vw,.86rem);
  letter-spacing:.26em;text-indent:.26em;text-transform:uppercase;
  color:var(--t1);
  transition:color .4s var(--rise),border-color .4s var(--rise)}
.p-film__cap svg{
  width:.62rem;height:.62rem;fill:currentColor;flex:none;
  color:var(--brass);transition:transform .4s var(--rise)}
.p-film__cap:hover,.p-film__cap:focus-visible{color:var(--brass);outline:none}
.p-film__cap:hover svg{transform:translateX(.22rem)}
.p-film__note{
  margin:1.1rem auto 0;max-width:34rem;text-align:center;font-weight:300;
  font-size:clamp(.7rem,.68rem + .12vw,.78rem);line-height:1.8;color:var(--warm);
}
@media (prefers-reduced-motion:reduce){
  .p-film__play,.p-film__play span,.p-film__cap,.p-film__cap svg{transition:none}
}

/* ---- the gallery, the three rules the donor sheet is missing ----
   THE SHEET SETS --1'S ASPECT AND NEVER ITS COLUMNS, so a lone full-width
   frame sits a third of the width wide with two holes beside it. That has
   bitten Liebo Builders, 515 Shenandoah and 715 Davis; it is written down
   here so it cannot bite a generated page as well.

   The shape modifiers come after the --1/--2 aspect rules on purpose: same
   specificity, later wins, so one row can say both how many columns it has
   and how tall they are. Renderings arrive in four or five ratios and
   forcing them into one slot crops the roofline off the elevations. */
/* ---- what the house has ----
   The facts list answers how big. This answers what is in it, which is the
   question a Private Exclusive actually gets asked, and it is a list rather
   than a paragraph because that is how it arrives from the builder. Same
   hairline and same spaced caps as the facts above it, one weight quieter,
   so the two read as one block and not as two ideas. */
.p-feat{
  max-width:52rem;margin:clamp(2rem,4vh,2.8rem) auto 0;padding:0;list-style:none;
  display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:0 clamp(1.6rem,4vw,3rem);
}
@media (max-width:760px){ .p-feat{grid-template-columns:repeat(2,minmax(0,1fr))} }
@media (max-width:460px){ .p-feat{grid-template-columns:1fr;max-width:26rem} }
.p-feat li{
  border-top:1px solid var(--line);padding:.95rem 0;
  font-family:var(--ui);font-weight:300;
  font-size:clamp(.7rem,.67rem + .14vw,.8rem);
  letter-spacing:.14em;text-transform:uppercase;color:var(--t2);
}
.p-gal__row--1{grid-template-columns:1fr}
.p-gal__row--pano .p-shot{aspect-ratio:2/1}
.p-gal__row--wide .p-shot{aspect-ratio:16/9}
@media (max-width:760px){ .p-gal__row--pano .p-shot{aspect-ratio:16/9} }
</style>
'''

FACTS = [("Status","status"),("Price","price"),("Square Feet","sqft"),
         ("Bedrooms","beds"),("Bathrooms","baths"),("Garage","garage"),
         ("Acreage","acres"),("MLS","mls"),("Completion","completion")]

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
    # THE VEIL FLAG WAS NEVER READ. Every page got p-hero--veil whatever
    # properties.json said, so a rendering could only ever appear blurred.
    # With no image the veil class is what paints the fallback ground, so a
    # page without one keeps it regardless.
    if p["hero"]:
        hero_cls = "p-hero" + (" p-hero--veil" if p.get("veil", True) else "")
    else:
        hero_cls = "p-hero p-hero--veil p-hero--noimg"
    focus = f' style="--hero-focus:{p["focus"]}"' if p.get("focus") else ""
    hero_img = (f'\n  <img class="hero__media"{focus} src="../../media/{p["hero"]}" alt="" aria-hidden="true">'
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

    # --- the residence ------------------------------------------------------
    # The placeholder says the page is early rather than pretending it is
    # finished. A property with something true to say overrides it with
    # "story"; "features" is what the house has, which is the question a
    # Private Exclusive actually gets asked.
    story = esc(p["story"]) if p.get("story") else (
        "It is early here. What is settled is on this page; what is not is shown\n"
        "       as a blank rather than guessed at, and fills in as the house does.")
    feat = ""
    if p.get("features"):
        items = "\n".join(f"    <li>{esc(x)}</li>" for x in p["features"])
        feat = f'\n  <ul class="p-feat">\n{items}\n  </ul>\n'

    # --- the gallery --------------------------------------------------------
    # Rooms, rows, frames, straight out of properties.json. The rows are what
    # the page is without JavaScript; gallery.js turns the same markup into a
    # contact sheet with a viewer, so the rows still have to be right.
    gal, gal_js = "", ""
    if p.get("gallery"):
        rooms = []
        for room in p["gallery"]:
            rows = []
            for r in room["rows"]:
                shape = f' p-gal__row--{r["shape"]}' if r.get("shape") else ""
                shots = "\n".join(
                    f'      <a class="p-shot" href="../../media/{f}">'
                    f'<img src="../../media/{f}" alt="{esc(alt)}" loading="lazy" decoding="async"></a>'
                    for f, alt in r["shots"])
                rows.append(f'    <div class="p-gal__row p-gal__row--{len(r["shots"])}{shape}">\n{shots}\n    </div>')
            body_rows = "\n".join(rows)
            rooms.append(f'  <div class="p-gal">\n'
                         f'    <div class="p-gal__head"><span>{esc(room["room"])}</span><i></i></div>\n'
                         f'{body_rows}\n  </div>')
        note = p.get("gallery_note") or "Renderings"
        rooms_html = "\n\n".join(rooms)
        gal = f'''
<!-- ================================ GALLERY ===============================
     Rooms and rows from data/properties.json. gallery.js rebuilds this into
     a contact sheet with a viewer; with that file missing it stays rooms,
     frames, and a click that opens the picture. -->
<section class="p-sec p-sec--tight" aria-labelledby="gal-h">
  <h2 class="p-eyebrow" id="gal-h">Gallery</h2>
  <div class="p-lede">
    <p class="p-gal__note">{esc(note)}</p>
  </div>

{rooms_html}
</section>
'''
        gal_js = '''
<script defer src="../../gallery.js"></script>
'''

    # --- the film -----------------------------------------------------------
    # "film" in properties.json is a stem, not a path: "cm735-film" wants
    # media/cm735-film.mp4 beside media/cm735-film-poster.jpg. One value,
    # two files, and no way to set a poster that belongs to another film.
    film, film_js = "", ""
    if p.get("film"):
        stem = p["film"]
        cap  = p.get("film_cap") or "Watch the Project Update"
        note = p.get("film_note") or ""
        note_html = f'\n    <p class="p-film__note">{esc(note)}</p>' if note else ""
        film = f'''
<!-- ================================== FILM ================================
     Self hosted. The source is in media/ and the poster beside it; nothing
     is fetched until somebody presses play. -->
<section class="p-sec p-sec--tight" id="film" aria-labelledby="film-h">
  <h2 class="p-eyebrow" id="film-h">Film</h2>
  <div class="p-film">
    <div class="p-film__frame">
      <video id="pFilm" playsinline preload="none"
             poster="../../media/{stem}-poster.jpg"
             aria-label="{esc(cap)} &mdash; {esc(p["address"])}">
        <source src="../../media/{stem}.mp4" type="video/mp4">
      </video>
      <button class="p-film__play" id="pFilmPlay" type="button"
              aria-label="{esc(cap)} &mdash; {esc(p["address"])}">
        <span><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5v14l11-7z"/></svg></span>
      </button>
    </div>
    <button class="p-film__cap" id="pFilmCap" type="button">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5v14l11-7z"/></svg>
      {esc(cap)}
    </button>{note_html}
  </div>
</section>
'''
        film_js = '''
<script>
/* The film. The frame holds a poster and a single mark until it is asked
   for; the first press is what hands the browser its own controls and
   starts the file downloading. Two ways in, the mark and the line of
   words, because a bare circle is not a control to everybody. */
(() => {
  const v = document.getElementById("pFilm");
  if (!v) return;
  const b = document.getElementById("pFilmPlay"), c = document.getElementById("pFilmCap");
  const go = () => { b.hidden = true; v.controls = true; v.play(); };
  b.addEventListener("click", go);
  if (c) c.addEventListener("click", go);
})();
</script>
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

    # ---- how to ask about it ---------------------------------------------
    # An Active listing is on the open market and showable; a Private
    # Exclusive is neither, and Coming Soon is not yet. Saying the wrong one
    # of those is a fact error, not a wording preference. Where a property
    # has a listing agent, their own line answers faster than the general
    # number, and the fallback is what every page used to print.
    LEAD = {
        "Active":      "This one is on the market and showing now.",
        "Coming Soon": "This one is not on the open market yet.",
    }
    inquire_lead = LEAD.get((p.get("status") or "").strip(),
                            "This is a Private Exclusive and is not on the open market.")
    _ag = (agents or {}).get(p.get("agent") or "", {})
    inquire_tel  = _ag.get("tel") or "6158120066"
    inquire_mail = _ag.get("email") or "connect@edengrovetennessee.com"
    inquire_tel_pretty = (f"({inquire_tel[:3]})&nbsp;{inquire_tel[3:6]}-{inquire_tel[6:]}"
                          if len(inquire_tel) == 10 and inquire_tel.isdigit() else inquire_tel)

    # ---- the top of the page ---------------------------------------------
    # "Coming Soon" above "Active" is the page contradicting itself, so the
    # kicker is dropped on anything already on the market. Everything else
    # keeps the kicker, and with it the brass rule that hangs off it.
    _st = (p.get("status") or "").strip()
    hero_soon = "" if _st == "Active" else '<span class="p-hero__soon">Coming Soon</span>\n      '
    hero_cta  = "Request Information" if _st == "Active" else "Register Interest"

    # The figures under the address, in the order the hand-built pages use
    # them, and only the ones we actually have. A property with none of them
    # gets no line and no rule rather than an empty frame.
    _baths = (p.get("baths") or "").strip()
    _m = re.match(r"^(\d+)\s*Full(?:,\s*(\d+)\s*Half)?$", _baths)
    if _m:
        _baths = _m.group(1) + ("." + _m.group(2) if _m.group(2) else "")
    _bits = [b for b in (
        (p.get("price") or "").strip(),
        f'{p["sqft"]} Sq Ft'  if p.get("sqft")  else "",
        f'{p["beds"]} Bed'    if p.get("beds")  else "",
        f'{_baths} Bath'      if _baths         else "",
    ) if b]
    hero_price = ('<p class="p-hero__price">'
                  + "<i>&middot;</i>".join(esc(b) for b in _bits)
                  + "</p>\n      ") if _bits else ""

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
      {hero_soon}<span class="p-hero__status">{esc(p["status"])}</span>
      <h1>{h1}</h1>
      {hero_price}<a class="p-hero__cta" href="#inquire">{hero_cta}</a>
    </div>
  </div>
</section>

<!-- ============================== THE RESIDENCE =========================== -->
<section class="p-sec" aria-labelledby="res-h">
  <h2 class="p-eyebrow" id="res-h">The Residence</h2>
  <div class="p-story">
    <p>{story}</p>
  </div>
{feat}
  <dl class="p-facts">
{facts_block(p)}
  </dl>
</section>
{gal}{film}{builder}{loc}{follow}{presented}
<!-- ================================ INQUIRE =============================== -->
<section class="p-sec p-sec--tight" id="inquire" aria-labelledby="enq-h">
  <h2 class="p-eyebrow" id="enq-h">Inquiries</h2>
  <div class="p-lede">
    <p>{inquire_lead} To ask about it, call or text
       <a href="tel:+1{inquire_tel}">{inquire_tel_pretty}</a> or
       email <a href="mailto:{inquire_mail}?subject={urllib.parse.quote(p["address"])}">{inquire_mail}</a>.</p>
  </div>
</section>

'''
    return head_for(p, head) + body + tail.replace("</body>", gal_js + film_js + follow_js + "</body>")

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
