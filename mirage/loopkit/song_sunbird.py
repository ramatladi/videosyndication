"""Song 2 "Sunbird Valley" (drums: wuss-dance-drums + drums-deep-house-124, tribal perc tops) - inspired by the public data of Nora En Pure's "Come With Me" (Sello's Apple Music library):
120 BPM, F# minor, deep house; her documented signature = melodic/organic deep house, piano, strings, flute (wind),
tribal percussion with Western instruments. Only tempo, key, genre and instrumentation are borrowed; the chord
progression, hook, bass line and arrangement are original (no melody or audio of the reference is used).

    python3 mirage/loopkit/song_sunbird.py --out /home/claude/songs/sunbird
"""
import argparse, glob, os, sys
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parts as P  # noqa: E402
ST = P.ST; SR = P.SR

BPM = 120
# F#m9 | Bm9 | Dmaj9 | C#m7   (i - iv - VI - v; A and C# held as common tones)
CHORDS = [[57, 61, 64, 68], [57, 61, 62, 66], [57, 61, 64, 66], [56, 59, 61, 64]]
ROOTS = [30, 35, 38, 37]                                     # F#1 B1 D2 C#2
COMP = [(0.5, .4, 86), (1.5, .3, 72), (2.25, .45, 82), (3.5, .4, 78)]          # airy offbeat piano
BASS = [(0.0, .5, 0, 104), (1.0, .25, 12, 70), (1.5, .45, 0, 94), (2.5, .3, 7, 86), (3.0, .25, 12, 76), (3.5, .45, 7, 88)]
BASS_END = [(0.0, .5, 0, 104), (1.0, .25, 12, 70), (1.5, .45, 0, 94), (2.5, .3, -2, 86), (3.0, .3, -4, 86), (3.5, .45, -5, 92)]   # C# B A G# into F#
A5, Gs4, A4, B4, Cs5, D5, E5, Fs5 = 81, 68, 69, 71, 73, 74, 76, 78
HOOK = [   # flute: long breaths, call (bars 1-4) and answer (5-8)
    [(0.0, 1.4, Cs5, 92), (1.5, .45, E5, 84), (2.0, .95, Fs5, 98), (3.0, .45, E5, 84), (3.5, .45, Cs5, 80)],
    [(0.0, 1.9, B4, 90), (2.5, .45, A4, 76), (3.0, .45, B4, 80), (3.5, .45, Cs5, 84)],
    [(0.0, 1.4, E5, 94), (1.5, .45, Fs5, 88), (2.0, .95, A5, 102), (3.0, .95, Fs5, 90)],
    [(0.0, .95, E5, 92), (1.0, .95, Cs5, 86), (2.0, 1.9, Gs4, 82)],
    [(0.0, 1.4, Cs5, 92), (1.5, .45, E5, 84), (2.0, .95, Fs5, 98), (3.0, .45, E5, 84), (3.5, .45, Cs5, 80)],
    [(0.0, 1.9, D5, 92), (2.5, .45, Cs5, 80), (3.0, .45, B4, 80), (3.5, .45, A4, 78)],
    [(0.0, .95, A4, 86), (1.0, .45, B4, 82), (1.5, .45, Cs5, 86), (2.0, 1.4, E5, 96), (3.5, .45, Cs5, 82)],
    [(0.0, .45, B4, 86), (0.5, 3.2, Cs5, 90)],
]
# harp: rising 8th-note arpeggio through each chord (Nora-style organic pluck), two octaves up
ARP = [0, 1, 2, 3, 2, 1, 3, 2]


def ev_chords():
    return [(b * 4 + bt + i * .007, ln, k, v - 6 * (i == 0)) for b in range(8) for (bt, ln, v) in COMP for i, k in enumerate(CHORDS[b % 4])]


def ev_bass():
    return [(b * 4 + bt, ln, ROOTS[b % 4] + iv, v) for b in range(8) for (bt, ln, iv, v) in (BASS_END if b == 7 else BASS)]


def ev_hook():
    return [(b * 4 + bt, ln, k, v) for b in range(8) for (bt, ln, k, v) in HOOK[b]]


def ev_strings():
    return [(b * 4, 4.0, k, 50) for b in range(8) for k in CHORDS[b % 4]]


def ev_arp():
    return [(b * 4 + s * .5, .45, CHORDS[b % 4][ARP[s]] + 12, 70 + 8 * (s % 2 == 0)) for b in range(8) for s in range(8)]


def ev_perc():
    """tribal hand percussion (2 bars, repeated): conga/bongo call-and-response + shaker 16ths."""
    one = [('conga_lo', 0.75, 92), ('conga_hi', 1.5, 84), ('conga_hi', 1.75, 70), ('conga_lo', 2.75, 88), ('bongo_hi', 3.25, 74),
           ('bongo_lo', 3.5, 80), ('conga_hi', 4.5, 82), ('conga_lo', 5.25, 86), ('bongo_hi', 6.0, 72), ('conga_hi', 6.5, 84),
           ('conga_lo', 6.75, 90), ('bongo_lo', 7.5, 78)]
    sh = [('shaker', s * .25, 60 + 14 * (s % 2)) for s in range(32)]
    return [(i, t + r * 8, v) for r in range(4) for (i, t, v) in one + sh]


def render_perc(bpm, seed=7):
    rng = np.random.default_rng(seed); beat = 60 / bpm; N = int(round(32 * beat * SR)); out = np.zeros((N + SR * 2, 2), np.float32)
    pan = {'conga_lo': -.35, 'conga_hi': .3, 'bongo_hi': .45, 'bongo_lo': -.2, 'shaker': .15}
    for (inst, t, v) in ev_perc():
        sw = .02 * beat if abs((t % .5) - .25) < 1e-6 else 0
        p = max(0, int((t * beat + sw + rng.normal(0, .004)) * SR))
        y = ST.render(inst, 60, .3, int(np.clip(v + rng.integers(-4, 5), 1, 127)), .3)
        pl, pr = np.sqrt(.5 - pan[inst] / 2), np.sqrt(.5 + pan[inst] / 2)
        out[p:p + len(y), 0] += y[:len(out) - p, 0] * pl * 1.4; out[p:p + len(y), 1] += y[:len(out) - p, 1] * pr * 1.4
    tail = out[N:].copy(); out = out[:N]; out[:len(tail)] += tail[:N]
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='/home/claude/songs/sunbird'); ap.add_argument('--drums', default='/home/claude/loops/drums')
    a = ap.parse_args(); tag = f'{BPM}bpm_F#m_studio'
    def save(cat, name, y):
        os.makedirs(os.path.join(a.out, cat), exist_ok=True)
        f = os.path.join(a.out, cat, f'{cat}_{tag}_{name}.wav'); sf.write(f, y / max(1e-6, np.abs(y).max()) * .9, SR, subtype='PCM_24'); print(f)
    save('keys', 'piano', P.render(BPM, ev_chords(), 'piano_steinway', release=.5, seed=1, swing=.015))
    save('bass', 'upright', P.render(BPM, ev_bass(), 'upright_bass', release=.25, seed=2, swing=.015))
    fl = P.render(BPM, ev_hook(), 'flute', release=.5, seed=3, humanize_ms=8)
    pf = P.render(BPM, [(t, min(d, .5), k, v - 18) for t, d, k, v in ev_hook()], 'piano_steinway', release=.9, seed=4)   # soft piano doubling gives the flute a front edge
    save('melody', 'flute', fl + .35 * pf / max(1e-6, np.abs(pf).max()) * np.abs(fl).max())
    st = P.render(BPM, ev_strings(), 'string_section', release=.8, seed=5, humanize_ms=0)
    hp = P.render(BPM, ev_arp(), 'harp', release=.8, seed=6, swing=.015)
    save('pad', 'strings_harp', st / np.abs(st).max() + .55 * hp / np.abs(hp).max())
    save('drums', 'tribal_perc_nokick', render_perc(BPM))
    os.makedirs(os.path.join(a.out, 'drums'), exist_ok=True)
    for f in glob.glob(os.path.join(a.drums, '*.wav')) + glob.glob(os.path.join(a.drums, '*.csv')):
        d = os.path.join(a.out, 'drums', os.path.basename(f))
        if not os.path.exists(d): os.symlink(f, d)


if __name__ == '__main__':
    main()
