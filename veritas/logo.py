"""Add an employer's official logo to the Veritas logo registry (veritas/logos/).

usage: python3 veritas/logo.py <slug> "<Employer>" <candidate file> <source URL> [--bg "#RRGGBB"]
The candidate is a file fetch.py saved from the employer's own site (veritas/fetched/<day>/logos/<slug>/). SVGs are
drawn at high resolution (CSS var() colours fall back to the colour the SVG itself declares); the result is trimmed
to the logo and saved as veritas/logos/<slug>.png. --bg is the tile colour the logo sits on: white by default, or the
employer's own dark/brand colour for a logo published in white (as the employer's site shows it).
The logo is used unchanged: never redrawn, recoloured or cropped into something else.
"""
import sys, os, io, re, json, datetime
from PIL import Image

D = os.path.dirname(os.path.abspath(__file__)); LOGOS = os.path.join(D, "logos"); REG = os.path.join(LOGOS, "logos.json")

def raster(path):
    if path.lower().endswith(".svg") or open(path, "rb").read(200).lstrip().startswith(b"<"):
        import cairosvg
        svg = open(path, encoding="utf-8", errors="replace").read()
        root = re.search(r"<svg\b[^>]*>", svg).group(0)
        own = re.search(r'\bfill="(#[0-9a-fA-F]{3,8})"', root)
        svg = re.sub(r"var\(--[^,)]+,\s*([^)]+)\)", r"\1", svg)                      # var(--x, #abc) -> #abc
        svg = re.sub(r"var\(--[^)]+\)", own.group(1) if own else "#000000", svg)      # var(--x) -> the SVG's own fill
        png = cairosvg.svg2png(bytestring=svg.encode(), output_height=480)
        return Image.open(io.BytesIO(png)).convert("RGBA")
    return Image.open(path).convert("RGBA")

def main():
    a = sys.argv[1:]; bg = "#FFFFFF"
    if "--bg" in a: i = a.index("--bg"); bg = a[i + 1]; del a[i:i + 2]
    slug, employer, src, source = a
    im = raster(src)
    box = im.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if not box: sys.exit("logo is empty (fully transparent)")
    im = im.crop(box)
    if im.height > 480: im = im.resize((round(im.width * 480 / im.height), 480), Image.LANCZOS)
    os.makedirs(LOGOS, exist_ok=True)
    out = os.path.join(LOGOS, f"{slug}.png"); im.save(out, optimize=True)
    reg = json.load(open(REG)) if os.path.exists(REG) else {}
    reg[slug] = {"employer": employer, "file": f"{slug}.png", "bg": bg.upper(), "source": source,
                 "size": list(im.size), "added": datetime.date.today().isoformat()}
    json.dump(dict(sorted(reg.items())), open(REG, "w"), indent=1, ensure_ascii=False); open(REG, "a").write("\n")
    print("logo", slug, im.size, "on", bg, "->", out)

if __name__ == "__main__":
    main()
