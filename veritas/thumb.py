"""Thumbnail for a Veritas Recruitment Agency upload: the employer's official logo, the role, the city and the pay.

usage: python3 veritas/thumb.py veritas/jobs/vraNNN.json out/vraNNN_thumb.jpg
Video: 1280x720. Short: 1080x1920 cover. JPEG under 2 MB (YouTube's limit). The logo comes from veritas/logos/
(job.logo); without one the employer's name is set in type instead.
"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from logotile import logo_tile

D = os.path.dirname(os.path.abspath(__file__)); F = os.path.join(D, "fonts")
SERIF, BOLD, SEMI, MED = (os.path.join(F, n) for n in ("SourceSerif4-Bold.ttf", "IBMPlexSans-Bold.ttf", "IBMPlexSans-SemiBold.ttf", "IBMPlexSans-Medium.ttf"))
NAVY, NAVY2, GOLD, WHITE, MUTED = (11, 26, 47), (20, 44, 80), (212, 175, 55), (246, 244, 238), (182, 194, 214)
font = lambda p, s: ImageFont.truetype(p, s)
JOB = json.load(open(sys.argv[1])); OUT = sys.argv[2]; J = JOB["job"]
SHORT = JOB["format"] == "short"
W, H = (1080, 1920) if SHORT else (1280, 720)

def backdrop():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); base = np.zeros((H, W, 3), np.float32)
    for c in range(3): base[..., c] = NAVY[c] + (NAVY2[c] - NAVY[c]) * (yy / H)
    for cx, cy, r, s in ((0.8, 0.15, 0.6, 34), (0.1, 0.9, 0.5, 22)):
        g = np.exp(-(((xx - cx * W) ** 2 + (yy - cy * H) ** 2) / (2 * (r * min(W, H)) ** 2)))
        for c in range(3): base[..., c] += g * s * (GOLD[c] / 255)
    base[((xx + yy) % 46) < 1.2] += 6
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")

def wrap(d, text, f, width):
    out, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= width or not cur: cur = t
        else: out.append(cur); cur = w
    return out + ([cur] if cur else [])

def fit(d, text, path, size, width, max_lines, min_size):
    while size > min_size:
        f = font(path, size); ls = wrap(d, text, f, width)
        if len(ls) <= max_lines: return f, ls
        size -= 2
    f = font(path, min_size); return f, wrap(d, text, f, width)[:max_lines]

def tracked(d, x, y, text, f, fill, sp, center=False):
    ws = [d.textlength(c, font=f) for c in text]; tot = sum(ws) + sp * (len(text) - 1)
    if center: x -= tot / 2
    for c, w in zip(text, ws): d.text((x, y), c, font=f, fill=fill); x += w + sp

role = J.get("short_title") or J["title"]
place = J["location"]; pay = J["pay"].replace(" a year", "/yr")
img = backdrop(); d = ImageDraw.Draw(img)

if SHORT:
    tracked(d, W / 2, 100, "VERITAS", font(SERIF, 76), GOLD, 15, True)
    tracked(d, W / 2, 196, "RECRUITMENT AGENCY", font(SEMI, 27), MUTED, 7, True)
    tile = logo_tile(J.get("logo"), 340, W - 160, 62, border=True)
    y = 380
    if tile: img.alpha_composite(tile, ((W - tile.width) // 2, y)); y += tile.height + 90
    else:
        ef, el = fit(d, J["employer"], BOLD, 120, W - 160, 2, 70)
        for s in el: d.text(((W - d.textlength(s, font=ef)) / 2, y), s, font=ef, fill=GOLD); y += int(ef.size * 1.1)
        y += 50
    pf = font(BOLD, 40); pt = "NOW HIRING · USA"; pw = d.textlength(pt, font=pf) + 64
    d.rounded_rectangle(((W - pw) / 2, y, (W + pw) / 2, y + 76), radius=38, fill=GOLD)
    d.text(((W - pw) / 2 + 32, y + 13), pt, font=pf, fill=NAVY); y += 150
    tf, tl = fit(d, role, BOLD, 112, W - 140, 4, 60)
    for s in tl: d.text(((W - d.textlength(s, font=tf)) / 2, y), s, font=tf, fill=WHITE); y += int(tf.size * 1.12)
    y += 34
    lf = font(MED, 60); d.text(((W - d.textlength(place, font=lf)) / 2, y), place, font=lf, fill=MUTED); y += 130
    cf, _ = fit(d, pay, BOLD, 84, W - 220, 1, 50); cw = d.textlength(pay, font=cf) + 80
    d.rounded_rectangle(((W - cw) / 2, y, (W + cw) / 2, y + cf.size + 56), radius=30, fill=(31, 50, 84), outline=GOLD, width=5)
    d.text(((W - cw) / 2 + 40, y + 22), pay, font=cf, fill=WHITE); y += cf.size + 56
    af = font(SEMI, 44); at = "Application link in the description"
    d.text(((W - d.textlength(at, font=af)) / 2, H - 230), at, font=af, fill=GOLD)
else:
    tracked(d, 60, 42, "VERITAS", font(SERIF, 46), GOLD, 9)
    tracked(d, 62, 104, "RECRUITMENT AGENCY", font(SEMI, 17), MUTED, 5)
    tile = logo_tile(J.get("logo"), 210, 520, 40, border=True)
    lx, colx = 60, 620
    if tile:
        if tile.width > 540: tile = tile.resize((540, round(tile.height * 540 / tile.width)), Image.LANCZOS)
        img.alpha_composite(tile, (lx + (520 - tile.width) // 2, 200 + (340 - tile.height) // 2))
    else:
        ef, el = fit(d, J["employer"], BOLD, 92, 520, 3, 52); yy = 230
        for s in el: d.text((lx, yy), s, font=ef, fill=GOLD); yy += int(ef.size * 1.1)
    y = 200
    pf = font(BOLD, 28); pt = "NOW HIRING · USA"; pw = d.textlength(pt, font=pf) + 44
    d.rounded_rectangle((colx, y, colx + pw, y + 54), radius=27, fill=GOLD); d.text((colx + 22, y + 10), pt, font=pf, fill=NAVY)
    y += 84
    tf, tl = fit(d, role, BOLD, 68, W - colx - 50, 3, 40)
    for s in tl: d.text((colx, y), s, font=tf, fill=WHITE); y += int(tf.size * 1.1)
    y += 18
    lf, ll = fit(d, place, MED, 36, W - colx - 50, 1, 26); d.text((colx, y), ll[0], font=lf, fill=MUTED); y += int(lf.size * 1.5)
    cf, _ = fit(d, pay, BOLD, 52, W - colx - 90, 1, 32); cw = d.textlength(pay, font=cf) + 48
    d.rounded_rectangle((colx, y, colx + cw, y + cf.size + 34), radius=18, fill=(31, 50, 84), outline=GOLD, width=4)
    d.text((colx + 24, y + 13), pay, font=cf, fill=WHITE)
    af = font(SEMI, 26); at = "Application link in the description"
    d.text((colx, H - 72), at, font=af, fill=GOLD)
d.rectangle((0, H - 12, W, H), fill=GOLD)
img = img.convert("RGB"); q = 92
while True:
    img.save(OUT, "JPEG", quality=q, optimize=True)
    if os.path.getsize(OUT) < 1_900_000 or q < 60: break
    q -= 8
print("thumb", OUT, f"{W}x{H}", os.path.getsize(OUT) // 1024, "KB")
