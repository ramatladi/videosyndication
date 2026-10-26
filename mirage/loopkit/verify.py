"""Verify a Looperman loop library before use (Sello, 26 Oct 2026: "use Looperman where completeness and accuracy are
met, use other sources as a fallback").

completeness: the file decodes, is bar-exact at its labelled tempo (whole number of 4/4 bars, within 0.08 beat) and
              not silent;
accuracy:     tonal loops (bass, keys, melody, pad, vocals) get their key from the audio (chroma vs Krumhansl key
              profiles). The uploader's label is kept when the audio agrees (same key or relative major/minor);
              otherwise the audio estimate is used if it is confident (r >= 0.75; bass r >= 0.8), else the loop is
              set aside as unverified. Drum loops need no key.
Verified loops are renamed to <cat>_<bpm>bpm_<key>_... so the arranger key-matches on the verified key; the rest
move to <lib>/_unverified/. A report is written to <lib>/verify.json.

    python3 mirage/loopkit/verify.py /home/claude/loops
"""
import glob, json, os, shutil, sys
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arrange as A  # noqa: E402

N = 'C C# D D# E F F# G G# A A# B'.split()
MAJ = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MIN = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
TONAL = ('bass', 'keys', 'melody', 'pad', 'vocals')


def estimate(path):
    import librosa
    y, sr = librosa.load(path, sr=22050, mono=True)
    c = librosa.feature.chroma_cqt(y=y, sr=sr).mean(1)
    cands = [(float(np.corrcoef(np.roll(P, k), c)[0, 1]), k, m) for k in range(12) for P, m in ((MAJ, 'major'), (MIN, 'minor'))]
    return max(cands)


def same(a, b):
    if a == b: return True
    (pa, ma), (pb, mb) = a, b
    if ma == mb: return False
    rel = (pa + (3 if ma == 'minor' else -3)) % 12
    return rel == pb


def keyname(k): return N[k[0]] + ('m' if k[1] == 'minor' else '')


def main(lib):
    rep = []; un = os.path.join(lib, '_unverified'); os.makedirs(un, exist_ok=True)
    for f in sorted(glob.glob(os.path.join(lib, '*', '*.wav'))):
        if '/_unverified/' in f: continue
        b = os.path.basename(f); parts = b.split('_'); cat = parts[0]
        r = {'file': b, 'cat': cat}
        try:
            info = sf.info(f); bpm = float(parts[1].replace('bpm', ''))
            beats = info.frames / info.samplerate * bpm / 60; nb = round(beats)
            x, _ = sf.read(f, always_2d=True, dtype='float32')
            r['bars'] = nb / 4
            if abs(beats - nb) > .08 or nb % 4: r['fail'] = f'not bar-exact ({beats:.2f} beats)'
            elif np.abs(x).max() < 1e-3: r['fail'] = 'silent'
        except Exception as e:
            r['fail'] = f'unreadable: {e}'
        if 'fail' not in r and cat in TONAL:
            lab = A.parse_key(parts[2]) if parts[2] != 'nokey' else None
            rr, k, m = estimate(f); est = (k, m); r.update(label=keyname(lab) if lab else None, estimate=keyname(est), r=round(rr, 2))
            thr = .8 if cat == 'bass' else .75
            if lab and same(lab, est): r['key'] = keyname(lab); r['basis'] = 'label confirmed by audio'
            elif rr >= thr: r['key'] = keyname(est); r['basis'] = 'audio estimate (label wrong or missing)'
            else: r['fail'] = 'key not verifiable'
        if 'fail' in r:
            shutil.move(f, os.path.join(un, b))
        elif cat in TONAL and r['key'] != parts[2]:
            parts[2] = r['key']; nf = os.path.join(os.path.dirname(f), '_'.join(parts)); os.rename(f, nf); r['renamed'] = os.path.basename(nf)
        rep.append(r)
    json.dump(rep, open(os.path.join(lib, 'verify.json'), 'w'), indent=1)
    ok = [r for r in rep if 'fail' not in r]
    print(f'{len(ok)}/{len(rep)} loops verified;', {c: sum(1 for r in ok if r["cat"] == c) for c in sorted({r["cat"] for r in rep})})
    for r in rep:
        if 'fail' in r: print('  set aside:', r['file'][:70], '-', r['fail'])


if __name__ == '__main__':
    main(sys.argv[1])
