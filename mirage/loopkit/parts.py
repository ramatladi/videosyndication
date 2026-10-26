"""Hand-written musical parts (chords, bass, hook, pad) rendered on the CC0 studio pack's real recordings
(Steinway grand, upright bass, string sections) as bar-exact loops the arranger can use next to the Looperman drums.

The parts are written out note by note like a producer would (no random melody): a classic deep-house i-VI-III-VII
progression with smooth voice leading, a syncopated chord comp, a walking-but-locked upright bass and a singable
two-bar hook that answers itself and resolves on bar 8.

    python3 mirage/loopkit/parts.py --out /home/claude/loops --bpm 122
"""
import argparse, os, sys
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'djvelvetgrey', 'v2'))
import studio as ST  # noqa: E402

SR = 44100
# A minor: Am9 | Fmaj9 | Cmaj9 | G6  (x2)    voicings move by step (common tones held)
CHORDS = [[57, 60, 64, 67, 71], [57, 60, 64, 65, 67], [55, 59, 60, 64, 67], [55, 59, 62, 64, 67]]   # A C E G B | A C E F G | G B C E G | G B D E G
ROOTS = [33, 29, 36, 31]                       # A1 F1 C2 G1
# chord comp: (beat, length, velocity) - offbeat-pushed deep-house stabs
COMP = [(0.0, .45, 92), (0.75, .3, 70), (1.5, .45, 84), (2.5, .35, 76), (3.25, .6, 88)]
# bass: (beat, length, interval from root, velocity)
BASS = [(0.0, .45, 0, 104), (0.75, .2, 12, 72), (1.5, .4, 0, 96), (2.5, .3, 7, 84), (3.0, .4, 12, 80), (3.5, .45, 7, 88)]
BASS_VARY = {3: [(0.0, .45, 0, 104), (0.75, .2, 12, 72), (1.5, .4, 0, 96), (2.5, .25, 5, 84), (3.0, .25, 4, 84), (3.5, .45, 2, 92)]}  # bar 4: walk-up to A
# hook: per bar (beat, length, midi, velocity); bars 1-4 call, 5-8 answer + resolve
E5, D5, C5, B4, A4, G5, G4 = 76, 74, 72, 71, 69, 79, 67
HOOK = [
    [(0.5, .45, E5, 96), (1.0, .45, D5, 82), (1.5, .45, C5, 88), (2.0, 1.0, D5, 94), (3.5, .45, E5, 86)],
    [(0.0, 1.4, C5, 92), (2.0, .45, A4, 78), (2.5, .45, C5, 84), (3.0, .9, D5, 90)],
    [(0.5, .45, E5, 96), (1.0, .45, D5, 82), (1.5, .45, C5, 88), (2.0, 1.0, G5, 100), (3.5, .45, E5, 86)],
    [(0.0, 1.4, D5, 92), (2.0, 1.8, B4, 84)],
    [(0.5, .45, E5, 96), (1.0, .45, D5, 82), (1.5, .45, C5, 88), (2.0, 1.0, D5, 94), (3.5, .45, E5, 86)],
    [(0.0, 1.4, C5, 92), (2.0, .45, A4, 78), (2.5, .45, C5, 84), (3.0, .9, E5, 92)],
    [(0.5, .45, G5, 98), (1.0, .45, E5, 86), (1.5, .45, D5, 88), (2.0, 1.0, C5, 94), (3.5, .45, D5, 86)],
    [(0.0, .45, D5, 90), (0.5, .45, E5, 92), (1.0, 2.6, A4, 88)],
]


def render(bpm, events, inst, bars=8, release=.6, seed=0, swing=0.0, humanize_ms=6):
    rng = np.random.default_rng(seed)
    beat = 60 / bpm; N = int(round(bars * 4 * beat * SR)); out = np.zeros((N + SR * 4, 2), np.float32)
    for (t, dur, key, vel) in events:
        sw = swing * beat if abs((t % 1) - .5) < 1e-6 else 0           # swing offbeat 8ths slightly late
        p = int((t * beat + sw + rng.normal(0, humanize_ms / 1000)) * SR); p = max(0, p)
        y = ST.render(inst, key, dur * beat, int(np.clip(vel + rng.integers(-3, 4), 1, 127)), release)
        out[p:p + len(y)] += y[: len(out) - p]
    tail = out[N:].copy(); out = out[:N]; out[: len(tail)] += tail[: N]     # wrap the ring-out into the loop start
    return out


def chords_events():
    ev = []
    for b in range(8):
        c = CHORDS[b % 4]
        for (bt, ln, v) in COMP:
            for i, k in enumerate(c): ev.append((b * 4 + bt + i * .006, ln, k, v - 6 * (i == 0)))   # tiny roll, softer bottom
    return ev


def bass_events():
    ev = []
    for b in range(8):
        pat = BASS_VARY.get(b % 4, BASS) if b == 7 else BASS
        for (bt, ln, iv, v) in pat: ev.append((b * 4 + bt, ln, ROOTS[b % 4] + iv, v))
    return ev


def hook_events():
    return [(b * 4 + bt, ln, k, v) for b in range(8) for (bt, ln, k, v) in HOOK[b]]


def pad_events():
    return [(b * 4, 4.0, k, 52) for b in range(8) for k in CHORDS[b % 4][:4]]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='/home/claude/loops'); ap.add_argument('--bpm', type=float, default=122)
    a = ap.parse_args(); bpm = a.bpm; tag = f'{int(bpm)}bpm_Am_studio'
    jobs = [('keys', 'piano_steinway', chords_events(), .5, 1, .015), ('bass', 'upright_bass', bass_events(), .25, 2, .015),
            ('melody', 'piano_steinway', hook_events(), .9, 3, .015), ('pad', 'string_section', pad_events(), .8, 4, 0)]
    for cat, inst, ev, rel, seed, sw in jobs:
        y = render(bpm, ev, inst, release=rel, seed=seed, swing=sw)
        if cat == 'melody':                                                 # hook doubled an octave up, quietly, for shine
            y = y + .28 * render(bpm, [(t, d, k + 12, v - 10) for t, d, k, v in ev], 'piano_steinway', release=rel, seed=5, swing=sw)
        os.makedirs(os.path.join(a.out, cat), exist_ok=True)
        f = os.path.join(a.out, cat, f'{cat}_{tag}_{inst}.wav')
        sf.write(f, y / max(1e-6, np.abs(y).max()) * .9, SR, subtype='PCM_24'); print(f)


if __name__ == '__main__':
    main()
