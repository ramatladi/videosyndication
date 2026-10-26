"""Reframe a landscape photo to 16:9 so the face sits clear of the brand pill (top ~20%) and the equalizer/title (below
~62%): adds `--extend-top` px of sky (each column's top colour, smoothed, with the photo's own vertical sky gradient and
grain) above the photo, then crops 16:9 from the top. Use only when the photo's top edge is plain sky/background.

    python3 mirage/reframe.py in.jpg out.jpg --extend-top 150
"""
import argparse
import numpy as np
from PIL import Image
from scipy.ndimage import uniform_filter1d

ap = argparse.ArgumentParser(); ap.add_argument('src'); ap.add_argument('dst'); ap.add_argument('--extend-top', type=int, default=150)
a = ap.parse_args()
x = np.asarray(Image.open(a.src).convert('RGB')).astype(float); H, W, _ = x.shape; E = a.extend_top
row = uniform_filter1d(x[:12].mean(0), max(3, W // 8 | 1), axis=0)
g = (x[0].mean() - x[min(120, H - 1)].mean()) / 120
top = np.stack([row + g * (E - i) for i in range(E)]) + np.random.default_rng(0).normal(0, 1.6, (E, W, 3))
c = np.concatenate([top, x], 0)
Image.fromarray(np.clip(c, 0, 255).astype('uint8')).crop((0, 0, W, int(W * 9 / 16))).save(a.dst, quality=92)
print(a.dst)
