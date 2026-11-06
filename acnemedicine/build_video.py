"""Build an Acne Medicine Johannesburg video from a spec: photos with slow zoom, on-screen captions and a natural
female voice (Kokoro af_heart), plus a 1280x720 thumbnail built from the product photo.

    python3 acnemedicine/build_video.py acnemedicine/days/<date>/<id>.spec.json out/<id>.mp4 out/<id>.jpg

Spec:
{
  "id": "amj002", "format": "short" | "video",
  "voice": "af_heart",                                  # always a female voice
  "product": "breakout clearing foaming wash",
  "thumbnail": {"image": "<product photo path>", "title": "…"},
  "scenes": [ {"image": "<path>", "fit": "contain"|"cover", "caption": "…", "say": "…"}, … ]
}
Product packshots (plain backgrounds) use "contain"; people/lifestyle photos use "cover".
Short = 1080x1920 (keep under 60 s); video = 1920x1080 (about 3 min).
No commission line in the video: it goes in the description only (Sello, 6 Nov 2026).
"""
import json, os, subprocess, sys, tempfile
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

SIZES = {'short': (1080, 1920), 'video': (1920, 1080)}
BG = (244, 239, 234); INK = (30, 30, 30); ACCENT = (46, 125, 110)
FPS = 30


def font(size, bold=False):
    p = f'/usr/share/fonts/truetype/dejavu/DejaVuSans{"-Bold" if bold else ""}.ttf'
    return ImageFont.truetype(p, size) if os.path.exists(p) else ImageFont.load_default()


def wrap(d, text, f, width):
    words, lines, cur = text.split(), [], ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=f) <= width:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return '\n'.join(lines)


def base_frame(img_path, fit, W, H, margin=1.15):
    """Return an image (W*margin x H*margin) to zoom into: cover-cropped photo, or packshot on a soft backdrop."""
    w, h = int(W * margin), int(H * margin)
    im = ImageOps.exif_transpose(Image.open(img_path)).convert('RGB')
    if fit == 'cover':
        return ImageOps.fit(im, (w, h), Image.LANCZOS, centering=(0.5, 0.4))
    bg = ImageOps.fit(im, (w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(60))
    bg = Image.blend(bg, Image.new('RGB', (w, h), BG), 0.75)
    im.thumbnail((int(w * 0.78), int(h * 0.62)), Image.LANCZOS)
    bg.paste(im, ((w - im.width) // 2, int(h * 0.42 - im.height / 2)))
    return bg


def caption_overlay(text, W, H):
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    if not text:
        return ov
    d = ImageDraw.Draw(ov)
    short = H > W
    f = font(56 if short else 50, True)
    body = wrap(d, text, f, int(W * (0.84 if short else 0.7)))
    bb = d.multiline_textbbox((0, 0), body, font=f, spacing=14, align='center')
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    y = int(H * (0.74 if short else 0.80)) - th // 2
    pad = 34
    d.rounded_rectangle([W // 2 - tw // 2 - pad, y - pad, W // 2 + tw // 2 + pad, y + th + pad], 28, fill=(255, 255, 255, 228))
    d.multiline_text((W // 2, y), body, font=f, fill=INK, anchor='ma', spacing=14, align='center')
    d.rectangle([0, 0, W, 10], fill=ACCENT + (255,))
    d.text((W // 2, H - (90 if short else 54)), 'Acne Medicine Johannesburg', font=font(32 if short else 28),
           fill=(255, 255, 255, 235), anchor='ma', stroke_width=3, stroke_fill=(0, 0, 0, 160))
    return ov


def thumbnail(spec, out, path=lambda p: p):
    t = spec['thumbnail']; W, H = 1280, 720
    im = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(im)
    p = ImageOps.exif_transpose(Image.open(path(t['image']))).convert('RGB'); p.thumbnail((560, 640), Image.LANCZOS)
    im.paste(p, (W - p.width - 70, (H - p.height) // 2))
    f = font(76, True)
    txt = wrap(d, t['title'], f, 620)
    d.multiline_text((70, H // 2), txt, font=f, fill=INK, anchor='lm', spacing=12)
    d.rectangle([0, 0, W, 14], fill=ACCENT)
    im.save(out, quality=90)


def main(spec_path, out, thumb_out):
    s = json.load(open(spec_path)); W, H = SIZES[s['format']]
    root = os.path.dirname(os.path.abspath(spec_path))
    path = lambda p: p if os.path.isabs(p) else os.path.normpath(os.path.join(root, p))
    from kokoro_onnx import Kokoro
    m = os.path.expanduser('~/.cache/kokoro'); k = Kokoro(f'{m}/kokoro.onnx', f'{m}/voices.bin')
    voice = s.get('voice', 'af_heart')
    assert voice.startswith(('af_', 'bf_')), 'female voices only'
    with tempfile.TemporaryDirectory() as td:
        parts = []
        for i, sc in enumerate(s['scenes']):
            a, sr = k.create(sc['say'], voice=voice, speed=1.0, lang='en-us' if voice[0] == 'a' else 'en-gb')
            pad = np.zeros(int(sr * 0.35), dtype=a.dtype)
            audio = np.concatenate([pad, a, pad]); sf.write(f'{td}/{i}.wav', audio, sr)
            dur = len(audio) / sr; n = int(dur * FPS) + 1
            base_frame(path(sc['image']), sc.get('fit', 'cover'), W, H).save(f'{td}/{i}.png')
            caption_overlay(sc.get('caption', ''), W, H).save(f'{td}/{i}c.png')
            zin = i % 2 == 0          # alternate zoom in / out
            z = f"'1+0.13*on/{n}'" if zin else f"'1.13-0.13*on/{n}'"
            vf = (f"[0:v]scale={int(W*1.15)*2}:-1,zoompan=z={z}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={W}x{H}:fps={FPS}[bg];"
                  f"[bg][1:v]overlay=0:0,format=yuv420p[v]")
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', f'{td}/{i}.png', '-loop', '1', '-i', f'{td}/{i}c.png',
                            '-i', f'{td}/{i}.wav', '-filter_complex', vf, '-map', '[v]', '-map', '2:a', '-t', f'{dur:.3f}',
                            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '21', '-r', str(FPS), '-c:a', 'aac', '-b:a', '160k',
                            '-ar', '48000', f'{td}/{i}.mp4'], check=True)
            parts.append(f"file '{td}/{i}.mp4'")
        open(f'{td}/l.txt', 'w').write('\n'.join(parts))
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', f'{td}/l.txt', '-c', 'copy',
                        '-movflags', '+faststart', out], check=True)
    thumbnail(s, thumb_out, path)
    print(out, thumb_out)


if __name__ == '__main__':
    main(*sys.argv[1:4])
