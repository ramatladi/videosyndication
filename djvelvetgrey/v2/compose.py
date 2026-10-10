"""DJ Velvet Grey engine v2 — composition: briefs, motifs, hooks, catalog screening.

A track starts from a written brief (mood, lead character, motif, harmony, groove, arc).
The motif is written first (a 2-bar cell = rhythm + contour), then developed into an
8-bar call-and-response hook. Candidates are compared by intervals + rhythm, so a
transposed or shifted copy of an earlier motif is still caught.

Nothing here judges how a melody *sounds*; scores are compositional evidence only.
"""
import json, os, itertools
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG = os.path.join(os.path.dirname(HERE), 'catalog.json')

NOTE = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
MINOR = (0, 2, 3, 5, 7, 8, 10)
CHORD_TYPES = {'m9': [0, 3, 7, 10, 14], 'm7': [0, 3, 7, 10], 'maj9': [0, 4, 7, 11, 14],
               'maj7': [0, 4, 7, 11], 'add9': [0, 4, 7, 14], 'sus2': [0, 2, 7, 14], 'm11': [0, 3, 7, 10, 17]}
PROGRESSIONS = [
    [(0, 'm9'), (8, 'maj9'), (3, 'maj7'), (10, 'add9')],
    [(0, 'm7'), (5, 'm9'), (8, 'maj7'), (7, 'm7')],
    [(0, 'm9'), (8, 'maj7'), (5, 'm9'), (10, 'add9')],
    [(8, 'maj7'), (10, 'add9'), (0, 'm9'), (0, 'm7')],
    [(0, 'm9'), (3, 'maj7'), (10, 'add9'), (5, 'm7')],
    [(5, 'm9'), (10, 'add9'), (3, 'maj7'), (8, 'maj7')],
    [(0, 'm9'), (10, 'add9'), (8, 'maj7'), (10, 'add9')],
    [(0, 'm11'), (5, 'm9'), (10, 'sus2'), (3, 'maj9')],
    [(8, 'maj9'), (3, 'maj7'), (10, 'add9'), (0, 'm9')],
]

# 2-bar (8-beat) rhythm cells: (start_beat, duration). Deliberately different characters.
RHYTHM_CELLS = {
    'lilt':     [(0, .75), (.75, .75), (1.5, 1), (3, .5), (3.5, .5), (4, 1.5), (6, 2)],
    'call':     [(.5, .5), (1, .5), (1.5, 1.5), (4.5, .5), (5, .5), (5.5, 2)],
    'dotted':   [(0, 1.5), (1.5, 1.5), (3, 1), (4, 1.5), (5.5, .5), (6, 1.5)],
    'offbeat':  [(.5, .5), (1.5, .5), (2.5, .75), (3.25, .75), (4.5, .5), (5.5, 1), (6.5, 1.5)],
    'syncop':   [(0, .75), (.75, .25), (1, 1), (2.5, .5), (3, 1), (4.75, .75), (5.5, .5), (6, 1.5)],
    'sparse':   [(0, 2), (2.5, .5), (3, 1), (4, 3)],
    'threes':   [(0, .75), (.75, .75), (1.5, .75), (2.25, 1.75), (4, .75), (4.75, .75), (5.5, 2.5)],
    'question': [(1, .5), (1.5, .5), (2, 1), (3, 1), (5, .5), (5.5, .5), (6, 2)],
    'skip':     [(0, .5), (.75, .5), (1.5, .5), (2.25, .75), (4, .5), (4.75, .5), (5.5, .5), (6.25, 1.75)],
    'anthem':   [(0, 1), (1, .5), (1.5, 1.5), (3, 1), (4, 1), (5, .5), (5.5, 2.5)],
}
CONTOURS = ['arch', 'rise', 'fall', 'zigzag', 'leapstep', 'pedal', 'wave', 'valley']

GROOVES = {   # bass patterns over one bar: (beat, dur_beats, semitone offset from root)
    'offbeat':  [(.5, .42, 0), (1.5, .42, 0), (2.5, .42, 0), (3.5, .42, 0)],
    'rolling':  [(.5, .25, 0), (1.25, .25, 0), (1.5, .5, 0), (2.5, .25, 0), (2.75, .25, 12), (3.5, .5, 0)],
    'syncop':   [(.5, .5, 0), (1.75, .25, 0), (2.5, .5, 0), (3.25, .25, 12), (3.5, .5, 0)],
    'octave':   [(.5, .25, 0), (.75, .25, 12), (1.5, .25, 0), (1.75, .25, 12), (2.5, .25, 0), (2.75, .25, 12), (3.5, .25, 0), (3.75, .25, 12)],
    'walk':     [(.5, .5, 0), (1.75, .25, 7), (2.5, .5, 0), (3.5, .25, 10), (3.75, .25, 12)],
    'sustain':  [(.5, 1.0, 0), (2.5, .75, 0), (3.5, .25, 12)],
}

# Arrangement arcs. Every template teases the motif in the first ~5-10 s and states the
# full hook by bar ~8-12 (~15-25 s at 118-124 BPM); the second drop develops the idea.
TEMPLATES = {
    'classic': [('intro', 4), ('hook', 8), ('groove', 8), ('break', 8), ('build', 8), ('drop1', 16), ('break2', 8), ('drop2', 16), ('outro', 16)],
    'early':   [('intro', 4), ('hook', 16), ('break', 8), ('build', 4), ('drop1', 16), ('interlude', 8), ('drop2', 16), ('outro', 20)],
    'burn':    [('intro', 8), ('hook', 8), ('groove', 8), ('build', 8), ('drop1', 16), ('break', 12), ('drop2', 20), ('outro', 12)],
    'wave':    [('intro', 4), ('groove', 4), ('hook', 8), ('drop1', 16), ('break', 8), ('build', 4), ('drop2', 24), ('outro', 24)],
}
LEADS = ['mallet', 'pluck', 'flute', 'rhodes', 'kalimba', 'glass']


def key_name(tonic): return NOTE[tonic % 12] + ' minor'


class Harmony:
    def __init__(self, tonic, progression):
        self.tonic = tonic
        self.prog = [tuple(p) for p in progression]
        self.scale = [m for m in range(24, 108) if (m - tonic) % 12 in MINOR]
        self.chords, self.roots, self.pcs = [], [], []
        for deg, typ in self.prog:
            root = tonic + deg
            notes = [root + i for i in CHORD_TYPES[typ]]
            while min(notes) > 56: notes = [n - 12 for n in notes]
            while min(notes) < 48: notes = [n + 12 for n in notes]
            self.chords.append(notes)
            b = root % 12 + 24
            while b < 28: b += 12
            self.roots.append(b)
            self.pcs.append({n % 12 for n in notes[:3]})

    def chord_tones_in(self, ci, lo, hi):
        return [m for m in range(lo, hi + 1) if m % 12 in self.pcs[ci]]


def contour_steps(name, n, rng):
    """n-1 scale-step moves describing the motif's shape."""
    k = n - 1
    if name == 'arch':
        h = max(1, k // 2); s = [1] * h + [-1] * (k - h)
    elif name == 'rise':
        s = [1, 1, -1, 1, 2, -1, 1, 1][:k]
    elif name == 'fall':
        s = [-1, -1, 1, -1, -2, 1, -1, -1][:k]
    elif name == 'zigzag':
        s = [2 if i % 2 == 0 else -1 for i in range(k)]
    elif name == 'leapstep':
        s = [3] + [-1] * (k - 1)
    elif name == 'pedal':
        s = [0, 1, -1, 0, 2, -2, 0, 1][:k]
    elif name == 'wave':
        s = [1, 1, -2, 1, 1, -2, 1, 1][:k]
    else:  # valley
        h = max(1, k // 2); s = [-1] * h + [1] * (k - h)
    if len(s) < k: s += [rng.choice([-1, 1])] * (k - len(s))
    return s[:k]


def fold(m, lo, hi):
    while m > hi: m -= 12
    while m < lo: m += 12
    return m


def realise(h, rhythm, steps, start_deg, bar0, lo, hi, end_on_root=False):
    """Turn rhythm + scale-step contour into pitches, snapping strong/long notes to chord tones."""
    pool = [m for m in h.scale if lo <= m <= hi]
    idx = int(np.argmin([abs(m - start_deg) for m in pool]))
    notes = []
    for i, (st, d) in enumerate(rhythm):
        if i > 0: idx = int(np.clip(idx + steps[i - 1], 0, len(pool) - 1))
        m = pool[idx]
        ci = (bar0 + int(st // 4)) % 4
        strong = d >= .75 or abs(st % 4) < 1e-6 or i == len(rhythm) - 1
        if strong and m % 12 not in h.pcs[ci]:
            cands = h.chord_tones_in(ci, lo, hi)
            direction = np.sign(steps[i - 1]) if i > 0 else 0
            prev = notes[-1][2] if notes else None
            def key(c):
                pen = abs(c - m)
                if direction > 0 and prev is not None and c <= prev: pen += 6   # keep the contour's motion
                if direction < 0 and prev is not None and c >= prev: pen += 6
                return (pen, c)
            m = min(cands, key=key)
            idx = int(np.argmin([abs(p - m) for p in pool]))
        if end_on_root and i == len(rhythm) - 1:
            root_pc = h.chords[ci][0] % 12
            cands = [c for c in range(lo, hi + 1) if c % 12 == root_pc] or [m]
            m = min(cands, key=lambda c: abs(c - m))
        notes.append((st, d, m))
    return notes


def make_hook(h, cell, contour, start_deg, lo, hi, rng):
    """8-bar call-and-response hook. Returns dict of lead/answer note lists (beats from hook start)."""
    rhythm = RHYTHM_CELLS[cell]
    steps = contour_steps(contour, len(rhythm), rng)
    call = realise(h, rhythm, steps, start_deg, 0, lo, hi)
    # response: inverted contour, rhythm trimmed (first note dropped, last held), ends on a chord root
    r_rhythm = rhythm[1:] if len(rhythm) > 4 else rhythm
    r_steps = [-s for s in steps[1:len(r_rhythm)]] + [0] * max(0, len(r_rhythm) - 1 - len(steps[1:]))
    resp = realise(h, r_rhythm, r_steps, call[-1][2] - 2, 2, lo - 5, hi - 3, end_on_root=True)
    # call repeated with a varied tail (last two notes nudged up a step)
    steps2 = steps[:-1] + [steps[-1] + 1]
    call2 = realise(h, rhythm, steps2, start_deg, 0, lo, hi)
    # resolution: response rhythm, original contour falling home
    res_steps = [-abs(s) if i >= len(r_rhythm) // 2 else s for i, s in enumerate(steps[1:len(r_rhythm)])]
    res_steps += [0] * max(0, len(r_rhythm) - 1 - len(res_steps))
    resol = realise(h, r_rhythm, res_steps, call2[-1][2], 2, lo - 5, hi - 3, end_on_root=True)
    shift = lambda ph, beats: [(st + beats, d, m) for st, d, m in ph]
    return {'call': call, 'lead': call + shift(call2, 16),
            'answer': shift(resp, 8) + shift(resol, 24), 'steps': steps}


def motif_repr(call):
    pitches = [m for _, _, m in call]
    return {'intervals': [b - a for a, b in zip(pitches, pitches[1:])],
            'onsets': [int(round(st * 4)) for st, _, _ in call],
            'durs': [int(round(d * 4)) for _, d, _ in call]}


# ---------------------------------------------------------------- similarity
def _edit(a, b, cost):
    D = np.zeros((len(a) + 1, len(b) + 1))
    D[:, 0] = np.arange(len(a) + 1); D[0, :] = np.arange(len(b) + 1)
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            D[i, j] = min(D[i - 1, j] + 1, D[i, j - 1] + 1, D[i - 1, j - 1] + cost(a[i - 1], b[j - 1]))
    return D[-1, -1] / max(len(a), len(b), 1)


def similarity_distance(m1, m2):
    """0 = same motif (incl. transposed or shifted), ~1 = unrelated. Intervals + rhythm + contour."""
    i1, i2 = m1['intervals'], m2['intervals']
    icost = lambda x, y: min(abs(x - y) / 7.0, 1.0)
    d_int = min(_edit(i1, i2[k:] + i2[:k], icost) for k in range(max(1, len(i2))))
    sgn = lambda v: [int(np.sign(x)) for x in v]
    d_con = min(_edit(sgn(i1), sgn(i2[k:] + i2[:k]), lambda x, y: 0 if x == y else 1) for k in range(max(1, len(i2))))
    on1 = set(o % 32 for o in m1['onsets'])
    best = 1.0
    for sh in range(32):
        on2 = set((o + sh) % 32 for o in m2['onsets'])
        best = min(best, 1 - len(on1 & on2) / len(on1 | on2))
    return round(0.45 * d_int + 0.35 * best + 0.20 * d_con, 3)


FLAG_THRESHOLD = 0.18   # from calibrate(): repeats/transpositions/shifts 0.0, one changed interval ~0.06,
                        # different motifs 0.26-0.61 — flag below 0.18 for revision/review


def calibrate():
    """Known cases used to set FLAG_THRESHOLD; returns their distances."""
    h = Harmony(57, PROGRESSIONS[0]); rng = np.random.default_rng(0)
    base = make_hook(h, 'lilt', 'arch', 69, 64, 80, rng)['call']
    b = motif_repr(base)
    transposed = motif_repr([(s, d, m + 5) for s, d, m in base])
    shifted = dict(b, onsets=[(o + 2) % 32 for o in b['onsets']])
    one_note = dict(b, intervals=b['intervals'][:-1] + [b['intervals'][-1] + 2])
    other = motif_repr(make_hook(h, 'sparse', 'zigzag', 72, 64, 80, rng)['call'])
    other2 = motif_repr(make_hook(h, 'offbeat', 'fall', 67, 64, 80, rng)['call'])
    return {'identical': similarity_distance(b, b), 'transposed': similarity_distance(b, transposed),
            'shifted_8th': similarity_distance(b, shifted), 'one_interval_changed': similarity_distance(b, one_note),
            'different_motif_a': similarity_distance(b, other), 'different_motif_b': similarity_distance(b, other2)}


def load_catalog():
    try: return json.load(open(CATALOG))
    except Exception: return []


def screen(motif, brief, catalog):
    """Catalog screening: close motifs, plus identical groove+progression+template combos."""
    flags, nearest = [], None
    for e in catalog:
        d = similarity_distance(motif, e['motif'])
        if nearest is None or d < nearest[1]: nearest = (e.get('title'), d)
        if d < FLAG_THRESHOLD: flags.append(f"motif close to '{e.get('title')}' (distance {d})")
        same = sum([e.get('progression') == brief.get('progression'), e.get('template') == brief.get('arc'),
                    e.get('bass_a') == brief.get('groove', {}).get('bass_a'), e.get('lead') == brief.get('lead')])
        if same == 4: flags.append(f"same progression, arc, groove and lead as '{e.get('title')}'")
    return {'flags': flags, 'nearest': nearest}


def score_motif(call, lo, hi):
    """Compositional evidence only (not a listening judgement)."""
    r = motif_repr(call)
    iv = r['intervals']
    pitches = [m for _, _, m in call]
    rng_ = max(pitches) - min(pitches)
    sync = sum(1 for st, _, _ in call if abs(st * 2 - round(st * 2)) > 1e-6 or abs(st % 1 - .5) < 1e-6)
    step_ratio = sum(1 for x in iv if abs(x) <= 2) / max(1, len(iv))
    leap = any(abs(x) >= 4 for x in iv)
    s = 0.0
    s += 1.0 if 4 <= len(call) <= 8 else 0.4
    s += 1.0 if rng_ <= 12 else (0.6 if rng_ <= 16 else 0.0)
    s += 1.0 - min(abs(sync - 3) / 3, 1)
    s += 1.0 - min(abs(step_ratio - 0.65) / 0.4, 1)
    s += 0.6 if leap else 0.0
    s += 0.4 if len(set(iv)) >= 3 else 0.0
    return round(s, 2), {'notes': len(call), 'range_semitones': rng_, 'syncopations': sync,
                         'stepwise_ratio': round(step_ratio, 2), 'has_leap': leap}


def candidates(brief, n=6):
    """n genuinely different motif candidates (distinct cell + contour, pairwise distance >= 0.3)."""
    rng = np.random.default_rng(brief['seed'])
    h = Harmony(brief['tonic'], brief['progression'])
    lo, hi = brief['tonic'] + 9, brief['tonic'] + 24
    cat = load_catalog()
    combos = list(itertools.product(RHYTHM_CELLS, CONTOURS))
    rng.shuffle(combos)
    out = []
    for cell, con in combos:
        if any(c['cell'] == cell for c in out): continue
        start = int(rng.choice(h.chord_tones_in(0, lo + 2, hi - 5)))
        hook = make_hook(h, cell, con, start, lo, hi, rng)
        rep = motif_repr(hook['call'])
        if any(similarity_distance(rep, c['motif']) < 0.3 for c in out): continue
        sc, ev = score_motif(hook['call'], lo, hi)
        scr = screen(rep, brief, cat)
        if scr['flags']: sc -= 1.5
        out.append({'id': len(out) + 1, 'cell': cell, 'contour': con, 'start': start, 'motif': rep,
                    'score': sc, 'evidence': ev, 'catalog': scr})
        if len(out) == n: break
    return out


def hook_from_spec(brief, spec):
    rng = np.random.default_rng(brief['seed'])
    h = Harmony(brief['tonic'], brief['progression'])
    lo, hi = brief['tonic'] + 9, brief['tonic'] + 24
    return h, make_hook(h, spec['cell'], spec['contour'], spec['start'], lo, hi, rng)


def add_to_catalog(entry):
    cat = load_catalog()
    cat = [e for e in cat if e.get('id') != entry.get('id')] + [entry]
    json.dump(cat, open(CATALOG, 'w'), indent=1)


if __name__ == '__main__':
    print(json.dumps(calibrate(), indent=1))
