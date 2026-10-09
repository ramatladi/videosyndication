import os, sys, re, json, io, subprocess, random, math
import numpy as np, soundfile as sf, cairosvg
from PIL import Image, ImageDraw, ImageFont

D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
EP = json.load(open(sys.argv[1])); SEGMENTS = EP["segments"]
WORK = os.environ.get("WORK", "/tmp/wisewords_work"); os.makedirs(WORK, exist_ok=True)

FONTS = os.path.join(D, "fonts")
SERIF = os.path.join(FONTS, "SourceSerif4-Bold.ttf")
SANS_B = os.path.join(FONTS, "IBMPlexSans-Bold.ttf")
SANS_S = os.path.join(FONTS, "IBMPlexSans-SemiBold.ttf")
W, H, FPS, TOTAL = 1080, 1920, 30, 175.0
NFR = int(TOTAL * FPS)
OUT = sys.argv[2]

BG = (15, 22, 34); PANEL = (24, 35, 58); RED = (215, 38, 46); WHITE = (244, 241, 234)
GOLD = (217, 180, 90); UP = (47, 191, 113); DOWN = (255, 92, 92); MUTED = (150, 162, 184)

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
WAV = os.path.join(WORK, "mix.wav"); sf.write(WAV, audio, SR)

hop = SR // FPS
rms = np.array([np.sqrt(np.mean(voice[i * hop:(i + 1) * hop] ** 2)) for i in range(NFR)])
ref = np.percentile(rms[rms > 0.005], 90) if (rms > 0.005).any() else 1
lvl = rms / ref

# ---------- Marco scene variants ----------
svg = open(os.path.join(D, "marco.svg")).read()
MOUTH = '<path d="M312,224 Q320,229 328,224" stroke="#5A2E22" stroke-width="2" fill="none" stroke-linecap="round"/>'
EYES = 'd="M300,194 Q306,189 312,194 M328,194 Q334,189 340,194"'
assert MOUTH in svg and EYES in svg
SW, SH = 1188, 817
def render(s):
    png = cairosvg.svg2png(bytestring=s.encode(), output_width=SW, output_height=SH)
    return Image.open(io.BytesIO(png)).convert("RGB")
mouths = [MOUTH,
          '<ellipse cx="320" cy="225.5" rx="6.5" ry="2.6" fill="#4A2018"/>',
          '<ellipse cx="320" cy="226.5" rx="7.5" ry="5" fill="#4A2018"/><path d="M315,229 Q320,231 325,229" stroke="#C8746A" stroke-width="2" fill="none"/>']
scene = {}
for mi, m in enumerate(mouths):
    for bi, e in enumerate([EYES, 'd="M300,193 L312,193 M328,193 L340,193"']):
        scene[(mi, bi)] = render(svg.replace(MOUTH, m).replace(EYES, e))

# ---------- fonts ----------
def F(p, s): return ImageFont.truetype(p, s)
f_title, f_sub, f_head = F(SERIF, 60), F(SANS_S, 28), F(SANS_B, 46)
f_cap, f_idx, f_val, f_small = F(SANS_B, 60), F(SERIF, 64), F("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 66), F(SANS_S, 26)

# ---------- static layout ----------
SCENE_Y, SCENE_H = 150, 742
HEAD_Y, HEAD_H = SCENE_Y + SCENE_H, 104
TICK_Y, TICK_H = HEAD_Y + HEAD_H, 0
CAP_Y, CAP_H = TICK_Y + TICK_H + 20, 230
BOARD_Y, BOARD_H = CAP_Y + CAP_H + 10, 420

base = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(base)
d.text((48, 30), EP.get("title", "Wise Words"), font=f_title, fill=WHITE)
d.text((50, 104), EP.get("subtitle", "WITH MARCO REYES  ·  WISE WORDS"), font=f_sub, fill=GOLD)
d.rounded_rectangle((W - 170, 52, W - 48, 100), 6, fill=RED)
d.text((W - 109, 76), "LIVE", font=f_sub, fill=(255, 255, 255), anchor="mm")
d.rounded_rectangle((40, BOARD_Y, W - 40, BOARD_Y + BOARD_H), 18, fill=PANEL)

heads = []
for s in SEGMENTS:
    im = Image.new("RGB", (W, HEAD_H), RED); dd = ImageDraw.Draw(im)
    dd.text((48, HEAD_H // 2), s["head"], font=f_head, fill=(255, 255, 255), anchor="lm")
    heads.append(im)

# ticker strip
items = []
for s in SEGMENTS:
    if s.get("dir") in (1, -1):
        items.append((s["index"], ("▲ " if s["dir"] == 1 else "▼ ") + s["val"].lstrip("+-"), UP if s["dir"] == 1 else DOWN))
items += [("WORRY", "▼ 22.0%", DOWN), ("KINDNESS", "▲ 9.5%", UP), ("SCREEN TIME", "▼ 5.3%", DOWN), ("GRATITUDE", "▲ 7.7%", UP)]
f_tk = F("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
parts, x = [], 0
for name, v, c in items:
    parts.append((x, name, WHITE)); x += f_tk.getlength(name) + 16
    parts.append((x, v, c)); x += f_tk.getlength(v) + 60
strip_w = int(x)
strip = Image.new("RGB", (strip_w * 2 + W, TICK_H), (10, 15, 26)); sd = ImageDraw.Draw(strip)
for rep in range(3):
    for px, txt, c in parts:
        if rep * strip_w + px < strip.width:
            sd.text((rep * strip_w + px, TICK_H // 2), txt, font=f_tk, fill=c, anchor="lm")

# ---------- captions ----------
def chunks(text, maxc=34):
    ws, out, cur = text.split(), [], ""
    for w_ in ws:
        if cur and len(cur) + 1 + len(w_) > maxc: out.append(cur); cur = w_
        else: cur = (cur + " " + w_).strip()
    if cur: out.append(cur)
    return out
def wrap(text, font, maxw):
    ws, ls, cur = text.split(), [], ""
    for w_ in ws:
        t_ = (cur + " " + w_).strip()
        if font.getlength(t_) > maxw and cur: ls.append(cur); cur = w_
        else: cur = t_
    ls.append(cur); return ls
caps = []
for l in lines:
    ch = chunks(l_txt := SEGMENTS[l["seg"]]["lines"][l["line"]])
    tot = sum(len(c) for c in ch); t0 = l["start"]
    for c in ch:
        dur = l["dur"] * len(c) / tot
        caps.append((t0, t0 + dur + (gap * 0.6 if c == ch[-1] else 0), c)); t0 += dur
cap_cache = {}
def cap_img(text):
    if text not in cap_cache:
        im = Image.new("RGB", (W, CAP_H), BG); dd = ImageDraw.Draw(im)
        ls = wrap(text, f_cap, W - 120)
        y0 = CAP_H // 2 - (len(ls) * 76) // 2 + 38
        for i, ln in enumerate(ls):
            dd.text((W // 2, y0 + i * 76), ln, font=f_cap, fill=WHITE, anchor="mm")
        cap_cache[text] = im
    return cap_cache[text]

# ---------- board charts ----------
random.seed(7)
def series(direction, n=48):
    v, out = 50.0, []
    for i in range(n):
        if direction == 1: v += random.uniform(-1.5, 2.6)
        elif direction == -1: v += random.uniform(-2.8, 1.2)
        elif direction == 2: v += (-3.2 if i < n * 0.45 else 3.6) + random.uniform(-1.4, 1.4)
        else: v += random.uniform(-1.2, 1.2)
        out.append(v)
    return out
charts = [series(s.get("dir", 0)) for s in SEGMENTS]
def board(si, prog):
    s = SEGMENTS[si]; col = {1: UP, -1: DOWN}.get(s["dir"], GOLD)
    im = Image.new("RGB", (W - 80, BOARD_H), PANEL); dd = ImageDraw.Draw(im)
    dd.text((40, 34), "INDEX", font=f_small, fill=MUTED)
    dd.text((40, 66), s["index"], font=f_idx, fill=WHITE)
    arrow = {1: "▲ ", -1: "▼ "}.get(s["dir"], "")
    dd.text((W - 120, 92), arrow + s["val"].lstrip("+-") if arrow else s["val"], font=f_val, fill=col, anchor="rm")
    pts = charts[si]; lo, hi = min(pts), max(pts)
    cx0, cy0, cw, ch_ = 40, 170, W - 160, 130
    for gy in range(4):
        yy = cy0 + gy * ch_ / 3
        dd.line((cx0, yy, cx0 + cw, yy), fill=(36, 50, 79), width=2)
    k = max(2, int(len(pts) * prog))
    xy = [(cx0 + i * cw / (len(pts) - 1), cy0 + ch_ - (p - lo) / (hi - lo + 1e-6) * ch_) for i, p in enumerate(pts[:k])]
    dd.line(xy, fill=col, width=6, joint="curve")
    ex, ey = xy[-1]; dd.ellipse((ex - 9, ey - 9, ex + 9, ey + 9), fill=col)
    return im
board_cache = {}
f_q, f_qm, f_au = F(SERIF, 50), F(SERIF, 150), F(SANS_S, 34)
def qcard(si, prog):
    s = SEGMENTS[si]
    im = Image.new("RGB", (W - 80, BOARD_H), PANEL); dd = ImageDraw.Draw(im)
    dd.text((34, -10), "\u201c", font=f_qm, fill=GOLD)
    ls = wrap(s["quote"], f_q, W - 200)
    k = max(1, round(len(s["quote"].split()) * prog)); shown = 0
    for i, ln in enumerate(ls):
        ws = ln.split(); take = ws[:max(0, k - shown)]; shown += len(ws)
        if take: dd.text((70, 120 + i * 64), " ".join(take), font=f_q, fill=WHITE)
    if prog >= 1: dd.text((70, BOARD_H - 66), "\u2014 " + s["author"], font=f_au, fill=GOLD)
    return im

# ---------- frames ----------
seg_starts = [seg_start[i] for i in range(len(SEGMENTS))]
PREV = [float(x) for x in os.environ.get("PREVIEW","").split(",") if x]
ff = None if PREV else subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                       "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", WAV,
                       "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                       "-c:a", "aac", "-b:a", "192k", "-t", str(TOTAL), "-movflags", "+faststart", OUT],
                      stdin=subprocess.PIPE)
random.seed(3); blinks = set()
tb = 1.5
while tb < TOTAL:
    f0 = int(tb * FPS); blinks.update(range(f0, f0 + 4)); tb += random.uniform(2.8, 5.5)
ci, mouth_prev = 0, 0
for fi in (sorted(int(x*FPS) for x in PREV) if PREV else range(NFR)):
    tt = fi / FPS
    si = max(i for i, s in enumerate(seg_starts) if s <= tt)
    fr = base.copy()
    lv = lvl[fi]
    m = 2 if lv > 0.55 else 1 if lv > 0.18 else 0
    if m == 2 and mouth_prev == 2 and fi % 3 == 0: m = 1
    mouth_prev = m
    sc = scene[(m, 1 if fi in blinks else 0)]
    # slow drift + gentle push per segment
    local = tt - seg_starts[si]
    ox = int(54 + 40 * math.sin(tt / 9.0)); oy = int(38 + 22 * math.sin(tt / 13.0 + 1))
    fr.paste(sc.crop((ox, oy, ox + W, oy + SCENE_H)), (0, SCENE_Y))
    # headline slides in
    slide = min(1.0, local / 0.45); hx = int(-W * (1 - slide) ** 3)
    fr.paste(heads[si], (hx, HEAD_Y))
    while ci < len(caps) - 1 and caps[ci][1] < tt and caps[ci + 1][0] <= tt: ci += 1
    if caps[ci][0] <= tt <= caps[ci][1]:
        fr.paste(cap_img(caps[ci][2]), (0, CAP_Y))
    prog = min(1.0, local / 3.0)
    key = (si, round(prog, 2))
    if key not in board_cache: board_cache[key] = qcard(si, prog)
    fr.paste(board_cache[key], (40, BOARD_Y))
    if PREV: fr.save(os.path.join(WORK, f"frame_{fi}.png")); continue
    ff.stdin.write(fr.tobytes())
    if fi % 750 == 0: print("frame", fi, flush=True)
if ff: ff.stdin.close(); ff.wait()
print("done", OUT)
