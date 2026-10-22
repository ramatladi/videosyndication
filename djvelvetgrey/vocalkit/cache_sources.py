"""Pre-compute pitch analysis for every source (same format vocalize.py reads) + loop grid fit: python3 -I cache_sources.py"""
import os, glob, json, numpy as np, librosa
import sys
SR = 44100; SRC = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/dvg-vocals/src'; CACHE = '/home/claude/dvg-vocals/cache'
for p in sorted(glob.glob(SRC + '/*.mp3')):
    name = os.path.basename(p); cf = os.path.join(CACHE, name + '.json')
    if os.path.exists(cf): continue
    y, _ = librosa.load(p, sr=SR, mono=True); y = y / (np.abs(y).max() + 1e-9) * .8
    f0, v, _ = librosa.pyin(y, fmin=70, fmax=1100, sr=SR, frame_length=2048)
    f = f0[v & ~np.isnan(f0)]
    a = {'dur': len(y) / SR, 'voiced': float(v.mean()), 'n_voiced': int(len(f))}
    if len(f) >= 20:
        midi = librosa.hz_to_midi(f); cents = float(np.median(midi - np.round(midi)))
        a.update(cents=cents, hist=np.bincount(np.round(midi - cents).astype(int) % 12, minlength=12).tolist(), times=None)
    env = librosa.onset.onset_strength(y=y, sr=SR, hop_length=128); t = librosa.times_like(env, sr=SR, hop_length=128)
    best = (0, 0, 0)
    for bpm in np.arange(100, 176, .25):
        six = 60 / bpm / 4
        for off in np.arange(0, six, .004):
            sc = float((env * np.cos(2 * np.pi * (((t - off) % six) / six))).sum() / env.sum())
            if sc > best[0]: best = (sc, float(bpm), float(off))
    a['grid'] = {'score': round(best[0], 3), 'bpm': best[1], 'phase': round(best[2], 3)}
    json.dump(a, open(cf, 'w')); print(name, round(a['dur'], 1), 'voiced', round(a['voiced'], 2), 'grid', a['grid'])
