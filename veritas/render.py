"""Render a Veritas Recruitment Agency job video.

usage: python3 veritas/render.py veritas/jobs/vraNNN.json out.mp4
The job file's "format" picks the frame: "short" = 1080x1920 (YouTube Short, under 60 s), "video" = 1920x1080.
Needs $WORK/lines.json from tts.py. Layout: the Veritas wordmark, the job header (title, employer, place, pay), one
card per scene whose points appear as they are read, and the spoken line as a caption.
"""
import os, sys, json, math, subprocess
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter

D = os.path.dirname(os.path.abspath(__file__))
JOB = json.load(open(sys.argv[1])); OUT = sys.argv[2]
SCENES, J = JOB["scenes"], JOB["job"]
SHORT = JOB["format"] == "short"
W, H = (1080, 1920) if SHORT else (1920, 1080)
FPS = 30
WORK = os.environ.get("WORK", "/tmp/veritas_work")
F = os.path.join(D, "fonts")
SERIF, BOLD, SEMI, MED, REG = (os.path.join(F, n) for n in ("SourceSerif4-Bold.ttf", "IBMPlexSans-Bold.ttf", "IBMPlexSans-SemiBold.ttf", "IBMPlexSans-Medium.ttf", "IBMPlexSans-Regular.ttf"))
NAVY, NAVY2, GOLD, WHITE, MUTED = (11, 26, 47), (20, 44, 80), (212, 175, 55), (246, 244, 238), (182, 194, 214)
font = lambda path, size: ImageFont.truetype(path, size)

# ---------- timeline ----------
lines = json.load(open(os.path.join(WORK, "lines.json")))
INTRO, LINE_GAP, SCENE_GAP, TAIL = 0.45, 0.28, 0.6, 1.6
t = INTRO
for i, l in enumerate(lines):
    if i: t += SCENE_GAP if l["scene"] != lines[i - 1]["scene"] else LINE_GAP
    l["start"], l["end"] = t, t + l["dur"]; t += l["dur"]
TOTAL = t + TAIL
if SHORT and TOTAL > 59.0: sys.exit(f"SCRIPT TOO LONG: {TOTAL:.1f}s, cut about {TOTAL - 58.5:.1f}s of speech (Shorts stay under 60 s)")
if not SHORT and not 75 <= TOTAL <= 330: sys.exit(f"SCRIPT LENGTH {TOTAL:.1f}s: a video runs 75 s to 5.5 min")
NFR = int(math.ceil(TOTAL * FPS))
scene_start = {}
for l in lines: scene_start.setdefault(l["scene"], l["start"])

# ---------- audio: voice over a soft pad, mastered ----------
sr = lines[0]["sr"]; N = int(TOTAL * sr) + sr
voice = np.zeros(N, np.float32)
for l in lines:
    a, _ = sf.read(l["path"], dtype="float32"); s = int(l["start"] * sr); voice[s:s + len(a)] += a[: N - s]
tt = np.arange(N) / sr
chords = [(261.63, 329.63, 392.00, 493.88), (220.00, 261.63, 329.63, 392.00), (174.61, 220.00, 261.63, 329.63), (196.00, 246.94, 293.66, 392.00)]
pad = np.zeros(N, np.float32); bar = 4.0
for ci in range(int(TOTAL / bar) + 2):
    s0 = int(ci * bar * sr); s1 = min(N, int((ci + 1) * bar * sr + 0.5 * sr))
    if s0 >= N: break
    seg = tt[s0:s1] - ci * bar
    env = np.minimum(1, seg / 0.8) * np.minimum(1, np.maximum(0, (bar + 0.5 - seg) / 1.2))
    tone = sum(np.sin(2 * np.pi * f * seg) * 0.5 + np.sin(2 * np.pi * f * 0.5 * seg) * 0.25 for f in chords[ci % 4])
    pad[s0:s1] += (tone * env).astype(np.float32)
pad = np.convolve(pad, np.ones(32) / 32, mode="same").astype(np.float32)
speaking = np.convolve((np.abs(voice) > 0.02).astype(np.float32), np.ones(int(0.25 * sr)) / int(0.25 * sr), mode="same")
duck = 1 - 0.55 * np.clip(speaking * 3, 0, 1)
fade = np.minimum(1, tt / 1.0) * np.minimum(1, np.maximum(0, (TOTAL - tt) / 1.5))
pad *= (0.035 / (np.abs(pad).max() + 1e-9)) * duck * fade
mix = voice + pad
try:
    import pyloudnorm as pyln
    gain = 10 ** ((-15.0 - pyln.Meter(sr).integrated_loudness(mix)) / 20)
    mix = mix * min(gain, 0.95 / (np.abs(mix).max() + 1e-9))
except Exception:
    mix *= 0.89 / (np.abs(mix).max() + 1e-9)
mix = np.clip(mix, -0.98, 0.98).astype(np.float32)[: int(TOTAL * sr)]
WAV = os.path.join(WORK, "mix.wav"); sf.write(WAV, mix, sr)

# ---------- drawing helpers ----------
def wrap(draw, text, fnt, width):
    out, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=fnt) <= width or not cur: cur = trial
        else: out.append(cur); cur = word
    if cur: out.append(cur)
    return out

def fit(draw, text, path, size, width, max_lines, min_size=24):
    while size > min_size:
        f = font(path, size); ls = wrap(draw, text, f, width)
        if len(ls) <= max_lines: return f, ls
        size -= 2
    f = font(path, min_size); return f, wrap(draw, text, f, width)[:max_lines]

def tracked(draw, xy, text, fnt, fill, spacing, anchor_center=False):
    widths = [draw.textlength(c, font=fnt) for c in text]
    total = sum(widths) + spacing * (len(text) - 1)
    x, y = xy
    if anchor_center: x -= total / 2
    for c, w in zip(text, widths):
        draw.text((x, y), c, font=fnt, fill=fill); x += w + spacing
    return total

# Background: deep navy with a slow gold glow and fine diagonal lines (drawn once, panned each frame).
BW, BH = W + 360, H + 360
yy, xx = np.mgrid[0:BH, 0:BW].astype(np.float32)
base = np.zeros((BH, BW, 3), np.float32)
for c in range(3): base[..., c] = NAVY[c] + (NAVY2[c] - NAVY[c]) * (yy / BH)
for (cx, cy, r, s) in ((0.78, 0.18, 0.55, 26), (0.15, 0.85, 0.5, 18)):
    g = np.exp(-(((xx - cx * BW) ** 2 + (yy - cy * BH) ** 2) / (2 * (r * min(BW, BH)) ** 2)))
    for c in range(3): base[..., c] += g * s * (GOLD[c] / 255)
lines_mask = ((xx + yy) % 46) < 1.2
base[lines_mask] += 6
BG = np.clip(base, 0, 255).astype(np.uint8)

def background(t):
    ox = int(180 + 150 * math.sin(t * 0.11)); oy = int(180 + 150 * math.cos(t * 0.08))
    return Image.fromarray(BG[oy:oy + H, ox:ox + W])

# Static layer: wordmark, job header, pay chip.
static = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(static)
if SHORT:
    tracked(d, (W / 2, 78), "VERITAS", font(SERIF, 70), GOLD, 14, True)
    tracked(d, (W / 2, 168), "RECRUITMENT AGENCY", font(SEMI, 25), MUTED, 7, True)
    d.line((W / 2 - 150, 214, W / 2 + 150, 214), fill=GOLD, width=2)
    x0, y, colw = 80, 270, W - 160
else:
    tracked(d, (80, 58), "VERITAS", font(SERIF, 54), GOLD, 11)
    tracked(d, (82, 128), "RECRUITMENT AGENCY", font(SEMI, 20), MUTED, 6)
    d.line((82, 166, 330, 166), fill=GOLD, width=2)
    x0, y, colw = 80, 230, 800
pill = font(BOLD, 26 if SHORT else 22); ptxt = "NOW HIRING · USA"
pw = d.textlength(ptxt, font=pill) + 44
d.rounded_rectangle((x0, y, x0 + pw, y + (54 if SHORT else 46)), radius=27, fill=GOLD)
d.text((x0 + 22, y + (10 if SHORT else 8)), ptxt, font=pill, fill=NAVY)
y += 84 if SHORT else 72
tf, tl = fit(d, J["title"], BOLD, 74 if SHORT else 62, colw, 3 if SHORT else 4, 40)
for s in tl:
    d.text((x0, y), s, font=tf, fill=WHITE); y += int(tf.size * 1.14)
y += 14
ef = font(SEMI, 46 if SHORT else 40); d.text((x0, y), J["employer"], font=ef, fill=GOLD); y += int(ef.size * 1.3)
lf, ll = fit(d, J["location"] + ("  ·  " + J["workplace"] if J.get("workplace") else ""), MED, 38 if SHORT else 32, colw, 2, 26)
for s in ll:
    d.text((x0, y), s, font=lf, fill=MUTED); y += int(lf.size * 1.3)
y += 18
cf = font(BOLD, 40 if SHORT else 36); ctxt = J["pay"]
cw = d.textlength(ctxt, font=cf) + 48
d.rounded_rectangle((x0, y, x0 + cw, y + cf.size + 34), radius=18, fill=(255, 255, 255, 22), outline=GOLD, width=3)
d.text((x0 + 24, y + 14), ctxt, font=cf, fill=WHITE)
HEADER_BOTTOM = y + cf.size + 34

if SHORT: AREA = (60, HEADER_BOTTOM + 40, W - 60, 1540); CAP = (60, 1570, W - 60, 1840)
else: AREA = (960, 150, W - 70, 810); CAP = (80, 850, W - 80, 1010)
BSIZE, HEAD = (52, 36) if SHORT else (38, 30)

def bullet_blocks(d, sc, width):
    out = []
    for b in sc["bullets"]:
        bf, bl = fit(d, b, MED, sc.get("bullet_size", BSIZE), width, 3, 26); out.append((bf, bl))
    return out

def card_box(si):
    x1, y1, x2, y2 = AREA; d = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    h = 40 + HEAD + 40 + sum(len(bl) * int(bf.size * 1.25) + 26 for bf, bl in bullet_blocks(d, SCENES[si], (x2 - x1) - 140)) + 24
    h = min(h, y2 - y1); top = y1 + ((y2 - y1) - h) // 2 if SHORT else y1
    return (x1, top, x2, top + h)

def card_layer(si, shown):
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    x1, y1, x2, y2 = card_box(si)
    d.rounded_rectangle((x1, y1, x2, y2), radius=28, fill=(255, 255, 255, 18), outline=(212, 175, 55, 120), width=2)
    y = y1 + 40
    tracked(d, (x1 + 44, y), SCENES[si]["head"].upper(), font(BOLD, HEAD), GOLD, 3)
    y += HEAD + 40
    for bf, bl in bullet_blocks(d, SCENES[si], (x2 - x1) - 140)[:shown]:
        if y + len(bl) * bf.size * 1.25 > y2 - 10: break
        d.ellipse((x1 + 46, y + bf.size * 0.42, x1 + 62, y + bf.size * 0.42 + 16), fill=GOLD)
        for s in bl:
            d.text((x1 + 88, y), s, font=bf, fill=WHITE); y += int(bf.size * 1.25)
        y += 26
    return L

def caption_layer(text):
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if not text: return L
    d = ImageDraw.Draw(L); x1, y1, x2, y2 = CAP
    f, ls = fit(d, text, SEMI, 42 if SHORT else 38, (x2 - x1) - 80, 4 if SHORT else 3, 28)
    h = len(ls) * int(f.size * 1.28) + 36
    top = y2 - h if SHORT else y1
    d.rounded_rectangle((x1, top, x2, top + h), radius=20, fill=(4, 10, 20, 190))
    yy = top + 18
    for s in ls:
        d.text(((x1 + x2) / 2 - d.textlength(s, font=f) / 2, yy), s, font=f, fill=WHITE); yy += int(f.size * 1.28)
    return L

# Captions show each line as written: a scene's "show" list when given, else the spoken line with the spellings
# the voice needs turned back into the usual ones ("A W S" -> "AWS").
SPELL = [("four-oh-one-k", "401(k)"), ("C plus plus", "C++"), ("C sharp", "C#"), ("A P Is", "APIs"), ("A I", "AI"), ("A W S", "AWS"),
         ("S D E T", "SDET"), ("E T L", "ETL"), ("E L T", "ELT"), ("S Q L", "SQL"), ("S three", "S3"), ("E M R", "EMR"), ("U. S.", "U.S."), ("T C P I P", "TCP/IP")]
def shown_text(si, li):
    show = SCENES[si].get("show")
    if show and li < len(show) and show[li]: return show[li]
    txt = SCENES[si]["lines"][li]
    for a, b in SPELL: txt = txt.replace(a, b)
    return txt

# What is on screen at time t: the scene's card with as many points as have been read, and the line being read.
def state(t):
    si, shown, cap = 0, 0, ""
    for l in lines:
        if l["start"] - 0.05 <= t:
            si = l["scene"]; sc = SCENES[si]; n = len(sc["lines"]); nb = len(sc["bullets"])
            shown = nb if l["line"] >= n - 1 else min(nb, int(round((l["line"] + 1) * nb / n)))
            cap = shown_text(si, l["line"]) if t <= l["end"] + 0.25 else ""
    if t < lines[0]["start"]: si, shown = 0, 0
    return si, max(shown, 0), cap

cache = {}
def overlay(si, shown, cap):
    k = (si, shown, cap)
    if k not in cache:
        if len(cache) > 64: cache.clear()
        o = static.copy(); o.alpha_composite(card_layer(si, shown)); o.alpha_composite(caption_layer(cap)); cache[k] = o
    return cache[k]

enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-i", WAV, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                        "-movflags", "+faststart", "-shortest", OUT], stdin=subprocess.PIPE)
prev, fade_from, fade_t0 = None, None, -9
for fi in range(NFR):
    t = fi / FPS
    st = state(t)
    if prev is not None and st[:2] != prev[:2]: fade_from, fade_t0 = overlay(*prev), t
    o = overlay(*st)
    if fade_from is not None and t - fade_t0 < 0.3:
        o = Image.blend(fade_from, o, (t - fade_t0) / 0.3)
    frame = background(t).convert("RGBA"); frame.alpha_composite(o)
    dr = ImageDraw.Draw(frame)
    dr.rectangle((0, H - 10, int(W * t / TOTAL), H), fill=GOLD)
    enc.stdin.write(frame.convert("RGB").tobytes())
    prev = st
    if fi % (FPS * 10) == 0: print(f" frame {fi}/{NFR}", flush=True)
enc.stdin.close(); enc.wait()
if enc.returncode: sys.exit("encode failed")
print(f"rendered {OUT} {W}x{H} {TOTAL:.1f}s")
