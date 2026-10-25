"""Render a Wise Words episode.

usage: python3 render.py episode.json out.mp4 [tall|wide]
  tall = 1080x1920 (TikTok / Instagram Reels), wide = 1920x1080 (regular YouTube video).
Marco and his studio fill the whole frame; headline, captions and the quote card float on top.
"""
import os, sys, json, io, subprocess, random, math, re
import numpy as np, soundfile as sf, cairosvg, cv2
from PIL import Image, ImageDraw, ImageFont

D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
import scene

EP = json.load(open(sys.argv[1])); SEGMENTS = EP["segments"]
OUT = sys.argv[2]
FMT = sys.argv[3] if len(sys.argv) > 3 else "tall"
WORK = os.environ.get("WORK", "/tmp/wisewords_work"); os.makedirs(WORK, exist_ok=True)

FONTS = os.path.join(D, "fonts")
SERIF = os.path.join(FONTS, "SourceSerif4-Bold.ttf")
SANS_B = os.path.join(FONTS, "IBMPlexSans-Bold.ttf")
SANS_S = os.path.join(FONTS, "IBMPlexSans-SemiBold.ttf")
W, H = (1080, 1920) if FMT == "tall" else (1920, 1080)
FPS, TOTAL = 30, 175.0
NFR = int(TOTAL * FPS)

RED = (215, 38, 46); WHITE = (244, 241, 234); GOLD = (217, 180, 90); NAVY = (16, 24, 42)

# ---------- timeline ----------
lines = json.load(open(os.path.join(WORK, "lines.json")))
speech = sum(l["dur"] for l in lines)
intro, outro, seg_gap = 1.2, 2.2, 2.0
n_within = sum(len(s["lines"]) - 1 for s in SEGMENTS)
gap = (TOTAL - speech - intro - outro - seg_gap * (len(SEGMENTS) - 1)) / n_within
if gap < 0.35: sys.exit(f"SCRIPT TOO LONG: cut about {round((0.55 - gap) * n_within)} seconds of speech")
if gap > 1.35: sys.exit(f"SCRIPT TOO SHORT: add about {round((gap - 1.1) * n_within)} seconds of speech")
t = intro
for i, l in enumerate(lines):
    if i > 0:
        t += seg_gap if l["seg"] != lines[i - 1]["seg"] else gap
    l["start"] = t; t += l["dur"]; l["end"] = t
seg_start = {}
for l in lines:
    seg_start.setdefault(l["seg"], l["start"] - (0.6 if l["seg"] else intro))
seg_start[0] = 0.0
seg_starts = [seg_start[i] for i in range(len(SEGMENTS))]
seg_ends = seg_starts[1:] + [TOTAL]

def _w(x): return set(re.findall(r"[a-z']+", x.lower()))
qtime = {}
for si, s_ in enumerate(SEGMENTS):
    qw = _w(s_["quote"]); best = None
    for l in lines:
        if l["seg"] != si: continue
        ov = len(qw & _w(s_["lines"][l["line"]])) / max(1, len(qw))
        if ov >= 0.6 and (best is None or ov > best[0]): best = (ov, l["start"], l["dur"])
    qtime[si] = (best[1], best[2] * 0.9) if best else None

# ---------- audio ----------
SR = lines[0]["sr"]
audio = np.zeros(int(TOTAL * SR) + 1, dtype=np.float32)
for l in lines:
    a, _ = sf.read(l["path"], dtype="float32")
    s = int(l["start"] * SR); audio[s:s + len(a)] += a[: len(audio) - s]
voice = audio.copy()

def sting(at, notes, dur=1.6, vol=0.10):
    n = int(dur * SR); tt = np.arange(n) / SR
    env = np.exp(-tt * 3.0) * np.minimum(1, tt * 80)
    sig = sum(np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt) for f in notes)
    s = int(at * SR); audio[s:s + n] += (vol * env * sig / len(notes)).astype(np.float32)[: len(audio) - s]

sting(0.0, [392.0, 493.9, 587.3], 2.0, 0.16)
for si in range(1, len(SEGMENTS)):
    sting(seg_start[si], [587.3, 784.0], 0.8, 0.05)
sting(TOTAL - 2.0, [293.7, 392.0, 493.9], 2.0, 0.14)
audio = np.clip(audio / max(1.0, np.abs(audio).max() / 0.95), -1, 1)
WAV = os.path.join(WORK, f"mix_{FMT}.wav"); sf.write(WAV, audio, SR)

hop = SR // FPS
rms = np.array([np.sqrt(np.mean(voice[i * hop:(i + 1) * hop] ** 2)) for i in range(NFR)])
ref = np.percentile(rms[rms > 0.005], 90) if (rms > 0.005).any() else 1
lvl = rms / ref

# ---------- studio layers ----------
VW, VH = scene.VB
RS = W / VW if FMT == "wide" else H / VH          # px per scene unit at zoom 1
ZMAX = 1.3
SC = RS * ZMAX                                     # layers are drawn sharp enough for the closest shot
def svg_png(s):
    png = cairosvg.svg2png(bytestring=s.encode(), output_width=round(VW * SC), output_height=round(VH * SC))
    return Image.open(io.BytesIO(png)).convert("RGBA")
static = svg_png(scene.bg())
for layer in (scene.body(), scene.desk()):
    static.alpha_composite(svg_png(layer))
static = np.asarray(static.convert("RGB"))
hx0, hy0, hx1, hy1 = scene.HEAD_BOX
pad = 20
hbox = tuple(round(v * SC) for v in (hx0 - pad, hy0 - pad, hx1 + pad, hy1 + pad))
pivot = (round((scene.HEAD_PIVOT[0] - hx0 + pad) * SC), round((scene.HEAD_PIVOT[1] - hy0 + pad) * SC))
heads = {(m, e): svg_png(scene.head(m, e)).crop(hbox) for m in range(3) for e in range(2)}
hands = []
for mode in range(2):
    im = svg_png(scene.hands(mode)); bb = im.getbbox()
    hands.append((im.crop(bb), bb[:2]))
rot_cache = {}
def head_img(m, e, ang):
    k = (m, e, ang)
    if k not in rot_cache:
        rot_cache[k] = heads[(m, e)].rotate(ang, resample=Image.BICUBIC, center=pivot)
    return rot_cache[k]

# ---------- camera: alternating wide and close shots ----------
def view(si, tt):
    p = (tt - seg_starts[si]) / max(1.0, seg_ends[si] - seg_starts[si])
    close = si % 2 == 1 and si < len(SEGMENTS) - 1
    if FMT == "wide":
        z = (1.22 + 0.06 * p) if close else (1.0 + 0.045 * p)
        vw, vh = VW / z, VH / z
        cx = 600 + 0.14 * vw if close else 800 + 18 * math.sin(tt / 7)
        cy = 400 if close else 450
    else:
        z = (1.14 + 0.05 * p) if close else (1.0 + 0.045 * p)
        vh = VH / z; vw = vh * W / H
        cx = 600 + 10 * math.sin(tt / 7)
        cy = 420 if close else 450
    cx = min(max(cx, vw / 2), VW - vw / 2); cy = min(max(cy, vh / 2), VH - vh / 2)
    return cx - vw / 2, cy - vh / 2, vw, vh

# ---------- fonts & overlays ----------
def F(p, s): return ImageFont.truetype(p, s)
def wrap(text, font, maxw):
    ws, ls, cur = text.split(), [], ""
    for w_ in ws:
        t_ = (cur + " " + w_).strip()
        if font.getlength(t_) > maxw and cur: ls.append(cur); cur = w_
        else: cur = t_
    ls.append(cur); return ls

if FMT == "wide":
    f_title, f_sub, f_head, f_cap = F(SERIF, 58), F(SANS_S, 24), F(SANS_B, 38), F(SANS_B, 52)
    f_q, f_qs, f_qm, f_au = F(SERIF, 44), F(SERIF, 38), F(SERIF, 130), F(SANS_S, 30)
    TITLE_XY, SUB_XY, HEAD_Y, HEAD_H = (56, 30), (58, 100), H - 292, 64
    CAP_CY, CAP_MAXW, CAP_LH = H - 140, W - 360, 64
    CARD_X, CARD_W, CARD_TOP, CARD_BOTTOM = 1150, 712, 170, None
else:
    f_title, f_sub, f_head, f_cap = F(SERIF, 66), F(SANS_S, 28), F(SANS_B, 42), F(SANS_B, 60)
    f_q, f_qs, f_qm, f_au = F(SERIF, 50), F(SERIF, 43), F(SERIF, 140), F(SANS_S, 34)
    TITLE_XY, SUB_XY, HEAD_Y, HEAD_H = (48, 44), (50, 124), 196, 76
    CAP_CY, CAP_MAXW, CAP_LH = 1300, W - 100, 74
    CARD_X, CARD_W, CARD_TOP, CARD_BOTTOM = 44, W - 88, None, H - 56

# static overlay: shading, vignette, show title, LIVE pill
yy = np.linspace(0, 1, H)[:, None]; xx = np.linspace(0, 1, W)[None, :]
top = np.clip(1 - yy / (0.17 if FMT == "wide" else 0.16), 0, 1) ** 1.6 * 0.75
bot_start = 0.66 if FMT == "wide" else 0.55
bot = np.clip((yy - bot_start) / (1 - bot_start), 0, 1) ** 1.2 * (0.82 if FMT == "wide" else 0.86)
vig = np.clip((np.sqrt(((xx - 0.5) / 0.75) ** 2 + ((yy - 0.47) / 0.75) ** 2) - 0.55) / 0.45, 0, 1) * 0.45
alpha = np.clip(1 - (1 - top) * (1 - bot) * (1 - vig), 0, 1)
shade = np.zeros((H, W, 4), np.uint8); shade[..., 0:3] = (8, 10, 18); shade[..., 3] = (alpha * 255).astype(np.uint8)
overlay = Image.fromarray(shade, "RGBA")
od = ImageDraw.Draw(overlay)
od.text(TITLE_XY, EP.get("title", "Wise Words"), font=f_title, fill=WHITE)
od.text(SUB_XY, EP.get("subtitle", "WITH MARCO REYES  ·  STORY NIGHT"), font=f_sub, fill=GOLD)
lw = f_sub.getlength("LIVE") + 40; lx1 = W - 48; ly0 = TITLE_XY[1] + 18
od.rounded_rectangle((lx1 - lw, ly0, lx1, ly0 + 46), 8, fill=RED)
od.ellipse((lx1 - lw + 12, ly0 + 18, lx1 - lw + 22, ly0 + 28), fill=(255, 255, 255))
od.text((lx1 - lw / 2 + 8, ly0 + 23), "LIVE", font=f_sub, fill=(255, 255, 255), anchor="mm")

head_bands = []
for s in SEGMENTS:
    tw = f_head.getlength(s["head"])
    im = Image.new("RGBA", (int(tw + 88), HEAD_H), RED + (255,)); dd = ImageDraw.Draw(im)
    dd.rectangle((0, 0, 10, HEAD_H), fill=GOLD)
    dd.text((44, HEAD_H // 2), s["head"], font=f_head, fill=(255, 255, 255), anchor="lm")
    head_bands.append(im)

# ---------- captions ----------
def chunks(text, maxc=34):
    ws, out, cur = text.split(), [], ""
    for w_ in ws:
        if cur and len(cur) + 1 + len(w_) > maxc: out.append(cur); cur = w_
        else: cur = (cur + " " + w_).strip()
    if cur: out.append(cur)
    return out
caps = []
for l in lines:
    ch = chunks(SEGMENTS[l["seg"]]["lines"][l["line"]])
    tot = sum(len(c) for c in ch); t0 = l["start"]
    for c in ch:
        dur = l["dur"] * len(c) / tot
        caps.append((t0, t0 + dur + (gap * 0.6 if c == ch[-1] else 0), c)); t0 += dur
cap_cache = {}
def cap_img(text):
    if text not in cap_cache:
        ls = wrap(text, f_cap, CAP_MAXW)
        im = Image.new("RGBA", (W, CAP_LH * len(ls) + 40), (0, 0, 0, 0)); dd = ImageDraw.Draw(im)
        for i, ln in enumerate(ls):
            dd.text((W // 2, 20 + CAP_LH // 2 + i * CAP_LH), ln, font=f_cap, fill=(255, 255, 255), anchor="mm",
                    stroke_width=6, stroke_fill=(10, 10, 16))
        cap_cache[text] = im
    return cap_cache[text]

# ---------- quote card ----------
card_cache = {}
def card(si, prog, fade):
    key = (si, round(prog, 2), prog >= 1, round(fade, 1))
    if key in card_cache: return card_cache[key]
    s = SEGMENTS[si]; fq, lh = f_q, int(f_q.size * 1.3)
    ls = wrap(s["quote"], fq, CARD_W - 120)
    if len(ls) > 4: fq, lh = f_qs, int(f_qs.size * 1.3); ls = wrap(s["quote"], fq, CARD_W - 120)
    ch = 120 + lh * len(ls) + 80
    im = Image.new("RGBA", (CARD_W, ch), (0, 0, 0, 0)); dd = ImageDraw.Draw(im)
    a = int(232 * fade)
    dd.rounded_rectangle((0, 0, CARD_W - 1, ch - 1), 22, fill=NAVY + (a,), outline=GOLD + (int(200 * fade),), width=3)
    dd.text((34, -18), "“", font=f_qm, fill=GOLD + (int(255 * fade),))
    k = round(len(s["quote"].split()) * prog); shown = 0
    for i, ln in enumerate(ls):
        ws = ln.split(); take = ws[:max(0, k - shown)]; shown += len(ws)
        if take: dd.text((60, 104 + i * lh), " ".join(take), font=fq, fill=WHITE + (int(255 * fade),))
    if prog >= 1: dd.text((60, ch - 62), "— " + s["author"], font=f_au, fill=GOLD + (int(255 * fade),))
    card_cache[key] = im
    return im

# ---------- frames ----------
PREV = [float(x) for x in os.environ.get("PREVIEW", "").split(",") if x]
ff = None if PREV else subprocess.Popen(
    ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
     "-i", "-", "-i", WAV, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
     "-c:a", "aac", "-b:a", "192k", "-t", str(TOTAL), "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
random.seed(3); blinks = set()
tb = 1.5
while tb < TOTAL:
    f0 = int(tb * FPS); blinks.update(range(f0, f0 + 4)); tb += random.uniform(2.8, 5.5)
ci, mouth_prev = 0, 0
for fi in (sorted(int(x * FPS) for x in PREV) if PREV else range(NFR)):
    tt = fi / FPS
    si = max(i for i, s in enumerate(seg_starts) if s <= tt)
    local = tt - seg_starts[si]
    lv = lvl[fi]
    m = 2 if lv > 0.55 else 1 if lv > 0.18 else 0
    if m == 2 and mouth_prev == 2 and fi % 3 == 0: m = 1
    mouth_prev = m
    qt = qtime.get(si)
    pointing = qt is not None and 0 < si < len(SEGMENTS) - 1 and qt[0] - 0.2 <= tt <= qt[0] + qt[1] / 0.9 + 0.6
    # studio crop for this camera position, with Marco's head and hands
    left, top_, vw, vh = view(si, tt)
    box = (round(left * SC), round(top_ * SC), round((left + vw) * SC), round((top_ + vh) * SC))
    fr = Image.fromarray(static[box[1]:box[3], box[0]:box[2]])
    ang = round((1.4 * math.sin(tt * 2 * math.pi / 6.0) + (0.9 * math.sin(tt * 5.1) if lv > 0.18 else 0)) * 4) / 4
    hi = head_img(m, 1 if fi in blinks else 0, ang)
    bob = round(2.5 * SC * math.sin(tt * 2 * math.pi / 4.2))
    fr.paste(hi, (hbox[0] - box[0], hbox[1] - box[1] + bob), hi)
    him, hxy = hands[1 if pointing else 0]
    fr.paste(him, (hxy[0] - box[0], hxy[1] - box[1]), him)
    fr = Image.fromarray(cv2.resize(np.asarray(fr), (W, H), interpolation=cv2.INTER_LINEAR))
    fr.paste(overlay, (0, 0), overlay)
    # headline slides in
    slide = min(1.0, local / 0.45); hb = head_bands[si]
    fr.paste(hb, (int(-hb.width * (1 - slide) ** 3), HEAD_Y), hb)
    # captions
    while ci < len(caps) - 1 and caps[ci][1] < tt and caps[ci + 1][0] <= tt: ci += 1
    if caps[ci][0] <= tt <= caps[ci][1]:
        c = cap_img(caps[ci][2]); fr.paste(c, (0, int(CAP_CY - c.height / 2)), c)
    # quote card types out as Marco says the quote, then stays for the chapter
    t_on = qt[0] if qt else seg_starts[si] + 1.0
    if tt >= t_on - 0.3:
        prog = min(1.0, local / 3.0) if qt is None else max(0.0, min(1.0, (tt - qt[0]) / max(qt[1], 1.0)))
        fade = min(1.0, (tt - t_on + 0.3) / 0.35)
        out = max(0.0, min(1.0, (seg_ends[si] - tt) / 0.35)) if si < len(SEGMENTS) - 1 else 1.0
        cd = card(si, prog, min(fade, out))
        y = CARD_TOP if CARD_TOP is not None else CARD_BOTTOM - cd.height
        fr.paste(cd, (CARD_X, int(y + 24 * (1 - fade))), cd)
    if PREV: fr.save(os.path.join(WORK, f"{FMT}_{fi}.png")); continue
    ff.stdin.write(fr.tobytes())
    if fi % 750 == 0: print(FMT, "frame", fi, flush=True)
if ff: ff.stdin.close(); ff.wait()
print("done", OUT)
