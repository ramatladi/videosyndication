"""The employer's official logo on its tile, for the videos and thumbnails (registry: veritas/logos/logos.json)."""
import os, json
from PIL import Image, ImageDraw

D = os.path.dirname(os.path.abspath(__file__))
REG_PATH = os.path.join(D, "logos", "logos.json")
REG = json.load(open(REG_PATH)) if os.path.exists(REG_PATH) else {}
GOLD = (212, 175, 55)

def entry(slug):
    return REG.get(slug or "")

def logo_tile(slug, h, max_w, pad, radius=None, border=True):
    """RGBA tile h pixels tall (at most max_w wide) with the logo fitted inside, or None when there is no logo."""
    e = entry(slug)
    if not e: return None
    im = Image.open(os.path.join(D, "logos", e["file"])).convert("RGBA")
    ih = h - 2 * pad; iw = round(im.width * ih / im.height)
    if iw > max_w - 2 * pad: iw = max_w - 2 * pad; ih = round(im.height * iw / im.width)
    im = im.resize((max(1, iw), max(1, ih)), Image.LANCZOS)
    tw = max(iw + 2 * pad, h)
    bg = tuple(int(e.get("bg", "#FFFFFF")[i:i + 2], 16) for i in (1, 3, 5))
    tile = Image.new("RGBA", (tw, h), (0, 0, 0, 0)); td = ImageDraw.Draw(tile)
    r = radius if radius is not None else int(h * 0.18)
    td.rounded_rectangle((0, 0, tw - 1, h - 1), radius=r, fill=bg + (255,),
                         outline=GOLD + (255,) if border else None, width=max(2, h // 40) if border else 0)
    tile.alpha_composite(im, ((tw - im.width) // 2, (h - im.height) // 2))
    return tile

def shows_name(slug):
    """True when the logo itself carries the employer's name (a wordmark), so the name needn't be repeated beside it."""
    e = entry(slug); return bool(e and e.get("has_name", True))
