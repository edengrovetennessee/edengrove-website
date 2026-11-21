#!/usr/bin/env python3
"""The Residence becomes the listing description, and nothing else.

Ryan: I don't like this section, I want it to just be the listing
description. The sixteen-item feature grid came out of the remarks and
then sat under a three-sentence summary of the same remarks, so the page
said everything twice, once as prose and once as a wall of spaced
capitals.

Two changes:

  The generator can take a story as several paragraphs. It emitted one
  <p> around whatever it was given, which is fine for three sentences
  and unreadable for a full set of public remarks. A list, or a string
  with blank lines in it, becomes one <p> each. A plain string with no
  blank line renders exactly as before, so the other fourteen are
  untouched.

  6001 Dunham Springs carries the remarks themselves, in four
  paragraphs, and drops the feature list. The closing "6 bedrooms | 6
  full and 2 half baths | 2.13 acres" is left off: the facts table
  directly underneath already says it.
"""
import io, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ------------------------------------------------- 1. the generator
G = os.path.join(ROOT, "data", "build-property-pages.py")
g = io.open(G, encoding="utf-8").read()

OLD_STORY = '''    story = esc(p["story"]) if p.get("story") else (
        "It is early here. What is settled is on this page; what is not is shown\\n"
        "       as a blank rather than guessed at, and fills in as the house does.")'''
NEW_STORY = '''    # A story can be one string or several paragraphs. Public remarks run to
    # a dozen sentences and a single <p> of that is a wall; a three sentence
    # summary is one paragraph and should stay one. Both spellings work, and
    # a string with no blank line in it comes out exactly as it used to.
    _story = p.get("story")
    if isinstance(_story, (list, tuple)):
        _paras = [str(x).strip() for x in _story if str(x).strip()]
    elif _story:
        _paras = [x.strip() for x in str(_story).split("\\n\\n") if x.strip()]
    else:
        _paras = ["It is early here. What is settled is on this page; what is not is shown\\n"
                  "       as a blank rather than guessed at, and fills in as the house does."]
    story = "</p>\\n    <p>".join(esc(x) for x in _paras)'''

if "_paras" in g:
    print("generator already takes paragraphs")
else:
    assert g.count(OLD_STORY) == 1, "the story block has moved; patch by hand"
    g = g.replace(OLD_STORY, NEW_STORY, 1)
    io.open(G, "w", encoding="utf-8").write(g)
    print("generator: story may be several paragraphs")

# ------------------------------------------------- 2. the property
DATA = os.path.join(ROOT, "data", "properties.json")
d = json.load(io.open(DATA, encoding="utf-8"))
hit = [p for p in d["properties"] if p["slug"] == "6001-dunham-springs"]
assert hit, "6001-dunham-springs is not in the roster"
p = hit[0]

p["story"] = [
    "Set on 2.13 private acres in Hillwood, 6001 Dunham Springs sits down off "
    "the road beneath mature trees and feels like a true estate. Homes built "
    "with this level of craftsmanship rarely come to market. The home is "
    "currently under construction, and completion is slated for mid December "
    "2026. Preview showings begin Friday, November 27.",

    "The home’s 6,879 square feet are finished with detailed millwork, crown "
    "molding and custom trim throughout. A barrel ceiling runs across the "
    "living room and kitchen, and the living room is anchored by a stone "
    "fireplace. The kitchen is built around an oversized 12 x 6.5 foot island "
    "under a custom Arcustone hood. It also has a breakfast nook and a "
    "butler’s pantry with plenty of room for catering. A formal dining room "
    "completes the entertaining space.",

    "The primary suite on the main level offers his and hers closets, a "
    "soaking tub and its own private covered porch. A large study opens "
    "through glass paned double doors onto the covered front porch. Every "
    "bedroom has its own ensuite bath, and each bath has its own detailed "
    "touch. Upstairs you’ll find a large bonus room, an adjoining loft, "
    "bedrooms four and five, and a second laundry room to go with the large "
    "laundry on the main level.",

    "Out back, a covered porch with a fireplace overlooks a fenced, courtyard "
    "style yard with room to add a pool and spa. The pool house has a full "
    "kitchen and pantry. A three car garage and two private entrances off the "
    "driveway complete the property.",
]
p["features"] = None

io.open(DATA, "w", encoding="utf-8").write(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
print("6001: the remarks in four paragraphs, feature grid removed")
