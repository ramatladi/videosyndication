"""Choose a harmonically compatible set of verified Looperman loops for the next song (Looperman first, Sello 26 Oct).

Works from the committed index (mirage/loops/index.json: Drive id, verified key, per-bar chroma) so a scheduled run can
decide what it needs before downloading anything.

    python3 mirage/loopkit/pick.py --style deep [--seed 3] [--avoid-keys Em,Dm]
-> JSON: target key + bpm, the chosen loops (role, Drive id, shift), the keys loop's chord tones per bar (to write the
   hand-written fallback parts: bass/pad/keys that no verified loop covers), or {"none": reason} when no set qualifies
   (then the whole song is written by hand).

Rules: every tonal loop is shifted at most 3 semitones and stretched at most 8%; keys + melody must not clash (no
strong note a semitone from the other loop's 4 strongest notes in any bar); extra layers (melody2, pad, vocals, bass) are added only if they
clash with neither; a melody loop is not reused within 30 songs and a keys+melody pair never (mirage/songs/*.json).
"""
import argparse, glob, json, os, random, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(os.path.dirname(HERE))
INDEX = os.path.join(REPO, 'mirage', 'loops', 'index.json'); SONGS = os.path.join(REPO, 'mirage', 'songs')
N = 'C C# D D# E F F# G G# A A# B'.split()
BPM = {'tropical': (100, 112), 'trance': (132, 140), 'futurebass': (140, 150), 'nudisco': (112, 124), 'disco': (112, 124),
       'deep': (118, 124), 'melodic': (118, 124), 'afro': (118, 123), 'progressive': (120, 126), 'tech': (124, 127)}


def pk(k):
    m = k.endswith('m'); r = k[:-1] if m else k
    return N.index(r), 'minor' if m else 'major'


def shift(lab, key):
    if lab[1] != key[1]:
        rel = (lab[0] + (3 if lab[1] == 'minor' else -3)) % 12
        return ((key[0] - rel + 6) % 12) - 6
    return ((key[0] - lab[0] + 6) % 12) - 6


def bars(e, d): return [np.roll(np.array(b), d) for b in e['bar_chroma']]


def compat(a, b):
    L = int(np.lcm(len(a), len(b))); A_ = [a[i % len(a)] for i in range(L)]; B_ = [b[i % len(b)] for i in range(L)]
    cos = float(np.mean([x @ y / (np.linalg.norm(x) * np.linalg.norm(y) + 1e-9) for x, y in zip(A_, B_)]))
    # strict: a strong note (top 3) of either loop a semitone from any of the other's top 4 notes counts as a clash
    cl = sum(1 for x, y in zip(A_, B_) for s1, s2 in ((x, y), (y, x)) for p in np.argsort(s1)[-3:] for q in np.argsort(s2)[-4:]
             if (p - q) % 12 in (1, 11)) / (2 * L)
    return cos, cl


def history():
    specs = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(SONGS, '*.json')))]
    recent_mel = {s['loops'].get(r) for s in specs[-30:] if s.get('loops') for r in ('melody', 'melody2')} - {None}
    pairs = {(s['loops'].get('keys'), s['loops'].get('melody')) for s in specs if s.get('loops')}
    recent_keys = [s['key'] for s in specs[-4:]]
    recent_keys_loops = {s['loops'].get('keys') for s in specs[-4:] if s.get('loops')}
    used_drums = [s['loops'].get(r) for s in specs[-6:] if s.get('loops') for r in ('drums_main', 'drums_alt', 'drums_tops')]
    return recent_mel, pairs, recent_keys, used_drums, recent_keys_loops


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--style', required=True); ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--avoid-keys', default='')
    a = ap.parse_args(); rng = random.Random(a.seed)
    idx = json.load(open(INDEX))['loops']; lo, hi = BPM.get(a.style, (118, 126))
    recent_mel, pairs, recent_keys, used_drums, recent_keys_loops = history()
    avoid = set(filter(None, a.avoid_keys.split(','))) | set(recent_keys)
    tonal = [e for e in idx if e['cat'] != 'drums' and e['key'] and e.get('bar_chroma')]
    ok_tempo = lambda e, t: abs(e['bpm'] / t - 1) <= .08
    best = []
    for kname in [n + q for n in N for q in ('', 'm')]:
        if kname in avoid: continue
        key = pk(kname)
        for t in range(lo, hi + 1):
            pool = [(e, shift(pk(e['key']), key)) for e in tonal if ok_tempo(e, t)]
            pool = [(e, d) for e, d in pool if abs(d) <= 3]
            K = [p for p in pool if p[0]['cat'] == 'keys' and p[0]['looperman_id'] not in recent_keys_loops]; M = [p for p in pool if p[0]['cat'] == 'melody' and p[0]['looperman_id'] not in recent_mel]
            for (ke, kd) in K:
                for (me, md) in M:
                    if (ke['looperman_id'], me['looperman_id']) in pairs: continue
                    cos, cl = compat(bars(ke, kd), bars(me, md))
                    if cl <= .25: best.append((cl, -cos, abs(kd) + abs(md), kname, t, ke, kd, me, md, pool))
    if not best:
        print(json.dumps({'none': f'no clash-free keys+melody pair for {a.style} ({lo}-{hi} BPM) in the verified library'})); return
    best.sort(key=lambda b: b[:3]); top = best[:max(1, min(5, len(best)))]
    cl, ncos, _, kname, t, ke, kd, me, md, pool = rng.choice(top)
    chosen = {'keys': (ke, kd), 'melody': (me, md)}
    for role, cat in (('melody2', 'melody'), ('vocals', 'vocals'), ('pad', 'pad'), ('bass', 'bass')):
        cands = []
        for e, d in pool:
            if e['cat'] != cat or any(e is c[0] for c in chosen.values()): continue
            if role == 'melody2' and e['looperman_id'] in recent_mel: continue
            scores = [compat(bars(e, d), bars(c[0], c[1])) for c in chosen.values() if c[0]['cat'] != 'drums']
            if all(s[1] <= .25 for s in scores): cands.append((sum(s[1] for s in scores), -min(s[0] for s in scores), e, d))
        if cands: cands.sort(key=lambda c: c[:2]); chosen[role] = (cands[0][2], cands[0][3])
    drums = [e for e in idx if e['cat'] == 'drums' and abs(e['bpm'] / t - 1) <= .06]
    fresh = lambda pool_: sorted(pool_, key=lambda e: (e['looperman_id'] in used_drums, rng.random()))
    full = fresh([e for e in drums if e['kick'] > .18]); tops = fresh([e for e in drums if e['kick'] <= .18])
    if len(full) >= 2 and tops:
        chosen['drums_main'] = (full[0], 0); chosen['drums_alt'] = (full[1], 0); chosen['drums_tops'] = (tops[0], 0)
    kb = bars(ke, kd)
    chords = [[N[p] for p in np.argsort(b)[::-1][:4]] for b in kb]
    out = {'key': kname, 'bpm': t, 'clash': cl, 'cos': round(-ncos, 2),
           'loops': {r: {'looperman_id': e['looperman_id'], 'drive_id': e['drive_id'], 'drive_title': e['drive_title'], 'verified_key': e['key'],
                         'shift': d, 'bpm': e['bpm']} for r, (e, d) in chosen.items()},
           'keys_loop_chord_tones_per_bar': chords,
           'hand_write': [r for r in ('bass', 'pad') if r not in chosen] + ([] if 'drums_main' in chosen else ['drums'])}
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
