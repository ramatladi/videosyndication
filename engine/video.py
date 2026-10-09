#!/usr/bin/env python3
"""Render a cast-engine episode.
usage: python3 engine/video.py episodes/epNNN.json WORKDIR video OUT.mp4
       python3 engine/video.py episodes/epNNN.json WORKDIR frames t1,t2,..."""
import cairo, math, sys, json, subprocess, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cast import Character, hexc, src, rrect, clamp, lerp
from scenes import draw_scene, draw_front, FLOOR_Y

W, H, FPS = 1080, 1920, 30
EP = json.load(open(sys.argv[1])); WD = sys.argv[2]
TL = json.load(open(f'{WD}/timeline.json'))
TOTAL, INTRO, END, LINES = TL['total'], TL['intro'], TL['end'], TL['lines']
ENV = dict(np.load(f'{WD}/env.npz'))
SCENE = EP.get('scene', 'studio'); DESK = bool(EP.get('desk', False))
CAST = [Character(c) for c in EP['cast']]
IDS = [c['id'] for c in EP['cast']]
n = len(CAST)
XS = {1: [540], 2: [330, 750], 3: [215, 540, 865], 4: [150, 400, 680, 930]}[min(4, n)]
BASE = {1: 1.0, 2: 0.9, 3: 0.78, 4: 0.66}[min(4, n)]
FEET_Y = 1700 if not DESK else 1780
POS = {}
WIDE = ({1: 1.3, 2: 1.15, 3: 1.04, 4: 0.96}[min(4, n)], 540, FEET_Y - 560)
for k, (cid, ch) in enumerate(zip(IDS, CAST)):
    s = BASE * float(EP['cast'][k].get('scale', 1.0))
    POS[cid] = (XS[k], FEET_Y, s)
SPEC = {c['id']: c for c in EP['cast']}

def ease(u): u = clamp(u); return u * u * (3 - 2 * u)
def env(cid, t):
    a = ENV.get(cid); i = int(t * FPS)
    return float(a[i]) if a is not None and 0 <= i < len(a) else 0.0
def current_line(t):
    cur = None
    for k, l in enumerate(LINES):
        if l['start'] - 0.05 <= t: cur = k
    return cur

def head_pos(cid):
    x, fy, s = POS[cid]; ch = CAST[IDS.index(cid)]
    return x, fy + ch.head[1] * s, ch.head[2] * s

def shot_for(k):
    l = LINES[k]; shot = l.get('shot', 'CU'); spk = l['spk']
    if shot == 'W' or n == 1 and shot == 'TWO':
        return WIDE
    if shot == 'TWO' or len(spk) > 1:
        group = spk if len(spk) > 1 else [spk[0], next((LINES[j]['spk'][0] for j in range(k - 1, -1, -1) if LINES[j]['spk'][0] != spk[0]), IDS[(IDS.index(spk[0]) + 1) % n])]
        hs = [head_pos(c) for c in group]
        x0 = min(h[0] for h in hs); x1 = max(h[0] for h in hs)
        z = clamp(900 / max(400, x1 - x0 + 420), 1.0, 1.6)
        cy = sum(h[1] for h in hs) / len(hs) + 260 / z
        return (z, (x0 + x1) / 2, cy)
    target = shot if shot in POS else spk[0]
    hx, hy, hr = head_pos(target)
    z = clamp(560 / (hr * 2.6), 1.3, 2.4)
    return (z, hx, hy + 330 / z)

def camera(t):
    z, cx, cy = _camera(t)
    cy = min(cy, 2330 - 960 / z); cx = max(-480 + 540 / z, min(1560 - 540 / z, cx))
    return z, cx, cy

def _camera(t):
    if t < INTRO: z, cx, cy = WIDE; return z * (1 + 0.05 * t / INTRO), cx, cy
    k = current_line(t)
    if k is None: return WIDE
    z, cx, cy = shot_for(k)
    nxt = LINES[k + 1]['start'] if k + 1 < len(LINES) else TOTAL
    u = clamp((t - LINES[k]['start']) / max(0.6, nxt - LINES[k]['start']))
    if t > END: u2 = ease((t - END) / 2.0); z, cx, cy = lerp(z, WIDE[0], u2), lerp(cx, WIDE[1], u2), lerp(cy, WIDE[2], u2)
    return z * (1 + 0.04 * u), cx, cy

def text_box(ctx, rows, y, sizes, colors, pad=26):
    ctx.select_font_face('DejaVu Sans', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ws, hs = [], []
    for txt, sz in zip(rows, sizes):
        ctx.set_font_size(sz); ws.append(ctx.text_extents(txt).x_advance); hs.append(sz * 1.22)
    bw = max(ws) + pad * 2; bh = sum(hs) + pad * 1.4; x0 = (W - bw) / 2; y0 = y - bh / 2
    rrect(ctx, x0, y0, bw, bh, 26); ctx.set_source_rgba(0, 0, 0, 0.55); ctx.fill()
    cy = y0 + pad * 0.7
    for txt, sz, col, w_, h_ in zip(rows, sizes, colors, ws, hs):
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

def label_color(cid):
    c = SPEC[cid].get('label_color') or SPEC[cid].get('color', '#ffffff')
    r, g, b, _ = hexc(c)
    if 0.299 * r + 0.587 * g + 0.114 * b < 0.45: r, g, b = r + (1 - r) * 0.55, g + (1 - g) * 0.55, b + (1 - b) * 0.55
    return (r, g, b)

def draw_captions(ctx, t):
    if t < INTRO + 0.2:
        it = EP.get('intro') or ['']
        ctx.push_group()
        text_box(ctx, it, 330, [62] * (len(it) - 1) + [42 if len(it) > 1 else 62],
                 [(1, 1, 1)] * (len(it) - 1) + [(1, 0.75, 0.3) if len(it) > 1 else (1, 1, 1)])
        ctx.pop_group_to_source(); ctx.paint_with_alpha(clamp(t / 0.3) * clamp((INTRO + 0.2 - t) / 0.3)); return
    for k, l in enumerate(LINES):
        end = min(l['end'] + 0.35, LINES[k + 1]['start'] - 0.02) if k + 1 < len(LINES) else l['end'] + 0.6
        if l['start'] - 0.05 <= t < end:
            body = wrap(ctx, l['text'], 56, 900)
            name = ' & '.join(SPEC[c].get('name', c).upper() for c in l['spk'])
            text_box(ctx, [name] + body, 1360, [36] + [56] * len(body), [label_color(l['spk'][0])] + [(1, 1, 1)] * len(body))
            return

def draw_frame(ctx, t):
    ctx.set_operator(cairo.OPERATOR_SOURCE); ctx.set_source_rgb(0, 0, 0); ctx.paint(); ctx.set_operator(cairo.OPERATOR_OVER)
    z, cx, cy = camera(t)
    ctx.save(); ctx.translate(W / 2, H / 2); ctx.scale(z, z); ctx.translate(-cx, -cy)
    draw_scene(ctx, SCENE, t)
    k = current_line(t); l = LINES[k] if k is not None else None
    speaking = l['spk'] if l and l['start'] <= t < l['end'] else []
    focus = (l['spk'][0] if l else IDS[0])
    for cid, ch in zip(IDS, CAST):
        x, fy, s = POS[cid]
        talk = env(cid, t)
        gest = None
        if l and cid in l['spk'] and l.get('gesture') and t < l['end'] + 0.6: gest = l['gesture']
        jump = 0.0
        if l and cid in l['spk'] and l.get('jump'):
            u = (t - l['start']) / 0.6
            if 0 <= u <= 1: jump = 160 * math.sin(math.pi * u)
        if cid == focus:
            prev = next((LINES[j]['spk'][0] for j in range(k - 1, -1, -1) if LINES[j]['spk'][0] != cid), None) if k is not None else None
            tgt = POS[prev][0] if prev else 540
        else:
            tgt = POS[focus][0]
        look = clamp((tgt - x) / 300, -1, 1)
        bob = 5 * math.sin(t * 1.7 + IDS.index(cid)) + 8 * talk * abs(math.sin(t * 6))
        ctx.save(); ctx.translate(x, fy); ctx.scale(s, s)
        ch.draw(ctx, dict(t=t, talk=talk, gesture=gest, look=look, bob=bob, jump=jump))
        ctx.restore()
    draw_front(ctx, SCENE, t, DESK)
    ctx.restore()
    g = cairo.RadialGradient(W / 2, H * 0.5, 450, W / 2, H * 0.5, 1300)
    g.add_color_stop_rgba(0, 0, 0, 0, 0); g.add_color_stop_rgba(1, 0, 0, 0, 0.5); ctx.set_source(g); ctx.paint()
    if t < 0.4: ctx.set_source_rgba(0, 0, 0, 1 - t / 0.4); ctx.paint()
    if t > TOTAL - 1.0: ctx.set_source_rgba(0, 0, 0, clamp((t - TOTAL + 1.0) / 0.8)); ctx.paint()
    draw_captions(ctx, t)

def main():
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); ctx = cairo.Context(surf)
    if sys.argv[3] == 'frames':
        for ts in sys.argv[4].split(','):
            draw_frame(ctx, float(ts)); surf.write_to_png(f'{WD}/f_{float(ts):05.1f}.png')
        return
    out = sys.argv[4]
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
           '-i', f'{WD}/audio.wav', '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p',
           '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    nf = int(TOTAL * FPS)
    for i in range(nf):
        draw_frame(ctx, i / FPS); surf.flush(); p.stdin.write(bytes(surf.get_data()))
        if i % 300 == 0: print(f'frame {i}/{nf}', flush=True)
    p.stdin.close(); p.wait(); print('done')

if __name__ == '__main__':
    main()
