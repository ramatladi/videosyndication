"""Procedural backdrops. World is 1080 wide x 1920 tall; floor line at FLOOR_Y; drawn over x -500..1580.
draw_scene(ctx, name, t) draws the background; draw_front(ctx, name, t) draws foreground props (desks etc.)."""
import math, random, cairo, sys, os
from cast import hexc, src, ellipse, fs, rrect, shade

FLOOR_Y = 1250
X0, X1, Y0, Y1 = -500, 1580, -300, 2350
SCENES = ['studio', 'kitchen', 'living_room', 'classroom', 'office', 'street_night', 'park_day', 'stadium', 'bedroom', 'barn', 'halloween_porch']

def vgrad(ctx, y0, y1, c0, c1, x0=X0, x1=X1, ya=None, yb=None):
    g = cairo.LinearGradient(0, y0, 0, y1); g.add_color_stop_rgba(0, *hexc(c0)); g.add_color_stop_rgba(1, *hexc(c1))
    ctx.set_source(g); ctx.rectangle(x0, ya if ya is not None else y0, x1 - x0, (yb if yb is not None else y1) - (ya if ya is not None else y0)); ctx.fill()

def glow(ctx, x, y, r, rgb, a):
    g = cairo.RadialGradient(x, y, 0, x, y, r)
    g.add_color_stop_rgba(0, *rgb, a); g.add_color_stop_rgba(1, *rgb, 0)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source(g); ctx.arc(x, y, r, 0, 6.3); ctx.fill(); ctx.restore()

def floor_boards(ctx, c0, c1, line='#00000040'):
    vgrad(ctx, FLOOR_Y, Y1, c0, c1)
    for xb in range(-2600, 3700, 140):
        x1 = 540 + (xb - 540) * 0.12
        ctx.move_to(x1, FLOOR_Y); ctx.line_to(xb, Y1); ctx.set_source_rgba(0, 0, 0, 0.18); ctx.set_line_width(3); ctx.stroke()

def window(ctx, x, y, w, h, sky0, sky1, frame='#ffffff', night=False, t=0, clouds=True):
    rrect(ctx, x - 14, y - 14, w + 28, h + 28, 10); src(ctx, frame); ctx.fill()
    g = cairo.LinearGradient(0, y, 0, y + h); g.add_color_stop_rgba(0, *hexc(sky0)); g.add_color_stop_rgba(1, *hexc(sky1))
    ctx.rectangle(x, y, w, h); ctx.set_source(g); ctx.fill()
    if night:
        ctx.arc(x + w * 0.7, y + h * 0.3, 40, 0, 6.3); src(ctx, '#f7f1d5'); ctx.fill()
    elif clouds:
        for i in range(3):
            cx = x + ((i * 170 + t * 12) % (w + 160)) - 80
            ctx.save(); ctx.rectangle(x, y, w, h); ctx.clip()
            for dx, r in ((0, 34), (34, 44), (72, 30)): ctx.arc(cx + dx, y + 60 + i * 50, r, 0, 6.3)
            src(ctx, '#ffffff', 0.9); ctx.fill(); ctx.restore()
    ctx.rectangle(x + w / 2 - 6, y, 12, h); ctx.rectangle(x, y + h / 2 - 6, w, 12); src(ctx, frame); ctx.fill()

def plant(ctx, x, y, s=1.0):
    for i in range(7):
        a = -math.pi / 2 + (i - 3) * 0.32
        ellipse(ctx, x + math.cos(a) * 70 * s, y - 90 * s + math.sin(a) * 60 * s, 26 * s, 70 * s, a + math.pi / 2); fs(ctx, '#2ecc71' if i % 2 else '#27ae60', lw=4)
    ctx.move_to(x - 55 * s, y - 40 * s); ctx.line_to(x + 55 * s, y - 40 * s); ctx.line_to(x + 40 * s, y + 60 * s); ctx.line_to(x - 40 * s, y + 60 * s); ctx.close_path(); fs(ctx, '#d35400', lw=5)

def draw_scene(ctx, name, t):
    rng = random.Random(name)
    if name == 'studio':
        vgrad(ctx, Y0, FLOOR_Y, '#0f1c3d', '#1d2f5f')
        for i in range(12):
            x = -400 + i * 170; ctx.rectangle(x, Y0, 10, FLOOR_Y - Y0); ctx.set_source_rgba(1, 1, 1, 0.03); ctx.fill()
        rrect(ctx, 220, 260, 640, 240, 40); ctx.set_source_rgba(1, 0.3, 0.6, 0.12); ctx.fill()
        rrect(ctx, 220, 260, 640, 240, 40); src(ctx, '#ff4fa3'); ctx.set_line_width(10); ctx.stroke()
        ctx.arc(330, 380, 60, 0, 6.3); src(ctx, '#ff4fa3'); ctx.set_line_width(10); ctx.stroke()
        for k in range(4): rrect(ctx, 430 + k * 100, 340 + (k % 2) * 30, 70, 90 - (k % 2) * 30, 10); src(ctx, '#4fd1ff'); ctx.fill()
        glow(ctx, 540, 380, 520, (1, 0.3, 0.6), 0.18)
        for x in (60, 1020):
            ctx.rectangle(x - 70, 600, 140, 600); src(ctx, '#162a52'); ctx.fill()
            for y in range(640, 1180, 110):
                for k in range(3): rrect(ctx, x - 55 + k * 38, y, 30, 80, 4); src(ctx, ['#f39c12', '#e74c3c', '#9b59b6', '#1abc9c'][(y // 110 + k) % 4]); ctx.fill()
        floor_boards(ctx, '#2c2238', '#120d18')
    elif name == 'kitchen':
        vgrad(ctx, Y0, FLOOR_Y, '#fdf2e9', '#f6e1cf')
        for y in range(700, 1000, 60):
            for x in range(-500, 1600, 60): ctx.rectangle(x + 2, y + 2, 56, 56); src(ctx, '#ffffff'); ctx.fill()
        window(ctx, 360, 230, 360, 300, '#7ec8f2', '#d6f0ff', t=t)
        for x in (-500, 760):
            ctx.rectangle(x, 160, 820 if x < 0 else 820, 300); ctx.set_source_rgba(0, 0, 0, 0)
        for x0, x1 in ((-500, 300), (780, 1580)):
            for x in range(x0, x1, 160): rrect(ctx, x + 8, 140, 144, 300, 14); fs(ctx, '#7fb3a6', lw=5)
        rrect(ctx, -500, 1000, 2080, 40, 6); src(ctx, '#ecf0f1'); ctx.fill()
        for x in range(-500, 1580, 200): rrect(ctx, x + 10, 1040, 180, 210, 12); fs(ctx, '#5d9c8c', lw=5); ctx.arc(x + 100, 1080, 8, 0, 6.3); src(ctx, '#ecf0f1'); ctx.fill()
        rrect(ctx, 1150, 380, 260, 870, 30); fs(ctx, '#dfe6e9', lw=6); ctx.move_to(1150, 700); ctx.line_to(1410, 700); src(ctx, '#7f8c8d'); ctx.set_line_width(5); ctx.stroke()
        for k, c in enumerate(('#e74c3c', '#f1c40f', '#2ecc71')): ctx.arc(150 + k * 70, 960, 30, 0, 6.3); fs(ctx, c, lw=4)
        vgrad(ctx, FLOOR_Y, Y1, '#c8a27a', '#8e6b4a')
        for y in range(FLOOR_Y, Y1, 100):
            for x in range(-500 + (y // 100 % 2) * 50, 1600, 100): ctx.rectangle(x, y, 50, 50); ctx.set_source_rgba(1, 1, 1, 0.08); ctx.fill()
    elif name == 'living_room':
        vgrad(ctx, Y0, FLOOR_Y, '#d9c3a5', '#c4a982')
        for x in range(-500, 1600, 90): ctx.rectangle(x, Y0, 40, FLOOR_Y - Y0); ctx.set_source_rgba(1, 1, 1, 0.07); ctx.fill()
        window(ctx, 120, 260, 300, 380, '#5d6d7e', '#a9cce3', frame='#f5f5f5', t=t)
        rrect(ctx, 600, 330, 380, 240, 16); fs(ctx, '#2d3436'); rrect(ctx, 620, 350, 340, 200, 8); src(ctx, '#74b9ff'); ctx.fill()
        glow(ctx, 790, 450, 300, (0.4, 0.7, 1), 0.12)
        rrect(ctx, -300, 820, 1700, 260, 80); fs(ctx, '#6c5ce7', lw=7)
        rrect(ctx, -320, 950, 1740, 300, 60); fs(ctx, '#5a4bd1', lw=7)
        for x in (100, 380, 660, 940): rrect(ctx, x, 860, 220, 150, 50); fs(ctx, '#a29bfe', lw=5)
        ctx.move_to(-200, 600); ctx.line_to(-120, 300); ctx.line_to(-40, 600); src(ctx, '#ffeaa7'); ctx.fill(); glow(ctx, -120, 500, 300, (1, 0.9, 0.5), 0.2)
        floor_boards(ctx, '#a1724a', '#6e4b2e')
        ellipse(ctx, 540, 1500, 700, 140); src(ctx, '#e17055', 0.5); ctx.fill()
    elif name == 'classroom':
        vgrad(ctx, Y0, FLOOR_Y, '#f3e6c8', '#e8d4a8')
        rrect(ctx, 120, 220, 840, 460, 14); fs(ctx, '#2d5a3d', '#8b5a2b', 22)
        ctx.select_font_face('DejaVu Sans', cairo.FONT_SLANT_ITALIC, cairo.FONT_WEIGHT_NORMAL); ctx.set_font_size(60)
        for i, txt in enumerate(('2 + 2 = ?', 'a b c', 'quiz today!')): ctx.move_to(190, 330 + i * 110); ctx.set_source_rgba(1, 1, 1, 0.75); ctx.show_text(txt)
        ctx.arc(1150, 300, 90, 0, 6.3); fs(ctx, '#ffffff', lw=10)
        ctx.move_to(1150, 300); ctx.line_to(1150 + 50 * math.sin(t), 300 - 50 * math.cos(t)); src(ctx, '#000000'); ctx.set_line_width(8); ctx.stroke()
        for x in (-260, 1330): window(ctx, x - 130, 260, 260, 360, '#81d4fa', '#e1f5fe', t=t)
        floor_boards(ctx, '#b0a18a', '#7f7260')
        for x in (-150, 1230):
            rrect(ctx, x - 140, 1050, 280, 40, 8); fs(ctx, '#d6a35c', lw=5)
            for s in (-1, 1): ctx.rectangle(x + s * 110 - 8, 1090, 16, 160); src(ctx, '#7f8c8d'); ctx.fill()
    elif name == 'office':
        vgrad(ctx, Y0, FLOOR_Y, '#dfe9f3', '#c9d6e3')
        for x in range(-400, 1500, 520):
            window(ctx, x, 180, 400, 520, '#a7c7e7', '#e8f1fb', frame='#95a5a6', t=t)
            for y in range(180, 700, 26): ctx.rectangle(x, y, 400, 10); src(ctx, '#ecf0f1', 0.85); ctx.fill()
        rrect(ctx, -500, 900, 2080, 350, 0); src(ctx, '#7f8c8d'); ctx.fill()
        for x in range(-480, 1580, 360): rrect(ctx, x, 880, 340, 370, 12); fs(ctx, '#95a5a6', lw=5)
        for x in (60, 1000): rrect(ctx, x - 90, 770, 180, 120, 10); fs(ctx, '#2d3436'); rrect(ctx, x - 80, 780, 160, 100, 6); src(ctx, '#55efc4'); ctx.fill()
        plant(ctx, 540, 1150, 0.9)
        floor_boards(ctx, '#6c7a89', '#3d4855')
    elif name == 'street_night':
        vgrad(ctx, Y0, FLOOR_Y, '#0b1026', '#2b2d5c')
        for i in range(40): ctx.arc(rng.uniform(-400, 1500), rng.uniform(-250, 500), rng.uniform(1, 3), 0, 6.3); ctx.set_source_rgba(1, 1, 0.9, 0.4 + 0.4 * math.sin(t * 2 + i)); ctx.fill()
        ctx.arc(860, 220, 90, 0, 6.3); src(ctx, '#f7f1d5'); ctx.fill(); glow(ctx, 860, 220, 300, (0.8, 0.85, 1), 0.25)
        x = -500
        while x < 1580:
            w = rng.uniform(220, 360); h = rng.uniform(500, 1000)
            ctx.rectangle(x, FLOOR_Y - h, w - 10, h); src(ctx, rng.choice(['#1e2a4a', '#24305a', '#1a2340'])); ctx.fill()
            for yy in range(int(FLOOR_Y - h + 40), FLOOR_Y - 60, 90):
                for xx in range(int(x + 25), int(x + w - 50), 70):
                    on = rng.random() > 0.45
                    ctx.rectangle(xx, yy, 40, 55); ctx.set_source_rgba(1, 0.85, 0.45, 0.85) if on else src(ctx, '#11182e'); ctx.fill()
            x += w
        vgrad(ctx, FLOOR_Y, Y1, '#3b3b4f', '#1c1c28')
        ctx.rectangle(X0, FLOOR_Y, X1 - X0, 40); src(ctx, '#6c6c80'); ctx.fill()
        for lx in (-80, 1160):
            ctx.rectangle(lx - 10, 500, 20, FLOOR_Y - 500); src(ctx, '#2d3436'); ctx.fill()
            ellipse(ctx, lx, 500, 50, 24); src(ctx, '#ffeaa7'); ctx.fill(); glow(ctx, lx, 520, 420, (1, 0.85, 0.5), 0.3)
    elif name == 'park_day':
        vgrad(ctx, Y0, FLOOR_Y, '#74b9ff', '#dff3ff')
        ctx.arc(900, 120, 110, 0, 6.3); src(ctx, '#ffe066'); ctx.fill(); glow(ctx, 900, 120, 380, (1, 0.95, 0.6), 0.35)
        for i in range(3):
            cx = ((i * 520 + t * 18) % 2200) - 500
            for dx, r in ((0, 60), (60, 80), (140, 55)): ctx.arc(cx + dx, 200 + i * 90, r, 0, 6.3)
            src(ctx, '#ffffff', 0.95); ctx.fill()
        ctx.move_to(X0, 1000); ctx.curve_to(0, 860, 500, 980, 900, 900); ctx.curve_to(1200, 860, 1400, 940, X1, 920); ctx.line_to(X1, FLOOR_Y); ctx.line_to(X0, FLOOR_Y); ctx.close_path(); src(ctx, '#7bc96f'); ctx.fill()
        for tx in (-180, 1200, 980):
            ctx.rectangle(tx - 26, 820, 52, 400); src(ctx, '#7a5230'); ctx.fill()
            for dx, dy, r in ((0, 700, 180), (-110, 780, 130), (110, 780, 130), (0, 600, 120)): ctx.arc(tx + dx, dy, r, 0, 6.3); fs(ctx, '#3fa34d', lw=5)
        rrect(ctx, 160, 1060, 300, 30, 8); fs(ctx, '#a0522d', lw=4); rrect(ctx, 160, 1000, 300, 26, 8); fs(ctx, '#a0522d', lw=4)
        vgrad(ctx, FLOOR_Y, Y1, '#6ab04c', '#3d7a2a')
        for i in range(160):
            x = rng.uniform(X0, X1); y = rng.uniform(FLOOR_Y, Y1)
            ctx.move_to(x, y); ctx.line_to(x + 6, y - 22); ctx.set_source_rgba(0.2, 0.45, 0.15, 0.6); ctx.set_line_width(4); ctx.stroke()
    elif name == 'stadium':
        vgrad(ctx, Y0, 400, '#0c1445', '#26306b')
        for lx in (-200, 1280):
            for k in range(3): ctx.arc(lx + (k - 1) * 50, 60, 22, 0, 6.3); src(ctx, '#fffde7'); ctx.fill()
            glow(ctx, lx, 60, 420, (1, 1, 0.85), 0.35)
        for row in range(10):
            y = 300 + row * 75
            ctx.rectangle(X0, y, X1 - X0, 75); src(ctx, '#2c3e50' if row % 2 else '#34495e'); ctx.fill()
            for x in range(-480 + (row % 2) * 30, 1580, 60):
                ctx.arc(x, y + 30, 18, 0, 6.3); src(ctx, rng.choice(['#e74c3c', '#3498db', '#f1c40f', '#ecf0f1', '#2ecc71'])); ctx.fill()
        rrect(ctx, 290, 120, 500, 150, 14); fs(ctx, '#111111', '#7f8c8d', 10)
        ctx.select_font_face('DejaVu Sans Mono', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); ctx.set_font_size(90)
        ctx.move_to(350, 230); src(ctx, '#f39c12'); ctx.show_text('HOME 21')
        ctx.rectangle(X0, 1050, X1 - X0, 200); src(ctx, '#1e3d2f'); ctx.fill()
        vgrad(ctx, FLOOR_Y, Y1, '#2e8b3a', '#1d5e26')
        for y in range(FLOOR_Y + 120, Y1, 260): ctx.rectangle(X0, y, X1 - X0, 12); src(ctx, '#ffffff', 0.8); ctx.fill()
    elif name == 'bedroom':
        vgrad(ctx, Y0, FLOOR_Y, '#c8b6e2', '#b39ddb')
        window(ctx, 640, 240, 340, 340, '#1a237e', '#5c6bc0', frame='#f3e5f5', night=True, t=t)
        for k, (x, c) in enumerate(((120, '#ff7675'), (330, '#74b9ff'))): rrect(ctx, x, 280, 160, 220, 8); fs(ctx, c, lw=5)
        for i in range(14):
            x = -400 + i * 140; ctx.arc(x, 150 + 30 * math.sin(i), 10, 0, 6.3); src(ctx, '#fff59d'); ctx.fill(); glow(ctx, x, 150 + 30 * math.sin(i), 60, (1, 0.95, 0.5), 0.25)
        rrect(ctx, -460, 880, 760, 370, 40); fs(ctx, '#fd79a8', lw=7); rrect(ctx, -440, 820, 260, 120, 40); fs(ctx, '#ffffff', lw=6)
        floor_boards(ctx, '#a1887f', '#6d4c41')
    elif name == 'halloween_porch':
        vgrad(ctx, Y0, FLOOR_Y, '#1b1035', '#3c2a63')
        ctx.arc(250, 200, 100, 0, 6.3); src(ctx, '#f7e7b4'); ctx.fill(); glow(ctx, 250, 200, 360, (1, 0.9, 0.6), 0.3)
        rrect(ctx, 420, 300, 1300, 950, 0); src(ctx, '#3b2f2f'); ctx.fill()
        for y in range(300, 1250, 50): ctx.move_to(420, y); ctx.line_to(1580, y); ctx.set_source_rgba(0, 0, 0, 0.3); ctx.set_line_width(3); ctx.stroke()
        rrect(ctx, 700, 560, 280, 690, 10); fs(ctx, '#5b3a29', lw=8); ctx.arc(940, 920, 14, 0, 6.3); src(ctx, '#f1c40f'); ctx.fill()
        window(ctx, 1060, 520, 260, 260, '#f39c12', '#e67e22', frame='#2d2020', night=False, t=0, clouds=False)
        glow(ctx, 1190, 650, 300, (1, 0.6, 0.2), 0.3)
        for k, x in enumerate((-300, -120, 1280)):
            r = 70 - k * 10; y = FLOOR_Y - r
            ellipse(ctx, x, y, r * 1.2, r); fs(ctx, '#e67e22', lw=6)
            for s in (-1, 1): ctx.move_to(x + s * r * 0.4, y - r * 0.3); ctx.line_to(x + s * r * 0.15, y); ctx.line_to(x + s * r * 0.6, y); ctx.close_path(); src(ctx, '#ffd166'); ctx.fill()
            glow(ctx, x, y, r * 3, (1, 0.6, 0.15), 0.25)
        floor_boards(ctx, '#5d4037', '#2e1f1a')
    elif name == 'barn':
        here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(here))
        import render as R
        R.draw_bg(ctx, t, 0.0)
    else:
        vgrad(ctx, Y0, FLOOR_Y, '#dfe6e9', '#b2bec3'); floor_boards(ctx, '#95a5a6', '#636e72')

def draw_front(ctx, name, t, desk=False):
    if desk:
        col = {'studio': '#1b1b2f', 'office': '#8d6e63', 'kitchen': '#ecf0f1', 'classroom': '#d6a35c'}.get(name, '#5d4037')
        rrect(ctx, -500, 1420, 2080, 80, 20); fs(ctx, shade(col, 1.3), lw=8)
        ctx.rectangle(-500, 1490, 2080, 900); src(ctx, col); ctx.fill()
        if name == 'studio':
            for x in (200, 540, 880):
                ctx.move_to(x, 1420); ctx.line_to(x, 1300); src(ctx, '#2d3436'); ctx.set_line_width(14); ctx.stroke()
                rrect(ctx, x - 32, 1210, 64, 110, 30); fs(ctx, '#636e72', lw=6)
            ctx.rectangle(-500, 1600, 2080, 14); src(ctx, '#ff4fa3', 0.8); ctx.fill()
