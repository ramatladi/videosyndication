"""DJ Velvet Grey video: one credited nature photo, slow zoom, title, live equalizer.

    python3 video.py --image photo.jpg --audio track.wav --title "Name" --style chill|deep \
                     --credit "Photo: Jane Doe / Unsplash" --out out.mp4

1080x1920 (9:16) at 24 fps, same length as the audio, sized to stay under ~27 MB.
"""
import argparse, subprocess, os, shutil, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy.io import wavfile

W, H, FPS = 1080, 1920, 24
HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, 'fonts')
STYLE_LABEL = {'chill': 'Melodic Chill House', 'deep': 'Deep House'}


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)


def cover(img, w, h):
    s = max(w / img.width, h / img.height)
    img = img.resize((int(img.width * s + .5), int(img.height * s + .5)), Image.LANCZOS)
    x, y = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


def wrap(draw, text, f, maxw):
    words, lines, cur = text.split(), [], ''
    for wd in words:
        t = (cur + ' ' + wd).strip()
        if draw.textlength(t, font=f) <= maxw: cur = t
        else: lines.append(cur); cur = wd
    lines.append(cur)
    return lines


def overlay(title, style, credit):
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    # soft dark gradients top and bottom for legibility
    grad = np.zeros((H, W, 4), np.uint8)
    y = np.arange(H)[:, None]
    a = np.clip((y - H * .52) / (H * .48), 0, 1) ** 1.3 * 190 + np.clip((H * .16 - y) / (H * .16), 0, 1) * 120
    grad[..., 3] = a.astype(np.uint8)
    ov = Image.alpha_composite(ov, Image.fromarray(grad, 'RGBA'))
    d = ImageDraw.Draw(ov)
    # brand
    fb = font('IBMPlexSans-SemiBold.ttf', 34)
    brand = '  '.join('DJ VELVET GREY')
    d.text((W / 2, 150), brand, font=fb, fill=(255, 255, 255, 235), anchor='mm')
    d.line([(W / 2 - 60, 196), (W / 2 + 60, 196)], fill=(255, 255, 255, 150), width=2)
    # title
    size = 104
    while True:
        ft = font('SourceSerif4-Bold.ttf', size)
        lines = wrap(d, title, ft, W - 160)
        if len(lines) <= 2 or size <= 70: break
        size -= 6
    lh = int(size * 1.12)
    y0 = 1430 - lh * (len(lines) - 1)
    shadow = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ds = ImageDraw.Draw(shadow)
    for i, ln in enumerate(lines):
        ds.text((W / 2, y0 + i * lh + 4), ln, font=ft, fill=(0, 0, 0, 170), anchor='mm')
    ov = Image.alpha_composite(ov, shadow.filter(ImageFilter.GaussianBlur(8)))
    d = ImageDraw.Draw(ov)
    for i, ln in enumerate(lines):
        d.text((W / 2, y0 + i * lh), ln, font=ft, fill=(255, 255, 255, 255), anchor='mm')
    fl = font('IBMPlexSans-SemiBold.ttf', 36)
    d.text((W / 2, 1430 + lh * .5 + 40), STYLE_LABEL[style], font=fl, fill=(255, 255, 255, 200), anchor='mm')
    fc = font('IBMPlexSans-SemiBold.ttf', 28)
    d.text((W / 2, H - 70), credit, font=fc, fill=(255, 255, 255, 190), anchor='mm')
    return ov, y0 - lh // 2


def bands(audio_path, nframes, nb=40):
    sr, x = wavfile.read(audio_path)
    m = x.astype(np.float32).mean(1) / 32768
    hop = sr / FPS; win = 2048
    edges = np.geomspace(40, 12000, nb + 1)
    freqs = np.fft.rfftfreq(win, 1 / sr)
    idx = [(np.searchsorted(freqs, edges[i]), max(np.searchsorted(freqs, edges[i + 1]), np.searchsorted(freqs, edges[i]) + 1)) for i in range(nb)]
    hann = np.hanning(win)
    out = np.zeros((nframes, nb))
    for f in range(nframes):
        c = int(f * hop)
        seg = m[max(0, c - win // 2):c + win // 2]
        if len(seg) < win: seg = np.pad(seg, (0, win - len(seg)))
        sp = np.abs(np.fft.rfft(seg * hann))
        out[f] = [sp[a:b].mean() for a, b in idx]
    out = np.log10(out + 1e-4)
    lo, hi = np.percentile(out, 25, axis=0), np.percentile(out, 99.5, axis=0)
    out = np.clip((out - lo) / (hi - lo + 1e-9), 0, 1) ** 1.7
    for f in range(1, nframes):  # fast attack, slow release
        out[f] = np.maximum(out[f], out[f - 1] * 0.82)
    return out


def main():
    ap = argparse.ArgumentParser()
    for k in ('image', 'audio', 'title', 'style', 'credit', 'out'): ap.add_argument('--' + k, required=True)
    a = ap.parse_args()
    sr, x = wavfile.read(a.audio)
    dur = len(x) / sr
    nframes = int(round(dur * FPS))
    work = a.out + '.work'; os.makedirs(work, exist_ok=True)
    # 2x-resolution background keeps the slow zoom smooth (half-pixel steps)
    big = cover(Image.open(a.image).convert('RGB'), W * 2, H * 2)
    big = big.filter(ImageFilter.UnsharpMask(radius=3, percent=35, threshold=3))
    big.save(os.path.join(work, 'bg.png'))
    ov, title_top = overlay(a.title, a.style, a.credit)
    ov.save(os.path.join(work, 'ov.png'))
    bd = bands(a.audio, nframes)
    nb = bd.shape[1]; bar_w, gap, BHt = 14, 8, 110
    BWt = nb * bar_w + (nb - 1) * gap
    dx, dy = np.random.default_rng(len(a.title)).uniform(-1, 1, 2)
    z = f"(1+0.12*(0.5-0.5*cos(PI*on/{nframes})))"
    xs = f"(iw-iw/zoom)/2+{dx:.3f}*(iw-iw/zoom)/2*on/{nframes}"
    ys = f"(ih-ih/zoom)/2+{dy:.3f}*(ih-ih/zoom)/2*on/{nframes}"
    fc = (f"[0:v]zoompan=z='{z}':x='{xs}':y='{ys}':d=1:s={W}x{H}:fps={FPS},format=rgba[bg];"
          f"[bg][1:v]overlay=0:0:format=auto[a];"
          f"[a][2:v]overlay=x={(W - BWt) // 2}:y={title_top - 40 - BHt}:format=auto[b];"
          f"[b]fade=t=in:st=0:d=1,fade=t=out:st={dur - 2:.3f}:d=2,format=yuv420p[v]")
    cmd = ['ffmpeg', '-y', '-v', 'error',
           '-loop', '1', '-framerate', str(FPS), '-t', f'{dur:.3f}', '-i', os.path.join(work, 'bg.png'),
           '-loop', '1', '-framerate', str(FPS), '-t', f'{dur:.3f}', '-i', os.path.join(work, 'ov.png'),
           '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{BWt}x{BHt}', '-r', str(FPS), '-i', 'pipe:0',
           '-i', a.audio, '-filter_complex', fc, '-map', '[v]', '-map', '3:a',
           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-maxrate', '1000k', '-bufsize', '2000k',
           '-c:a', 'aac', '-b:a', '192k', '-t', f'{dur:.3f}', '-movflags', '+faststart', a.out]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(nframes):
        im = Image.new('RGBA', (BWt, BHt), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        for i in range(nb):
            h = 6 + bd[f, i] * (BHt - 14)
            xx = i * (bar_w + gap)
            d.rounded_rectangle([xx, BHt / 2 - h / 2, xx + bar_w - 1, BHt / 2 + h / 2], radius=7, fill=(255, 255, 255, 205))
        try: enc.stdin.write(im.tobytes())
        except BrokenPipeError: break
    enc.stdin.close()
    if enc.wait() != 0: raise SystemExit('ffmpeg failed')
    shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    main()
