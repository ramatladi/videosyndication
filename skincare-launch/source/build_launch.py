"""Build the six skincare-launch videos (1920x1080) from specs.json.

    python3 skincare-launch/build_launch.py [slug ...]      -> skincare-launch/out/<slug>.mp4 + .jpg + .json

Each video: free Pexels photos (credited in the description), a female Kokoro voice, an original music bed
synthesised here (no third-party audio), a commission/disclaimer strip on screen for the whole video, and the
commission spoken in scene 2 and the closing scene. Not for the Acne Medicine queue.
"""
import json, os, subprocess, sys, tempfile
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
W, H, FPS, SR = 1920, 1080, 30, 24000
INTER = '/usr/share/fonts/opentype/inter/Inter-{}.otf'
from PIL import ImageFont

CREDITS = {
    '286951': 'Linda Prebreza', '7020241': 'Yan Krukau', '7020264': 'Yan Krukau', '6810872': 'Yaroslav Shuraev',
    '7321554': 'Kaboompics', '3852167': 'Anna Shvets', '8140918': 'Ron Lach', '9185875': 'Timur Weber',
    '9185864': 'Timur Weber', '6690238': 'Tara Winstead', '6690845': 'Tara Winstead', '7814991': 'Mikhail Nilov',
    '5269653': 'Armin Rimoldi', '5202453': 'Kaboompics', '7466779': 'Anna Tarazevich', '27544680': 'Deepa Nishad',
    '5240623': 'Anete Lusina', '6781117': 'Monstera Production', '7321267': 'Kaboompics',
    '8185803': 'Kindel Media', '20817639': 'Laura Chouette', '8276910': 'Kindel Media', '8093198': 'Kindel Media',
    '30982094': 'Karen Laårk Boshoff', '5202462': 'Kaboompics', '7320730': 'Kaboompics', '7019486': 'Yan Krukau',
    '3762870': 'Shiny Diamond', '4612160': 'cottonbro studio'}
for p in json.load(open(f'{REPO}/acnemedicine/photos/pool.json')):
    CREDITS.setdefault(p['id'], p['by'])


def photo(pid):
    for d in (f'{HERE}/photos', f'{REPO}/acnemedicine/photos/pexels'):
        if os.path.exists(f'{d}/{pid}.jpg'):
            return f'{d}/{pid}.jpg'
    raise FileNotFoundError(pid)


def font(size, weight='SemiBold'):
    return ImageFont.truetype(INTER.format(weight), size)


def wrap(d, text, f, width):
    lines, cur = [], ''
    for w in text.split():
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=f) <= width or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    return '\n'.join(lines + [cur])


def base(pid, cx=0.5, margin=1.12):
    im = ImageOps.exif_transpose(Image.open(photo(pid))).convert('RGB')
    w, h = int(W * margin), int(H * margin)
    if im.width / im.height >= 1.2:
        return ImageOps.fit(im, (w, h), Image.LANCZOS, centering=(cx, 0.4))
    # portrait photo: sharp copy on a soft blurred copy of itself
    bg = ImageOps.fit(im, (w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(60))
    bg = Image.blend(bg, Image.new('RGB', (w, h), (240, 236, 230)), 0.3)
    fg = im.copy(); fg.thumbnail((int(w * 0.9), int(h * 0.94)), Image.LANCZOS)
    bg.paste(fg, ((w - fg.width) // 2, (h - fg.height) // 2))
    return bg


def overlay(v, sc, i):
    """Caption card (position per channel style), kicker chip, disclosure strip, optional checklist/counter."""
    st, acc = v['style'], tuple(v['style']['accent'])
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    pos = st['caption']
    fk, fc = font(30, 'Bold'), font(50, 'SemiBold')
    box_w = 760 if pos in ('left', 'right') else 1300
    body = wrap(d, sc['caption'], fc, box_w - 80)
    bb = d.multiline_textbbox((0, 0), body, font=fc, spacing=12)
    th = bb[3] - bb[1]
    kw = d.textlength(sc['kicker'], font=fk) + 44
    ch = th + 70 + 64
    if pos == 'left':
        x0, y0 = 70, (H - ch) // 2
    elif pos == 'right':
        x0, y0 = W - 70 - box_w, (H - ch) // 2
    elif pos == 'top':
        x0, y0 = (W - box_w) // 2, 120
    else:
        x0, y0 = (W - box_w) // 2, H - 150 - ch
    d.rounded_rectangle([x0, y0, x0 + box_w, y0 + ch], 26, fill=(255, 255, 255, 236))
    d.rounded_rectangle([x0 + 36, y0 + 30, x0 + 36 + kw, y0 + 30 + 48], 24, fill=acc + (255,))
    d.text((x0 + 36 + 22, y0 + 54), sc['kicker'], font=fk, fill='white', anchor='lm')
    d.multiline_text((x0 + 40, y0 + 104), body, font=fc, fill=(28, 28, 28), spacing=12)
    if st.get('checklist'):                     # packing list that ticks off
        items, n = st['checklist'], sc.get('ticks', 0)
        cx0 = 70 if pos == 'right' else W - 470; cy0 = 120
        d.rounded_rectangle([cx0, cy0, cx0 + 400, cy0 + 70 + 62 * len(items)], 22, fill=(255, 255, 255, 230))
        d.text((cx0 + 30, cy0 + 22), 'PACKING LIST', font=font(26, 'Bold'), fill=acc)
        for k, it in enumerate(items):
            y = cy0 + 74 + 62 * k; done = k < n
            d.rounded_rectangle([cx0 + 30, y, cx0 + 66, y + 36], 8, outline=acc, width=4, fill=acc if done else None)
            if done:
                d.line([(cx0 + 38, y + 18), (cx0 + 46, y + 28), (cx0 + 60, y + 8)], fill='white', width=5)
            d.text((cx0 + 84, y + 18), it, font=font(32, 'Medium'), fill=(28, 28, 28), anchor='lm')
    if st.get('counter'):                       # scavenger-hunt progress dots
        n, tot = sc.get('found', 0), st['counter']
        cx0, cy0 = W - 70 - (tot * 64 + 210), 110
        d.rounded_rectangle([cx0, cy0, W - 70, cy0 + 84], 42, fill=(255, 255, 255, 232))
        d.text((cx0 + 34, cy0 + 42), f'FOUND {n}/{tot}', font=font(30, 'Bold'), fill=acc, anchor='lm')
        for k in range(tot):
            x = cx0 + 230 + k * 64
            d.ellipse([x, cy0 + 22, x + 40, cy0 + 62], fill=acc if k < n else None, outline=acc, width=4)
    # brand + disclosure strip, on screen for the whole video
    d.rectangle([0, H - 74, W, H], fill=(20, 20, 20, 215))
    d.rectangle([0, 0, W, 10], fill=acc + (255,))
    d.text((40, H - 37), v['brand'], font=font(30, 'Bold'), fill='white', anchor='lm')
    disc = 'We earn a commission from our links  ·  '
    disc += ('Not dermatologists or doctors  ·  Not medical advice' if v['credential_line']
             else 'General product info, not medical advice')
    fs = 26
    while 40 + d.textlength(v['brand'], font=font(30, 'Bold')) + 60 + d.textlength(disc, font=font(fs, 'Medium')) > W - 40:
        fs -= 1
    d.text((W - 40, H - 37), disc, font=font(fs, 'Medium'), fill=(235, 235, 235), anchor='rm')
    return ov


def music(st, seconds, sr=48000):
    """Original ambient bed: soft detuned pad chords + a quiet pluck on each beat. Generated here, no samples."""
    m = st['music']; beat = 60 / m['bpm']; bar = beat * 4
    n = int(seconds * sr); t = np.arange(n) / sr; out = np.zeros(n)
    hz = lambda midi: 440 * 2 ** ((midi - 69) / 12)
    nbars = int(np.ceil(seconds / bar)) + 1
    rng = np.random.default_rng(m['root'])
    for b in range(nbars):
        chord = m['prog'][b % len(m['prog'])]; s0 = int(b * bar * sr); s1 = min(n, int((b + 1.15) * bar * sr))
        if s0 >= n:
            break
        tt = t[s0:s1] - b * bar; L = s1 - s0
        env = np.minimum(1, tt / 1.2) * np.minimum(1, (s1 / sr - b * bar - tt) / 0.8)
        for iv in chord:
            f = hz(m['root'] + iv - 12)
            for det in (-0.12, 0.12):
                out[s0:s1] += 0.05 * env * np.sin(2 * np.pi * f * (1 + det / 100) * tt)
        for k in range(4):                      # gentle pluck arpeggio
            ps = int((b * bar + k * beat) * sr)
            if ps >= n:
                break
            pl = min(int(1.2 * sr), n - ps); pt = np.arange(pl) / sr
            f = hz(m['root'] + chord[rng.integers(len(chord))] + 12)
            out[ps:ps + pl] += 0.035 * np.exp(-pt * 4) * np.sin(2 * np.pi * f * pt) * (1 + 0.3 * np.sin(2 * np.pi * 2 * f * pt))
    fade = np.minimum(1, np.minimum(t / 2, (seconds - t) / 3))
    out = np.convolve(out * fade, np.ones(6) / 6, mode='same')
    return (out / (np.abs(out).max() + 1e-9) * 0.5).astype(np.float32), sr


def build(v, k):
    out = f'{HERE}/out/{v["slug"]}'; os.makedirs(os.path.dirname(out), exist_ok=True)
    voice = v['voice']; assert voice[:3] in ('af_', 'bf_'), 'female voices only'
    motion = v['style']['motion']
    with tempfile.TemporaryDirectory() as td:
        parts, total = [], 0.0
        for i, sc in enumerate(v['scenes']):
            a, sr = k.create(sc['say'], voice=voice, speed=1.0, lang='en-us' if voice[0] == 'a' else 'en-gb')
            pad = np.zeros(int(sr * 0.4), dtype=a.dtype)
            audio = np.concatenate([pad, a, pad]); sf.write(f'{td}/{i}.wav', audio, sr)
            dur = len(audio) / sr; total += dur; nfr = int(dur * FPS) + 1
            base(sc['image'], sc.get('cx', 0.5)).save(f'{td}/{i}.png')
            overlay(v, sc, i).save(f'{td}/{i}c.png')
            if motion == 'in':
                z, x, y = f"'1+0.10*on/{nfr}'", "'iw/2-(iw/zoom/2)'", "'ih/2-(ih/zoom/2)'"
            elif motion == 'out':
                z, x, y = f"'1.10-0.10*on/{nfr}'", "'iw/2-(iw/zoom/2)'", "'ih/2-(ih/zoom/2)'"
            elif motion == 'pan_r':
                z, x, y = "'1.08'", f"'(iw-iw/zoom)*on/{nfr}'", "'ih/2-(ih/zoom/2)'"
            else:
                z, x, y = "'1.08'", f"'(iw-iw/zoom)*(1-on/{nfr})'", "'ih/2-(ih/zoom/2)'"
            vf = (f"[0:v]scale={int(W*1.12)*2}:-1,zoompan=z={z}:x={x}:y={y}:d={nfr}:s={W}x{H}:fps={FPS}[bg];"
                  f"[bg][1:v]overlay=0:0,fade=t=in:st=0:d=0.25,format=yuv420p[v]")
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', f'{td}/{i}.png', '-loop', '1', '-i', f'{td}/{i}c.png',
                            '-i', f'{td}/{i}.wav', '-filter_complex', vf, '-map', '[v]', '-map', '2:a', '-t', f'{dur:.3f}',
                            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-r', str(FPS), '-c:a', 'pcm_s16le',
                            '-ar', '48000', f'{td}/{i}.mkv'], check=True)
            parts.append(f"file '{td}/{i}.mkv'")
        open(f'{td}/l.txt', 'w').write('\n'.join(parts))
        bed, msr = music(v['style'], total + 1); sf.write(f'{td}/music.wav', bed, msr)
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', f'{td}/l.txt',
                        '-i', f'{td}/music.wav', '-filter_complex',
                        '[1:a]volume=0.16[m];[0:a][m]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-15:TP=-1.5:LRA=11[a]',
                        '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-ar', '48000',
                        '-movflags', '+faststart', out + '.mp4'], check=True)
    thumb(v, out + '.jpg')
    return out


def thumb(v, path):
    t, acc = v['thumb'], tuple(v['style']['accent']); TW, TH = 1280, 720
    im = Image.new('RGB', (TW, TH), (246, 242, 236)); d = ImageDraw.Draw(im)
    p = ImageOps.fit(ImageOps.exif_transpose(Image.open(photo(t['image']))).convert('RGB'), (620, TH), Image.LANCZOS,
                     centering=(0.5, 0.4))
    im.paste(p, (TW - 620, 0))
    d.rectangle([0, 0, TW, 14], fill=acc)
    d.text((56, 80), t['kicker'], font=font(34, 'Bold'), fill=acc)
    f = font(76, 'Bold'); d.multiline_text((56, TH // 2), wrap(d, t['title'], f, 580), font=f, fill=(25, 25, 25),
                                           anchor='lm', spacing=10)
    d.text((56, TH - 60), v['brand'], font=font(32, 'SemiBold'), fill=(60, 60, 60))
    im.save(path, quality=90)


def description(v):
    photos = []
    for sc in v['scenes'] + [{'image': v['thumb']['image']}]:
        if sc['image'] not in photos:
            photos.append(sc['image'])
    names = []
    for pid in photos:
        if CREDITS[pid] not in names:
            names.append(CREDITS[pid])
    lines = [v['scenes'][0]['say'], '',
             f'We earn a commission if you buy through our link at https://{v["domain"]}/.']
    if v['credential_line']:
        lines.append(f'{v["domain"]} is not run by dermatologists or doctors.')
    lines += ['General product information, not medical advice. Product details are taken from the official '
              f'product pages (checked {SPEC["checked"]}); check the current page and ingredient list before you buy.',
              '', f'Shop: https://{v["domain"]}/', '',
              'Photos from Pexels (free licence): ' + ', '.join(names) + '.',
              'Music: original, made for this video. Narration: Kokoro text-to-speech.']
    return '\n'.join(lines), [{'pexels_id': pid, 'photographer': CREDITS[pid],
                               'url': f'https://www.pexels.com/photo/{pid}/', 'licence': 'Pexels License'} for pid in photos]


SPEC = json.load(open(f'{HERE}/specs.json'))
if __name__ == '__main__':
    from kokoro_onnx import Kokoro
    m = os.path.expanduser('~/.cache/kokoro'); k = Kokoro(f'{m}/kokoro.onnx', f'{m}/voices.bin')
    want = sys.argv[1:]
    for v in SPEC['videos']:
        if want and v['slug'] not in want:
            continue
        out = build(v, k)
        desc, photos = description(v)
        json.dump({'description': desc, 'photos': photos}, open(out + '.json', 'w'), indent=1, ensure_ascii=False)
        print(out)
