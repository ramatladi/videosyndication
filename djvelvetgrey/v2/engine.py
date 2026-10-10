"""DJ Velvet Grey engine v3 — one shared DSP / mix / master foundation, style-specific modules.

The style profile (styles.py) decides the drums, percussion, bass articulation, chord comping,
musical focal point (melody, bass or rhythm), hook density, arrangement and mix balance.
Arrangements are fitted to the 2:59 format at any supported tempo (compose.fit_sections).
"""
import numpy as np, scipy.signal as ss
from scipy.ndimage import minimum_filter1d, uniform_filter1d
import compose as C
import styles as S
from instruments import *          # noqa: F401,F403  (SR, filters, all voices)
import instruments as I

ENGINE_VERSION = '3.1.0'
LEN = 179.0

# ---------------------------------------------------------------- pattern libraries (beats within a bar)
HATS = {   # (beat, open?, velocity)
    'offbeat':       [(q + .5, True, .6) for q in range(4)],
    'offbeat_ghost': [(q + .5, True, .58) for q in range(4)] + [(b, False, .28) for b in (.25, 1.75, 2.25, 3.75)],
    'house16':       [(s * .25, False, (.55 if s % 2 else .3)) for s in range(16)] + [(q + .5, True, .5) for q in range(4)],
    'disco16':       [(s * .25, False, (.45 if s % 4 == 2 else .28)) for s in range(16) if s % 4 != 2] + [(q + .5, True, .75) for q in range(4)],
    'rolling16':     [(s * .25, False, (.42 if s % 2 else .32)) for s in range(16)] + [(q + .5, True, .45) for q in range(4)],
    'shuffle':       [(s * .25, False, (.55 if s % 4 in (1, 3) else .25)) for s in range(16)] + [(q + .5, True, .38) for q in range(4)],
    'shuffle_soft':  [(s * .25, False, (.38 if s % 4 in (1, 3) else .18)) for s in range(16)] + [(q + .5, True, .45) for q in range(4)],
    'light':         [(q + .5, True, .4) for q in range(4)],
    'afro':          [(q * .5, False, (.4 if q % 2 else .25)) for q in range(8)] + [(q + .5, True, .32) for q in range(4)],
}
KICKS = {'four_soft': [0, 1, 2, 3], 'four': [0, 1, 2, 3], 'four_hard': [0, 1, 2, 3],
         'afro': None}          # afro: chosen per track from AFRO_KICKS
AFRO_KICKS = [[0, 1, 2, 3], [0, 1.5, 2, 3], [0, 1, 2.75, 3.5], [0, 2, 2.75]]
PERC = {   # (instrument, beat, velocity, pan)
    'deep':     [('shaker', s * .25, (1.0 if s % 4 == 2 else (.5 if s % 2 else .32)), .35) for s in range(16)] + [('rim', 2.75, .35, -.5)],
    'light':    [('shaker', q + .5, .5, .35) for q in range(4)],
    'house':    [('tamb', q + .5, .55, .3) for q in range(4)] + [('rim', .75, .3, -.5), ('rim', 2.75, .3, -.5)],
    'afro':     [('shaker', s * .25, (.8 if s % 4 == 2 else (.45 if s % 2 else .3)), .35) for s in range(16)]
                + [('conga_lo', .75, .55, .5), ('conga_hi', 1.5, .5, .55), ('conga_hi', 2.25, .45, .55), ('conga_lo', 3.0, .55, .5),
                   ('conga_hi', 3.5, .5, .55), ('tom_lo', 0, .45, -.4), ('tom_lo', 1.5, .4, -.4), ('tom_mid', 3.0, .4, -.3),
                   ('bell_hi', 0, .3, -.6), ('bell_lo', .5, .25, -.6), ('bell_hi', 1.5, .3, -.6), ('bell_hi', 2.5, .3, -.6), ('bell_lo', 3, .25, -.6)],
    'tropical': [('shaker', q * .5, (.5 if q % 2 else .35), .35) for q in range(8)] + [('conga_hi', 1.75, .35, .5), ('conga_lo', 3.25, .35, .5)],
    'disco':    [('tamb', s * .25, (.6 if s % 4 == 2 else .25), .3) for s in range(16)] + [('conga_hi', 1.5, .3, .5), ('conga_lo', 3.5, .3, .5)],
    'soulful':  [('conga_lo', .75, .45, .5), ('conga_hi', 1.5, .4, .55), ('conga_hi', 2.75, .4, .55), ('conga_lo', 3.25, .45, .5)]
                + [('tamb', q + .5, .4, .3) for q in range(4)],
    'prog':     [('shaker', s * .25, (.42 if s % 2 else .26), .35) for s in range(16)] + [('rim', 3.75, .3, -.5), ('wood', 1.25, .22, .55)],
    'vocal':    [('tamb', q * .5, (.5 if q % 2 else .22), .3) for q in range(8)] + [('conga_hi', 2.5, .3, .55)],
    'nudisco':  [('shaker', s * .25, (.5 if s % 4 == 2 else .22), .35) for s in range(16)] + [('wood', 1.75, .3, .5), ('conga_lo', 3.25, .35, .5)],
    'tech':     [('rim', .75, .5, -.5), ('rim', 2.25, .45, -.5), ('rim', 3.5, .4, -.5), ('wood', 1.75, .35, .5),
                 ('shaker', .5, .35, .35), ('shaker', 1.5, .35, .35), ('shaker', 2.5, .35, .35), ('shaker', 3.5, .35, .35)],
}
EXTRA_PERC = {'deep': [('conga_hi', 1.75, .45, .6), ('conga_lo', 3.25, .45, .6), ('conga_hi', 3.5, .45, .6)],
              'afro': [('wood', s / 3, .3, .6) for s in range(12) if s % 3 != 0],
              'tech': [('wood', .25, .3, .6), ('wood', 2.5, .3, .6), ('rim', 3.75, .3, -.5)],
              'default': [('conga_hi', 1.75, .4, .6), ('conga_lo', 3.25, .4, .6), ('tamb', 2.5, .3, .3)]}
COMP = {   # (beat, duration, velocity)
    'dub_stab':       [(0, 1.4, 1.0), (1.75, .6, .8), (2.75, 1.1, .9)],
    'house_piano':    [(0, .4, 1.0), (.75, .25, .75), (1.5, .4, .9), (2.5, .25, .8), (3, .4, .95), (3.5, .25, .75)],
    'afro_stab':      [(.5, .3, .7), (2.25, .3, .6), (3.5, .4, .7)],
    'tropical_pluck': [(.5, .25, .8), (1.5, .25, .8), (2.5, .25, .8), (3.25, .2, .6), (3.5, .25, .8)],
    'tech_stab':      [(1.75, .2, .9), (3.25, .15, .6)],
    'soul_comp':      [(0, .5, .9), (.75, .75, .75), (1.75, .5, .8), (2.5, .5, .75), (3.25, .75, .8)],
    'gated8':         [(q * .5, .32, (.95 if q % 2 == 0 else .7)) for q in range(8)],
    'poly_stab':      [(.5, .3, .9), (1.25, .2, .7), (2, .4, .85), (2.75, .25, .75), (3.5, .3, .8)],
    'organ_hold':     [(0, 3.4, .75), (3.5, .45, .55)],
    'filter_loop':    [(0, .25, 1.0), (.5, .25, .8), (.75, .25, .7), (1.5, .25, .9), (2, .25, .8), (2.5, .25, .85), (3, .25, .9), (3.5, .25, .8)],
}


def perc_hit(name, vel):
    return {'shaker': lambda: I.shaker(vel), 'rim': lambda: I.rim(vel), 'tamb': lambda: I.tamb(vel),
            'conga_hi': lambda: I.conga(245, vel), 'conga_lo': lambda: I.conga(170, vel), 'tom_lo': lambda: I.tom(95, vel),
            'tom_mid': lambda: I.tom(140, vel), 'bell_hi': lambda: I.bell(1180, vel), 'bell_lo': lambda: I.bell(790, vel),
            'wood': lambda: I.wood(1900, vel)}[name]()


class TrackV2:
    def __init__(self, brief, spec, template=None, length=None, lufs=None):
        self.b = brief; self.spec = spec
        self.style_name = S.ALIASES.get(brief.get('style', 'deep'), brief.get('style', 'deep'))
        self.P = S.get(self.style_name)
        self.bpm = brief['bpm']; self.beat = 60 / self.bpm; self.bar = 4 * self.beat
        self.h, self.hook = C.hook_from_spec(brief, spec)
        self.length = length or LEN
        base = template or C.TEMPLATES[brief['arc']]
        self.sections = base if template else C.fit_sections(base, self.bpm, self.length)
        self.nbars = sum(n for _, n in self.sections)
        self.N = int(SR * (self.nbars * self.bar + 4))
        self.rng = np.random.default_rng(brief['seed'] + 7)
        self.swing = brief.get('groove', {}).get('swing', 0.0)
        self.lufs = lufs if lufs is not None else brief.get('loudness_lufs', self.P['lufs'])
        self.hr = self.P.get('harm_rhythm', 1)
        self.meta = {'engine_version': ENGINE_VERSION, 'style': self.style_name, 'sections': [], 'drop2_changes': [],
                     'length_s': self.length, 'target_lufs': self.lufs}

    # ------------------------------------------------------------ helpers
    def T(self, bar, beat=0.0, jitter=0.0):
        if self.swing and abs(beat % .5 - .25) < 1e-6: beat += self.swing
        return bar * self.bar + beat * self.beat + jitter

    def zeros(self): return np.zeros((self.N, 2), np.float32)

    def place(self, dst, sig, t, pan=0.0, g=1.0):
        i = int(round(t * SR))
        if i < 0: sig = sig[-i:]; i = 0
        if sig.ndim == 1:
            a = (pan + 1) * np.pi / 4
            sig = np.stack([sig * np.cos(a), sig * np.sin(a)], 1) * np.sqrt(2)
        n = min(len(sig), self.N - i)
        if n > 0: dst[i:i + n] += g * sig[:n]

    def hum(self, ms=4.0): return float(self.rng.normal(0, ms / 1000))

    def ci(self, B):
        """Chord index, section-relative: every section (and every 8-bar hook inside it) starts on chord 0,
        so the hook, which is harmonised as one 8-bar cycle, always sits on the chords it was written for.
        The intro is anchored one bar late so the tease (bar 1) lands on chord 0."""
        return ((B - self.anchor) // self.hr) % 4

    def chord_left(self, B, sec_end):
        """Bars until the next chord change (or section end) from bar B."""
        return min(self.hr - ((B - self.anchor) % self.hr), sec_end - B)

    def chord_start(self, B, k):
        return k == 0 or (B - self.anchor) % self.hr == 0

    def play(self, dst, notes, bar0, kind, g=1.0, octave=0, pan=0.0, only=None, dur_scale=1.0):
        for st, d, m in notes:
            if only is not None and not (only[0] <= st < only[1]): continue
            self.place(dst, I.note(kind, m + octave, d * self.beat * dur_scale), self.T(bar0, st), pan, g * (.9 + .1 * self.rng.random()))

    def chord_hit(self, dst, kind, notes, t, dur, vel, pan=0.0, top=None):
        voices = list(notes[:4]) if top is None else [n for n in notes[:4] if n < top][-3:] + [top]
        spread = np.linspace(-.35, .35, len(voices))
        for v, p in zip(voices, spread):
            if kind == 'guitar':
                self.place(dst, I.guitar_note(v + 12, dur, vel * .7), t, pan + p)
            else:
                self.place(dst, I.note(kind, v + (12 if kind in ('stab', 'pluck') else 0), dur, vel / len(voices) * 2), t, pan + p)

    # ------------------------------------------------------------ render
    def render(self):
        I._cache.clear()                      # bounded memory across many renders in one process
        b, h, P = self.b, self.h, self.P
        L = {k: self.zeros() for k in ('kick', 'clap', 'hats', 'perc', 'bass', 'pad', 'comp', 'lead', 'answer', 'counter', 'fx')}
        kick_t = []
        lead_k = b['lead']; ans_k = b.get('answer', P['answers'][0])
        g = b['groove']
        bass_a = C.GROOVES[g['bass_a']]; bass_b = C.GROOVES[g.get('bass_b', P['bass_b'][0])]
        kpat = KICKS[P['kick']] or AFRO_KICKS[b['seed'] % len(AFRO_KICKS)]
        focal = P['focal']; drop2 = P['drop2']; every = P['hook_every']
        comp_pat = P['comp']; comp_inst = P['comp_inst']
        self.meta.update({'kick_pattern': kpat, 'focal': focal, 'hats': P['hats'], 'perc': P['perc'], 'comp': comp_pat})
        comp_env = []      # per-bar comp filter cutoff (french/tech filter automation)
        bar = 0
        for si, (name, nb) in enumerate(self.sections):
            self.meta['sections'].append({'name': name, 'start_bar': bar, 'bars': nb, 'start_s': round(bar * self.bar, 2)})
            self.anchor = bar + (1 if name == 'intro' and nb >= 4 else 0)
            for k in range(nb):
                B = bar + k; ci = self.ci(B); blk = k % 8
                cl = self.chord_left(B, bar + nb); cst = self.chord_start(B, k)
                fill_bar = (blk == 7) or (nb < 8 and k == nb - 1)
                drums = name in ('hook', 'groove', 'drop1', 'drop2', 'outro') or (name == 'intro' and k >= 1)
                full = name in ('hook', 'drop1', 'drop2')
                d2 = name == 'drop2'
                chord = h.chords[ci]
                # ---------------- pad / sustained layer
                cut = {'intro': 700 + 900 * k / max(nb, 1), 'build': 1200 + 3500 * k / nb, 'break': 1800, 'break2': 1800,
                       'interlude': 1500, 'groove': 2000, 'outro': 1700}.get(name, 3000)
                if P['pad'] in ('warm', 'supersaw') and cst:      # one pad per chord, never across a change
                    c2 = cut * (1.6 if P['pad'] == 'supersaw' else 1.0)
                    self.place(L['pad'], I.pad_chord(chord, self.bar * cl, c2, si), self.T(B))
                elif P['pad'] == 'strings' and cst and (name in ('intro', 'break', 'break2', 'interlude', 'build') or d2 or name == 'hook'):
                    for v in chord[:4]:
                        self.place(L['pad'], I.strings_note(v + 12, self.bar * cl * .95, .5, attack=.4), self.T(B), np.random.default_rng(v).uniform(-.4, .4))
                elif P['pad'] is None and cst and name in ('intro', 'break', 'break2', 'interlude', 'build'):
                    # styles without a pad still need harmony in the intro and breakdowns (no silent body):
                    # piano styles restrike soft chords, the others get a dark filtered chord bed
                    if comp_inst == 'piano':
                        for q in (0, 2.5):
                            if q < 4 * cl: self.chord_hit(L['pad'], 'piano', chord, self.T(B, q), (4 * cl - q) * self.beat * .95, .55)
                    else:
                        self.place(L['pad'], I.pad_chord(chord, self.bar * cl, 900 + 300 * (name == 'build'), si), self.T(B))
                # ---------------- kick
                if drums and not (name == 'outro' and k >= nb - 2):
                    for q in kpat:
                        if P['fill'] == 'filter_drop' and fill_bar and q >= 2: continue
                        self.place(L['kick'], I.kick(.95 if q % 2 == 0 else .88, P['kick']), self.T(B, q)); kick_t.append(self.T(B, q))
                # ---------------- bass
                if name in ('hook', 'groove', 'drop1', 'drop2') or (name == 'outro' and k < 8):
                    hn = self.hook_notes(k) if focal == 'bass' and name in ('hook', 'drop1', 'drop2') and (k % every) < 8 else []
                    if hn:                 # bass focal: the bass plays the hook (folded into the bass register)
                        for st, dd, m in hn:
                            self.bass_voice(L['bass'], C.fold(m - 24, 33, 52), min(dd, .75) * self.beat * .9, B, st, 1.0)
                    else:                  # bars without hook notes keep the style's bass pattern (no silent bars)
                        pat = bass_b if (d2 and 'bass_b' in drop2) else bass_a
                        for item in pat:
                            q, dd, o = item[:3]; vel = item[3] if len(item) > 3 else 1.0
                            self.bass_voice(L['bass'], h.roots[ci] + o, dd * self.beat * .95, B, q, vel, bright=d2)
                elif name in ('interlude', 'break2') and cst:      # held for exactly one chord
                    self.place(L['bass'], I.bass_note(h.roots[ci], cl * self.bar * .9, .15), self.T(B), g=.6)
                # ---------------- hats / perc
                if drums or name in ('break', 'interlude', 'build'):
                    soft = .45 if not drums else 1.0
                    for (inst, q, v, pan) in PERC[P['perc']]:
                        if drums and fill_bar and q >= 3 and name != 'intro': continue
                        if not drums and inst not in ('shaker', 'tamb', 'bell_hi', 'bell_lo'): continue
                        self.place(L['perc'], perc_hit(inst, v * soft * (.85 + .3 * self.rng.random())), self.T(B, q, self.hum(3)), pan)
                    if drums:
                        for (q, op, v) in HATS[P['hats']]:
                            if fill_bar and q >= 3: continue
                            if not full and not op and P['hats'] in ('offbeat_ghost',): continue
                            self.place(L['hats'], I.hat(op, v * (.9 + .2 * self.rng.random())), self.T(B, q, self.hum(2)), -.15 if op else .25)
                    if (d2 and 'extra_perc' in drop2) or (name == 'hook' and k >= 8 and 'extra_perc' in drop2):
                        for (inst, q, v, pan) in EXTRA_PERC.get(P['perc'], EXTRA_PERC['default']):
                            self.place(L['perc'], perc_hit(inst, v), self.T(B, q, self.hum(4)), pan)
                    if d2 and 'triplet_perc' in drop2:
                        for s3 in range(12):
                            if s3 % 3: self.place(L['perc'], I.wood(2300, .22), self.T(B, s3 / 3, self.hum(2)), .55)
                # ---------------- backbeat + fills
                if drums and name != 'intro':
                    bb = P['backbeat']
                    for q in (1, 3):
                        if fill_bar and q == 3: continue
                        if bb == 'clap': self.place(L['clap'], I.clap(.9), self.T(B, q))
                        elif bb == 'snare': self.place(L['clap'], I.snare(.85), self.T(B, q))
                        elif bb == 'snap': self.place(L['clap'], I.snap(.8), self.T(B, q))
                        else: self.place(L['clap'], I.clap(.55), self.T(B, q)); self.place(L['perc'], I.rim(.45), self.T(B, q + .02), -.4)
                    if fill_bar: self.fill(L, B)
                if name == 'build':
                    rel = k / nb; step = 1 if rel < .5 else (.5 if rel < .75 else .25)
                    for q in np.arange(0, 4, step):
                        hit = I.snare(.25 + .7 * (k * 4 + q) / (nb * 4), tail=False) if P['backbeat'] == 'snare' else I.clap(.25 + .7 * (k * 4 + q) / (nb * 4), tail=False)
                        self.place(L['clap'], hit, self.T(B, q))
                # ---------------- comping
                comp_on = name in ('groove', 'hook', 'drop1', 'drop2') or (name == 'outro' and k < 8) or \
                          (comp_pat == 'arp16' and name in ('break', 'build', 'intro')) or (comp_pat == 'filter_loop' and name != 'outro')
                comp_env.append(self.comp_cutoff(name, k, nb))
                if comp_on:
                    cv = .6 if name in ('break', 'intro', 'build') else 1.0
                    hn = self.hook_notes(k) if focal == 'rhythm' and name in ('hook', 'drop1', 'drop2') and (k % every) < 8 else []
                    if hn:          # rhythm focal: the hook is carried by chord stabs voiced under the melody
                        for st, dd, m in hn:
                            self.chord_hit(L['comp'], comp_inst, chord, self.T(B, st), min(dd, .6) * self.beat, cv, top=C.fold(m, 60, 79))
                    else:           # bars without hook notes keep the style's comping pattern
                        self.comp_bar(L['comp'], comp_pat, comp_inst, chord, B, cv, d2)
                    if d2 and 'organ_layer' in drop2 and cst:      # held for exactly one chord
                        for v in chord[:4]: self.place(L['comp'], I.organ_note(v, self.bar * cl * .95, .35), self.T(B), .2)
                    if d2 and 'strings_stab' in drop2:
                        for q in (1.5, 3.5):
                            for v in chord[1:4]: self.place(L['pad'], I.strings_note(v + 12, .3 * self.beat * 2, .45, attack=.01), self.T(B, q), .3)
                    if d2 and 'arp_double' in drop2:
                        self.comp_bar(L['comp'], 'arp16', 'glass', [n + 12 for n in chord], B, .45, False, offset=.125)
                # ---------------- melody / hook
                self.melody(L, name, k, nb, B, lead_k, ans_k, focal, every, drop2)
                # ---------------- countermelody (guide tones, kept below the lead register)
                if d2 and 'counter' in drop2:
                    th, sv = h.guides(ci)
                    root = chord[0]
                    tone = C.fold(root + (sv if k % 2 == 0 else th), h.tonic - 5, h.tonic + 6)
                    self.place(L['counter'], I.note('rhodes' if lead_k != 'rhodes' else 'glass', tone, 3 * self.beat), self.T(B, .5), -.3, .6)
                # ---------------- fx
                if name == 'build' and k == 0:
                    rs = int(nb * self.bar * SR); tr = np.arange(rs) / rs
                    self.place(L['fx'], filt(self.rng.standard_normal(rs), 2500, 'high') * tr ** 2, self.T(B), g=.3)
                if name in ('drop1', 'drop2', 'hook') and k == 0:
                    t = np.arange(int(2.5 * SR)) / SR
                    self.place(L['fx'], filt(self.rng.standard_normal(len(t)), 5500, 'high') * np.exp(-t * 1.7), self.T(B), g=.4)
            bar += nb
        secs = self.meta['sections']
        first = lambda names: next((x['start_bar'] for x in secs if x['name'] in names), None)
        tb = 1 if secs and secs[0]['name'] == 'intro' and secs[0]['bars'] >= 4 else first(('groove', 'hook'))
        hb_ = first(('hook', 'drop1'))
        self.meta['tease_s'] = round(tb * self.bar, 1) if tb is not None else None
        self.meta['full_hook_s'] = round(hb_ * self.bar, 1) if hb_ is not None else None
        self.meta['drop2_changes'] = list(drop2)
        self.meta['outro_start_s'] = round(secs[-1]['start_bar'] * self.bar, 2)
        return self.mix(L, kick_t, comp_env)

    # ------------------------------------------------------------ parts
    def hook_notes(self, k):
        """Lead-hook notes falling in bar k of the current 8-bar hook, as (beat-in-bar, dur, midi)."""
        hb = k % 8
        return [(st - hb * 4, d, m) for st, d, m in self.hook['lead'] if hb * 4 <= st < hb * 4 + 4]

    def bass_voice(self, dst, m, dur, B, q, vel, bright=False):
        kind = self.P['bass']
        if kind == 'acid': sig = I.acid_note(m, dur, min(1.0, vel + (.2 if bright else 0)))
        elif kind == 'funk': sig = I.funk_bass(m, dur, vel)
        else: sig = I.bass_note(m, dur, .7 if bright else .5) * vel
        self.place(dst, sig, self.T(B, q))

    def comp_cutoff(self, name, k, nb):
        if self.P['comp'] == 'filter_loop' or 'filter_open' in self.P['drop2']:
            if name in ('intro', 'break', 'break2', 'interlude'): return 500 + 900 * k / max(nb, 1)
            if name == 'build': return 900 + 5000 * k / max(nb, 1)
            if name == 'drop2': return 12000
            if name == 'outro': return 4000 * (1 - k / max(nb, 1)) + 400
            return 3200 + 2000 * np.sin(np.pi * k / max(nb, 1))
        return 16000

    def comp_bar(self, dst, pat, inst, chord, B, cv, d2, offset=0.0):
        if pat == 'arp16':
            tones = sorted(chord[:4]) + [n + 12 for n in sorted(chord[:4])]
            shape = [0, 2, 4, 2, 1, 3, 5, 3] if self.b['seed'] % 2 else [0, 1, 2, 3, 4, 5, 6, 5]
            for s16 in range(16):
                m = tones[shape[s16 % 8] % len(tones)] + 12
                self.place(dst, I.note(inst, m, .22 * self.beat, .55 * cv), self.T(B, s16 * .25 + offset), (-.35 if s16 % 2 else .35))
            return
        if pat == 'guitar16':
            for s16 in range(16):
                acc = s16 % 4 == 2; ghost = s16 % 2 == 1
                v = (1.0 if acc else (.35 if ghost else .55)) * cv
                if (s16 % 4 == 0) and self.rng.random() < .35: continue
                self.chord_hit(dst, 'guitar', chord[1:4], self.T(B, s16 * .25, self.hum(2)), .12, v, pan=.35 if s16 % 2 else -.15)
            return
        for (q, dd, v) in COMP[pat]:
            self.chord_hit(dst, inst, chord, self.T(B, q, self.hum(2)), dd * self.beat, v * cv)

    def melody(self, L, name, k, nb, B, lead_k, ans_k, focal, every, drop2):
        hb = k % 8
        fits = k + 8 <= nb              # never start an 8-bar hook that would spill into the next section
        if name == 'intro' and k in (1, 2) and nb >= 4:          # tease, ~2-6 s in
            self.play(L['lead'], self.hook['call'], (B - k) + 1, lead_k, g=.55, only=((k - 1) * 4, k * 4))
        lead_g = {'melody': 1.0, 'bass': .45, 'rhythm': .5}[focal]
        if name in ('hook', 'drop1', 'drop2', 'break', 'break2') and hb == 0 and fits:
            if name in ('drop1', 'drop2') and (k % every) >= 8: return
            oct_ = 12 if (name == 'drop2' and k >= 8 and 'lead_oct' in drop2) else 0
            g = (.75 if name.startswith('break') else 1.0) * (1.0 if name.startswith('break') else lead_g)
            self.play(L['lead'], self.hook['lead'], B, lead_k, g=g, octave=oct_)
            self.play(L['answer'], self.hook['answer'], B, ans_k, g=g * .8, pan=.25)
            if name == 'drop2' and 'lead_layer' in drop2:
                self.play(L['answer'], self.hook['lead'], B, ans_k, g=.4, octave=12, pan=-.25)
        if name == 'groove' and hb == 0:
            self.play(L['lead'], self.hook['call'], B, lead_k, g=.8 * lead_g)
        if name == 'build' and k % 2 == 0 and self.ci(B) == 0 and (B - self.anchor) % self.hr == 0:
            self.play(L['lead'], self.hook['call'], B, lead_k, g=.5 + .4 * k / nb, only=(0, 4))
        if name == 'interlude' and hb == 0 and fits:
            self.play(L['answer'], self.hook['call'], B, ans_k, g=.7, octave=-12, pan=-.2)
        if name == 'outro' and k in (0, 8) and k + 2 <= nb:
            self.play(L['lead'], self.hook['call'], B, lead_k, g=.6 if k else .8)

    # ------------------------------------------------------------ mix
    def mix(self, L, kick_t, comp_env):
        N = self.N; P = self.P; off = P.get('mix', {})

        def sc(depth, rel):
            env = np.ones(N); seg = 1 - depth * np.exp(-np.arange(int(.4 * SR)) / SR / rel)
            for tk in kick_t:
                i = int(tk * SR); n = min(len(seg), N - i)
                if n > 0: env[i:i + n] = np.minimum(env[i:i + n], seg[:n])
            return env[:, None]

        def rms_db(x):
            a = np.abs(x).mean(1); w = int(.4 * SR)
            r = np.sqrt(np.maximum(uniform_filter1d(a ** 2, w), 0)); act = r[r > r.max() * .05]
            return 20 * np.log10(np.sqrt((act ** 2).mean()) + 1e-12) if len(act) else -120

        def stage(x, key, target_db):
            if np.abs(x).max() == 0: return x
            return x * 10 ** ((target_db + off.get(key, 0) - rms_db(x)) / 20)

        def comp(x, thr_db=-18, ratio=2.5, att=.005, rel=.12):
            env = np.sqrt(np.maximum(uniform_filter1d((x ** 2).mean(1), int(att * SR) + 1), 0))
            env = ss.lfilter([1 - np.exp(-1 / (rel * SR))], [1, -np.exp(-1 / (rel * SR))], env)
            lvl = 20 * np.log10(env + 1e-9); over = np.maximum(lvl - thr_db, 0)
            return x * (10 ** (-over * (1 - 1 / ratio) / 20))[:, None]

        def reverb(x, secs, decay, seed):
            n = int(secs * SR); t = np.arange(n) / SR; r = np.random.default_rng(seed)
            ir = r.standard_normal((n, 2)) * np.exp(-t * decay)[:, None]; ir = filt(ir, 7000)
            ir[:int(.025 * SR)] = 0; ir /= np.sqrt((ir ** 2).sum(0))
            m = x.mean(1)
            return np.stack([ss.oaconvolve(m, ir[:, 0])[:N], ss.oaconvolve(m, ir[:, 1])[:N]], 1)

        def delay(x, beats, fb=.35):
            d = int(beats * self.beat * SR); y = np.zeros_like(x); m = filt(x.mean(1), 4000)
            for i in range(1, 6): y[i * d:, i % 2] += fb ** i * m[:N - i * d]
            return y

        # comp filter automation (bar-wise envelope -> sample envelope)
        compb = L['comp']
        if np.abs(compb).max() > 0 and min(comp_env) < 16000:
            env = np.repeat(np.array(comp_env, float), int(self.bar * SR))
            env = np.pad(env, (0, max(0, N - len(env))), 'edge')[:N]
            env = uniform_filter1d(env, int(.5 * SR))
            compb = np.stack([I.lp_env(compb[:, 0], env, .9), I.lp_env(compb[:, 1], env, .9)], 1)
        sc_d = P.get('sc', .5)
        kick_ = stage(L['kick'], 'kick', -14)
        bass = stage(np.tanh(1.2 * filt(L['bass'], 30, 'high')), 'bass', -16.5) * sc(min(.8, sc_d + .05), .09)
        drums = comp(stage(L['clap'], 'clap', -23) + stage(filt(L['hats'], 6000, 'high'), 'hats', -27) + stage(L['perc'], 'perc', -25.5), -20, 2)
        pad = stage(filt(L['pad'], 160, 'high'), 'pad', -23) * sc(sc_d, .11)
        compg = stage(filt(compb, 180, 'high'), 'comp', -24) * sc(sc_d * .8, .1)
        lead = stage(filt(L['lead'], 220, 'high'), 'lead', -19)
        answer = stage(filt(L['answer'], 220, 'high'), 'answer', -23.5)
        counter = stage(filt(L['counter'], 200, 'high'), 'counter', -27)
        fx = stage(L['fx'], 'fx', -29)
        send = lead * .35 + answer * .45 + pad * .25 + compg * (.35 if P['comp'] == 'dub_stab' else .15) + L['clap'] * .02
        rev = filt(filt(reverb(send, P.get('verb', 2.6), 2.4, self.b['seed']), 300, 'high'), 9000) * sc(.3, .15)
        dly = delay(lead + answer * .5 + (compg * .6 if P['comp'] == 'dub_stab' else 0), .75) * .22
        mix = kick_ + bass + drums + pad + compg + (lead + answer + counter) * sc(.2, .1) + stage(rev, 'rev', -24) + stage(dly, 'dly', -29) + fx
        low = ss.sosfiltfilt(ss.butter(4, 120, 'low', fs=SR, output='sos'), mix, axis=0)
        mix = (mix - low) + low.mean(1, keepdims=True)
        mix = filt(mix, 25, 'high')[:int(self.length * SR)]
        fade = int(min(8.0, self.length * .1) * SR); mix[-fade:] *= (np.linspace(1, 0, fade) ** 2)[:, None]
        mix[:int(.02 * SR)] *= np.linspace(0, 1, int(.02 * SR))[:, None]
        out, achieved = master(mix, self.lufs)
        self.meta['achieved_lufs_master'] = achieved
        return out

    def fill(self, L, B):
        f = self.P['fill']
        if f in ('clap_conga', 'clap_roll', 'conga_run') and f != 'conga_run' and (f == 'clap_roll' or (B // 8) % 2 == 0):
            for i, q in enumerate(np.arange(3, 4, .25)): self.place(L['clap'], I.clap(.35 + .15 * i, tail=False), self.T(B, q))
        elif f in ('clap_conga', 'conga_run'):
            for i, (q, f0) in enumerate(((3, 260), (3.25, 230), (3.5, 200), (3.75, 170))): self.place(L['perc'], I.conga(f0, .6), self.T(B, q), .5 - .3 * i)
        elif f == 'snare_roll':
            for i, q in enumerate(np.arange(3, 4, .25)): self.place(L['clap'], I.snare(.3 + .15 * i, tail=False), self.T(B, q))
        elif f == 'tom_run':
            for i, (q, f0) in enumerate(((3, 190), (3.25, 160), (3.5, 130), (3.75, 100))): self.place(L['perc'], I.tom(f0, .55), self.T(B, q), .4 - .25 * i)
        elif f == 'marimba_run':
            tones = sorted(self.h.chords[self.ci(B)][:4])
            for i, q in enumerate((3, 3.25, 3.5, 3.75)): self.place(L['answer'], I.marimba_note(tones[i % len(tones)] + 24, .2, .5), self.T(B, q), .3)
        elif f == 'perc_drop':
            for q in (3.25, 3.5, 3.75): self.place(L['perc'], I.rim(.45), self.T(B, q), -.4)
        elif f == 'filter_drop':
            for i, q in enumerate(np.arange(3, 4, .25)): self.place(L['clap'], I.clap(.25 + .12 * i, tail=False), self.T(B, q))


# ---------------------------------------------------------------- master
def true_peak_env(x, os_=4, chunk=1 << 20):
    out = np.zeros(len(x))
    for s in range(0, len(x), chunk):
        a, e = max(0, s - 64), min(len(x), s + chunk + 64)
        up = np.abs(ss.resample_poly(x[a:e].astype(np.float32), os_, 1, axis=0)).max(1)
        pk = up[: (len(up) // os_) * os_].reshape(-1, os_).max(1)
        out[s:min(len(x), s + chunk)] = pk[s - a: s - a + min(chunk, len(x) - s)]
    return out


def limit(x, ceiling_db=-2.0, look_ms=3.0, release_ms=40.0):
    ceil = 10 ** (ceiling_db / 20)
    pk = true_peak_env(x)
    g = np.minimum(1.0, ceil / np.maximum(pk, 1e-9))
    W = int(look_ms / 1000 * SR)
    g = minimum_filter1d(g, size=4 * W + 1)
    a = np.exp(-1 / (release_ms / 1000 * SR))           # smooth recovery (less distortion than a pure box)
    g = np.minimum(g, ss.lfilter([1 - a], [1, -a], g, zi=[g[0] * a])[0])
    g = uniform_filter1d(g, size=2 * W + 1)
    return x * g[:, None]


def master(mix, target_lufs, ceiling_db=-2.8):
    """Gain to target, limit at -2.8 dBTP (lossy codecs overshoot by ~1-1.5 dB; this keeps the export trim small
    so the delivered loudness stays near the style target), then compensate the loudness lost to limiting (up to 4 passes).
    Returns (audio, achieved integrated LUFS). Codec headroom is handled later by export.py."""
    import pyloudnorm as pyln
    meter = pyln.Meter(SR)
    for _ in range(4):
        cur = meter.integrated_loudness(mix)
        mix = mix * 10 ** ((target_lufs - cur) / 20)
        mix = limit(mix, ceiling_db)
        achieved = meter.integrated_loudness(mix)
        if abs(achieved - target_lufs) < .3: break
    return mix, round(float(achieved), 2)
