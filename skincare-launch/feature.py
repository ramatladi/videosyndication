"""Product-feature renderer for the six skincare channels (launch rebuild and daily use).

    python3 skincare-launch/feature.py <features.json> [slug ...]   -> skincare-launch/out/feature/<slug>.{mp4,jpg,srt,json}

One named Dermalogica product per video. Store images (skincare-launch/store, verified in sources.json) carry the
product; free Pexels photos only set the locality. Scene types: cover, photo, stat, bullets, steps, note, end.
Each channel has its own look (accent, card side, corner radius, chip style, transition, thumbnail layout).
Commission disclosure lives in the YouTube description only and is refused anywhere on screen or in narration.
American English; American female voices (af_*).
"""
import json, os, re, subprocess, sys, tempfile
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, f'{REPO}/acnemedicine')
FPS, XF = 30, 0.4
INTER = '/usr/share/fonts/opentype/inter/Inter-{}.otf'
BANNED = re.compile(r'commission|affiliate|moisturis|colour|licence|millilitre', re.I)


def F(size, w='SemiBold'):
    return ImageFont.truetype(INTER.format(w), size)


def img(path):
    p = path if os.path.isabs(path) else (f'{HERE}/store/{path}' if os.path.exists(f'{HERE}/store/{path}') else f'{HERE}/photos/{path}')
    return ImageOps.exif_transpose(Image.open(p)).convert('RGB')


def trim(im, pad=0.08):
    """Crop a white-background packshot to the product, with a little air."""
    diff = ImageChops.difference(im, Image.new('RGB', im.size, (255, 255, 255))).convert('L').point(lambda v: 255 if v > 18 else 0)
    bb = diff.getbbox() or (0, 0, *im.size)
    w, h = bb[2] - bb[0], bb[3] - bb[1]; p = int(max(w, h) * pad)
    return im.crop((max(0, bb[0] - p), max(0, bb[1] - p), min(im.width, bb[2] + p), min(im.height, bb[3] + p)))


def wrap(d, text, f, width):
    out, cur = [], ''
    for w in text.split():
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=f) <= width or not cur:
            cur = t
        else:
            out.append(cur); cur = w
    return '\n'.join(out + [cur])


def shadow_card(size, radius, fill=(255, 255, 255, 255), blur=28, off=10, alpha=90):
    w, h = size; m = blur * 2
    sh = Image.new('RGBA', (w + 2 * m, h + 2 * m), (0, 0, 0, 0)); d = ImageDraw.Draw(sh)
    d.rounded_rectangle([m, m + off, m + w, m + h + off], radius, fill=(0, 0, 0, alpha))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    ImageDraw.Draw(sh).rounded_rectangle([m, m, m + w, m + h], radius, fill=fill)
    return sh, m


def product_card(pack, w, h, radius):
    card, m = shadow_card((w, h), radius)
    p = trim(pack); p.thumbnail((int(w * 0.84), int(h * 0.84)), Image.LANCZOS)
    card.paste(p, (m + (w - p.width) // 2, m + (h - p.height) // 2))
    return card, m


def chip(d, xy, text, acc, style, size=30, fg='white', on_photo=False):
    f = F(size, 'Bold'); x, y = xy; tw = d.textlength(text, font=f); ph = size + 22
    if style == 'pill':
        d.rounded_rectangle([x, y, x + tw + 44, y + ph], ph // 2, fill=acc)
    elif style == 'square':
        d.rectangle([x, y, x + tw + 40, y + ph], fill=acc)
    else:  # underline
        d.rectangle([x, y + ph - 6, x + tw + 4, y + ph], fill=acc); fg = fg if on_photo else acc
        x -= 22
    d.text((x + 22, y + ph // 2), text, font=f, fill=fg, anchor='lm')
    return ph


class Look:
    def __init__(self, ch, short):
        self.ch, self.short = ch, short
        self.W, self.H = (1080, 1920) if short else (1920, 1080)
        self.acc = tuple(ch['accent']); self.side = ch['card_side']; self.r = ch['radius']; self.chip = ch['chip']
        self.tint = tuple(int(c + (255 - c) * 0.86) for c in self.acc)


def background(L, sc, pack):
    W, H = int(L.W * 1.1), int(L.H * 1.1)
    if sc.get('image') and sc['type'] != 'figure':
        im = img(sc['image'])
        bg = ImageOps.fit(im, (W, H), Image.LANCZOS, centering=(sc.get('cx', 0.5), sc.get('cy', 0.42)))
        if sc['type'] in ('stat', 'bullets', 'steps', 'note') and not sc.get('sharp'):
            bg = Image.blend(bg.filter(ImageFilter.GaussianBlur(26)), Image.new('RGB', (W, H), L.tint), 0.35)
        return bg
    # gradient in the channel tint
    g = Image.new('RGB', (W, H), L.tint); d = ImageDraw.Draw(g)
    for i in range(H):
        t = i / H; c = tuple(int(L.tint[k] * (1 - t * 0.35) + L.acc[k] * t * 0.35) for k in range(3))
        d.line([(0, i), (W, i)], fill=c)
    return g


def overlay(L, sc, v, pack):
    W, H = L.W, L.H; acc = L.acc
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    t = sc['type']; m = 64 if L.short else 80
    left = L.side == 'left'

    def scrim(top, bottom, a=170):
        s = Image.new('L', (1, 256)); [s.putpixel((0, i), int(a * (i / 255) ** 1.6)) for i in range(256)]
        s = s.resize((W, bottom - top)); blk = Image.new('RGBA', (W, bottom - top), (12, 12, 14, 255)); blk.putalpha(s)
        ov.alpha_composite(blk, (0, top))

    def text_block(x, y, width, kicker, head, sub=None, color=(255, 255, 255), hs=None):
        hs = hs or (74 if L.short else 66)
        y += chip(d, (x, y), kicker, acc, L.chip, on_photo=color == (255, 255, 255)) + 26
        fh = F(hs, L.ch['title_weight']); body = wrap(d, head, fh, width)
        d.multiline_text((x, y), body, font=fh, fill=color, spacing=10)
        y += d.multiline_textbbox((x, y), body, font=fh, spacing=10)[3] - y + 18
        if sub:
            fs = F(38 if L.short else 34, 'Medium'); sb = wrap(d, sub, fs, width)
            d.multiline_text((x, y), sb, font=fs, fill=color, spacing=8)
            y = d.multiline_textbbox((x, y), sb, font=fs, spacing=8)[3]
        return y

    if t in ('cover', 'end'):
        if L.short:
            cw = int(W * 0.74); card, mm = product_card(pack, cw, cw, L.r)
            ov.alpha_composite(card, ((W - cw) // 2 - mm, 330 - mm))
            y = 330 + cw + 64
            d.text((m, y), 'DERMALOGICA', font=F(32, 'Bold'), fill=acc); y += 56
            fh = F(92, 'Bold'); body = wrap(d, v['product_name'], fh, W - 2 * m)
            d.multiline_text((m, y), body, font=fh, fill=(20, 20, 22), spacing=6)
            y = d.multiline_textbbox((m, y), body, font=fh, spacing=6)[3] + 26
            sb = wrap(d, sc.get('sub', ''), F(44, 'Medium'), W - 2 * m)
            d.multiline_text((m, y), sb, font=F(44, 'Medium'), fill=(60, 60, 64), spacing=8)
            ylast = d.multiline_textbbox((m, y), sb, font=F(44, 'Medium'), spacing=8)[3]
        else:
            cw = 760; card, mm = product_card(pack, cw, cw, L.r)
            cx = W - m - cw if left else m
            ov.alpha_composite(card, (cx - mm, (H - cw) // 2 - mm))
            x = m if left else m + cw + 90; width = W - cw - 2 * m - 90
            y = 250
            d.text((x, y), 'DERMALOGICA', font=F(34, 'Bold'), fill=acc); y += 64
            fh = F(104, 'Bold'); body = wrap(d, v['product_name'], fh, width)
            d.multiline_text((x, y), body, font=fh, fill=(20, 20, 22), spacing=6)
            y = d.multiline_textbbox((x, y), body, font=fh, spacing=6)[3] + 30
            sb = wrap(d, sc.get('sub', ''), F(44, 'Medium'), width)
            d.multiline_text((x, y), sb, font=F(44, 'Medium'), fill=(60, 60, 64), spacing=8)
            ylast = d.multiline_textbbox((x, y), sb, font=F(44, 'Medium'), spacing=8)[3]
        if t == 'end':
            # site link: pill in the text column, under the product name (never over the product card)
            px, pw = (m, W - 2 * m) if L.short else (x, width)
            f = F(44 if L.short else 42, 'Bold'); txt = f"Find it at {v['domain']}"
            tw = d.textlength(txt, font=f)
            while tw + 80 > pw and f.size > 28:
                f = F(f.size - 2, 'Bold'); tw = d.textlength(txt, font=f)
            y0 = ylast + 48; ph = f.size + 46
            d.rounded_rectangle([px, y0, px + tw + 80, y0 + ph], ph // 2, fill=acc)
            d.text((px + 40, y0 + ph // 2), txt, font=f, fill='white', anchor='lm')
            d.text((px + 4, y0 + ph + 22), 'Link in the description', font=F(34 if L.short else 32, 'SemiBold'), fill=(60, 60, 64))
    elif t == 'photo':
        if L.short:
            scrim(int(H * 0.45), H)
            text_block(m, int(H * 0.60), W - 2 * m, sc['kicker'], sc['headline'], sc.get('sub'))
        else:
            scrim(int(H * 0.35), H)
            x = m if left else W // 2
            text_block(x, int(H * 0.56), W // 2 - m - 20, sc['kicker'], sc['headline'], sc.get('sub'))
    elif t == 'figure':
        fig = img(sc['image'])
        if L.short:
            bw = W - 2 * m; fig.thumbnail((bw - 40, int(H * 0.46)), Image.LANCZOS)
            card, mm = shadow_card((fig.width + 40, fig.height + 40), L.r); card.paste(fig, (mm + 20, mm + 20))
            ov.alpha_composite(card, ((W - fig.width - 40) // 2 - mm, 260 - mm))
            text_block(m, 260 + fig.height + 110, W - 2 * m, sc['kicker'], sc['headline'], sc.get('sub'), color=(20, 20, 22))
        else:
            fw = W // 2 - m - 40; fig.thumbnail((fw - 40, H - 2 * m - 120), Image.LANCZOS)
            card, mm = shadow_card((fig.width + 40, fig.height + 40), L.r); card.paste(fig, (mm + 20, mm + 20))
            fx = W - m - fig.width - 40 if left else m
            ov.alpha_composite(card, (fx - mm, (H - fig.height - 40) // 2 - mm))
            tx = m if left else W // 2 + 40
            text_block(tx, int(H * 0.36), W // 2 - m - 60, sc['kicker'], sc['headline'], sc.get('sub'), color=(20, 20, 22))
    elif t == 'stat':
        if L.short:
            panel = (m, 300, W - m, 1000)
        else:
            panel = (m, m + 60, W // 2 - 30, H - m - 60) if left else (W // 2 + 30, m + 60, W - m, H - m - 60)
        d.rounded_rectangle(panel, L.r, fill=acc + (240,))
        cx = (panel[0] + panel[2]) // 2
        fs = 260 if len(sc['stat']) <= 4 else 190
        while d.textlength(sc['stat'], font=F(fs, 'Bold')) > panel[2] - panel[0] - 90 and fs > 90:
            fs -= 10
        d.text((cx, panel[1] + (panel[3] - panel[1]) * 0.42), sc['stat'], font=F(fs, 'Bold'), fill='white', anchor='mm')
        d.multiline_text((cx, panel[1] + (panel[3] - panel[1]) * 0.72), wrap(d, sc['label'], F(46, 'SemiBold'), panel[2] - panel[0] - 80),
                         font=F(46, 'SemiBold'), fill='white', anchor='ma', align='center', spacing=8)
        if L.short:
            cw = 560; card, mm = product_card(pack, cw, cw, L.r); ov.alpha_composite(card, ((W - cw) // 2 - mm, 1080 - mm))
        else:
            cw = 640; card, mm = product_card(pack, cw, cw, L.r)
            px = (W // 2 + (W // 2 - cw) // 2) if left else (W // 2 - cw) // 2
            ov.alpha_composite(card, (px - mm, (H - cw) // 2 - mm))
    elif t in ('bullets', 'steps', 'note'):
        if L.short:
            bx0, bx1 = m, W - m
        else:
            bx0, bx1 = (m, W // 2 + 60) if left else (W // 2 - 60, W - m)
        x = bx0 + 60; width = bx1 - bx0 - 120
        fh = F(64 if L.short else 58, L.ch['title_weight']); fb = F(42 if L.short else 38, 'Medium')

        def body(dd, y):
            y += chip(dd, (x, y), sc['kicker'], acc, L.chip) + 30
            hb = wrap(dd, sc['headline'], fh, width)
            dd.multiline_text((x, y), hb, font=fh, fill=(20, 20, 22), spacing=8)
            y = dd.multiline_textbbox((x, y), hb, font=fh, spacing=8)[3] + 40
            for i, it in enumerate(sc.get('items', [])):
                if t == 'steps':
                    dd.ellipse([x, y - 4, x + 54, y + 50], fill=acc); dd.text((x + 27, y + 23), str(i + 1), font=F(30, 'Bold'), fill='white', anchor='mm')
                else:
                    dd.rounded_rectangle([x + 12, y + 12, x + 32, y + 32], 6, fill=acc)
                ib = wrap(dd, it, fb, width - 80)
                dd.multiline_text((x + 80, y), ib, font=fb, fill=(40, 40, 44), spacing=6)
                y = dd.multiline_textbbox((x + 80, y), ib, font=fb, spacing=6)[3] + 30
            return y
        hgt = body(ImageDraw.Draw(Image.new('RGBA', (W, H))), 56) + 56 - (30 if sc.get('items') else 40)
        hgt = max(hgt, 360)
        by0 = int(H * 0.40) if L.short else (H - hgt) // 2
        card, mm = shadow_card((bx1 - bx0, hgt), L.r, fill=(255, 255, 255, 246))
        ov.alpha_composite(card, (bx0 - mm, by0 - mm)); d = ImageDraw.Draw(ov)
        body(d, by0 + 56)
        # the product itself beside (videos) or below (Shorts) the card, so every text card is anchored to its SKU
        if L.short:
            cw = min(480, H - 430 - (by0 + hgt + 60))
            if cw >= 300:
                pc, pm = product_card(pack, cw, cw, L.r); ov.alpha_composite(pc, ((W - cw) // 2 - pm, by0 + hgt + 60 - pm))
        else:
            cw = 560; pc, pm = product_card(pack, cw, cw, L.r)
            px = (W // 2 + 60 + (W // 2 - 60 - m - cw) // 2) if left else (m + (W // 2 - 60 - m - cw) // 2)
            ov.alpha_composite(pc, (px - pm, (H - cw) // 2 - pm))
        d = ImageDraw.Draw(ov)
    # channel badge + fine print, on every scene
    badge = f"{v['locality'].upper()}  ·  {v['desk'].upper()}"
    fbadge = F(26, 'Bold'); bw = d.textlength(badge, font=fbadge) + 48
    by = 70 if L.short else 46
    d.rounded_rectangle([m, by, m + bw, by + 54], 27, fill=(255, 255, 255, 230)); d.text((m + 24, by + 27), badge, font=fbadge, fill=acc, anchor='lm')
    fine = 'Not dermatologists or doctors · Not medical advice' if v['credential_line'] else 'General product information · Not medical advice'
    ff = F(26 if L.short else 24, 'SemiBold'); fw = d.textlength(fine, font=ff) + 40
    fx, fy = (m, by + 66) if L.short else (W - m - fw, by + 6)
    d.rounded_rectangle([fx, fy, fx + fw, fy + 42], 21, fill=(16, 16, 18, 150))
    d.text((fx + 20, fy + 21), fine, font=ff, fill=(255, 255, 255, 240), anchor='lm')
    return ov


def thumbnail(v, path):
    """1280x720, one composition per channel (thumb_layout), always the store's own product photo."""
    ch = v['channel']; acc = tuple(ch['accent']); lay = v['thumb'].get('layout') or ch.get('thumb_layout', 'right'); W, H = 1280, 720
    pack = img(v['packshot']); tint = tuple(int(c + (255 - c) * 0.88) for c in acc)
    im = Image.new('RGB', (W, H), tint); d = ImageDraw.Draw(im)
    words = v['thumb']['text']; kicker = v['thumb']['kicker']
    if lay in ('right', 'left'):
        cw = 560; card, m = product_card(pack, cw, cw, 34); cx = W - cw - 50 if lay == 'right' else 50
        im.paste(card, (cx - m, (H - cw) // 2 - m), card)
        tx = 60 if lay == 'right' else cw + 110; width = W - cw - 170
    elif lay == 'split':  # solid accent half with white type, product card on the tint half
        ImageDraw.Draw(im).rectangle([0, 0, W // 2 + 40, H], fill=acc)
        cw = 520; card, m = product_card(pack, cw, cw, 34); im.paste(card, (W - cw - 70 - m, (H - cw) // 2 - m), card)
        tx, width = 60, W // 2 - 60
    elif lay == 'center':
        cw = 430; card, m = product_card(pack, cw, cw, 34); im.paste(card, ((W - cw) // 2 - m, 230 - m), card)
        tx, width = None, W - 120
    else:  # photo: store lifestyle photo behind, product card bottom-right
        bg = ImageOps.fit(img(v['thumb']['photo']), (W, H), Image.LANCZOS, centering=(0.5, 0.4))
        im.paste(bg); xs = np.clip((0.78 - np.arange(W) / W) / 0.33, 0, 1) ** 0.9 * 215
        a = Image.fromarray(np.tile(xs.astype(np.uint8), (H, 1)), 'L')
        im.paste(Image.new('RGB', (W, H), (10, 10, 12)), (0, 0), a)
        cw = 400; card, m = product_card(pack, cw, cw, 30); im.paste(card, (W - cw - 50 - m, (H - cw) // 2 - m), card)
        tx, width = 60, 640
    d = ImageDraw.Draw(im)
    dark = lay not in ('photo', 'split')
    if tx is None:
        f = F(78, 'Bold'); d.text((W // 2, 70), kicker, font=F(34, 'Bold'), fill=acc, anchor='mm')
        d.text((W // 2, 150), words, font=f, fill=(20, 20, 22), anchor='mm')
    else:
        d.text((tx, 120), kicker, font=F(36, 'Bold'), fill=acc if dark else (255, 255, 255))
        f = F(84, 'Bold'); body = wrap(d, words, f, width)
        d.multiline_text((tx, 190), body, font=f, fill=(20, 20, 22) if dark else (255, 255, 255), spacing=8)
        bb = d.multiline_textbbox((tx, 190), body, font=f, spacing=8)
        pn = wrap(d, 'Dermalogica ' + v['product_name'], F(38, 'SemiBold'), width)
        d.multiline_text((tx, bb[3] + 28), pn, font=F(38, 'SemiBold'), fill=acc if dark else (255, 255, 255), spacing=6)
        d.text((tx, H - 80), f"{v['locality']}  ·  {v['domain']}", font=F(30, 'SemiBold'), fill=(70, 70, 74) if dark else (235, 235, 235))
    d.rectangle([0, 0, W, 12], fill=acc)
    im.save(path, quality=92)


def check_text(v):
    for sc in v['scenes']:
        blob = ' '.join(str(sc.get(k, '')) for k in ('say', 'headline', 'sub', 'kicker', 'label', 'stat')) + ' '.join(sc.get('items', []))
        assert not BANNED.search(blob), (v['slug'], blob[:80])
    assert v.get('spoken_name', v['product_name']).lower() in ' '.join(s['say'].lower() for s in v['scenes']), 'product must be spoken'
    assert v['product_name'].lower() in v['title'].lower(), 'product must be in the title'
    assert len(v['title']) <= 100 and v['voice'].startswith('af_')


def _lufs(path):
    r = subprocess.run(['ffmpeg', '-i', path, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    return json.loads(r[r.rindex('{'):r.rindex('}') + 1])


def master(path):
    """Second loudness pass: linear loudnorm to -14 LUFS; if the true-peak ceiling holds it short of -14.5,
    lift with a peak limiter (ceiling about -2 dBTP). Video stream is copied."""
    def run(af):
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', path, '-map', '0', '-c:v', 'copy', '-af', af, '-c:a', 'aac',
                        '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', path + '.tmp.mp4'], check=True)
        os.replace(path + '.tmp.mp4', path)
    m = _lufs(path)
    run(f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
        f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    for _ in range(3):
        m = _lufs(path); gap = -14.2 - float(m['input_i'])
        if gap <= 0.3:
            break
        run(f"aresample=192000,volume={gap + 0.2:.2f}dB,alimiter=limit=0.79:attack=2:release=60:level=false,aresample=48000")


def build(v, k, outdir):
    check_text(v)
    short = v['format'] == 'short'; L = Look(v['channel'], short); W, H = L.W, L.H
    pack = img(v['packshot']); o = f'{outdir}/{v["slug"]}'
    with tempfile.TemporaryDirectory() as td:
        durs, clips = [], []
        for i, sc in enumerate(v['scenes']):
            a, sr = k.create(sc['say'], voice=v['voice'], speed=v.get('speed', 1.0), lang='en-us')
            pad = np.zeros(int(sr * 0.3), dtype=a.dtype); audio = np.concatenate([pad, a, pad])
            sf.write(f'{td}/{i}.wav', audio, sr); d = len(audio) / sr; durs.append(d)
            vd = d + (XF if i < len(v['scenes']) - 1 else 0); n = int(vd * FPS) + 2
            background(L, sc, pack).save(f'{td}/{i}b.png'); overlay(L, sc, v, pack).save(f'{td}/{i}o.png')
            z = f"'1+0.06*on/{n}'" if i % 2 == 0 else f"'1.06-0.06*on/{n}'"
            vf = (f"[0:v]scale={int(W*1.1)*2}:-1,zoompan=z={z}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={W}x{H}:fps={FPS}[b];"
                  f"[b][1:v]overlay=0:0,format=yuv420p[v]")
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', f'{td}/{i}b.png', '-loop', '1', '-i', f'{td}/{i}o.png',
                            '-filter_complex', vf, '-map', '[v]', '-t', f'{vd:.3f}', '-c:v', 'libx264', '-preset', 'veryfast',
                            '-crf', '18', '-r', str(FPS), f'{td}/{i}.mp4'], check=True)
            clips.append(f'{td}/{i}.mp4')
        # video: crossfades between scenes; audio: narration back to back (+ original music bed)
        tr = v['channel']['transition']; inputs = sum((['-i', c] for c in clips), []); chain, last, off = [], '[0:v]', 0.0
        for i in range(1, len(clips)):
            off += durs[i - 1]; lab = f'[x{i}]'
            chain.append(f"{last}[{i}:v]xfade=transition={tr}:duration={XF}:offset={off - XF + XF:.3f}{lab}"); last = lab
        total = sum(durs)
        chain.append(f"{last}drawbox=x=0:y=ih-8:w='iw*t/{total:.3f}':h=8:color=0x{''.join(f'{c:02x}' for c in L.acc)}@0.95:t=fill,format=yuv420p[vout]")
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', *inputs, '-filter_complex', ';'.join(chain), '-map', '[vout]',
                        '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-r', str(FPS), '-t', f'{total:.3f}', f'{td}/v.mp4'], check=True)
        wav = np.concatenate([sf.read(f'{td}/{i}.wav')[0] for i in range(len(clips))]); sf.write(f'{td}/n.wav', wav, 24000)
        import build_launch as B
        bed, msr = B.music({'music': v['channel']['music']}, total + 1); sf.write(f'{td}/m.wav', bed, msr)
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', f'{td}/v.mp4', '-i', f'{td}/n.wav', '-i', f'{td}/m.wav', '-filter_complex',
                        '[2:a]volume=0.13[m];[1:a]aresample=48000[n];[n][m]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]',
                        '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart',
                        '-shortest', o + '.mp4'], check=True)
    master(o + '.mp4')
    import discover as D
    timing = D.timing_from_audio(durs, pad=0.3)
    open(o + '.srt', 'w').write(D.srt([s['say'] for s in v['scenes']], timing))
    json.dump({'scenes': [round(x, 3) for x in durs]}, open(o + '.timing.json', 'w'))
    thumbnail(v, o + '.jpg')
    return o, durs


def description(v, durs):
    import discover as D
    lines = [v['lead'], '', f'We earn a commission if you buy through our link at https://{v["domain"]}/.', '',
             *[f'• {f}' for f in v['facts']], '']
    if v['format'] == 'video':
        chap = D.chapters([s.get('chapter') or s.get('headline') or s.get('kicker', 'Overview').title() for s in v['scenes']],
                          D.timing_from_audio(durs, pad=0.3))
        if chap:
            lines += ['Chapters:', chap, '']
    if v['credential_line']:
        lines.append(f"{v['domain']} is not run by dermatologists or doctors.")
    lines += ['General product information, not medical advice. Product details from the official product listing '
              f"({v['product_url']}, checked {v['checked']}); check the current listing before you buy.", '',
              f"Shop: https://{v['domain']}/", '',
              'Product images: Dermalogica South Africa store listing.']
    if v.get('free_photos'):
        lines.append('Photos from Pexels (free license): ' + ', '.join(f"{p['by']}" for p in v['free_photos']) + '.')
    lines += ['Music: original, made for this video. Narration: Kokoro text-to-speech.', '', v['hashtags']]
    desc = '\n'.join(lines); assert len(desc.encode()) <= 5000 and 'earn a commission' in desc
    return desc


if __name__ == '__main__':
    spec = json.load(open(sys.argv[1])); want = sys.argv[2:]
    out = os.environ.get('FEATURE_OUT', f'{HERE}/out/feature'); os.makedirs(out, exist_ok=True)
    from kokoro_onnx import Kokoro
    m = os.path.expanduser('~/.cache/kokoro'); k = Kokoro(f'{m}/kokoro.onnx', f'{m}/voices.bin')
    for v in spec['videos']:
        if want and v['slug'] not in want:
            continue
        v['channel'] = spec['channels'][v['domain']]; v.update({x: v['channel'][x] for x in ('locality', 'desk', 'credential_line', 'voice')})
        v['checked'] = spec['checked']
        o, durs = build(v, k, out)
        json.dump({'title': v['title'], 'description': description(v, durs), 'tags': v['tags'], 'duration': round(sum(durs), 2)},
                  open(o + '.json', 'w'), indent=1, ensure_ascii=False)
        print(o, round(sum(durs), 1))
