"""Song 3 "Marina Embers" (drums: wuss-dance-drums + drums-deep-house-124, tops house-drum-loop) - hand-written rework of the Jerro-inspired track (Sello's library: Jerro "Lido", public data 121 BPM,
D# minor, Progressive House; Jerro's style = emotional melodic progressive house, plucky hooks, rolling bass, big
piano breakdowns). Only tempo, key and genre are borrowed; progression, hook, bass and arrangement are original.

    python3 mirage/loopkit/song_lido.py --out /home/claude/songs/lido
"""
import argparse, glob, os, sys
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parts as P  # noqa: E402
SR = P.SR

BPM = 121
# B(add9) | C#(add9) | D#m7 | A#m7 | B(add9) | C#(add9) | G#m7 | A#7   (VI-VII-i-v ... iv-V: the A#7's D natural pulls home)
CHORDS = [[54, 59, 61, 63], [56, 61, 63, 65], [58, 61, 63, 66], [56, 58, 61, 65],
          [54, 59, 61, 63], [56, 61, 63, 65], [54, 56, 59, 63], [56, 58, 62, 65]]
ROOTS = [35, 37, 39, 34, 35, 37, 32, 34]                 # B1 C#2 D#2 A#1 B1 C#2 G#1 A#1
COMP = [(0.0, 1.9, 84), (2.5, 1.4, 74)]                  # sustained piano pulses (the sidechain makes them breathe)
# rolling progressive bass: offbeat 16th pairs, octave on the second of each pair
BASS = [(0.5, .2, 0, 100), (0.75, .18, 12, 78), (1.5, .2, 0, 98), (1.75, .18, 12, 76),
        (2.5, .2, 0, 100), (2.75, .18, 12, 78), (3.5, .2, 0, 98), (3.75, .18, 7, 80)]
Gs4, As4, B4, Cs5, D5, Ds5, F5, Fs5, Gs5, As5 = 68, 70, 71, 73, 74, 75, 77, 78, 80, 82
HOOK = [
    [(0.0, .5, Fs5, 96), (0.75, .25, Ds5, 78), (1.0, .5, Cs5, 86), (1.5, .5, Ds5, 88), (2.25, .5, Fs5, 92), (3.0, .5, Gs5, 98), (3.5, .5, Fs5, 86)],
    [(0.0, .75, F5, 94), (0.75, .25, Ds5, 78), (1.0, 1.0, Cs5, 88), (2.5, .5, Gs4, 80), (3.0, .5, Cs5, 84), (3.5, .5, Ds5, 88)],
    [(0.0, .5, Fs5, 96), (0.75, .25, Ds5, 78), (1.0, .5, Cs5, 86), (1.5, .5, Ds5, 88), (2.25, .5, As5, 100), (3.0, .5, Gs5, 92), (3.5, .5, Fs5, 86)],
    [(0.0, 1.5, F5, 94), (2.0, .5, Cs5, 82), (2.5, .5, Ds5, 86), (3.0, 1.0, F5, 92)],
    [(0.0, .5, Fs5, 96), (0.75, .25, Ds5, 78), (1.0, .5, Cs5, 86), (1.5, .5, Ds5, 88), (2.25, .5, Fs5, 92), (3.0, .5, Gs5, 98), (3.5, .5, Fs5, 86)],
    [(0.0, .75, F5, 94), (0.75, .25, Ds5, 78), (1.0, 1.0, Cs5, 88), (2.5, .5, Gs4, 80), (3.0, .5, Cs5, 84), (3.5, .5, Ds5, 88)],
    [(0.0, .5, Ds5, 92), (0.75, .25, B4, 76), (1.0, .5, Ds5, 86), (1.5, .5, Fs5, 90), (2.25, .5, Gs5, 96), (3.0, .5, Fs5, 88), (3.5, .5, Ds5, 84)],
    [(0.0, 1.0, D5, 92), (1.0, .5, F5, 88), (1.5, .5, Gs5, 94), (2.0, 1.0, F5, 90), (3.0, 1.0, D5, 86)],
]


def ev_chords():
    return [(b * 4 + bt + i * .006, ln, k, v - 6 * (i == 0)) for b in range(8) for (bt, ln, v) in COMP for i, k in enumerate(CHORDS[b])]


def ev_bass():
    return [(b * 4 + bt, ln, ROOTS[b] + iv, v) for b in range(8) for (bt, ln, iv, v) in BASS]


def ev_hook(shift=0, dv=0):
    return [(b * 4 + bt, ln, k + shift, v + dv) for b in range(8) for (bt, ln, k, v) in HOOK[b]]


def ev_strings():
    return [(b * 4, 4.0, k + 12, 48) for b in range(8) for k in CHORDS[b][1:]]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='/home/claude/songs/lido'); ap.add_argument('--drums', default='/home/claude/loops/drums')
    a = ap.parse_args(); tag = f'{BPM}bpm_D#m_studio'
    def nrm(y): return y / max(1e-6, np.abs(y).max())
    def save(cat, name, y):
        os.makedirs(os.path.join(a.out, cat), exist_ok=True)
        f = os.path.join(a.out, cat, f'{cat}_{tag}_{name}.wav'); sf.write(f, nrm(y) * .9, SR, subtype='PCM_24'); print(f)
    save('keys', 'piano', P.render(BPM, ev_chords(), 'piano_steinway', release=.7, seed=11))
    save('bass', 'upright', P.render(BPM, ev_bass(), 'upright_bass', release=.15, seed=12, humanize_ms=3))
    pz = P.render(BPM, ev_hook(), 'violin_pizz', release=.4, seed=13, humanize_ms=4)       # plucked hook
    hp = P.render(BPM, ev_hook(dv=-8), 'harp', release=.6, seed=14, humanize_ms=4)          # harp body under the pizz
    pn = P.render(BPM, ev_hook(12, -20), 'piano_steinway', release=.5, seed=15)             # high piano sparkle
    save('melody', 'pizz_harp', nrm(pz) + .6 * nrm(hp) + .22 * nrm(pn))
    save('pad', 'strings', P.render(BPM, ev_strings(), 'string_section', release=.9, seed=16, humanize_ms=0))
    os.makedirs(os.path.join(a.out, 'drums'), exist_ok=True)
    for f in glob.glob(os.path.join(a.drums, '*.wav')) + glob.glob(os.path.join(a.drums, '*.csv')):
        d = os.path.join(a.out, 'drums', os.path.basename(f))
        if not os.path.exists(d): os.symlink(f, d)


if __name__ == '__main__':
    main()
