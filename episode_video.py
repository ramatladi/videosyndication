#!/usr/bin/env python3
"""Render one Marigold, Pip & Gourdon episode.
usage: python3 episode_video.py WORKDIR video OUT.mp4 | python3 episode_video.py WORKDIR frames t1,t2"""
import cairo, math, sys, json, subprocess
import numpy as np
import render as R
from render import clamp, lerp, ease, ellipse, fill_stroke, src, glow, hrand

W, H, FPS = 1080, 1920, 30
WD = sys.argv[1]
TL = json.load(open(f'{WD}/timeline.json'))
TOTAL = TL['total']; LINES = TL['lines']; EV = TL['events']
ENV = dict(np.load(f'{WD}/env.npz'))
INTRO = TL['intro']; INTRO_TEXT = TL.get('intro_text') or []
FLY = EV['fly']; CANDLE = EV['candle']; ARMS = EV['arms']; FLARES = EV.get('flares', [])
END = EV['end']
RETURN_LINE = next((l['start'] for l in LINES if FLY and l['start'] > FLY), TOTAL)

MX, MY, MS = 420.0, 1760.0, 0.95
GX, GY = 845.0, 1690.0
SHOTS = {'W': (1.0, 560, 1040), 'MP': (1.7, 470, 640), 'M': (2.3, 420, 700), 'P': (2.6, 545, 790), 'G': (1.9, 815, 1770)}
COLORS = {'M': (1.0, 0.62, 0.25), 'P': (0.45, 0.85, 0.95), 'G': (1.0, 0.82, 0.3)}
NAMES = {'M': 'MARIGOLD', 'P': 'PIP', 'G': 'GOURDON', 'MP': 'MARIGOLD & PIP'}

def env(s, t):
    a = ENV.get(s); i = int(t * FPS)
    return float(a[i]) if a is not None and 0 <= i < len(a) else 0.0

def speaking(t):
    for l in LINES:
        if l['start'] <= t < l['end']: return l
    return None

def camera(t):
    if t < INTRO:
        z, cx, cy = SHOTS['W']; return z * (1 + 0.06 * t / INTRO), cx, cy
    if t >= END:
        u = ease((t - END - 0.3) / 3.0)
        return lerp(1.0, 1.45, u), lerp(560, 440, u), lerp(1040, 820, u)
    if FLY and FLY <= t < RETURN_LINE:
        z, cx, cy = SHOTS['W']; return z, cx, cy
    cur = None; nxt = TOTAL
    for k, l in enumerate(LINES):
        if l['start'] <= t: cur = l; nxt = LINES[k + 1]['start'] if k + 1 < len(LINES) else TOTAL
    z, cx, cy = SHOTS[cur['shot']]
    u = clamp((t - cur['start']) / max(0.5, nxt - cur['start']))
    return z * (1 + 0.045 * u), cx, cy

def candle(t):
    if CANDLE and t >= CANDLE: return max(0.0, 1 - (t - CANDLE) / 0.12)
    boost = 0.5 if any(a <= t < b for a, b in FLARES) else 0.0
    return 1.0 + boost + 0.6 * env('G', t)

def arms_out(t):
    return max([ease((t - a) / 0.5) * (1 - ease((t - b) / 0.5)) for a, b in ARMS] + [0.0])

def pip_pos(t):
    sx, sy = MX + MS * 120, MY - MS * 1002
    bob = 4 * math.sin(t * 1.6)
    def path(u, p0, p1, p2):
        return ((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * p1[0] + u * u * p2[0],
                (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * p1[1] + u * u * p2[1])
    off, ctrl = (1350, -250), (980, 420)
    if not FLY: return sx, sy + bob * MS, None, False
    if FLY <= t < FLY + 0.9:
        u = ease((t - FLY) / 0.9); x, y = path(u, (sx, sy), ctrl, off); return x, y, math.sin(t * 28), True
    if FLY + 0.9 <= t < FLY + 2.3: return None
    if FLY + 2.3 <= t < FLY + 3.1:
        u = ease((t - FLY - 2.3) / 0.8); x, y = path(u, off, ctrl, (sx, sy)); return x, y, math.sin(t * 28), True
    land = 8 * math.exp(-(t - FLY - 3.1) * 8) * math.sin((t - FLY - 3.1) * 25) if t > FLY + 3.1 else 0
    return sx, sy + bob * MS + land, None, False

# ------------------------------------------------ Gourdon the jack-o'-lantern
def draw_gourdon(ctx, t, talk, c):
    x, y, rx, ry = GX, GY, 150, 122
    fl = 0.85 + 0.15 * math.sin(t * 17) * math.sin(t * 6.1)
    lit = clamp(c) * fl
    if c > 0: glow(ctx, x, y, 430, (1, 0.55, 0.15), 0.30 * min(1.6, c) * fl)
    ellipse(ctx, x, y + ry - 6, rx * 1.05, 22); ctx.set_source_rgba(0, 0, 0, 0.5); ctx.fill()
    for i, dx in enumerate((-0.6, 0.6, -0.3, 0.3, 0)):
        ellipse(ctx, x + dx * rx, y, rx * 0.52, ry); fill_stroke(ctx, '#c5521a' if i < 4 else '#db6522', '#3a1606', 5)
    ellipse(ctx, x - 45, y - 60, 40, 16, -0.4); ctx.set_source_rgba(1, 0.9, 0.6, 0.15); ctx.fill()
    ctx.move_to(x - 6, y - ry + 10); ctx.curve_to(x - 4, y - ry - 30, x + 20, y - ry - 38, x + 30, y - ry - 44)
    src(ctx, '#3d5a22'); ctx.set_line_width(16); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.stroke()
    ctx.move_to(x + 10, y - ry - 20); ctx.curve_to(x + 50, y - ry - 40, x + 60, y - ry, x + 40, y - ry + 5)
    src(ctx, '#4f7a2c'); ctx.set_line_width(5); ctx.stroke()
    def carve():
        if lit > 0.02:
            g = cairo.RadialGradient(x, y, 10, x, y, rx)
            g.add_color_stop_rgba(0, 1, 0.95, 0.6, 1); g.add_color_stop_rgba(1, 1, 0.6, 0.15, 1)
            ctx.set_source(g); ctx.fill_preserve()
            ctx.set_source_rgba(0.09, 0.04, 0.02, 1 - lit); ctx.fill_preserve()
        else:
            src(ctx, '#170a04'); ctx.fill_preserve()
        src(ctx, '#3a1606'); ctx.set_line_width(4); ctx.stroke()
    # eyes with dramatic slant (brow drops while talking)
    for s in (-1, 1):
        ex = x + s * 55
        ctx.move_to(ex - s * 38, y - 52 - 8 * talk); ctx.line_to(ex + s * 30, y - 34 + 4 * talk); ctx.line_to(ex - s * 4, y - 2); ctx.close_path(); carve()
    ctx.move_to(x, y - 10); ctx.line_to(x - 16, y + 18); ctx.line_to(x + 16, y + 18); ctx.close_path(); carve()
    # jagged mouth: lower lip drops with speech
    mo = 18 + 46 * clamp(talk)
    top = [(x - 100, y + 30), (x - 70, y + 44), (x - 52, y + 32), (x - 25, y + 46), (x, y + 34), (x + 25, y + 46), (x + 52, y + 32), (x + 70, y + 44), (x + 100, y + 30)]
    ctx.move_to(*top[0])
    for p in top[1:]: ctx.line_to(*p)
    ctx.curve_to(x + 80, y + 40 + mo * 1.4, x - 80, y + 40 + mo * 1.4, x - 100, y + 30); ctx.close_path(); carve()
    for k, tx in enumerate((-38, 38)):  # teeth on the lower lip
        by = y + 40 + mo * 1.05
        ctx.move_to(x + tx - 14, by + 2); ctx.line_to(x + tx, by - 22 + (1 - talk) * 6); ctx.line_to(x + tx + 14, by + 2); ctx.close_path()
        fill_stroke(ctx, '#d4601f', '#3a1606', 3)
    if CANDLE and t > CANDLE:  # smoke from the snuffed candle
        for k in range(6):
            age = t - CANDLE - k * 0.12
            if 0 < age < 3:
                ctx.set_source_rgba(0.75, 0.75, 0.8, 0.22 * (1 - age / 3))
                ctx.arc(x + 20 * math.sin(age * 3 + k), y - ry - 50 - age * 110, 10 + age * 18, 0, 6.3); ctx.fill()

# ------------------------------------------------ captions
def text_box(ctx, lines_txt, y, sizes, colors, pad=26):
    ctx.select_font_face('DejaVu Sans', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    hs = []; ws = []
    for txt, sz in zip(lines_txt, sizes):
        ctx.set_font_size(sz); e = ctx.text_extents(txt); ws.append(e.x_advance); hs.append(sz * 1.22)
    bw = max(ws) + pad * 2; bh = sum(hs) + pad * 1.4
    x0 = (W - bw) / 2; y0 = y - bh / 2; r = 26
    ctx.new_path(); ctx.arc(x0 + r, y0 + r, r, math.pi, 1.5 * math.pi); ctx.arc(x0 + bw - r, y0 + r, r, 1.5 * math.pi, 0)
    ctx.arc(x0 + bw - r, y0 + bh - r, r, 0, 0.5 * math.pi); ctx.arc(x0 + r, y0 + bh - r, r, 0.5 * math.pi, math.pi); ctx.close_path()
    ctx.set_source_rgba(0, 0, 0, 0.55); ctx.fill()
    cy = y0 + pad * 0.7
    for txt, sz, col, w_, h_ in zip(lines_txt, sizes, colors, ws, hs):
        ctx.set_font_size(sz); cy += h_
        ctx.move_to((W - w_) / 2, cy - sz * 0.28); ctx.text_path(txt)
        ctx.set_source_rgba(0, 0, 0, 1); ctx.set_line_width(7); ctx.set_line_join(cairo.LINE_JOIN_ROUND); ctx.stroke_preserve()
        ctx.set_source_rgba(*col, 1); ctx.fill()

def wrap(ctx, text, size, maxw):
    ctx.select_font_face('DejaVu Sans', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); ctx.set_font_size(size)
    out, cur = [], ''
    for w_ in text.split():
        trial = (cur + ' ' + w_).strip()
        if ctx.text_extents(trial).x_advance > maxw and cur: out.append(cur); cur = w_
        else: cur = trial
    out.append(cur); return out

def draw_captions(ctx, t):
    if t < INTRO + 0.2:
        a = clamp(t / 0.3)
        ctx.push_group()
        it = INTRO_TEXT or ['']
        text_box(ctx, it, 330, [62] * (len(it) - 1) + [42 if len(it) > 1 else 62],
                 [(1, 1, 1)] * (len(it) - 1) + [(1, 0.75, 0.3) if len(it) > 1 else (1, 1, 1)])
        ctx.pop_group_to_source(); ctx.paint_with_alpha(a * clamp((INTRO + 0.2 - t) / 0.3)); return
    for k, l in enumerate(LINES):
        end = min(l['end'] + 0.35, LINES[k + 1]['start'] - 0.02) if k + 1 < len(LINES) else l['end'] + 0.6
        if l['start'] - 0.05 <= t < end:
            body = wrap(ctx, l['text'], 56, 900)
            col = COLORS.get(l['spk'], (1, 0.7, 0.5))
            text_box(ctx, [NAMES[l['spk']]] + body, 1330, [36] + [56] * len(body), [col] + [(1, 1, 1)] * len(body))
            return

# ------------------------------------------------ frame
state = {'tilt': 0.05, 'pip_head': 0.0}
def draw_frame(ctx, t):
    R.EYE_DEV.clear()
    ctx.set_operator(cairo.OPERATOR_SOURCE); ctx.set_source_rgb(0, 0, 0); ctx.paint(); ctx.set_operator(cairo.OPERATOR_OVER)
    z, cx, cy = camera(t)
    ctx.save(); ctx.translate(W / 2, H / 2); ctx.scale(z, z); ctx.translate(-cx, -cy)
    R.draw_bg(ctx, t, 0.0)
    R.draw_fog(ctx, t, False)
    l = speaking(t); spk = l['spk'] if l else None
    em, ep, eg_ = env('M', t), env('P', t), env('G', t)
    tgt = 0.05 + (0.1 if spk == 'G' else 0) + (0.07 if spk == 'P' else 0) + 0.05 * em * math.sin(t * 6)
    state['tilt'] += (tgt - state['tilt']) * 0.15
    bob = 4 * math.sin(t * 1.6) + 6 * em * abs(math.sin(t * 5))
    eyes = 0.0
    if t > END + 0.9: eyes = min(1, (t - END - 0.9) / 0.15) * (0.85 + 0.15 * math.sin(t * 13))
    R.draw_char(ctx, t, MS, MX, MY, 0, 0, bob, 0, eyes, state['tilt'], False, mouth=em, arms_out=arms_out(t), hold_rake=False)
    pp = pip_pos(t)
    if pp:
        ht = -0.25 if spk == 'G' else (-0.1 * ep * math.sin(t * 9) - 0.05 * ep)
        state['pip_head'] += (ht - state['pip_head']) * 0.2
        R.draw_crow(ctx, pp[0], pp[1] + (bob * MS if not pp[3] else 0), 0.78 * MS, pp[2], state['pip_head'], ep, t)
    draw_gourdon(ctx, t, eg_, candle(t))
    R.draw_motes(ctx, t)
    R.draw_fog(ctx, t, True)
    ctx.restore()
    g = cairo.RadialGradient(W / 2, H * 0.5, 400, W / 2, H * 0.5, 1250)
    g.add_color_stop_rgba(0, 0, 0, 0, 0); g.add_color_stop_rgba(1, 0, 0, 0, 0.72)
    ctx.set_source(g); ctx.paint()
    if t < 0.5: ctx.set_source_rgba(0, 0, 0, 1 - t / 0.5); ctx.paint()
    if t > END:
        dk = 0.5 * ease((t - END) / 0.25) + 0.5 * ease((t - (TOTAL - 2.0)) / 1.2)
        ctx.set_source_rgba(0, 0, 0, dk); ctx.paint()
        if dk > 0.6:
            for x, y, r in R.EYE_DEV:
                glow(ctx, x, y, r * 0.8, (1, 0.72, 0.2), 0.8 * (dk - 0.5) * clamp((TOTAL - 0.3 - t) / 0.5))
    draw_captions(ctx, t)

def main():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); ctx = cairo.Context(surf)
    if sys.argv[2] == 'frames':
        for ts in sys.argv[3].split(','):
            draw_frame(ctx, float(ts)); surf.write_to_png(f'{WD}/s_{float(ts):05.1f}.png')
        return
    out = sys.argv[3]
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
           '-i', f'{WD}/audio.wav', '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p',
           '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    nf = int(TOTAL * FPS)
    for i in range(nf):
        draw_frame(ctx, i / FPS); surf.flush(); p.stdin.write(bytes(surf.get_data()))
        if i % 150 == 0: print(f'frame {i}/{nf}', flush=True)
    p.stdin.close(); p.wait(); print('done')

if __name__ == '__main__':
    main()
