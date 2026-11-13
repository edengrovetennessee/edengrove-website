"""Builds the thumbnails the neighborhoods map's hover cards use.

Every pin in data/map-pins.json with an "img" value names a photograph that
already lives in media/ - media/hood-7.jpg becomes media/thumb/hood-7.webp.
Nothing new is sourced here; this only makes a small version of a picture the
site already shows, so a card that opens on hover is not pulling down a
900 KB hero.

560x370 is the card's photograph at 2x. Cover-crop, never letterbox: a band
of background above a house looks like a mistake. At quality 74 the whole set
is about 1.1 MB and each card is 30-50 KB, loaded lazily when the card opens.

Five listings have no "img" at all - there is no photograph of them yet, and
the card says so rather than borrowing one from somewhere else. Run from
anywhere:  python3 data/map-make-thumbs.py
"""
import os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC, OUT = os.path.join(ROOT, "media"), os.path.join(ROOT, "media", "thumb")
W, H, Q = 560, 370, 74

names = sorted(n[:-4] for n in os.listdir(SRC)
               if n.startswith("hood-") and n.endswith(".jpg"))
names += ["dv-hero", "jd-hero", "n9-hero", "sh-hero", "ut-hero"]

os.makedirs(OUT, exist_ok=True)
total = 0
for n in names:
    s = os.path.join(SRC, n + ".jpg")
    if not os.path.exists(s):
        print("  missing", n)
        continue
    im = Image.open(s).convert("RGB")
    k = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    l, t = (im.width - W) // 2, (im.height - H) // 2
    im.crop((l, t, l + W, t + H)).save(
        os.path.join(OUT, n + ".webp"), "WEBP", quality=Q, method=6)
    total += os.path.getsize(os.path.join(OUT, n + ".webp"))
print(f"{len(names)} thumbnails, {total / 1024:.0f} KB")
