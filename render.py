#!/usr/bin/env python3
"""Marigold & Pip — an original take on the 'Ramalama Costume Walk' format.
Low leg-level walk toward camera, rake dragging, then slow pull-back reveal.
All characters, visuals and audio are original and generated here."""
import cairo, math, sys, random, subprocess, wave
import numpy as np

W, H, FPS = 1080, 1920, 30
DUR = 15.2

# ---------------------------------------------------------------- helpers
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def lerp(a, b, u): return a + (b - a) * u
def ease(u): u = clamp(u); return u * u * (3 - 2 * u)
def ease3(u):
    u = clamp(u); return 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2
def ease_out_back(u):
    u = clamp(u); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (u - 1) ** 3 + c1 * (u - 1) ** 2
def hexc(h, a=1.0):
    h = h.lstrip('#'); return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)
def src(ctx, h, a=1.0): ctx.set_source_rgba(*hexc(h, a))
def ellipse(ctx, cx, cy, rx, ry, rot=0.0):
    ctx.save(); ctx.translate(cx, cy); ctx.rotate(rot); ctx.scale(rx, ry)
    ctx.arc(0, 0, 1, 0, 2 * math.pi); ctx.restore()
def hrand(*k):
    x = math.sin(sum((i + 1) * 12.9898 * v for i, v in enumerate(k)) + 78.233) * 43758.5453
    return x - math.floor(x)
def fill_stroke(ctx, fill, stroke='#1a120c', lw=5, a=1.0):
    src(ctx, fill, a); ctx.fill_preserve(); src(ctx, stroke); ctx.set_line_width(lw); ctx.stroke()
def glow(ctx, x, y, r, rgb, a):
    g = cairo.RadialGradient(x, y, 0, x, y, r)
    g.add_color_stop_rgba(0, rgb[0], rgb[1], rgb[2], a)
    g.add_color_stop_rgba(0.35, rgb[0], rgb[1], rgb[2], a * 0.45)
    g.add_color_stop_rgba(1, rgb[0], rgb[1], rgb[2], 0)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source(g)
    ctx.arc(x, y, r, 0, 2 * math.pi); ctx.fill(); ctx.restore()

# ---------------------------------------------------------------- timeline
WALK0, STEP, NSTEP, SWING = 0.6, 0.66, 11, 0.42
LANDS = [WALK0 + k * STEP + SWING for k in range(NSTEP)]
WALK_END = WALK0 + NSTEP * STEP          # 7.86
PB0, PB1 = 8.3, 11.3                    # pull-back
HIT = 11.3                              # full reveal + lightning
FLY0, FLY1 = 9.0, 10.8                  # crow flies to shoulder
RAKE0 = 10.95                           # rake swings upright
CAWS = [12.9, 13.22]
BLACK0, BLACK1 = 14.0, 14.9
HORIZON, FY0, FY1 = 980.0, 1380.0, 1780.0

def walk_state(t):
    """progress p, lift left, lift right, body bob, moving?"""
    if t < WALK0: return 0.0, 0.0, 0.0, 0.0, False
    u = (t - WALK0) / STEP; k = int(math.floor(u)); f = u - k
    if k >= NSTEP:
        return 1.0, 0.0, 0.0, 16 * math.exp(-(t - LANDS[-1]) * 10), False
    fs = SWING / STEP
    if f < fs:
        a = f / fs; prog = ease(a); lift = math.sin(math.pi * a) ** 1.3; moving = True
        bl = 16 * math.exp(-(t - LANDS[k - 1]) * 10) if k > 0 else 0
        bob = -lift * 12 + bl
    else:
        prog, lift, moving = 1.0, 0.0, False
        bob = 16 * math.exp(-(t - LANDS[k]) * 10)
    p = (k + prog) / NSTEP
    ll = lift if k % 2 == 1 else 0.0
    lr = lift if k % 2 == 0 else 0.0
    return p, ll, lr, bob, moving

def feet(t):
    p = walk_state(t)[0]
    fy = lerp(FY0, FY1, p); s = (fy - HORIZON) / (FY1 - HORIZON)
    fx = 540 + 14 * math.sin(p * math.pi * 3) * (1 - p)
    return fx, fy, s

def camera(t):
    a = ease3((t - PB0) / (PB1 - PB0))
    zoom = lerp(2.0, 1.0, a); cy = lerp(1680, 960, a)
    sh = 0.0
    for L in LANDS:
        if t >= L: sh += 7 * math.exp(-(t - L) * 14) * math.sin((t - L) * 70)
    if t >= HIT: sh += 16 * math.exp(-(t - HIT) * 6) * math.sin((t - HIT) * 55)
    dx = 3 * math.sin(t * 0.9) + 2 * math.sin(t * 2.3); dy = 3 * math.cos(t * 0.7)
    return zoom, 540 + dx / zoom, cy + (dy + sh) / zoom

def flash(t):
    f = 0.0
    if t >= HIT: f += 0.8 * math.exp(-(t - HIT) * 8)
    if t >= HIT + 0.32: f += 0.5 * math.exp(-(t - HIT - 0.32) * 14)
    return f

def eye_glow(t):
    if t < HIT: return 0.0
    return min(1, (t - HIT) / 0.08) * (0.85 + 0.15 * math.sin(t * 13) * math.sin(t * 3.1))

def rake_amt(t): return ease_out_back((t - RAKE0) / (HIT - RAKE0)) if t > RAKE0 else 0.0

def head_tilt(t):
    return 0.15 * ease((t - 12.0) / 0.6) - 0.09 * ease((t - 13.5) / 0.5)

# ---------------------------------------------------------------- static scenery data
rng = random.Random(7)
PLANKS = list(range(-300, 1400, 72))
KNOTS = [(rng.uniform(-300, 1380), rng.uniform(0, 1030), rng.uniform(5, 11)) for _ in range(40)]
STALKS = [(rng.uniform(325, 755), rng.uniform(50, 130), rng.uniform(-0.25, 0.25)) for _ in range(48)]
STARS = [(rng.uniform(335, 745), rng.uniform(365, 820), rng.uniform(1, 2.6), rng.uniform(0, 6)) for _ in range(40)]
MOTES = [(rng.uniform(240, 840), rng.uniform(650, 2100), rng.uniform(1.5, 4), rng.uniform(0, 6.28), rng.uniform(8, 25)) for _ in range(70)]
FOG = [(rng.uniform(-300, 1400), rng.uniform(1080, 2200), rng.uniform(200, 380), rng.uniform(-28, 28)) for _ in range(18)]
BATS = [(1.4, 640, 1.0, 1), (3.0, 520, 0.8, -1), (5.3, 720, 0.9, 1), (12.0, 600, 1.15, -1), (12.5, 690, 0.8, 1)]
BOLT = [(430, 360)]
for i in range(9):
    BOLT.append((BOLT[-1][0] + rng.uniform(-30, 40), BOLT[-1][1] + rng.uniform(45, 70)))
DX0, DX1, DY0, DY1 = 330, 750, 360, 1050

# ---------------------------------------------------------------- background
def draw_bat(ctx, x, y, sc, t, d):
    ctx.save(); ctx.translate(x, y); ctx.scale(sc * d, sc)
    w = math.sin(t * 22)
    ctx.move_to(0, 0)
    for side in (-1, 1):
        ctx.move_to(0, 0); ctx.line_to(side * 14, -10 * w - 4); ctx.line_to(side * 28, -14 * w)
        ctx.line_to(side * 22, 2); ctx.line_to(side * 14, -2); ctx.line_to(side * 8, 4); ctx.close_path()
    src(ctx, '#05060c'); ctx.fill(); ellipse(ctx, 0, 0, 6, 7); ctx.fill(); ctx.restore()

def draw_pumpkin(ctx, x, y, rx, ry, face, t, phase):
    flick = 0.8 + 0.2 * math.sin(t * 19 + phase) * math.sin(t * 5.3 + phase)
    if face: glow(ctx, x, y, rx * 3.0, (1, 0.6, 0.15), 0.28 * flick)
    for i, dx in enumerate((-0.55, 0.55, -0.25, 0.25, 0)):
        ellipse(ctx, x + dx * rx, y, rx * 0.55, ry); fill_stroke(ctx, '#c9581c' if i < 4 else '#de6a24', '#3a1a08', 4)
    ctx.move_to(x - 4, y - ry + 6); ctx.curve_to(x - 2, y - ry - 18, x + 12, y - ry - 22, x + 16, y - ry - 26)
    src(ctx, '#3d5a22'); ctx.set_line_width(9); ctx.stroke()
    if not face: return
    src(ctx, '#ffd36a'); ctx.set_source_rgba(1, 0.82 * flick + 0.1, 0.35, 1)
    for s in (-1, 1):
        ctx.move_to(x + s * rx * 0.42, y - ry * 0.45); ctx.line_to(x + s * rx * 0.18, y - ry * 0.05)
        ctx.line_to(x + s * rx * 0.62, y - ry * 0.05); ctx.close_path(); ctx.fill()
    ctx.move_to(x - rx * 0.6, y + ry * 0.2)
    pts = 7
    for i in range(1, pts + 1):
        u = i / pts
        ctx.line_to(x - rx * 0.6 + u * rx * 1.2, y + ry * (0.2 + (0.0 if i % 2 else 0.18)) + ry * 0.25 * math.sin(u * math.pi))
    ctx.curve_to(x + rx * 0.4, y + ry * 0.75, x - rx * 0.4, y + ry * 0.75, x - rx * 0.6, y + ry * 0.2)
    ctx.fill()

def draw_bale(ctx, x0, y0, x1, y1):
    ctx.save()
    ctx.new_path(); r = 18
    ctx.move_to(x0 + r, y0); ctx.line_to(x1 - r, y0); ctx.curve_to(x1, y0, x1, y0, x1, y0 + r)
    ctx.line_to(x1, y1); ctx.line_to(x0, y1); ctx.line_to(x0, y0 + r); ctx.curve_to(x0, y0, x0, y0, x0 + r, y0)
    ctx.close_path(); ctx.clip_preserve()
    g = cairo.LinearGradient(0, y0, 0, y1); g.add_color_stop_rgba(0, *hexc('#a9823b')); g.add_color_stop_rgba(1, *hexc('#5e4318'))
    ctx.set_source(g); ctx.fill()
    for i in range(70):
        sx = x0 + hrand(i, x0) * (x1 - x0); sy = y0 + hrand(i, y0) * (y1 - y0)
        ctx.move_to(sx, sy); ctx.line_to(sx + 26 * (hrand(i, 3) - 0.5), sy + 10 * (hrand(i, 4) - 0.5))
        ctx.set_source_rgba(0.95, 0.8, 0.4, 0.35); ctx.set_line_width(2.5); ctx.stroke()
    for bx in (x0 + (x1 - x0) * 0.3, x0 + (x1 - x0) * 0.7):
        ctx.rectangle(bx - 6, y0, 12, y1 - y0); src(ctx, '#4a2d14'); ctx.fill()
    ctx.restore()
    ctx.new_path()

def draw_bg(ctx, t, fl):
    # back wall
    g = cairo.LinearGradient(0, -300, 0, 1050)
    g.add_color_stop_rgba(0, *hexc('#0d0a16')); g.add_color_stop_rgba(1, *hexc('#221a34'))
    ctx.set_source(g); ctx.rectangle(-500, -500, 2080, 1551); ctx.fill()
    for x in PLANKS:
        ctx.rectangle(x + 4, -500, 10, 1550); ctx.set_source_rgba(1, 1, 1, 0.025); ctx.fill()
        ctx.move_to(x, -500); ctx.line_to(x, 1050); src(ctx, '#09060f'); ctx.set_line_width(3); ctx.stroke()
    for kx, ky, kr in KNOTS:
        ellipse(ctx, kx, ky, kr * 1.6, kr); ctx.set_source_rgba(0, 0, 0, 0.35); ctx.set_line_width(2); ctx.stroke()
    # doorway: night sky, moon, cornfield
    ctx.save(); ctx.rectangle(DX0, DY0, DX1 - DX0, DY1 - DY0); ctx.clip()
    g = cairo.LinearGradient(0, DY0, 0, DY1)
    g.add_color_stop_rgba(0, *hexc('#0a1430')); g.add_color_stop_rgba(1, *hexc('#33305f'))
    ctx.set_source(g); ctx.paint()
    for sx, sy, sr, ph in STARS:
        ctx.set_source_rgba(1, 1, 0.9, 0.5 + 0.5 * math.sin(t * 2 + ph)); ctx.arc(sx, sy, sr, 0, 6.3); ctx.fill()
    glow(ctx, 565, 580, 330, (0.75, 0.82, 1.0), 0.35)
    ctx.arc(565, 580, 80, 0, 6.3); src(ctx, '#efe7c9'); ctx.fill()
    for cx, cy, cr in ((540, 560, 14), (590, 600, 10), (575, 545, 7), (548, 612, 8)):
        ctx.arc(cx, cy, cr, 0, 6.3); ctx.set_source_rgba(0.6, 0.55, 0.45, 0.35); ctx.fill()
    for bt, by, bs, d in BATS:
        u = (t - bt) / 3.6
        if 0 <= u <= 1:
            bx = DX0 - 40 + u * (DX1 - DX0 + 80) if d > 0 else DX1 + 40 - u * (DX1 - DX0 + 80)
            draw_bat(ctx, bx, by + 30 * math.sin(u * 9), bs, t, d)
    if 0 <= t - HIT < 0.16 or 0 <= t - HIT - 0.32 < 0.08:
        ctx.move_to(*BOLT[0])
        for p in BOLT[1:]: ctx.line_to(*p)
        ctx.set_source_rgba(0.8, 0.85, 1, 0.5); ctx.set_line_width(16); ctx.stroke_preserve()
        ctx.set_source_rgba(1, 1, 1, 1); ctx.set_line_width(5); ctx.stroke()
    ctx.move_to(DX0, 960); ctx.curve_to(450, 930, 600, 950, DX1, 925); ctx.line_to(DX1, DY1); ctx.line_to(DX0, DY1); ctx.close_path()
    src(ctx, '#0a0e1a'); ctx.fill()
    for sx, sh, lean in STALKS:
        sw = math.sin(t * 1.3 + sx * 0.05) * 0.04
        tx, ty = sx + (lean + sw) * sh, DY1 - sh
        ctx.move_to(sx, DY1); ctx.line_to(tx, ty); src(ctx, '#05070c'); ctx.set_line_width(4); ctx.stroke()
        for lf in (0.45, 0.7):
            lx, ly = lerp(sx, tx, lf), lerp(DY1, ty, lf)
            d = 1 if hrand(sx, lf) > 0.5 else -1
            ctx.move_to(lx, ly); ctx.curve_to(lx + d * 14, ly - 10, lx + d * 24, ly - 4, lx + d * 30, ly + 6)
            ctx.set_line_width(3); ctx.stroke()
    if fl > 0: ctx.set_source_rgba(0.85, 0.9, 1, min(1, fl)); ctx.paint()
    ctx.restore()
    # door leaves + frame
    for side in (-1, 1):
        ex = DX0 if side < 0 else DX1
        ctx.move_to(ex, DY0 - 10); ctx.line_to(ex + side * 125, DY0 + 40); ctx.line_to(ex + side * 125, DY1 + 5); ctx.line_to(ex, DY1)
        ctx.close_path(); fill_stroke(ctx, '#2b1c13', '#0d0806', 4)
        for i in range(1, 4):
            ctx.move_to(ex + side * 31 * i, DY0 - 10 + 12 * i); ctx.line_to(ex + side * 31 * i, DY1 + 2)
            src(ctx, '#140c08'); ctx.set_line_width(3); ctx.stroke()
        ctx.move_to(ex, DY0 + 20); ctx.line_to(ex + side * 125, DY1 - 20); src(ctx, '#3a271a'); ctx.set_line_width(14); ctx.stroke()
    ctx.rectangle(DX0 - 14, DY0 - 16, DX1 - DX0 + 28, 30); src(ctx, '#2e1e14'); ctx.fill()
    # beams & posts
    ctx.rectangle(-500, 248, 2080, 52); src(ctx, '#2a1d15'); ctx.fill()
    ctx.rectangle(-500, 248, 2080, 6); ctx.set_source_rgba(1, 0.9, 0.7, 0.06); ctx.fill()
    for px in (90, 990):
        ctx.rectangle(px - 27, -500, 54, 1550); src(ctx, '#261a13'); ctx.fill()
    for a, b in (((117, 430), (270, 290)), ((963, 430), (810, 290))):
        ctx.move_to(*a); ctx.line_to(*b); src(ctx, '#241811'); ctx.set_line_width(28); ctx.stroke()
    # cobweb
    cx, cy = 117, 300
    ctx.set_source_rgba(0.8, 0.8, 0.9, 0.22); ctx.set_line_width(1.5)
    for ang in np.linspace(0.05, 1.5, 6):
        ctx.move_to(cx, cy); ctx.line_to(cx + 150 * math.cos(ang), cy + 150 * math.sin(ang)); ctx.stroke()
    for r in (35, 65, 95, 125):
        ctx.arc(cx, cy, r, 0.05, 1.5); ctx.stroke()
    # floor
    g = cairo.LinearGradient(0, 1050, 0, 2300)
    g.add_color_stop_rgba(0, *hexc('#2c2018')); g.add_color_stop_rgba(1, *hexc('#120c08'))
    ctx.set_source(g); ctx.rectangle(-500, 1050, 2080, 1300); ctx.fill()
    for xb in range(-2600, 3700, 115):
        x1 = 540 + (xb - 540) * (1050 - HORIZON) / (2300 - HORIZON)
        ctx.move_to(x1, 1050); ctx.line_to(xb, 2300); src(ctx, '#0e0907'); ctx.set_line_width(3); ctx.stroke()
    Z = 10.0
    while True:
        y = HORIZON + 700 / Z
        if y > 2300: break
        if y > 1050:
            ctx.move_to(-500, y); ctx.line_to(1580, y); ctx.set_source_rgba(0, 0, 0, 0.45); ctx.set_line_width(2); ctx.stroke()
        Z -= 0.8
        if Z <= 0.2: break
    # moonbeam on floor
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    g = cairo.LinearGradient(0, 1050, 0, 2300)
    g.add_color_stop_rgba(0, 0.45, 0.55, 1.0, 0.22 + 0.3 * fl); g.add_color_stop_rgba(1, 0.45, 0.55, 1.0, 0.04 + 0.2 * fl)
    ctx.set_source(g)
    ctx.move_to(DX0, 1050); ctx.line_to(DX1, 1050); ctx.line_to(1180, 2300); ctx.line_to(-100, 2300); ctx.close_path(); ctx.fill()
    # light shaft in air
    g = cairo.LinearGradient(0, DY0, 0, 1700)
    g.add_color_stop_rgba(0, 0.5, 0.6, 1, 0.07); g.add_color_stop_rgba(1, 0.5, 0.6, 1, 0.0)
    ctx.set_source(g); ctx.move_to(DX0 + 30, DY0); ctx.line_to(DX1 - 30, DY0); ctx.line_to(1000, 1700); ctx.line_to(80, 1700); ctx.close_path(); ctx.fill()
    ctx.restore()
    # bales + pumpkins
    draw_bale(ctx, 40, 945, 345, 1085)
    draw_bale(ctx, 755, 965, 1045, 1085)
    draw_pumpkin(ctx, 205, 898, 62, 50, True, t, 0.0)
    draw_pumpkin(ctx, 850, 925, 46, 40, True, t, 2.1)
    draw_pumpkin(ctx, 965, 937, 34, 30, False, t, 0)
    # hanging lantern
    ang = 0.1 * math.sin(2 * math.pi * t / 2.6)
    px, py = 230, 298
    lx, ly = px + math.sin(ang) * 170, py + math.cos(ang) * 170
    ctx.move_to(px, py); ctx.line_to(lx, ly - 40); src(ctx, '#111111'); ctx.set_line_width(3); ctx.stroke()
    flick = 0.85 + 0.15 * math.sin(t * 23) * math.sin(t * 7.3)
    glow(ctx, lx, ly, 440, (1, 0.62, 0.25), 0.30 * flick)
    ctx.save(); ctx.translate(lx, ly); ctx.rotate(-ang)
    ctx.rectangle(-24, -30, 48, 62); src(ctx, '#ffbf5a', 0.95); ctx.fill()
    ctx.set_source_rgba(1, 0.95, 0.7, flick); ellipse(ctx, 0, 4, 8, 14); ctx.fill()
    for bx in (-24, 0, 24):
        ctx.move_to(bx, -30); ctx.line_to(bx, 32); src(ctx, '#151010'); ctx.set_line_width(4); ctx.stroke()
    ctx.move_to(-30, -30); ctx.line_to(0, -48); ctx.line_to(30, -30); ctx.close_path(); src(ctx, '#151010'); ctx.fill()
    ctx.rectangle(-30, 30, 60, 8); ctx.fill()
    ctx.restore()

def draw_motes(ctx, t):
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for mx, my, mr, ph, sp in MOTES:
        y = 650 + ((my - 650 - t * sp) % 1450)
        x = mx + 12 * math.sin(t * 0.7 + ph)
        ctx.set_source_rgba(0.75, 0.82, 1, 0.18 + 0.15 * math.sin(t * 2.5 + ph))
        ctx.arc(x, y, mr, 0, 6.3); ctx.fill()
    ctx.restore()

def draw_fog(ctx, t, front):
    for i, (fx, fy, fr, vx) in enumerate(FOG):
        if (i % 2 == 0) != front: continue
        x = (fx + vx * t + 300) % 1900 - 300
        g = cairo.RadialGradient(x, fy, 0, x, fy, fr)
        a = 0.06 if front else 0.11
        g.add_color_stop_rgba(0, 0.6, 0.63, 0.8, a); g.add_color_stop_rgba(1, 0.6, 0.63, 0.8, 0)
        ctx.set_source(g); ellipse(ctx, x, fy, fr, fr * 0.45); ctx.fill()

# ---------------------------------------------------------------- rake trail
RAKE_TR = (-230.0, -40.0)
def draw_trail(ctx, t):
    if t <= WALK0 + 0.05: return
    pts = []
    tt = WALK0
    while tt <= min(t, WALK_END + 0.01):
        fx, fy, s = feet(tt); pts.append((fx + s * RAKE_TR[0], fy + s * RAKE_TR[1], s)); tt += 0.04
    fx, fy, s = feet(t); pts.append((fx + s * RAKE_TR[0], fy + s * RAKE_TR[1], s))
    for off in (-55, -18, 18, 55):
        ctx.move_to(pts[0][0] + off * pts[0][2], pts[0][1])
        for x, y, s in pts[1:]: ctx.line_to(x + off * s, y)
        ctx.set_source_rgba(0.82, 0.74, 0.62, 0.22); ctx.set_line_width(3); ctx.stroke()

# ---------------------------------------------------------------- crow "Pip"
def draw_crow(ctx, x, y, sc, wing, head_ang, beak, t):
    ctx.save(); ctx.translate(x, y); ctx.scale(sc, sc)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    if wing is None:
        for lx in (-12, 10):
            ctx.move_to(lx, -16); ctx.line_to(lx - 3, 0); src(ctx, '#e39a35'); ctx.set_line_width(6); ctx.stroke()
            for d in (-12, 0, 10):
                ctx.move_to(lx - 3, 0); ctx.line_to(lx - 3 + d, 4); ctx.set_line_width(4); ctx.stroke()
    def wing_shape(theta, col):
        ctx.save(); ctx.translate(8, -78); ctx.rotate(theta)
        ctx.move_to(0, 0); ctx.curve_to(40, -40, 90, -110, 140, -120)
        ctx.line_to(120, -92); ctx.line_to(150, -86); ctx.line_to(118, -62); ctx.line_to(140, -48)
        ctx.line_to(96, -36); ctx.line_to(104, -18); ctx.curve_to(60, -6, 30, 6, 0, 10); ctx.close_path()
        fill_stroke(ctx, col, '#050408', 4); ctx.restore()
    if wing is not None: wing_shape(-0.2 + wing * 0.9, '#100e15')
    # tail
    ctx.move_to(40, -52); ctx.line_to(112, -28); ctx.line_to(104, -14); ctx.line_to(116, -6); ctx.line_to(44, -30); ctx.close_path()
    fill_stroke(ctx, '#121018', '#050408', 4)
    ellipse(ctx, 0, -60, 64, 48); fill_stroke(ctx, '#18161f', '#050408', 4)
    ellipse(ctx, -14, -46, 30, 18); ctx.set_source_rgba(1, 1, 1, 0.05); ctx.fill()
    if wing is None:
        ellipse(ctx, 18, -64, 48, 28, -0.2); fill_stroke(ctx, '#24212c', '#050408', 3)
        for i in range(3):
            ctx.move_to(30 + i * 10, -70 + i * 4); ctx.line_to(58 + i * 6, -52 + i * 4)
            ctx.set_source_rgba(0, 0, 0, 0.6); ctx.set_line_width(2.5); ctx.stroke()
    else:
        wing_shape(-0.5 + wing * 1.1, '#1d1a24')
    # head (rotates about neck)
    ctx.save(); ctx.translate(-30, -88); ctx.rotate(head_ang); ctx.translate(30, 88)
    for i, (sx, sy) in enumerate(((-52, -138), (-42, -142), (-32, -138))):
        ctx.move_to(sx - 6, sy + 8); ctx.line_to(sx + 2 * i - 2, sy - 12); ctx.line_to(sx + 6, sy + 8); src(ctx, '#18161f'); ctx.fill()
    ctx.arc(-45, -108, 34, 0, 6.3); fill_stroke(ctx, '#18161f', '#050408', 4)
    # beak
    for part, sign, rot in ((((-74, -119), (-120, -107), (-74, -104)), -1, 0.35), (((-74, -105), (-110, -101), (-74, -95)), 1, 0.5)):
        ctx.save(); ctx.translate(-74, -108); ctx.rotate(sign * beak * rot); ctx.translate(74, 108)
        ctx.move_to(*part[0]); ctx.line_to(*part[1]); ctx.line_to(*part[2]); ctx.close_path()
        fill_stroke(ctx, '#e3a43a', '#5a3208', 3); ctx.restore()
    ctx.arc(-55, -118, 11, 0, 6.3); src(ctx, '#f4f1e6'); ctx.fill()
    ctx.arc(-58, -118, 6, 0, 6.3); src(ctx, '#0a0a0a'); ctx.fill()
    ctx.arc(-60, -121, 2.2, 0, 6.3); src(ctx, '#ffffff'); ctx.fill()
    ctx.restore()
    # little striped scarf (matches Marigold's stockings)
    ctx.save()
    ellipse(ctx, -24, -86, 30, 12, -0.3); ctx.clip_preserve(); src(ctx, '#e0702a'); ctx.fill()
    for i in range(-3, 4):
        ctx.rectangle(-54 + i * 14, -110, 6, 50); src(ctx, '#1b1416'); ctx.fill()
    ctx.restore()
    ctx.move_to(-12, -84); ctx.curve_to(0, -60, 10 + 6 * math.sin(t * 6), -46, 4 + 8 * math.sin(t * 6), -30)
    src(ctx, '#e0702a'); ctx.set_line_width(12); ctx.stroke()
    ctx.restore()

def crow_state(t):
    fx, fy, s = feet(t)
    gx, gy, gsc = fx + 195 * s, fy + 12 * s, 0.85 * s
    if t < FLY0:
        hop = 0.0
        if WALK0 <= t < WALK_END:
            u = ((t - WALK0) / STEP * 2) % 1; hop = abs(math.sin(math.pi * u)) * 28 * s
        head = -0.35 * ease((t - WALK_END) / 0.4) if t > WALK_END else 0.0
        if t > FLY0 - 0.25: hop = 18 * math.sin(math.pi * clamp((t - FLY0 + 0.25) / 0.25))  # crouch-hop
        return gx, gy - hop, gsc, None, head, 0.0
    sx, sy = 540 + 120, FY1 - 1002
    if t < FLY1:
        u = ease((t - FLY0) / (FLY1 - FLY0))
        p0, p1, p2 = (gx, gy), (fx + 420, fy - 560), (sx, sy)
        x = (1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * p1[0] + u * u * p2[0]
        y = (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * p1[1] + u * u * p2[1]
        return x, y, lerp(0.85, 0.78, u), math.sin(t * 28), 0.0, 0.0
    beak = 0.0; head = 0.0
    for c in CAWS:
        if c <= t < c + 0.26:
            beak = math.sin(math.pi * (t - c) / 0.26); head = -0.25 * beak
    land = 10 * math.exp(-(t - FLY1) * 9) * math.sin((t - FLY1) * 30)
    _, _, _, bob, _ = walk_state(t)
    return sx, sy + land + bob_hit(t), 0.78, None, head, beak

def bob_hit(t):
    return 14 * math.exp(-(t - HIT) * 7) * math.sin(min(math.pi, (t - HIT) * 12)) if t >= HIT else 0.0

# ---------------------------------------------------------------- Marigold
EYE_DEV = []
def draw_rake(ctx, a, bob, t, sparks):
    H_tr, H_up = (-185.0, -720.0 + bob), (-212.0, -735.0 + bob)
    Hx, Hy = lerp(H_tr[0], H_up[0], clamp(a)), lerp(H_tr[1], H_up[1], clamp(a))
    ang_tr = math.atan2(RAKE_TR[1] - H_tr[1], RAKE_TR[0] - H_tr[0])
    ang = lerp(ang_tr, math.radians(268), a)
    d = (math.cos(ang), math.sin(ang)); n = (-d[1], d[0])
    hl, bl = lerp(682, 595, a), lerp(155, 715, a)
    head = (Hx + d[0] * hl, Hy + d[1] * hl); butt = (Hx - d[0] * bl, Hy - d[1] * bl)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.move_to(*butt); ctx.line_to(*head); src(ctx, '#1a120c'); ctx.set_line_width(24); ctx.stroke()
    ctx.move_to(*butt); ctx.line_to(*head); src(ctx, '#7a5432'); ctx.set_line_width(16); ctx.stroke()
    ctx.move_to(butt[0] + n[0] * 3, butt[1] + n[1] * 3); ctx.line_to(head[0] + n[0] * 3, head[1] + n[1] * 3)
    ctx.set_source_rgba(1, 0.85, 0.6, 0.25); ctx.set_line_width(4); ctx.stroke()
    # rake head
    b0 = (head[0] - n[0] * 82, head[1] - n[1] * 82); b1 = (head[0] + n[0] * 82, head[1] + n[1] * 82)
    for k in range(9):
        u = k / 8
        px, py = lerp(b0[0], b1[0], u), lerp(b0[1], b1[1], u)
        ctx.move_to(px, py); ctx.line_to(px + d[0] * 58, py + d[1] * 58)
        src(ctx, '#121214'); ctx.set_line_width(10); ctx.stroke()
        ctx.move_to(px, py); ctx.line_to(px + d[0] * 56, py + d[1] * 56)
        src(ctx, '#7d7d88'); ctx.set_line_width(5); ctx.stroke()
    ctx.move_to(*b0); ctx.line_to(*b1); src(ctx, '#121214'); ctx.set_line_width(20); ctx.stroke()
    ctx.move_to(*b0); ctx.line_to(*b1); src(ctx, '#5a5a66'); ctx.set_line_width(12); ctx.stroke()
    if sparks:
        tip = (head[0] + d[0] * 58, head[1] + d[1] * 58)
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        tb = math.floor((t - 0.35) / 0.035) * 0.035
        while tb <= t:
            if WALK0 <= tb < WALK_END and walk_state(tb)[4]:
                for j in range(3):
                    r1, r2, r3 = hrand(tb * 100, j), hrand(tb * 100, j + 7), hrand(tb * 100, j + 13)
                    age = t - tb
                    if 0 <= age <= 0.35:
                        x = tip[0] + (r1 - 0.5) * 150 + (r2 - 0.5) * 300 * age
                        y = tip[1] - (160 + 260 * r3) * age + 900 * age * age
                        al = 1 - age / 0.35
                        ctx.set_source_rgba(1, 0.55 + 0.35 * r2, 0.2, al * 0.9)
                        ctx.arc(x, y, 3.5 + 3 * r3, 0, 6.3); ctx.fill()
            tb += 0.035
        ctx.restore()
    return (Hx, Hy)

def burlap_texture(ctx, x0, y0, x1, y1, step=15):
    for i, x in enumerate(np.arange(x0 - (y1 - y0), x1, step)):
        ctx.move_to(x, y0); ctx.line_to(x + (y1 - y0), y1)
        ctx.set_source_rgba(0, 0, 0, 0.07); ctx.set_line_width(2); ctx.stroke()
        ctx.move_to(x + (y1 - y0), y0); ctx.line_to(x, y1)
        ctx.set_source_rgba(1, 1, 0.8, 0.05); ctx.stroke()

def stitches(ctx, pts, closed=True):
    ctx.set_dash([10, 8]); ctx.move_to(*pts[0])
    for p in pts[1:]: ctx.line_to(*p)
    if closed: ctx.close_path()
    src(ctx, '#f3e3c0', 0.9); ctx.set_line_width(3); ctx.stroke(); ctx.set_dash([])

def straw(ctx, x, y, ang0, ang1, n, l0, l1, seed, t=0.0, lw=5):
    for i in range(n):
        a = lerp(ang0, ang1, hrand(seed, i)); L = lerp(l0, l1, hrand(seed, i + 50))
        a += 0.05 * math.sin(t * 3 + i)
        ctx.move_to(x, y); ctx.line_to(x + math.cos(a) * L, y + math.sin(a) * L)
        src(ctx, '#e8c45a' if i % 3 else '#bf9634'); ctx.set_line_width(lw); ctx.stroke()

def draw_leg(ctx, side, lift, hip_y, t):
    ax, ay = side * 62, -100 - lift * 45
    hx = side * 56
    ctx.save()
    ctx.move_to(hx - 34, hip_y)
    ctx.curve_to(hx - 36 + side * lift * 8, lerp(hip_y, ay, 0.45), ax - 26, ay - 80, ax - 23, ay)
    ctx.line_to(ax + 23, ay)
    ctx.curve_to(ax + 26, ay - 80, hx + 36 + side * lift * 8, lerp(hip_y, ay, 0.45), hx + 34, hip_y)
    ctx.close_path()
    path = ctx.copy_path()
    ctx.clip()
    for i, y in enumerate(np.arange(hip_y, ay + 40, 36)):
        ctx.rectangle(-300, y, 600, 36); src(ctx, '#e0702a' if i % 2 == 0 else '#1b1416'); ctx.fill()
    g = cairo.LinearGradient(ax - 30, 0, ax + 30, 0)
    g.add_color_stop_rgba(0, 0, 0, 0, 0.35); g.add_color_stop_rgba(0.5, 1, 1, 1, 0.08); g.add_color_stop_rgba(1, 0, 0, 0, 0.4)
    ctx.set_source(g); ctx.paint()
    ctx.restore()
    ctx.append_path(path); src(ctx, '#0c0a0d'); ctx.set_line_width(5); ctx.stroke()
    return ax, ay

def draw_boot(ctx, side, lift, t):
    cx = side * 62; by = -lift * 45; sc = 1 + lift * 0.08
    ctx.save(); ctx.translate(cx, by); ctx.scale(sc, sc)
    col = '#5a3a22' if side < 0 else '#221d25'
    ctx.move_to(-38, -112); ctx.line_to(38, -112); ctx.line_to(42, -36); ctx.line_to(-42, -36); ctx.close_path()
    fill_stroke(ctx, col, '#0c0806', 5)
    ellipse(ctx, 0, -28, 68, 34); fill_stroke(ctx, col, '#0c0806', 5)
    ellipse(ctx, -14, -40, 26, 10, -0.2); ctx.set_source_rgba(1, 1, 1, 0.12); ctx.fill()
    ctx.move_to(0, -54); ctx.curve_to(4, -78, 30, -84, 26, -64); ctx.curve_to(22, -54, 10, -60, 14, -68)
    src(ctx, '#0c0806'); ctx.set_line_width(9); ctx.stroke()
    ctx.move_to(0, -54); ctx.curve_to(4, -78, 30, -84, 26, -64); ctx.curve_to(22, -54, 10, -60, 14, -68)
    src(ctx, col); ctx.set_line_width(4); ctx.stroke()
    ellipse(ctx, 0, -2, 70, 10); src(ctx, '#0c0806'); ctx.fill()
    if side < 0:
        ctx.rectangle(-28, -100, 30, 26); fill_stroke(ctx, '#8a5a3a', '#0c0806', 3)
        stitches(ctx, [(-26, -98), (0, -98), (0, -76), (-26, -76)])
    else:
        ctx.rectangle(-36, -78, 72, 12); src(ctx, '#3a3340'); ctx.fill()
        ctx.rectangle(-12, -82, 24, 20); src(ctx, '#d9b14a'); ctx.set_line_width(5); ctx.stroke()
    ctx.restore()

def draw_char(ctx, t, s, fx, fy, ll, lr, bob, a, eg, tilt, sparks, mouth=0.0, arms_out=0.0, hold_rake=True):
    ctx.save(); ctx.translate(fx, fy); ctx.scale(s, s)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ellipse(ctx, 0, 6, 250, 42); ctx.set_source_rgba(0, 0, 0, 0.45); ctx.fill()
    H = None
    if not hold_rake:
        H = (lerp(-118, -335, arms_out), lerp(-838, -1000, arms_out) + bob)
        a = -1
    elif a < 0.5: H = draw_rake(ctx, a, bob, t, sparks)
    hip_y = -560 + bob
    for side, lift in ((-1, ll), (1, lr)):
        ax, ay = draw_leg(ctx, side, lift, hip_y, t)
        draw_boot(ctx, side, lift, t)
        straw(ctx, ax, ay - 8, -math.pi + 0.3, -0.3, 8, 25, 55, side * 3 + 1, t)
    # landing dust puffs
    for k, L in enumerate(LANDS):
        age = t - L
        if 0 <= age < 0.55:
            side = 1 if k % 2 == 0 else -1
            for j, dx in enumerate((-80, 80, 0)):
                r = 20 + 110 * age * (0.8 + 0.4 * hrand(k, j))
                ctx.set_source_rgba(0.62, 0.58, 0.55, 0.32 * (1 - age / 0.55))
                ellipse(ctx, side * 62 + dx * (0.6 + age), -14 - 30 * age, r, r * 0.5); ctx.fill()
    ctx.save(); ctx.translate(0, bob)
    # skirt
    ctx.move_to(-100, -830); ctx.curve_to(-150, -720, -230, -560, -285, -470)
    n = 16
    for i in range(1, n + 1):
        x = -285 + 570 * i / n + 6 * math.sin(t * 4 + i * 0.8) + (lr - ll) * 10
        y = -470 + (0 if i % 2 == 0 else -38) + 8 * hrand(i, 5)
        ctx.line_to(x, y)
    ctx.curve_to(230, -560, 150, -720, 100, -830); ctx.close_path()
    skirt = ctx.copy_path()
    src(ctx, '#b48a52'); ctx.fill()
    ctx.save(); ctx.append_path(skirt); ctx.clip()
    burlap_texture(ctx, -300, -840, 300, -440)
    g = cairo.LinearGradient(0, -830, 0, -470)
    g.add_color_stop_rgba(0, 0, 0, 0, 0.0); g.add_color_stop_rgba(1, 0, 0, 0, 0.3)
    ctx.set_source(g); ctx.paint()
    for (px, py, pw, ph, col, rot) in ((-165, -630, 95, 85, '#6a3d8f', 0.12), (110, -690, 72, 70, '#3f7a4a', -0.1), (40, -560, 64, 52, '#a33b3b', 0.05)):
        ctx.save(); ctx.translate(px, py); ctx.rotate(rot)
        ctx.rectangle(-pw / 2, -ph / 2, pw, ph); fill_stroke(ctx, col, '#1a120c', 3)
        if col == '#a33b3b':
            for i in range(4):
                ctx.rectangle(-pw / 2 + i * 16, -ph / 2, 5, ph); ctx.set_source_rgba(1, 1, 1, 0.35); ctx.fill()
                ctx.rectangle(-pw / 2, -ph / 2 + i * 14, pw, 4); ctx.fill()
        stitches(ctx, [(-pw / 2 + 6, -ph / 2 + 6), (pw / 2 - 6, -ph / 2 + 6), (pw / 2 - 6, ph / 2 - 6), (-pw / 2 + 6, ph / 2 - 6)])
        ctx.restore()
    ctx.restore()
    ctx.append_path(skirt); src(ctx, '#2b1d10'); ctx.set_line_width(6); ctx.stroke()
    # torso
    ctx.move_to(-100, -830); ctx.curve_to(-110, -900, -125, -960, -125, -1000)
    ctx.curve_to(-110, -1030, -70, -1040, -50, -1040); ctx.line_to(50, -1040)
    ctx.curve_to(70, -1040, 110, -1030, 125, -1000); ctx.curve_to(125, -960, 110, -900, 100, -830); ctx.close_path()
    torso = ctx.copy_path()
    src(ctx, '#a97e48'); ctx.fill()
    ctx.save(); ctx.append_path(torso); ctx.clip(); burlap_texture(ctx, -130, -1045, 130, -825); ctx.restore()
    ctx.append_path(torso); src(ctx, '#2b1d10'); ctx.set_line_width(6); ctx.stroke()
    # heart patch + buttons
    ctx.save(); ctx.translate(-48, -935)
    ctx.move_to(0, 20); ctx.curve_to(-40, -6, -24, -38, 0, -18); ctx.curve_to(24, -38, 40, -6, 0, 20)
    fill_stroke(ctx, '#c4423f', '#3a0d0d', 3); ctx.restore()
    for i, (bc, by) in enumerate((('#e0a73a', -1000), ('#3f8f8a', -950), ('#8d5bb0', -900))):
        ctx.arc(28, by, 11 - i, 0, 6.3); fill_stroke(ctx, bc, '#1a120c', 3)
    # rope belt
    ctx.rectangle(-108, -848, 216, 26); fill_stroke(ctx, '#cdae6e', '#4a3418', 3)
    for x in range(-104, 108, 12):
        ctx.move_to(x, -846); ctx.line_to(x + 10, -824); ctx.set_source_rgba(0.3, 0.2, 0.05, 0.5); ctx.set_line_width(2); ctx.stroke()
    ctx.arc(40, -835, 15, 0, 6.3); fill_stroke(ctx, '#cdae6e', '#4a3418', 3)
    for ex, ey in ((25, -755), (62, -768)):
        ctx.move_to(40, -828); ctx.curve_to(40, -800, ex + 4 * math.sin(t * 3), ey - 30, ex + 6 * math.sin(t * 3 + 1), ey)
        src(ctx, '#4a3418'); ctx.set_line_width(12); ctx.stroke()
        ctx.move_to(40, -828); ctx.curve_to(40, -800, ex + 4 * math.sin(t * 3), ey - 30, ex + 6 * math.sin(t * 3 + 1), ey)
        src(ctx, '#cdae6e'); ctx.set_line_width(7); ctx.stroke()
    ctx.restore()  # end bob translate (rake & arms use explicit bob)
    if a >= 0.5: H = draw_rake(ctx, a, bob, t, False)
    ctx.save(); ctx.translate(0, bob)
    Hl = (H[0], H[1] - bob)
    # arms
    if hold_rake:
        armsL = ((-128, -978), ((-128 + Hl[0]) / 2 - 30, (-978 + Hl[1]) / 2), Hl)
    else:
        armsL = ((-128, -978), (lerp(-212, -232, arms_out), lerp(-878, -1000, arms_out)), Hl)
    armsR = ((128, -978), (lerp(212, 232, arms_out), lerp(-878, -1000, arms_out)), (lerp(118, 335, arms_out), lerp(-838, -1000, arms_out)))
    for S, E, Hn in (armsL, armsR):
        for col, w in (('#1a120c', 50), ('#a97e48', 40)):
            ctx.move_to(*S); ctx.curve_to(E[0], E[1], E[0], E[1], *Hn); src(ctx, col); ctx.set_line_width(w); ctx.stroke()
        cx, cy = lerp(E[0], Hn[0], 0.8), lerp(E[1], Hn[1], 0.8)
        ang = math.atan2(Hn[1] - E[1], Hn[0] - E[0])
        straw(ctx, cx, cy, ang - 1.1, ang + 1.1, 7, 22, 40, S[0], t, 4)
        ctx.arc(Hn[0], Hn[1], 27, 0, 6.3); fill_stroke(ctx, '#33502d', '#0d160b', 4)
        for k in range(3):
            ctx.arc(Hn[0] - 14 + k * 14, Hn[1] + 20, 9, 0, 6.3); fill_stroke(ctx, '#33502d', '#0d160b', 3)
    for sx in (-1, 1):
        ellipse(ctx, sx * 128, -992, 48, 38); fill_stroke(ctx, '#9c7240', '#2b1d10', 5)
        straw(ctx, sx * 128, -965, 0.4, math.pi - 0.4, 6, 18, 34, sx + 9, t, 4)
    # straw collar + neck rope
    straw(ctx, 0, -1040, -math.pi + 0.2, -0.2, 16, 40, 70, 77, t, 6)
    ellipse(ctx, 0, -1040, 64, 16); fill_stroke(ctx, '#cdae6e', '#4a3418', 4)
    # ---- head group
    ctx.save(); ctx.translate(0, -1040); ctx.rotate(tilt); ctx.translate(0, 1040)
    for side in (-1, 1):
        for i in range(18):
            bx, by = side * (60 + i * 3), -1195 + i * 6
            ex = side * (125 + i * 6 + 30 * hrand(i, side))
            ey = -1000 + i * 3 + 45 * hrand(i, 2 * side)
            cxp = (bx + ex) / 2 + side * 25 + 7 * math.sin(t * 3 + i)
            ctx.move_to(bx, by); ctx.curve_to(cxp, (by + ey) / 2, cxp, (by + ey) / 2, ex, ey)
            src(ctx, '#e8c45a' if i % 3 else '#bf9634'); ctx.set_line_width(8); ctx.stroke()
    ellipse(ctx, 0, -1140, 118, 125)
    head = ctx.copy_path(); src(ctx, '#caa16a'); ctx.fill()
    ctx.save(); ctx.append_path(head); ctx.clip(); burlap_texture(ctx, -125, -1270, 125, -1010, 13)
    g = cairo.RadialGradient(-30, -1180, 20, 0, -1140, 140)
    g.add_color_stop_rgba(0, 1, 1, 1, 0.08); g.add_color_stop_rgba(1, 0, 0, 0, 0.28)
    ctx.set_source(g); ctx.paint(); ctx.restore()
    ctx.append_path(head); src(ctx, '#2b1d10'); ctx.set_line_width(6); ctx.stroke()
    for sx in (-1, 1):
        ctx.arc(sx * 72, -1100, 21, 0, 6.3); ctx.set_source_rgba(0.92, 0.5, 0.5, 0.6); ctx.fill()
    # mismatched button eyes
    for (ex, ey, er, col, holes) in ((-48, -1160, 29, '#2f8f8f', 4), (47, -1157, 22, '#b33a3a', 2)):
        ctx.arc(ex, ey, er, 0, 6.3); fill_stroke(ctx, col, '#0d0a08', 5)
        ctx.arc(ex, ey, er * 0.75, 0, 6.3); ctx.set_source_rgba(0, 0, 0, 0.2); ctx.set_line_width(2); ctx.stroke()
        offs = [(-1, -1), (1, -1), (-1, 1), (1, 1)] if holes == 4 else [(-1, 0), (1, 0)]
        for ox, oy in offs:
            ctx.arc(ex + ox * er * 0.3, ey + oy * er * 0.3, er * 0.12, 0, 6.3); src(ctx, '#0d0a08'); ctx.fill()
        if eg > 0:
            glow(ctx, ex, ey, 95 * eg, (1, 0.72, 0.2), 0.75 * eg)
            ctx.arc(ex, ey, 7 * eg, 0, 6.3); ctx.set_source_rgba(1, 0.95, 0.6, eg); ctx.fill()
            d = ctx.user_to_device(ex, ey); r = ctx.user_to_device_distance(95, 0)
            EYE_DEV.append((d[0], d[1], math.hypot(*r)))
    # nose + stitched grin
    ctx.move_to(-12, -1125); ctx.line_to(12, -1125); ctx.line_to(0, -1100); ctx.close_path()
    fill_stroke(ctx, '#d9772b', '#3a1a08', 3)
    if mouth > 0.02:
        mo = 48 * clamp(mouth)
        ctx.move_to(-60, -1075); ctx.curve_to(-30, -1050, 30, -1050, 60, -1075)
        ctx.curve_to(35, -1050 + mo * 1.3, -35, -1050 + mo * 1.3, -60, -1075); ctx.close_path()
        fill_stroke(ctx, '#2a0b07', '#1a0f08', 4)
        ellipse(ctx, 0, -1050 + mo * 0.75, 22 * clamp(mouth) + 4, 9 * clamp(mouth) + 2); src(ctx, '#b8404a'); ctx.fill()
    ctx.move_to(-74, -1085); ctx.curve_to(-35, -1045, 35, -1045, 74, -1085)
    src(ctx, '#1a0f08'); ctx.set_line_width(6); ctx.stroke()
    for i in range(9):
        u = i / 8
        x = (1 - u) ** 3 * -74 + 3 * (1 - u) ** 2 * u * -35 + 3 * (1 - u) * u * u * 35 + u ** 3 * 74
        y = (1 - u) ** 3 * -1085 + 3 * (1 - u) ** 2 * u * -1045 + 3 * (1 - u) * u * u * -1045 + u ** 3 * -1085
        ctx.move_to(x - 4, y - 12); ctx.line_to(x + 4, y + 12); ctx.set_line_width(4); ctx.stroke()
    for i in range(7):
        x = -75 + i * 25
        ctx.move_to(x, -1238); ctx.line_to(x + 8 * math.sin(i * 2.1), -1205 + 8 * hrand(i, 9))
        src(ctx, '#e8c45a'); ctx.set_line_width(6); ctx.stroke()
    # hat
    sw = 8 * math.sin(t * 2.1) + (18 * math.exp(-(t - HIT) * 5) * math.sin((t - HIT) * 20) if t > HIT else 0)
    ellipse(ctx, 0, -1238, 222, 42); fill_stroke(ctx, '#3a2450', '#120a1a', 6)
    ctx.move_to(-112, -1250); ctx.curve_to(-95, -1360, -95, -1360, -35 + sw * 0.3, -1440)
    ctx.curve_to(30 + sw * 0.6, -1500, 30 + sw * 0.6, -1500, 112 + sw, -1430)
    ctx.curve_to(60 + sw * 0.7, -1440, 60 + sw * 0.7, -1440, 25 + sw * 0.4, -1405)
    ctx.curve_to(75, -1330, 75, -1330, 112, -1250); ctx.close_path()
    cone = ctx.copy_path(); src(ctx, '#3a2450'); ctx.fill()
    ctx.save(); ctx.append_path(cone); ctx.clip()
    ctx.rectangle(-140, -1296, 280, 40); src(ctx, '#e07b2a'); ctx.fill()
    g = cairo.LinearGradient(-110, 0, 110, 0); g.add_color_stop_rgba(0, 1, 1, 1, 0.1); g.add_color_stop_rgba(1, 0, 0, 0, 0.35)
    ctx.set_source(g); ctx.paint()
    ctx.save(); ctx.translate(-42, -1362); ctx.rotate(0.15)
    ctx.rectangle(-22, -18, 44, 36); fill_stroke(ctx, '#4e8a5b', '#10200f', 3)
    stitches(ctx, [(-18, -14), (18, -14), (18, 14), (-18, 14)]); ctx.restore()
    ctx.restore()
    ctx.append_path(cone); src(ctx, '#120a1a'); ctx.set_line_width(6); ctx.stroke()
    for k in range(10):
        an = k * math.pi / 5 + t * 0.4
        ellipse(ctx, 62 + 18 * math.cos(an), -1276 + 18 * math.sin(an), 12, 6, an); fill_stroke(ctx, '#f2c230', '#5a3a08', 2)
    ctx.arc(62, -1276, 12, 0, 6.3); fill_stroke(ctx, '#5a3a1a', '#22140a', 3)
    ctx.restore()  # head group
    ctx.restore()  # bob
    ctx.restore()

# ---------------------------------------------------------------- frame
def draw_frame(ctx, t):
    EYE_DEV.clear()
    ctx.set_operator(cairo.OPERATOR_SOURCE); ctx.set_source_rgb(0, 0, 0); ctx.paint()
    ctx.set_operator(cairo.OPERATOR_OVER)
    zoom, cx, cy = camera(t); fl = flash(t)
    ctx.save(); ctx.translate(W / 2, H / 2); ctx.scale(zoom, zoom); ctx.translate(-cx, -cy)
    draw_bg(ctx, t, fl)
    draw_fog(ctx, t, False)
    draw_trail(ctx, t)
    fx, fy, s = feet(t)
    p, ll, lr, bob, moving = walk_state(t)
    bob += bob_hit(t)
    a = rake_amt(t)
    crow = crow_state(t)
    crow_front = crow[3] is not None or t >= FLY1
    if not crow_front and False: pass
    draw_char(ctx, t, s, fx, fy, ll, lr, bob, a, eye_glow(t), head_tilt(t), True)
    draw_crow(ctx, crow[0], crow[1], crow[2], crow[3], crow[4], crow[5], t)
    draw_motes(ctx, t)
    draw_fog(ctx, t, True)
    ctx.restore()
    # screen-space: vignette, flash, fades
    g = cairo.RadialGradient(W / 2, H * 0.52, 380, W / 2, H * 0.52, 1250)
    g.add_color_stop_rgba(0, 0, 0, 0, 0); g.add_color_stop_rgba(1, 0, 0, 0, 0.78)
    ctx.set_source(g); ctx.paint()
    if fl > 0:
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source_rgba(0.8, 0.85, 1, fl * 0.55); ctx.paint(); ctx.restore()
    if t < 0.6: ctx.set_source_rgba(0, 0, 0, 1 - ease(t / 0.6)); ctx.paint()
    bk = ease((t - BLACK0) / (BLACK1 - BLACK0))
    if bk > 0:
        ctx.set_source_rgba(0, 0, 0, bk); ctx.paint()
        ef = 1 - ease((t - 14.55) / 0.45)
        for x, y, r in EYE_DEV:
            glow(ctx, x, y, r * 0.8, (1, 0.72, 0.2), 0.8 * bk * ef)
            ctx.arc(x, y, r * 0.08, 0, 6.3); ctx.set_source_rgba(1, 0.95, 0.6, bk * ef); ctx.fill()

# ---------------------------------------------------------------- audio
SR = 44100
def make_audio(path):
    n = int(SR * DUR)
    dry = np.zeros((2, n)); wet = np.zeros((2, n))
    rg = np.random.default_rng(3)
    def tt(d): return np.arange(int(d * SR)) / SR
    def bp(x, lo=None, hi=None):
        N = len(x); X = np.fft.rfft(x); f = np.fft.rfftfreq(N, 1 / SR); m = np.ones_like(f)
        if lo: m *= 1 / (1 + (lo / np.maximum(f, 1e-3)) ** 4)
        if hi: m *= 1 / (1 + (f / hi) ** 4)
        return np.fft.irfft(X * m, N)
    def add(t0, sig, g=1.0, pan=0.0, send=0.0):
        i = int(t0 * SR)
        if i >= n: return
        j = min(n, i + len(sig)); a = (pan + 1) * math.pi / 4
        seg = sig[:j - i] * g
        dry[0, i:j] += seg * math.cos(a); dry[1, i:j] += seg * math.sin(a)
        if send:
            wet[0, i:j] += seg * send * math.cos(a); wet[1, i:j] += seg * send * math.sin(a)
    mf = lambda m: 440 * 2 ** ((m - 69) / 12)
    def stomp(d=0.7):
        t = tt(d); f = 42 + 95 * np.exp(-t * 28)
        s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6.5)
        return s + bp(rg.standard_normal(len(t)), 60, 900) * np.exp(-t * 35) * 0.5
    def bass(freq, d=0.7):
        t = tt(d)
        s = sum(np.sin(2 * np.pi * freq * k * t) / k * np.exp(-t * (2 + k * 1.5)) for k in range(1, 8))
        return s * np.minimum(1, t / 0.005) * np.exp(-t * 2.2)
    def mbox(freq, d=1.8):
        t = tt(d)
        s = (np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * 2 * freq * t) * np.exp(-t * 5)
             + 0.18 * np.sin(2 * np.pi * 3.02 * freq * t) * np.exp(-t * 8) + 0.08 * np.sin(2 * np.pi * 5.4 * freq * t) * np.exp(-t * 14))
        return s * np.minimum(1, t / 0.002) * np.exp(-t * 2.6)
    def tick():
        t = tt(0.09)
        return (bp(rg.standard_normal(len(t)), 1500, 5000) * 0.6 + np.sin(2 * np.pi * 1700 * t)) * np.exp(-t * 90)
    def organ(freq, d=4.0):
        t = tt(d)
        s = sum(np.sin(2 * np.pi * freq * k * t * (1 + 0.0015 * k)) / k ** 1.3 for k in range(1, 9))
        return s * np.minimum(1, t / 0.04) * np.exp(-t * 0.75)
    def caw():
        t = tt(0.27); f = 720 - 260 * (t / 0.27) + 30 * np.sin(2 * np.pi * 28 * t)
        ph = 2 * np.pi * np.cumsum(f) / SR
        s = np.tanh(3.5 * np.sin(ph)) + 0.5 * np.tanh(3 * np.sin(2 * ph))
        s = bp(s, 500, 3200) + 0.3 * bp(rg.standard_normal(len(t)), 800, 3000)
        return s * np.minimum(1, t / 0.02) * np.clip(1 - (t / 0.27) ** 2, 0, 1)

    # drone (bed under the walk + pull-back)
    t = tt(HIT + 0.05)
    dr = (np.sin(2 * np.pi * 73.42 * t) + 0.6 * np.sin(2 * np.pi * 73.9 * t + 1) + 0.45 * np.sin(2 * np.pi * 110 * t)
          + 0.25 * np.sin(2 * np.pi * 146.8 * t))
    env = np.minimum(1, t / 1.5) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.5 * t))
    env *= 1 + 1.6 * np.clip((t - PB0) / (HIT - PB0), 0, 1) ** 2
    env *= np.clip((HIT + 0.05 - t) / 0.05, 0, 1)
    add(0, dr * env, 0.07)
    # footsteps, bass, off-beat ticks
    bassline = [38, 38, 34, 33]
    for k, L in enumerate(LANDS):
        add(L, stomp(), 0.85)
        add(L, bass(mf(bassline[k % 4])), 0.22)
        add(L + 0.33, tick(), 0.16, 0.35, 0.3)
    add(LANDS[-1] + 0.66, stomp(), 0.6)
    # music-box melody (original motif, D minor)
    barA = [74, 69, 77, 69, 76, 69, 73, 69]
    barB = [74, 69, 77, 69, 79, 77, 76, 73]
    barC = [74, 77, 81, 79, 77, 76, 74, None]
    t0 = LANDS[0] + 0.33 * 4
    for j, m in enumerate(barA + barB):
        if m: add(t0 + 0.33 * j, mbox(mf(m)), 0.16, 0.15 * math.sin(j), 0.5)
    add(LANDS[-1], mbox(mf(74), 2.5), 0.16, 0, 0.6); add(LANDS[-1], mbox(mf(69), 2.5), 0.1, 0, 0.6)
    arp = [62, 65, 69, 74, 77, 81, 86, 89, 93]
    for k, m in enumerate(arp):
        tk = PB0 + (HIT - 0.12 - PB0) * (1 - (1 - (k + 0.5) / len(arp)) ** 1.7)
        add(tk, mbox(mf(m), 1.2), 0.13, -0.3 + 0.6 * k / len(arp), 0.6)
    for j, m in enumerate(barC):
        if m: add(11.96 + 0.33 * j, mbox(mf(m)), 0.13, 0.2 * math.sin(j), 0.7)
    add(14.0, mbox(mf(62), 1.2), 0.12, 0, 0.8)
    # rake scrape
    ts = np.arange(0, WALK_END + 0.2, 0.001)
    mv = np.array([1.0 if walk_state(x)[4] else 0.18 for x in ts]); mv[ts < WALK0] = 0
    mv = np.convolve(mv, np.ones(30) / 30, mode='same')
    nlen = int((WALK_END + 0.2) * SR)
    envs = np.interp(np.arange(nlen) / SR, ts, mv)
    grit = np.repeat(0.55 + 0.45 * rg.random(nlen // 180 + 1), 180)[:nlen]
    scrape = bp(rg.standard_normal(nlen), 1800, 6500) * envs * grit
    add(0, scrape, 0.09, -0.45)
    # pull-back riser + heartbeat
    t = tt(HIT - PB0); u = t / (HIT - PB0)
    riser = bp(rg.standard_normal(len(t)), 2000, None) * u ** 2 * 0.35
    riser += np.sin(2 * np.pi * np.cumsum(110 * 4 ** u) / SR) * u * 0.25
    add(PB0, riser, 0.5, 0, 0.3)
    for hb in (8.3, 8.95, 9.5, 9.95, 10.32, 10.62, 10.86, 11.04, 11.17):
        add(hb, stomp(0.4), 0.45)
    t = tt(0.4); add(RAKE0 - 0.05, bp(rg.standard_normal(len(t)), 400, 3000) * np.sin(np.pi * t / 0.4) ** 2, 0.35, -0.5)
    # the reveal hit
    t = tt(3.0); f = 40 + 60 * np.exp(-t * 12)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.6)
    crash = bp(rg.standard_normal(len(t)), 300, 7000) * np.exp(-t * 2.2) * 0.35
    add(HIT, boom, 0.95); add(HIT, crash, 0.5, 0, 0.5)
    for m in (50, 53, 57, 62):
        add(HIT, organ(mf(m)), 0.05, 0, 0.6)
    t = tt(3.6)
    brown = np.cumsum(rg.standard_normal(len(t))); brown = bp(brown, 25, 260); brown /= np.max(np.abs(brown))
    rumble = brown * np.minimum(1, t / 0.15) * np.exp(-t * 1.1) * (0.6 + 0.4 * np.abs(bp(rg.standard_normal(len(t)), None, 6) * 40).clip(0, 1))
    add(HIT + 0.05, rumble, 0.55)
    add(HIT + 0.32, crash[:SR], 0.2, 0.3, 0.4)
    for c in CAWS:
        add(c, caw(), 0.3, 0.35, 0.5)
    # reverb
    ir_t = tt(1.6)
    for ch in range(2):
        ir = bp(rg.standard_normal(len(ir_t)), None, 5000) * np.exp(-ir_t * 3.2); ir /= np.sqrt(np.sum(ir ** 2))
        N = 1 << int(np.ceil(np.log2(n + len(ir))))
        rev = np.fft.irfft(np.fft.rfft(wet[ch], N) * np.fft.rfft(ir, N), N)[:n]
        dry[ch] += rev * 0.55
    tt_all = np.arange(n) / SR
    dry *= np.minimum(1, tt_all / 0.05) * np.clip((DUR - tt_all) / 0.4, 0, 1)
    pk = np.max(np.abs(dry))
    out = np.tanh(1.3 * dry / pk) / np.tanh(1.3) * 0.9
    pcm = (out.T * 32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())

# ---------------------------------------------------------------- main
def main():
    mode = sys.argv[1]
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); ctx = cairo.Context(surf)
    if mode == 'frames':
        for ts in sys.argv[3].split(','):
            draw_frame(ctx, float(ts)); surf.write_to_png(f"{sys.argv[2]}/f_{float(ts):05.2f}.png")
        return
    if mode == 'audio':
        make_audio(sys.argv[2]); return
    out, wav = sys.argv[2], sys.argv[3]
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
           '-i', wav, '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
           '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    nf = int(DUR * FPS)
    for i in range(nf):
        draw_frame(ctx, i / FPS); surf.flush(); p.stdin.write(bytes(surf.get_data()))
        if i % 60 == 0: print(f'frame {i}/{nf}', flush=True)
    p.stdin.close(); p.wait()

if __name__ == '__main__':
    main()
