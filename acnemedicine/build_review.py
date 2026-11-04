"""Build a product-review Short (1080x1920) from reviews/<id>.json: text cards + Kokoro natural voice.

    python3 acnemedicine/build_review.py acnemedicine/reviews/amj001.json out/amj001.mp4

Uses no product photos or third-party imagery: every frame is drawn here. Needs ~/.cache/kokoro (setup.sh).
"""
import json, os, subprocess, sys, tempfile
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont
from kokoro_onnx import Kokoro

W, H = 1080, 1920
BG, INK, SOFT, ACCENT = (244, 239, 234), (40, 40, 40), (105, 105, 105), (46, 125, 110)


def font(size, bold=False):
    for p in (f'/usr/share/fonts/truetype/dejavu/DejaVuSans{"-Bold" if bold else ""}.ttf',):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def card(head, sub, n, total, path):
    im = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 14], fill=ACCENT)
    fh, fs = font(84, True), font(46)
    hb = d.multiline_textbbox((0, 0), head, font=fh, spacing=16, align='center')
    sb = d.multiline_textbbox((0, 0), sub, font=fs, spacing=18, align='center') if sub else (0, 0, 0, 0)
    gap = 60 if sub else 0
    top = (H - ((hb[3] - hb[1]) + gap + (sb[3] - sb[1]))) // 2
    d.multiline_text((W // 2, top), head, font=fh, fill=INK, anchor='ma', spacing=16, align='center')
    if sub:
        d.multiline_text((W // 2, top + (hb[3] - hb[1]) + gap), sub, font=fs, fill=SOFT, anchor='ma', spacing=18, align='center')
    for i in range(total):           # progress dots
        x = W // 2 + (i - (total - 1) / 2) * 34
        d.ellipse([x - 8, H - 170, x + 8, H - 154], fill=ACCENT if i <= n else (210, 205, 200))
    d.text((W // 2, H - 110), 'Acne Medicine Johannesburg', font=font(34), fill=SOFT, anchor='ma')
    im.save(path)


def main(spec_path, out):
    s = json.load(open(spec_path))
    m = os.path.expanduser('~/.cache/kokoro')
    k = Kokoro(f'{m}/kokoro.onnx', f'{m}/voices.bin')
    with tempfile.TemporaryDirectory() as td:
        parts = []
        for i, sc in enumerate(s['scenes']):
            a, sr = k.create(sc['say'], voice=s.get('voice', 'af_heart'), speed=1.0, lang='en-us')
            pad = np.zeros(int(sr * 0.45), dtype=a.dtype)
            sf.write(f'{td}/{i}.wav', np.concatenate([pad, a, pad]), sr)
            card(sc['head'], sc.get('sub', ''), i, len(s['scenes']), f'{td}/{i}.png')
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-loop', '1', '-i', f'{td}/{i}.png', '-i', f'{td}/{i}.wav',
                            '-c:v', 'libx264', '-preset', 'veryfast', '-tune', 'stillimage', '-pix_fmt', 'yuv420p', '-r', '30',
                            '-c:a', 'aac', '-b:a', '160k', '-ar', '48000', '-shortest', f'{td}/{i}.mp4'], check=True)
            parts.append(f"file '{td}/{i}.mp4'")
        open(f'{td}/list.txt', 'w').write('\n'.join(parts))
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', f'{td}/list.txt',
                        '-c', 'copy', '-movflags', '+faststart', out], check=True)
    print(out)


if __name__ == '__main__':
    main(*sys.argv[1:3])
