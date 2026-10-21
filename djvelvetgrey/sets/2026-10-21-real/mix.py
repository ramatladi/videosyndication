import json, glob, subprocess, numpy as np, pyloudnorm as pyln
from scipy.io import wavfile
import sys; sys.path.insert(0, '/home/claude/videosyndication/djvelvetgrey/v2')
import engine as E
SR = 44100; XF = 14.0
files = sorted(glob.glob('/tmp/set/[0-9][0-9].wav'))
meter = pyln.Meter(SR); tracks = []; rows = []
for f in files:
    sr, x = wavfile.read(f); x = x.astype(np.float32) / 32768
    m = json.load(open(f[:-4] + '.json'))
    lufs = meter.integrated_loudness(x); pk = 20 * np.log10(np.abs(x).max())
    # longest near-silent stretch inside the track (excluding the last 10 s fade)
    env = np.abs(x[:-10 * SR]).max(1); w = SR // 10
    blk = env[:len(env) // w * w].reshape(-1, w).max(1); quiet = (blk < 1e-3).astype(int)
    run = mx = 0
    for q in quiet: run = run + 1 if q else 0; mx = max(mx, run)
    rows.append((m['title'], m['style'], m['bpm'], m['key'], round(lufs, 2), round(pk, 2), mx / 10, m['palette']))
    tracks.append(x)
for r in rows: print(r[:7])
# continuous set: equal-power crossfades of XF seconds; every track normalised to the same loudness first
target = min(meter.integrated_loudness(x) for x in tracks); out = None; starts = []; n = int(XF * SR)
for x in tracks:
    x = (x * 10 ** ((target - meter.integrated_loudness(x)) / 20)).astype(np.float32)   # gain <= 0: no limiter needed
    if out is None: out = x; starts.append(0.0); continue
    a = np.cos(np.linspace(0, np.pi / 2, n, dtype=np.float32))[:, None]; b = np.sin(np.linspace(0, np.pi / 2, n, dtype=np.float32))[:, None]
    starts.append((len(out) - n) / SR)
    out = np.concatenate([out[:-n], out[-n:] * a + x[:n] * b, x[n:]])
pk = np.abs(out).max(); y = out * min(1.0, 0.79 / pk); ach = round(target, 2)
wavfile.write('/tmp/set/set.wav', SR, (np.clip(y, -1, 1) * 32767).astype(np.int16))
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', '/tmp/set/set.wav', '-b:a', '320k', '-metadata', 'title=Real Instruments Set',
                '-metadata', 'artist=DJ Velvet Grey', '/tmp/set/DJ Velvet Grey - Real Instruments Set.mp3'], check=True)
tl = [f"{int(s // 60):02d}:{int(s % 60):02d}  {r[0]} - {r[1]}, {r[3]}, {r[2]} BPM" for s, r in zip(starts, rows)]
open('/tmp/set/tracklist.txt', 'w').write('DJ Velvet Grey - Real Instruments Set (recorded instruments only)\n\n' + '\n'.join(tl) + '\n')
print('\n'.join(tl)); print('set length', round(len(y) / SR / 60, 1), 'min; LUFS', ach, 'peak dBFS', round(20 * np.log10(np.abs(y).max()), 2))
json.dump([{'title': r[0], 'style': r[1], 'bpm': r[2], 'key': r[3], 'palette': r[7]} for r in rows], open('/tmp/set/palettes.json', 'w'), indent=1)
