"""Parametric cartoon characters: people, animals, mascots and talking objects.
Every character is described by a small JSON spec (see WRITING_GUIDE.md) and drawn with pycairo.
Local coordinates: feet at (0, 0), y grows downward, full height about 1050 units at scale 1."""
import math, cairo

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def lerp(a, b, u): return a + (b - a) * u
def hexc(h, a=1.0):
    h = h.lstrip('#')
    if len(h) == 3: h = ''.join(c * 2 for c in h)
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)
def shade(h, k):
    r, g, b, _ = hexc(h); f = lambda c: max(0, min(255, int(c * 255 * k)))
    return '#%02x%02x%02x' % (f(r), f(g), f(b))
def src(ctx, h, a=1.0): ctx.set_source_rgba(*hexc(h, a))
def ellipse(ctx, cx, cy, rx, ry, rot=0.0):
    ctx.save(); ctx.translate(cx, cy); ctx.rotate(rot); ctx.scale(max(rx, 0.01), max(ry, 0.01)); ctx.arc(0, 0, 1, 0, 2 * math.pi); ctx.restore()
def fs(ctx, fill, stroke='#1b1418', lw=7, a=1.0):
    src(ctx, fill, a); ctx.fill_preserve(); src(ctx, stroke); ctx.set_line_width(lw); ctx.stroke()
def rrect(ctx, x, y, w, h, r):
    r = min(r, w / 2, h / 2); ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0); ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi); ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi); ctx.close_path()

OUT = '#1b1418'
SKIN_DEFAULT = '#f1c27d'

# ---------------------------------------------------------------- gestures
# per side: (shoulder angle out from straight-down, elbow bend) in radians
GESTURES = {
    'rest':     lambda s, t: (0.22, 0.12),
    'talk':     lambda s, t: (0.55 + 0.18 * math.sin(t * 5 + s), 0.9 + 0.25 * math.sin(t * 7)) if s > 0 else (0.25, 0.15),
    'wave':     lambda s, t: (2.45, 0.35 + 0.45 * math.sin(t * 11)) if s > 0 else (0.22, 0.12),
    'point':    lambda s, t: (1.5, 0.05) if s > 0 else (0.22, 0.12),
    'shrug':    lambda s, t: (0.85, 1.75),
    'arms_up':  lambda s, t: (2.75 + 0.08 * math.sin(t * 9 + s), 0.15),
    'cross':    lambda s, t: (-0.15, -1.45),
    'hips':     lambda s, t: (0.75, -1.65),
    'facepalm': lambda s, t: (0.35, -2.75) if s > 0 else (0.22, 0.12),
    'think':    lambda s, t: (0.3, -2.45) if s > 0 else (-0.1, -1.35),
}

class Character:
    def __init__(self, spec):
        self.s = spec
        self.kind = spec.get('kind', 'human')
        self.color = spec.get('color', SKIN_DEFAULT)
        self.arm = {-1: [0.22, 0.12], 1: [0.22, 0.12]}
        self.blink_seed = (sum(map(ord, spec.get('id', 'x'))) % 97) / 9.7
        sh = spec.get('shape', 'gumdrop')
        # geometry anchors
        if self.kind in ('human', 'animal'):
            self.head = (0, -800, 200)          # cx, cy, r
            self.shoulder_y, self.arm_len = -520, (150, 140)
            self.face_y = -800
        else:
            top, w = {'gumdrop': (-930, 400), 'box': (-880, 430), 'cup': (-900, 400), 'phone': (-1000, 380),
                      'ghost': (-980, 420), 'pumpkin': (-860, 470), 'egg': (-960, 380), 'ball': (-880, 440),
                      'toast': (-930, 430), 'football': (-820, 470)}.get(sh, (-930, 400))
            self.top, self.width = top, w
            self.head = (0, top + 330, w / 2)
            self.face_y = top + 330
            self.shoulder_y, self.arm_len = top + 520, (110, 100)

    # -------------------------------------------------------- public
    def head_world(self):
        return self.head[0], self.head[1] - 40

    def draw(self, ctx, st):
        """st: t, talk (0-1), gesture, look (-1..1), bob, jump (px), scale"""
        t = st['t']; talk = st.get('talk', 0.0)
        g = GESTURES.get(st.get('gesture') or ('talk' if talk > 0.15 else 'rest'), GESTURES['rest'])
        dom = -1 if st.get('look', 0.0) < -0.1 else 1
        for s in (-1, 1):
            tgt = g(s * dom, t)
            self.arm[s][0] += (tgt[0] - self.arm[s][0]) * 0.25
            self.arm[s][1] += (tgt[1] - self.arm[s][1]) * 0.25
        ctx.save()
        ellipse(ctx, 0, 6, 190 if self.kind in ('human', 'animal') else self.width * 0.55, 34); ctx.set_source_rgba(0, 0, 0, 0.35); ctx.fill()
        ctx.translate(0, -st.get('jump', 0.0))
        ctx.set_line_join(cairo.LINE_JOIN_ROUND); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        bob = st.get('bob', 0.0)
        if self.kind in ('human', 'animal'):
            self._legs(ctx, t)
            ctx.translate(0, bob)
            self._torso(ctx)
            self._hair(ctx, back=True)
            self._head(ctx, t, talk, st)
            self._hair(ctx, back=False)
            self._accessories(ctx)
            self._arms(ctx, t)
        else:
            if self.s.get('shape') != 'ghost': self._stubby_legs(ctx)
            ctx.translate(0, bob + (math.sin(t * 2.2) * 18 if self.s.get('shape') == 'ghost' else 0))
            self._arms(ctx, t, behind=True)
            self._mascot_body(ctx)
            self._face(ctx, t, talk, st)
            self._accessories(ctx)
            self._arms(ctx, t)
        ctx.restore()

    # -------------------------------------------------------- body parts
    def _legs(self, ctx, t):
        bottom = self.s.get('bottom', '#3b4a6b'); shoes = self.s.get('shoes', '#2a2a2a')
        fur = self.color if self.kind == 'animal' and not self.s.get('bottom') else None
        for s in (-1, 1):
            rrect(ctx, s * 48 - 26, -280, 52, 255, 24); fs(ctx, fur or bottom)
            ellipse(ctx, s * 52, -22, 50, 26); fs(ctx, shoes)
            ellipse(ctx, s * 52 - 14, -30, 16, 7); ctx.set_source_rgba(1, 1, 1, 0.18); ctx.fill()

    def _stubby_legs(self, ctx):
        c = self.s.get('shoes', shade(self.color, 0.6))
        for s in (-1, 1):
            ctx.move_to(s * 60, -120); ctx.line_to(s * 66, -30); src(ctx, OUT); ctx.set_line_width(26); ctx.stroke()
            ctx.move_to(s * 60, -120); ctx.line_to(s * 66, -30); src(ctx, shade(self.color, 0.75)); ctx.set_line_width(16); ctx.stroke()
            ellipse(ctx, s * 74, -20, 42, 22); fs(ctx, c)

    def _torso(self, ctx):
        top = self.s.get('top', {}) or {}
        col = top.get('color', self.color if self.kind == 'animal' else '#d9534f')
        ctx.move_to(-112, -560); ctx.curve_to(-130, -450, -112, -330, -104, -240)
        ctx.line_to(104, -240); ctx.curve_to(112, -330, 130, -450, 112, -560)
        ctx.curve_to(60, -590, -60, -590, -112, -560); ctx.close_path()
        path = ctx.copy_path(); src(ctx, col); ctx.fill()
        ctx.save(); ctx.append_path(path); ctx.clip()
        pat = top.get('pattern', 'plain'); pc = top.get('pattern_color', '#ffffff')
        if pat == 'stripes':
            for y in range(-590, -230, 48): ctx.rectangle(-140, y, 280, 22); src(ctx, pc, 0.85); ctx.fill()
        elif pat == 'dots':
            for i, y in enumerate(range(-560, -240, 52)):
                for x in range(-120 + (i % 2) * 26, 130, 52): ctx.arc(x, y, 9, 0, 6.3); src(ctx, pc, 0.85); ctx.fill()
        elif pat == 'jersey':
            ctx.rectangle(-140, -590, 280, 40); src(ctx, pc); ctx.fill()
            for s in (-1, 1): ctx.rectangle(s * 112 - 12, -560, 24, 320); src(ctx, pc, 0.9); ctx.fill()
            num = str(top.get('number', ''))[:2]
            if num:
                ctx.select_font_face('DejaVu Sans', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); ctx.set_font_size(120)
                e = ctx.text_extents(num); ctx.move_to(-e.x_advance / 2, -335); ctx.text_path(num)
                src(ctx, pc); ctx.fill_preserve(); src(ctx, OUT); ctx.set_line_width(4); ctx.stroke()
        elif pat == 'hoodie':
            ctx.move_to(-60, -560); ctx.curve_to(-50, -500, 50, -500, 60, -560); src(ctx, shade(col, 0.75)); ctx.set_line_width(14); ctx.stroke()
            rrect(ctx, -70, -360, 140, 70, 20); src(ctx, shade(col, 0.85)); ctx.fill()
        elif pat == 'suit':
            ctx.move_to(-40, -575); ctx.line_to(0, -470); ctx.line_to(40, -575); ctx.close_path(); src(ctx, '#ffffff'); ctx.fill()
            ctx.move_to(-8, -520); ctx.line_to(8, -520); ctx.line_to(14, -400); ctx.line_to(0, -380); ctx.line_to(-14, -400); ctx.close_path()
            src(ctx, top.get('pattern_color', '#c0392b')); ctx.fill()
        elif pat == 'apron':
            rrect(ctx, -80, -500, 160, 280, 20); src(ctx, pc); ctx.fill()
        if self.kind == 'animal' and not self.s.get('top'):
            ellipse(ctx, 0, -380, 70, 120); src(ctx, self.s.get('belly', shade(self.color, 1.25))); ctx.fill()
        g = cairo.LinearGradient(-130, 0, 130, 0)
        g.add_color_stop_rgba(0, 0, 0, 0, 0.18); g.add_color_stop_rgba(0.5, 1, 1, 1, 0.06); g.add_color_stop_rgba(1, 0, 0, 0, 0.22)
        ctx.set_source(g); ctx.paint()
        ctx.restore()
        ctx.append_path(path); src(ctx, OUT); ctx.set_line_width(7); ctx.stroke()
        skin = self.color
        rrect(ctx, -34, -610, 68, 60, 20); fs(ctx, skin)

    def _mascot_body(self, ctx):
        sh = self.s.get('shape', 'gumdrop'); c = self.color; top, w = self.top, self.width; hw = w / 2
        if sh == 'gumdrop':
            ctx.move_to(-hw, -90); ctx.curve_to(-hw, top + 120, -hw * 0.7, top, 0, top); ctx.curve_to(hw * 0.7, top, hw, top + 120, hw, -90)
            ctx.curve_to(hw * 0.6, -60, -hw * 0.6, -60, -hw, -90); ctx.close_path(); fs(ctx, c, lw=8)
        elif sh == 'box':
            rrect(ctx, -hw, top, w, -90 - top, 50); fs(ctx, c, lw=8)
            ctx.move_to(-hw + 30, top + 110); ctx.line_to(hw - 30, top + 110); src(ctx, shade(c, 0.8)); ctx.set_line_width(10); ctx.stroke()
        elif sh == 'cup':
            ctx.move_to(-hw, top + 90); ctx.line_to(hw, top + 90); ctx.line_to(hw * 0.78, -90); ctx.line_to(-hw * 0.78, -90); ctx.close_path(); fs(ctx, c, lw=8)
            rrect(ctx, -hw - 20, top + 30, w + 40, 70, 30); fs(ctx, self.s.get('lid', '#f4f1ea'), lw=8)
            ctx.move_to(-hw * 0.9, top + 330); ctx.line_to(hw * 0.9, top + 330); ctx.line_to(hw * 0.86, top + 470); ctx.line_to(-hw * 0.86, top + 470); ctx.close_path()
            fs(ctx, self.s.get('sleeve', '#b07a4a'), lw=6)
        elif sh == 'phone':
            rrect(ctx, -hw, top, w, -90 - top, 60); fs(ctx, self.s.get('case', '#222831'), lw=8)
            rrect(ctx, -hw + 26, top + 60, w - 52, -90 - top - 120, 30); src(ctx, c); ctx.fill()
            rrect(ctx, -50, top + 22, 100, 20, 10); src(ctx, '#000000'); ctx.fill()
        elif sh == 'ghost':
            ctx.move_to(-hw, -80); ctx.curve_to(-hw, top + 120, -hw * 0.6, top, 0, top); ctx.curve_to(hw * 0.6, top, hw, top + 120, hw, -80)
            for i in range(6, -1, -1):
                x = -hw + w * i / 6; ctx.line_to(x, -80 + (40 if i % 2 else 0))
            ctx.close_path(); fs(ctx, c, lw=8)
        elif sh == 'pumpkin':
            for i, dx in enumerate((-0.62, 0.62, -0.3, 0.3, 0)):
                ellipse(ctx, dx * hw, (top - 90) / 2, hw * 0.55, (-90 - top) / 2); fs(ctx, shade(c, 0.9) if i < 4 else c, lw=7)
            ctx.move_to(0, top + 10); ctx.curve_to(0, top - 30, 20, top - 50, 40, top - 60); src(ctx, '#3d5a22'); ctx.set_line_width(22); ctx.stroke()
        elif sh in ('egg', 'ball'):
            ellipse(ctx, 0, (top - 90) / 2, hw, (-90 - top) / 2); fs(ctx, c, lw=8)
            if sh == 'ball':
                cy, ry = (top - 90) / 2, (-90 - top) / 2
                ctx.move_to(-hw, cy); ctx.curve_to(-hw / 2, cy - 60, hw / 2, cy - 60, hw, cy); src(ctx, shade(c, 0.6)); ctx.set_line_width(8); ctx.stroke()
        elif sh == 'football':
            cy, ry = (top - 90) / 2, (-90 - top) / 2
            ctx.move_to(-hw, cy); ctx.curve_to(-hw * 0.6, top - 20, hw * 0.6, top - 20, hw, cy); ctx.curve_to(hw * 0.6, -60, -hw * 0.6, -60, -hw, cy); ctx.close_path()
            fs(ctx, c, lw=8)
            ctx.move_to(-110, top + 90); ctx.line_to(110, top + 90); src(ctx, '#ffffff'); ctx.set_line_width(10); ctx.stroke()
            for k in range(-4, 5): ctx.move_to(k * 25, top + 70); ctx.line_to(k * 25, top + 110); ctx.stroke()
        elif sh == 'toast':
            ctx.move_to(-hw + 20, -90); ctx.line_to(-hw + 20, top + 180); ctx.curve_to(-hw - 60, top + 60, -hw * 0.6, top - 20, 0, top)
            ctx.curve_to(hw * 0.6, top - 20, hw + 60, top + 60, hw - 20, top + 180); ctx.line_to(hw - 20, -90); ctx.close_path()
            fs(ctx, self.s.get('crust', '#a0632b'), lw=8)
            ctx.move_to(-hw + 50, -120); ctx.line_to(-hw + 50, top + 190); ctx.curve_to(-hw - 10, top + 90, -hw * 0.5, top + 30, 0, top + 30)
            ctx.curve_to(hw * 0.5, top + 30, hw + 10, top + 90, hw - 50, top + 190); ctx.line_to(hw - 50, -120); ctx.close_path(); src(ctx, c); ctx.fill()
        # soft shading
        ctx.save(); g = cairo.LinearGradient(-hw, 0, hw, 0)
        g.add_color_stop_rgba(0, 1, 1, 1, 0.0); g.add_color_stop_rgba(1, 0, 0, 0, 0.0); ctx.restore()
        ellipse(ctx, -hw * 0.45, top + 140, hw * 0.18, 40, -0.5); ctx.set_source_rgba(1, 1, 1, 0.22); ctx.fill()

    def _head(self, ctx, t, talk, st):
        cx, cy, r = self.head; skin = self.color
        if self.kind == 'animal': self._ears(ctx, back=True)
        ctx.arc(cx, cy, r, 0, 2 * math.pi); fs(ctx, skin, lw=8)
        g = cairo.RadialGradient(cx - 60, cy - 80, 20, cx, cy, r)
        g.add_color_stop_rgba(0, 1, 1, 1, 0.12); g.add_color_stop_rgba(1, 0, 0, 0, 0.18)
        ctx.arc(cx, cy, r - 4, 0, 6.3); ctx.set_source(g); ctx.fill()
        if self.kind == 'human':
            for s in (-1, 1): ellipse(ctx, s * (r - 8), cy + 20, 26, 40); fs(ctx, skin, lw=6)
            ctx.arc(cx, cy, r - 4, 0, 6.3); src(ctx, skin); ctx.fill()
        if self.kind == 'animal': self._ears(ctx, back=False)
        self._face(ctx, t, talk, st)

    def _ears(self, ctx, back):
        e = self.s.get('ears', 'bear'); c = self.color; inner = self.s.get('inner', '#f5b7b1'); cx, cy, r = self.head
        for s in (-1, 1):
            if e == 'cat' or e == 'fox':
                big = 1.25 if e == 'fox' else 1.0
                if not back: continue
                ctx.move_to(s * 60, cy - r + 20); ctx.line_to(s * (150 * big), cy - r - 90 * big); ctx.line_to(s * 175, cy - r + 70); ctx.close_path(); fs(ctx, c, lw=7)
                ctx.move_to(s * 90, cy - r + 30); ctx.line_to(s * (145 * big), cy - r - 50 * big); ctx.line_to(s * 155, cy - r + 60); ctx.close_path(); src(ctx, inner); ctx.fill()
            elif e in ('bear', 'mouse'):
                if not back: continue
                rr = 80 if e == 'mouse' else 58
                ctx.arc(s * 150, cy - r + 30, rr, 0, 6.3); fs(ctx, c, lw=7)
                ctx.arc(s * 150, cy - r + 30, rr * 0.55, 0, 6.3); src(ctx, inner); ctx.fill()
            elif e == 'bunny':
                if not back: continue
                ellipse(ctx, s * 80, cy - r - 120, 46, 150, s * 0.15); fs(ctx, c, lw=7)
                ellipse(ctx, s * 80, cy - r - 110, 22, 110, s * 0.15); src(ctx, inner); ctx.fill()
            elif e == 'dog':
                if back: continue
                ellipse(ctx, s * (r - 10), cy - 20, 55, 120, -s * 0.25); fs(ctx, shade(c, 0.8), lw=7)

    def _face(self, ctx, t, talk, st):
        cx, cy, r = self.head; look = st.get('look', 0.0)
        eye = self.s.get('eye', 'round'); brows = self.s.get('brows', 'neutral')
        sc = r / 200.0
        ex, ey = 72 * sc, cy - 10 * sc
        blink = (math.sin(t * 1.3 + self.blink_seed) > 0.985) or ((t + self.blink_seed) % 4.1 < 0.12)
        rx, ry = {'big': (52, 64), 'sleepy': (44, 30), 'happy': (44, 50)}.get(eye, (44, 52))
        rx *= sc; ry *= sc
        for s in (-1, 1):
            x = s * ex
            if blink or eye == 'happy' and talk < 0.05:
                ctx.move_to(x - rx, ey); ctx.curve_to(x - rx / 2, ey - (ry * 0.6 if eye == 'happy' else 0), x + rx / 2, ey - (ry * 0.6 if eye == 'happy' else 0), x + rx, ey)
                src(ctx, OUT); ctx.set_line_width(8 * sc); ctx.stroke(); continue
            ellipse(ctx, x, ey, rx, ry); fs(ctx, '#ffffff', lw=6 * sc)
            px = x + look * rx * 0.35; py = ey + ry * 0.12
            ctx.arc(px, py, rx * 0.5, 0, 6.3); src(ctx, self.s.get('eye_color', '#3b2a1f')); ctx.fill()
            ctx.arc(px, py, rx * 0.3, 0, 6.3); src(ctx, '#000000'); ctx.fill()
            ctx.arc(px - rx * 0.18, py - ry * 0.22, rx * 0.15, 0, 6.3); src(ctx, '#ffffff'); ctx.fill()
            if eye == 'sleepy':
                ctx.rectangle(x - rx - 4, ey - ry - 4, rx * 2 + 8, ry * 0.9); src(ctx, self.color if self.kind in ('human', 'animal') else self._face_bg()); ctx.fill()
                ctx.move_to(x - rx, ey - ry * 0.1); ctx.line_to(x + rx, ey - ry * 0.1); src(ctx, OUT); ctx.set_line_width(6 * sc); ctx.stroke()
        # brows
        lift = 10 * sc * talk
        for s in (-1, 1):
            x = s * ex; by = ey - ry - 26 * sc - lift
            if brows == 'angry': a, b = (x - s * 40 * sc, by - 16 * sc), (x + s * 40 * sc, by + 14 * sc)
            elif brows == 'worried': a, b = (x - s * 40 * sc, by + 12 * sc), (x + s * 40 * sc, by - 14 * sc)
            elif brows == 'raised': a, b = (x - s * 40 * sc, by - 14 * sc), (x + s * 40 * sc, by - 14 * sc)
            else: a, b = (x - s * 40 * sc, by), (x + s * 40 * sc, by - 6 * sc)
            ctx.move_to(*a); ctx.line_to(*b); src(ctx, self.s.get('hair', {}).get('color', OUT) if isinstance(self.s.get('hair'), dict) else OUT)
            ctx.set_line_width(13 * sc); ctx.stroke()
        # snout / nose
        my = cy + 105 * sc
        if self.kind == 'animal' and self.s.get('snout', True):
            ellipse(ctx, 0, cy + 75 * sc, 78 * sc, 56 * sc); fs(ctx, self.s.get('muzzle', shade(self.color, 1.3)), lw=6 * sc)
            ellipse(ctx, 0, cy + 50 * sc, 26 * sc, 18 * sc); src(ctx, self.s.get('nose', '#2b1d1d')); ctx.fill()
            my = cy + 105 * sc
        elif self.kind == 'human':
            ctx.move_to(-8 * sc, cy + 40 * sc); ctx.curve_to(0, cy + 52 * sc, 10 * sc, cy + 50 * sc, 14 * sc, cy + 40 * sc)
            src(ctx, shade(self.color, 0.7)); ctx.set_line_width(6 * sc); ctx.stroke()
        if self.s.get('blush', True):
            for s in (-1, 1):
                ellipse(ctx, s * 120 * sc, cy + 55 * sc, 30 * sc, 18 * sc); ctx.set_source_rgba(1, 0.45, 0.45, 0.35); ctx.fill()
        # mouth
        if talk > 0.06:
            w = (38 + 18 * talk) * sc; h = (10 + 48 * talk) * sc
            ellipse(ctx, 0, my + h * 0.35, w, h); fs(ctx, '#5a1414', lw=6 * sc)
            ellipse(ctx, 0, my + h * 0.85, w * 0.55, h * 0.3); src(ctx, '#e06666'); ctx.fill()
            ctx.rectangle(-w * 0.6, my + h * 0.35 - h + 2, w * 1.2, h * 0.28); src(ctx, '#ffffff', 0.9)
            ctx.save(); ellipse(ctx, 0, my + h * 0.35, w - 3, h - 3); ctx.clip(); ctx.rectangle(-w, my + h * 0.35 - h, w * 2, h * 0.32); ctx.fill(); ctx.restore()
        else:
            mood = self.s.get('mouth', 'smile')
            if mood == 'flat':
                ctx.move_to(-30 * sc, my); ctx.line_to(30 * sc, my)
            elif mood == 'frown':
                ctx.move_to(-34 * sc, my + 12 * sc); ctx.curve_to(-14 * sc, my - 8 * sc, 14 * sc, my - 8 * sc, 34 * sc, my + 12 * sc)
            else:
                ctx.move_to(-38 * sc, my - 6 * sc); ctx.curve_to(-16 * sc, my + 22 * sc, 16 * sc, my + 22 * sc, 38 * sc, my - 6 * sc)
            src(ctx, OUT); ctx.set_line_width(8 * sc); ctx.stroke()

    def _face_bg(self):
        return self.color

    def _hair(self, ctx, back):
        hd = self.s.get('hair')
        if not hd or self.kind != 'human': return
        st = hd.get('style', 'short'); c = hd.get('color', '#4a2c1a'); cx, cy, r = self.head
        if back:
            if st == 'long':
                ctx.move_to(-r - 20, cy - 40); ctx.curve_to(-r - 40, cy + 200, -r + 20, cy + 300, -r + 60, cy + 320)
                ctx.line_to(r - 60, cy + 320); ctx.curve_to(r - 20, cy + 300, r + 40, cy + 200, r + 20, cy - 40); ctx.close_path(); fs(ctx, c)
            if st == 'ponytail':
                ellipse(ctx, r + 30, cy + 40, 50, 150, -0.3); fs(ctx, c)
            if st == 'bun':
                ctx.arc(0, cy - r - 30, 75, 0, 6.3); fs(ctx, c)
            return
        if st == 'bald': return
        if st in ('short', 'long', 'ponytail', 'bun'):
            ctx.move_to(-r - 6, cy + 10); ctx.curve_to(-r - 10, cy - r - 60, r + 10, cy - r - 60, r + 6, cy + 10)
            ctx.curve_to(r - 30, cy - 70, r - 80, cy - 110, 40, cy - 105)
            ctx.curve_to(10, cy - 70, -40, cy - 80, -60, cy - 110)
            ctx.curve_to(-120, cy - 90, -r + 10, cy - 40, -r - 6, cy + 10); ctx.close_path(); fs(ctx, c)
        elif st == 'curly' or st == 'afro':
            big = 1.35 if st == 'afro' else 1.0
            for i in range(14):
                a = math.pi * (1.02 + i / 13 * 0.96)
                ctx.arc(math.cos(a) * r * 0.95 * big, cy + math.sin(a) * r * 0.9 * big - (30 if st == 'afro' else 0), 62 * big, 0, 6.3); fs(ctx, c, lw=6)
            ctx.arc(0, cy - r * 0.55, r * 0.75, math.pi, 2 * math.pi); src(ctx, c); ctx.fill()
        elif st == 'spiky' or st == 'mohawk':
            n = 9 if st == 'spiky' else 5; span = 0.95 if st == 'spiky' else 0.35
            ctx.move_to(-r * span, cy - r * (0.5 if st == 'spiky' else 0.85))
            for i in range(n):
                u = (i + 0.5) / n; x = lerp(-r * span, r * span, u)
                ctx.line_to(x, cy - r - 90 - 20 * (i % 2)); ctx.line_to(lerp(-r * span, r * span, (i + 1) / n), cy - r * (0.5 if st == 'spiky' else 0.85))
            ctx.close_path(); fs(ctx, c)
            if st == 'spiky':
                ctx.move_to(-r, cy); ctx.curve_to(-r, cy - r * 1.1, r, cy - r * 1.1, r, cy); ctx.curve_to(r * 0.6, cy - r * 0.55, -r * 0.6, cy - r * 0.55, -r, cy); ctx.close_path(); fs(ctx, c)

    def _accessories(self, ctx):
        acc = self.s.get('accessories', [])
        cx, cy, r = self.head; sc = r / 200.0
        ex, ey = 72 * sc, cy - 10 * sc
        for a in acc:
            name, _, col = a.partition(':'); col = col or None
            if name in ('glasses', 'sunglasses'):
                for s in (-1, 1):
                    rrect(ctx, s * ex - 56 * sc, ey - 44 * sc, 112 * sc, 88 * sc, 30 * sc)
                    if name == 'sunglasses': src(ctx, '#111111', 0.92); ctx.fill_preserve()
                    src(ctx, col or OUT); ctx.set_line_width(11 * sc); ctx.stroke()
                ctx.move_to(-ex + 56 * sc, ey); ctx.line_to(ex - 56 * sc, ey); ctx.stroke()
            elif name == 'cap':
                c = col or '#2e86de'
                ctx.move_to(-r * 0.98, cy - 60 * sc); ctx.curve_to(-r, cy - r - 70 * sc, r, cy - r - 70 * sc, r * 0.98, cy - 60 * sc); ctx.close_path(); fs(ctx, c)
                ellipse(ctx, 120 * sc, cy - 70 * sc, 150 * sc, 34 * sc, 0.05); fs(ctx, shade(c, 0.8))
            elif name == 'beanie':
                c = col or '#e74c3c'
                ctx.move_to(-r * 1.0, cy - 40 * sc); ctx.curve_to(-r, cy - r - 90 * sc, r, cy - r - 90 * sc, r * 1.0, cy - 40 * sc); ctx.close_path(); fs(ctx, c)
                rrect(ctx, -r - 10, cy - 90 * sc, 2 * r + 20, 60 * sc, 26 * sc); fs(ctx, shade(c, 0.85))
                ctx.arc(0, cy - r - 70 * sc, 40 * sc, 0, 6.3); fs(ctx, '#ffffff')
            elif name == 'crown':
                c = col or '#f1c40f'; y0 = cy - r + 30 * sc
                ctx.move_to(-110 * sc, y0); ctx.line_to(-120 * sc, y0 - 120 * sc); ctx.line_to(-60 * sc, y0 - 60 * sc); ctx.line_to(0, y0 - 140 * sc)
                ctx.line_to(60 * sc, y0 - 60 * sc); ctx.line_to(120 * sc, y0 - 120 * sc); ctx.line_to(110 * sc, y0); ctx.close_path(); fs(ctx, c)
            elif name == 'headphones':
                c = col or '#34495e'
                ctx.arc(0, cy, r + 20, math.pi * 1.05, math.pi * 1.95); src(ctx, OUT); ctx.set_line_width(34 * sc); ctx.stroke()
                ctx.arc(0, cy, r + 20, math.pi * 1.05, math.pi * 1.95); src(ctx, c); ctx.set_line_width(22 * sc); ctx.stroke()
                for s in (-1, 1): rrect(ctx, s * (r + 10) - 40 * sc, cy - 60 * sc, 80 * sc, 130 * sc, 30 * sc); fs(ctx, c)
            elif name == 'mic_headset':
                ctx.move_to(-r + 10, cy + 20 * sc); ctx.curve_to(-r + 20, cy + 120 * sc, -120 * sc, cy + 140 * sc, -60 * sc, cy + 120 * sc)
                src(ctx, OUT); ctx.set_line_width(10 * sc); ctx.stroke(); ctx.arc(-55 * sc, cy + 118 * sc, 16 * sc, 0, 6.3); src(ctx, '#333333'); ctx.fill()
            elif name == 'bow':
                c = col or '#e84393'; bx, by = r * 0.6, cy - r * 0.75
                for s in (-1, 1):
                    ctx.move_to(bx, by); ctx.line_to(bx + s * 70 * sc, by - 45 * sc); ctx.line_to(bx + s * 70 * sc, by + 45 * sc); ctx.close_path(); fs(ctx, c)
                ctx.arc(bx, by, 18 * sc, 0, 6.3); fs(ctx, shade(c, 0.8))
            elif name == 'tophat' or name == 'witchhat' or name == 'party_hat' or name == 'chef_hat':
                c = col or {'tophat': '#222222', 'witchhat': '#5b2c83', 'party_hat': '#9b59b6', 'chef_hat': '#ffffff'}[name]; y0 = cy - r + 40 * sc
                if name == 'tophat':
                    ellipse(ctx, 0, y0, 170 * sc, 30 * sc); fs(ctx, c); rrect(ctx, -100 * sc, y0 - 210 * sc, 200 * sc, 210 * sc, 14 * sc); fs(ctx, c)
                    ctx.rectangle(-100 * sc, y0 - 60 * sc, 200 * sc, 30 * sc); src(ctx, '#c0392b'); ctx.fill()
                elif name == 'witchhat':
                    ellipse(ctx, 0, y0, 230 * sc, 40 * sc); fs(ctx, c)
                    ctx.move_to(-110 * sc, y0 - 10 * sc); ctx.line_to(40 * sc, y0 - 300 * sc); ctx.line_to(110 * sc, y0 - 10 * sc); ctx.close_path(); fs(ctx, c)
                elif name == 'party_hat':
                    ctx.move_to(-80 * sc, y0); ctx.line_to(0, y0 - 230 * sc); ctx.line_to(80 * sc, y0); ctx.close_path(); fs(ctx, c)
                    ctx.arc(0, y0 - 235 * sc, 22 * sc, 0, 6.3); fs(ctx, '#f1c40f')
                else:
                    rrect(ctx, -110 * sc, y0 - 110 * sc, 220 * sc, 110 * sc, 20 * sc); fs(ctx, c)
                    for k in (-1, 0, 1): ctx.arc(k * 80 * sc, y0 - 150 * sc, 70 * sc, 0, 6.3); fs(ctx, c)
                    rrect(ctx, -110 * sc, y0 - 110 * sc, 220 * sc, 110 * sc, 20 * sc); src(ctx, c); ctx.fill()
            elif name == 'tie' and self.kind in ('human', 'animal'):
                c = col or '#c0392b'
                ctx.move_to(-16, -560); ctx.line_to(16, -560); ctx.line_to(22, -400); ctx.line_to(0, -370); ctx.line_to(-22, -400); ctx.close_path(); fs(ctx, c, lw=5)
            elif name == 'scarf' and self.kind in ('human', 'animal'):
                c = col or '#e67e22'
                rrect(ctx, -90, -600, 180, 50, 24); fs(ctx, c); rrect(ctx, 30, -580, 46, 150, 18); fs(ctx, c)
            elif name == 'whistle':
                ctx.move_to(-40, -570); ctx.curve_to(-20, -480, 20, -480, 40, -570); src(ctx, '#f1c40f'); ctx.set_line_width(5); ctx.stroke()
                rrect(ctx, -18, -500, 36, 26, 8); fs(ctx, '#bdc3c7', lw=4)
            elif name == 'halo':
                ellipse(ctx, 0, cy - r - 60 * sc, 110 * sc, 26 * sc); src(ctx, '#f9e79f'); ctx.set_line_width(14 * sc); ctx.stroke()
            elif name == 'horns':
                c = col or '#c0392b'
                for s in (-1, 1):
                    ctx.move_to(s * 70 * sc, cy - r + 20 * sc); ctx.curve_to(s * 90 * sc, cy - r - 60 * sc, s * 130 * sc, cy - r - 80 * sc, s * 150 * sc, cy - r - 90 * sc)
                    ctx.curve_to(s * 120 * sc, cy - r - 30 * sc, s * 130 * sc, cy - r + 10 * sc, s * 120 * sc, cy - r + 50 * sc); ctx.close_path(); fs(ctx, c)

    def _arms(self, ctx, t, behind=False):
        if behind: return
        top = self.s.get('top', {}) or {}
        sleeve = top.get('color', self.color) if self.kind in ('human', 'animal') else shade(self.color, 0.8)
        hand = self.s.get('hand', self.color if self.kind in ('human', 'animal') else '#ffffff')
        L1, L2 = self.arm_len
        sx_off = 118 if self.kind in ('human', 'animal') else self.width * 0.48
        thick = 44 if self.kind in ('human', 'animal') else 18
        for s in (-1, 1):
            th, ph = self.arm[s]
            S = (s * sx_off, self.shoulder_y)
            E = (S[0] + s * math.sin(th) * L1, S[1] + math.cos(th) * L1)
            a2 = th + ph
            Hn = (E[0] + s * math.sin(a2) * L2, E[1] + math.cos(a2) * L2)
            ctx.move_to(*S); ctx.line_to(*E); ctx.line_to(*Hn); src(ctx, OUT); ctx.set_line_width(thick + 12); ctx.stroke()
            ctx.move_to(*S); ctx.line_to(*E); ctx.line_to(*Hn); src(ctx, sleeve); ctx.set_line_width(thick); ctx.stroke()
            ctx.arc(Hn[0], Hn[1], 30 if self.kind in ('human', 'animal') else 26, 0, 6.3); fs(ctx, hand, lw=6)
