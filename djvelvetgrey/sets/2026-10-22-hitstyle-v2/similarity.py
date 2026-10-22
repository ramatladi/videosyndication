"""Pairwise difference check of the 10 songs (audio + composition), with within-song baselines."""
import json, glob, itertools, numpy as np, librosa
import sys; sys.path.insert(0, '/home/claude/videosyndication/djvelvetgrey/v2'); import compose as C
F = sorted(glob.glob('/tmp/vox2/final/[0-9][0-9].delivery.wav')); SR = 22050
feat = []
for f in F:
    n = f.split('/')[-1][:2]; m = json.load(open(f'/tmp/vox2/final/{n}.meta.json'))
    y, _ = librosa.load(f, sr=SR, mono=True)
    mf = librosa.feature.mfcc(y=y, sr=SR, n_mfcc=20); tim = np.concatenate([mf.mean(1), mf.std(1)])
    tempo, beats = librosa.beat.beat_track(y=y, sr=SR, bpm=m['bpm'], tightness=400)
    ch = librosa.feature.chroma_cqt(y=y, sr=SR, hop_length=512); bc = librosa.util.sync(ch, beats, aggregate=np.median)
    bc = bc / (np.linalg.norm(bc, axis=0, keepdims=True) + 1e-9)
    secs = m['sections']; bar = 240 / m['bpm']
    feat.append(dict(n=n, title=m['title'], tim=tim, bc=bc, beats=librosa.frames_to_time(beats, sr=SR), secs=secs, bar=bar,
                     motif=C.motif_repr(C.hook_from_spec(m['brief'], m['brief']['motif'])[1]['call']), prog=m['brief']['progression'],
                     y=y, vocal_srcs={v['src'] for v in m['vocals']['tuning'].values()}))
T = np.array([f['tim'] for f in feat]); mu, sd = T.mean(0), T.std(0) + 1e-9; Z = (T - mu) / sd
def cos(a, b): return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))
def win(f, s0, nbeats=32):
    i = np.searchsorted(f['beats'], s0); return f['bc'][:, i:i + nbeats]
def harm(a, b):
    """best transposition-invariant match between the 16-beat chroma windows of the two songs' drops"""
    best = 0
    for sa in [s for s in a['secs'] if s['name'] in ('drop1', 'drop2', 'hook', 'groove')]:
        wa = win(a, sa['start_s'])
        for sb in [s for s in b['secs'] if s['name'] in ('drop1', 'drop2', 'hook', 'groove')]:
            wb = win(b, sb['start_s']); k = min(wa.shape[1], wb.shape[1])
            if k < 8: continue
            for sh in range(12): best = max(best, float((wa[:, :k] * np.roll(wb[:, :k], sh, axis=0)).sum(0).mean()))
    return best
def within(a):
    d = [s for s in a['secs'] if s['name'] in ('drop1', 'drop2')]
    if len(d) < 2: d = [s for s in a['secs'] if s['name'] in ('drop1', 'drop2', 'hook', 'groove')][:2]
    wa, wb = win(a, d[0]['start_s']), win(a, d[1]['start_s']); k = min(wa.shape[1], wb.shape[1])
    return float((wa[:, :k] * wb[:, :k]).sum(0).mean())
rows = []
for a, b in itertools.combinations(range(len(feat)), 2):
    A, B = feat[a], feat[b]
    rows.append((A['title'], B['title'], round(cos(Z[a], Z[b]), 2), round(harm(A, B), 3), round(C.similarity_distance(A['motif'], B['motif']), 2),
                 A['prog'] == B['prog'], sorted(A['vocal_srcs'] & B['vocal_srcs'])))
base = [round(within(f), 3) for f in feat]
print('within-song chroma match (same song, drop 1 vs drop 2):', base, 'mean', round(np.mean(base), 3))
rows.sort(key=lambda r: -r[3])
print('closest pairs by harmony (chroma match):')
for r in rows[:6]: print('  ', r)
print('closest pairs by timbre (MFCC cosine):')
for r in sorted(rows, key=lambda r: -r[2])[:5]: print('  ', r)
print('min hook distance', min(r[4] for r in rows), '| shared progression pairs', sum(r[5] for r in rows), '| pairs sharing a voice', sum(bool(r[6]) for r in rows))
json.dump({'within': base, 'pairs': rows}, open('/tmp/vox2/similarity.json', 'w'), indent=1, default=str)
