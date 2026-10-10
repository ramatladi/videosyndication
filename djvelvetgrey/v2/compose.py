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
MODES = {'minor': MINOR, 'dorian': (0, 2, 3, 5, 7, 9, 10), 'major': (0, 2, 4, 5, 7, 9, 11),
         'mixolydian': (0, 2, 4, 5, 7, 9, 10)}
CHORD_TYPES = {'m9': [0, 3, 7, 10, 14], 'm7': [0, 3, 7, 10], 'maj9': [0, 4, 7, 11, 14],
               'maj7': [0, 4, 7, 11], 'add9': [0, 4, 7, 14], 'sus2': [0, 2, 7, 14], 'm11': [0, 3, 7, 10, 17],
               'maj': [0, 4, 7, 12], 'min': [0, 3, 7, 12], '7': [0, 4, 7, 10], '9': [0, 4, 7, 10, 14],
               '6': [0, 4, 7, 9], '69': [0, 4, 7, 9, 14]}
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
    # optional 4th value = velocity (ghost notes)
    'funk':     [(0, .25, 0), (.5, .25, 12, .55), (.75, .25, 0), (1.5, .25, 10, .6), (1.75, .25, 12), (2.5, .25, 0),
                 (2.75, .25, 7, .5), (3.25, .25, 12, .55), (3.5, .5, 10)],
    'disco_oct': [(0, .25, 0), (.5, .25, 12), (1, .25, 0), (1.5, .25, 12), (2, .25, 0), (2.5, .25, 12), (3, .25, 0), (3.5, .25, 12)],
    'acid16':   [(q * .25, .2, o, v) for q, o, v in ((0, 0, 1), (2, 0, .6), (3, 12, .9), (5, 0, .5), (6, 3, .8), (8, 0, 1),
                                                       (10, 0, .6), (11, 12, .9), (13, 7, .6), (14, 10, .8))],
    'tech_roll': [(.5, .2, 0), (.75, .2, 0, .6), (1.5, .2, 0), (1.75, .2, 12, .7), (2.5, .2, 0), (2.75, .2, 0, .6), (3.5, .2, 0), (3.75, .2, 7, .7)],
    'afro_sub': [(0, .75, 0), (1.5, .5, 0, .8), (2.75, 1.0, 0)],
    'afro_roll': [(0, .5, 0), (.75, .25, 7, .7), (1.5, .5, 0), (2.25, .25, 10, .7), (2.75, .5, 0), (3.5, .5, 12, .8)],
    'prog_roll': [(q + o, .2, 0, v) for q in range(4) for o, v in ((.25, .7), (.5, 1.0), (.75, .75))],
    'tropical': [(.5, .5, 0), (1.5, .5, 7, .8), (2.5, .5, 0), (3.25, .25, 12, .7), (3.5, .5, 7, .8)],
}

# Arrangement arcs. Every template teases the motif in the first ~5-10 s and states the
# full hook by bar ~8-12 (~15-25 s at 118-124 BPM); the second drop develops the idea.
TEMPLATES = {
    'classic': [('intro', 4), ('hook', 8), ('groove', 8), ('break', 8), ('build', 8), ('drop1', 16), ('break2', 8), ('drop2', 16), ('outro', 16)],
    'early':   [('intro', 4), ('hook', 16), ('break', 8), ('build', 4), ('drop1', 16), ('interlude', 8), ('drop2', 16), ('outro', 20)],
    'burn':    [('intro', 8), ('hook', 8), ('groove', 8), ('build', 8), ('drop1', 16), ('break', 12), ('drop2', 20), ('outro', 12)],
    'wave':    [('intro', 4), ('groove', 4), ('hook', 8), ('drop1', 16), ('break', 8), ('build', 4), ('drop2', 24), ('outro', 24)],
    'prog':    [('intro', 4), ('hook', 8), ('groove', 8), ('build', 16), ('drop1', 16), ('break', 16), ('build', 8), ('drop2', 16), ('outro', 8)],
    'loop':    [('intro', 4), ('groove', 8), ('hook', 8), ('drop1', 16), ('break', 8), ('drop2', 24), ('outro', 16)],
}
LENGTH_S = 179.0


def fit_sections(template, bpm, length=LENGTH_S):
    """Fit an arrangement to the 2:59 format at any tempo, keeping phrase structure:
    the music must cover the full length (no short file) and the outro must actually be heard
    (no truncated ending). Adjusts the outro first, then breaks/interludes/grooves, then drop2,
    always in whole bars and never below musical minimums."""
    bar = 240.0 / bpm
    need = int(np.ceil(length / bar))           # bars that must exist so the file is never short
    secs = [list(x) for x in template]
    total = sum(n for _, n in secs)
    mins = {'outro': 8, 'break': 4, 'break2': 4, 'interlude': 4, 'groove': 4, 'build': 4, 'drop2': 8, 'drop1': 8, 'hook': 8, 'intro': 4}
    order = ['outro', 'break2', 'interlude', 'break', 'groove', 'build', 'drop2', 'drop1']
    # grow: extend outro (it is faded) so the file is never short
    if total < need: secs[-1][1] += need - total; total = need
    # shrink: remove whole bars until the outro starts no later than ~8 bars before the end
    target = need + 1
    while total > target:
        for name in order:
            idx = [i for i, (n, b) in enumerate(secs) if n == name and b > mins.get(n, 4)]
            if idx:
                i = idx[-1]; step = 1 if name == 'outro' else min(4, secs[i][1] - mins.get(name, 4), total - target)
                step = max(1, step); secs[i][1] -= step; total -= step; break
        else:
            break
    return [tuple(x) for x in secs]
LEADS = ['mallet', 'pluck', 'flute', 'rhodes', 'kalimba', 'glass']


def key_name(tonic, mode='minor'): return NOTE[tonic % 12] + ' ' + mode


def mode_fit(progression, mode):
    """Fraction of chord tones that belong to the mode's scale (1.0 = no clashes)."""
    sc = set(MODES[mode]); tones = [(d + i) % 12 for d, t in progression for i in CHORD_TYPES[t]]
    return sum(1 for x in tones if x in sc) / len(tones)


def best_mode(progression, modes):
    return max(modes, key=lambda m: (mode_fit(progression, m), -list(modes).index(m)))


class Harmony:
    def __init__(self, tonic, progression, mode='minor', hr=1):
        self.tonic = tonic; self.mode = mode; self.hr = hr      # hr = bars per chord
        self.prog = [tuple(p) for p in progression]
        self.types = [t for _, t in self.prog]
        self.scale = [m for m in range(24, 108) if (m - tonic) % 12 in MODES[mode]]
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

    def guides(self, ci):
        """(third-like, seventh-like) intervals above the chord root, by chord type."""
        iv = CHORD_TYPES[self.types[ci]]
        third = next((i for i in iv if i in (3, 4)), 2 if 2 in iv else 7)
        seventh = next((i for i in iv if i in (10, 11)), 9 if 9 in iv else (14 if 14 in iv else 7))
        return third, seventh

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
        ci = ((bar0 + int(st // 4)) // h.hr) % 4
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
    call2 = realise(h, rhythm, steps2, start_deg, 4, lo, hi)      # bars 4-5 (same chords as 0-1 when hr=1)
    # resolution: response rhythm, original contour falling home
    res_steps = [-abs(s) if i >= len(r_rhythm) // 2 else s for i, s in enumerate(steps[1:len(r_rhythm)])]
    res_steps += [0] * max(0, len(r_rhythm) - 1 - len(res_steps))
    resol = realise(h, r_rhythm, res_steps, call2[-1][2], 6, lo - 5, hi - 3, end_on_root=True)   # bars 6-7
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


def release_base(rid):
    """dvg001v2 -> dvg001: re-renders/versions of one release share an identity."""
    import re
    return re.sub(r'v\d+$', '', str(rid or ''))


def screen(motif, brief, catalog, answer=None, release=None):
    """Catalogue screening (own catalogue only). Compares the call motif, the answer phrase,
    bass, rhythm/groove, harmony and arrangement. Entries of the same release (any version)
    are skipped so re-renders never reject themselves."""
    flags, nearest = [], None
    base = release_base(release)
    g = brief.get('groove', {})
    feats = {'progression': brief.get('progression'), 'template': brief.get('arc'), 'bass_a': g.get('bass_a'),
             'bass_b': g.get('bass_b'), 'lead': brief.get('lead'), 'style': brief.get('style'), 'mode': brief.get('mode', 'minor')}
    for e in catalog:
        if base and release_base(e.get('id')) == base: continue
        d = similarity_distance(motif, e['motif'])
        if answer is not None and e.get('answer_motif'):
            d = min(d, similarity_distance(answer, e['answer_motif']), similarity_distance(motif, e['answer_motif']),
                    similarity_distance(answer, e['motif']))
        if nearest is None or d < nearest[1]: nearest = (e.get('title'), d)
        if d < FLAG_THRESHOLD: flags.append(f"motif/answer close to '{e.get('title')}' (distance {d})")
        same = [k for k, v in feats.items() if v is not None and e.get(k) == v]
        if len(same) >= 5: flags.append(f"production too similar to '{e.get('title')}' (same {', '.join(same)})")
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
    h = harmony_for(brief)
    lo, hi = brief['tonic'] + 9, brief['tonic'] + 24
    cat = load_catalog()
    cells = list(RHYTHM_CELLS)
    try:
        import styles as S
        cells = S.get(brief.get('style', 'deep')).get('cells') or cells
    except Exception:
        pass
    combos = list(itertools.product(cells, CONTOURS))
    rng.shuffle(combos)
    out = []
    per_cell = -(-n // len(cells))          # styles with few cells may use a cell more than once (different contour)
    for cell, con in combos:
        if sum(1 for c in out if c['cell'] == cell) >= per_cell: continue
        start = int(rng.choice(h.chord_tones_in(0, lo + 2, hi - 5)))
        hook = make_hook(h, cell, con, start, lo, hi, rng)
        rep = motif_repr(hook['call'])
        if any(similarity_distance(rep, c['motif']) < 0.3 for c in out): continue
        sc, ev = score_motif(hook['call'], lo, hi)
        ans = motif_repr(hook['answer'][:max(3, len(hook['answer']) // 2)])
        scr = screen(rep, brief, cat, answer=ans, release=brief.get('release'))
        if scr['flags']: sc -= 1.5
        out.append({'id': len(out) + 1, 'cell': cell, 'contour': con, 'start': start, 'motif': rep, 'answer_motif': ans,
                    'score': sc, 'evidence': ev, 'catalog': scr})
        if len(out) == n: break
    return out


def harmony_for(brief):
    """The brief's harmony with the style's harmonic rhythm (bars per chord)."""
    hr = 1
    try:
        import styles as S
        hr = S.get(brief.get('style', 'deep')).get('harm_rhythm', 1)
    except Exception:
        pass
    return Harmony(brief['tonic'], brief['progression'], brief.get('mode', 'minor'), hr)


def hook_from_spec(brief, spec):
    rng = np.random.default_rng(brief['seed'])
    h = harmony_for(brief)
    lo, hi = brief['tonic'] + 9, brief['tonic'] + 24
    return h, make_hook(h, spec['cell'], spec['contour'], spec['start'], lo, hi, rng)


def add_to_catalog(entry):
    cat = load_catalog()
    cat = [e for e in cat if e.get('id') != entry.get('id')] + [entry]
    json.dump(cat, open(CATALOG, 'w'), indent=1)


if __name__ == '__main__':
    print(json.dumps(calibrate(), indent=1))
