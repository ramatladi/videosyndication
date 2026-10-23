"""DJ Velvet Grey engine v4 — one shared DSP / mix / master foundation, style-specific modules.

v4: recorded (sampled) instruments for every acoustic/electric voice (piano, EP, organ, strings, brass, flute,
guitar, mallets, bass guitar, hand percussion, kit hats/claps/snares) via sampler.py, a per-track sound palette,
voice-led chord inversions, per-phrase drum and comping variations and fuller humanisation, so tracks of the
same style no longer share one sound set or one loop. Synth voices remain where the genre is electronic
(sub bass, acid, stabs, supersaw, glass/pluck leads, 909-style kick).

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
import sampler as SM

ENGINE_VERSION = '4.0.0'
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
         'afro': None,          # afro: chosen per track from AFRO_KICKS
         'half': [0, 1.5, 2.75]}   # half-time (future bass): the backbeat lands on beat 3 only (style half_time=True)
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
# v4: alternative comping rhythms per pattern; each track picks a main + a B variant, alternating per 8-bar phrase
COMP_VARIANTS = {
    'dub_stab':       [[(0, 1.2, 1.0), (1.5, .5, .75), (2.75, .9, .9), (3.75, .25, .6)], [(.5, 1.0, .9), (2.25, .6, .8), (3.5, .5, .75)]],
    'house_piano':    [[(0, .4, 1.0), (.75, .25, .7), (1.75, .4, .9), (2.5, .4, .85), (3.25, .25, .7)],
                       [(.5, .3, .9), (1, .3, .8), (1.75, .5, 1.0), (2.75, .3, .8), (3.5, .4, .9)],
                       [(0, .75, 1.0), (1.5, .25, .8), (2, .5, .9), (3, .25, .75), (3.5, .4, .9)]],
    'afro_stab':      [[(.75, .3, .7), (2.5, .3, .6), (3.25, .4, .7)], [(.5, .3, .7), (1.75, .2, .55), (3, .5, .7)]],
    'tropical_pluck': [[(.5, .25, .8), (1.25, .2, .6), (2.5, .25, .8), (3.5, .25, .8)], [(0, .25, .7), (.75, .25, .8), (2, .25, .7), (2.75, .25, .8), (3.5, .25, .8)]],
    'tech_stab':      [[(1.5, .2, .9), (3.75, .15, .6)], [(.75, .15, .7), (2.75, .2, .9)]],
    'soul_comp':      [[(0, .75, .9), (1.5, .5, .8), (2.25, .75, .75), (3.5, .5, .8)], [(.5, .5, .85), (1.75, .75, .8), (3, .5, .85), (3.75, .25, .6)]],
    'gated8':         [[(q * .5, .4 if q % 2 == 0 else .2, (.95 if q % 2 == 0 else .6)) for q in range(8)], [(q * .25, .18, (.95 if q % 4 == 0 else .55)) for q in range(16) if q % 4 != 3]],
    'poly_stab':      [[(.5, .3, .9), (1.5, .2, .7), (2.25, .4, .85), (3.5, .3, .8)], [(0, .4, .9), (.75, .2, .7), (2, .3, .85), (2.75, .2, .7), (3.25, .3, .8)]],
    'organ_hold':     [[(0, 1.9, .75), (2, 1.4, .65), (3.5, .45, .55)], [(0, 3.9, .7)]],
    'filter_loop':    [[(0, .25, 1.0), (.75, .25, .7), (1, .25, .8), (1.5, .25, .9), (2.25, .25, .8), (2.5, .25, .85), (3.5, .25, .8)]],
}
# v4: hat variations layered on the style's base pattern (added hits, removed hits), alternating per phrase
HAT_VARIANTS = [
    {'add': [], 'drop': []},
    {'add': [(3.75, False, .3)], 'drop': []},
    {'add': [(1.75, False, .28), (3.75, False, .3)], 'drop': []},
    {'add': [(2.5, True, .5)], 'drop': [.5]},
    {'add': [(q + .75, False, .22) for q in range(4)], 'drop': []},
]


def perc_hit_synth(name, vel):
    return {'shaker': lambda: I.shaker(vel), 'rim': lambda: I.rim(vel), 'tamb': lambda: I.tamb(vel),
            'conga_hi': lambda: I.conga(245, vel), 'conga_lo': lambda: I.conga(170, vel), 'tom_lo': lambda: I.tom(95, vel),
            'tom_mid': lambda: I.tom(140, vel), 'bell_hi': lambda: I.bell(1180, vel), 'bell_lo': lambda: I.bell(790, vel),
            'wood': lambda: I.wood(1900, vel)}[name]()


def track_variation(seed, style):
    """Per-track arrangement/performance choices from the seed (shared by the engine and brief_check)."""
    vr = np.random.default_rng(int(seed) * 13 + 5)
    cv = COMP_VARIANTS.get(S.get(style)['comp'], [])
    return {'voicing': ['close', 'open', 'close', 'shell'][int(vr.integers(4))],
            'comp_b': int(vr.integers(len(cv))) if cv else None, 'comp_swap': bool(vr.random() < .5) if cv else False,
            'hat_vars': [int(i) for i in vr.choice(len(HAT_VARIANTS), 2, replace=False)],
            'pad_src': ['synth', 'strings', 'blend'][int(vr.integers(3))], 'feel_ms': round(float(vr.uniform(-6, 6)), 1),
            'arp_shape': int(vr.integers(len(ARP_SHAPES))), 'bass_var': ['none', 'ghost', 'octave_push', 'anticipate'][int(vr.integers(4))],
            'kick_var': ['none', 'skip_bar8', 'pickup'][int(vr.integers(3))]}


ARP_SHAPES = [[0, 1, 2, 3, 4, 5, 6, 5], [0, 2, 4, 2, 1, 3, 5, 3], [0, 4, 2, 5, 1, 6, 3, 5], [4, 2, 0, 2, 5, 3, 1, 3],
              [0, 1, 2, 4, 3, 2, 1, 2], [0, 3, 1, 4, 2, 5, 3, 6]]


def style_kinds(style, brief=None):
    """Instrument kinds the track actually uses (the brief's lead/answer when given, else all the style allows)."""
    P = S.get(style)
    k = ({brief['lead'], brief.get('answer') or P['answers'][0]} if brief else set(P['leads']) | set(P['answers'])) | {P['comp_inst']}
    if P['comp'] == 'guitar16': k.add('guitar_mute')
    if P['bass'] == 'funk': k.add('funk_bass')
    if P['pad'] in ('warm', 'supersaw', 'strings') or P['pad'] is None: k.add('strings')
    if 'organ_layer' in P['drop2']: k.add('organ')
    if 'strings_stab' in P['drop2']: k |= {'strings', 'brass'}
    if 'counter' in P['drop2']: k |= {'rhodes', 'glass'}
    return sorted(x for x in k if x in SM.PRESETS and len(SM.PRESETS[x]) > 1)


def sound_fingerprint(seed, style, brief=None):
    """Compact description of the track's audible sound set (palette + variation), compared by brief_check.
    Only instruments the style uses and choices that sound different are included."""
    pal = SM.Palette(seed, style); v = track_variation(seed, style)
    fp = {k: pal.choice[k] for k in style_kinds(style, brief)}
    fp.update({'kit': pal.kit, 'hats': pal.hats, 'clap': pal.clap, 'perc': pal.perc, 'kick_layer': pal.kick_layer,
               'voicing': v['voicing'], 'comp': [v['comp_b'], v['comp_swap']], 'hat_vars': sorted(v['hat_vars']), 'pad_src': v['pad_src'],
               'arp': v['arp_shape'], 'bass_var': v['bass_var'], 'kick_var': v['kick_var']})
    return fp


def _layer(a, b):
    """Blend two one-shots at equal loudness (so a 'layer' really is half of each), keeping the louder's level."""
    n = max(len(a), len(b)); a = np.pad(a, (0, n - len(a))); b = np.pad(b, (0, n - len(b)))
    ra, rb = np.sqrt((a ** 2).mean()) + 1e-12, np.sqrt((b ** 2).mean()) + 1e-12
    ref = max(ra, rb)
    return (a * (ref / ra) + b * (ref / rb)) * .5


SAMPLED_PERC = {'shaker': 'shaker', 'rim': 'rim', 'tamb': 'tamb', 'conga_hi': 'conga_hi', 'conga_lo': 'conga_lo',
                'tom_lo': 'tom_lo', 'tom_mid': 'tom_mid', 'bell_hi': 'agogo_hi', 'bell_lo': 'agogo_lo', 'wood': 'wood'}


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
        # v4: per-track palette and variation choices (deterministic from the seed)
        if not SM.available():
            raise RuntimeError('engine v4 needs the sampled instruments: apt-get install -y fluid-soundfont-gm fluidsynth; pip install pyfluidsynth==1.4.0')
        SM.check_soundfont()                       # fail closed on any other SoundFont build
        self.sampled = True
        self.studio = brief.get('instruments') == 'studio'      # real mode + the CC0 studio pack (studio.py)
        self.real = brief.get('instruments') in ('real', 'studio')   # recorded instruments only, no synthesis at all
        self.pal = SM.Palette(brief['seed'], self.style_name, real=self.real, studio=self.studio)
        v = track_variation(brief['seed'], self.style_name)
        self.voicing = v['voicing']
        cv = COMP_VARIANTS.get(self.P['comp'], [])
        self.comp_a = COMP.get(self.P['comp']); self.comp_b = cv[v['comp_b']] if cv else None
        if cv and v['comp_swap']: self.comp_a, self.comp_b = self.comp_b, self.comp_a
        self.hat_vars = [HAT_VARIANTS[i] for i in v['hat_vars']]
        self.pad_src = v['pad_src']
        if self.real: self.pad_src = 'strings' if v['pad_src'] != 'blend' else 'choir'
        self.arp_shape = v['arp_shape']; self.bass_var = v['bass_var']; self.kick_var = v['kick_var']
        self.feel = v['feel_ms']            # ms: whole-band push (-) / laid-back (+) on hats, perc & comp
        self.prev_voicing = None
        if self.pal: self.meta['palette'] = self.pal.describe()
        self.meta['instruments'] = ('studio (recorded instruments only: CC0 studio pack + FluidR3)' if self.studio else
                                    'real (recorded instruments only)') if self.real else 'recorded + synth'
        if self.studio:
            import studio as _ST
            self.meta['studio_pack_sha256'] = _ST.pack_sha()
        self.meta.update({'voicing': self.voicing, 'pad_source': self.pad_src, 'feel_ms': self.feel,
                          'comp_variant': v['comp_b'], 'comp_swap': v['comp_swap'], 'hat_variants': v['hat_vars'],
                          'arp_shape': v['arp_shape'], 'bass_variation': v['bass_var'], 'kick_variation': v['kick_var']})

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
        elif pan:
            a = (np.clip(pan, -1, 1) + 1) * np.pi / 4
            sig = sig * (np.array([np.cos(a), np.sin(a)]) * np.sqrt(2))
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
            acc = 1.0 if abs(st % 1) < 1e-6 else .9                  # downbeats a touch stronger
            self.place(dst, self.voice(kind, m + octave, d * self.beat * dur_scale, .78 * acc * (.88 + .2 * self.rng.random())),
                       self.T(bar0, st, self.hum(5)), pan, g)

    def voice(self, kind, m, dur, vel=1.0):
        """Any melodic voice: sampled when a recorded instrument exists for it, else the engine's synth voice."""
        if self.pal is not None and self.pal.sampled(kind):
            return SM.note(self.pal, kind, m, dur, vel) * 4.0
        if self.real: raise RuntimeError(f'real-instruments mode has no recording for {kind!r}')
        return I.note(kind, m, dur, vel)

    def perc_hit(self, name, vel):
        if self.pal is not None and name in SAMPLED_PERC:
            return SM.hand(self.pal, SAMPLED_PERC[name], vel) * 3.0
        return perc_hit_synth(name, vel)

    def hat_sig(self, op, vel):
        mode = self.pal.hats if self.pal else 'synth'
        if self.real:
            return SM.drum(self.pal, 'hat_open' if op else 'hat', vel, kit=self.pal.kit, dur=.3 if op else .08).mean(1) * 3.0
        syn = I.hat(op, vel)
        if mode == 'synth': return syn
        smp = SM.drum(self.pal, 'hat_open' if op else 'hat', vel, kit=25 if mode == '808' else 0, dur=.3 if op else .08).mean(1) * 3.0
        if mode != 'layer': return smp
        return _layer(syn, smp)

    def clap_sig(self, vel, tail=True):
        mode = self.pal.clap if self.pal else 'synth'
        if self.real:      # a real hand clap, doubled slightly late for a two-person clap
            a = SM.drum(self.pal, 'clap', vel, kit=self.pal.kit, dur=.2).mean(1) * 3.0
            b = SM.drum(self.pal, 'clap', vel * .8, kit=0, dur=.2).mean(1) * 3.0
            d = int(.011 * SR); n = max(len(a), len(b) + d)
            return np.pad(a, (0, n - len(a))) + .6 * np.pad(b, (d, n - len(b) - d))
        syn = I.clap(vel, tail)
        if mode == 'synth': return syn
        smp = SM.drum(self.pal, 'clap', vel, kit=25 if mode == '808' else 0, dur=.2).mean(1) * 3.0
        if mode != 'layer': return smp
        return _layer(syn, smp)

    def snare_sig(self, vel, tail=True):
        if self.pal is None: return I.snare(vel, tail)
        smp = SM.drum(self.pal, 'snare', vel, dur=.25).mean(1) * 3.0
        if self.real: return smp
        syn = I.snare(vel, tail); n = max(len(syn), len(smp))
        return np.pad(syn, (0, n - len(syn))) * .35 + np.pad(smp, (0, n - len(smp))) * .85

    def kick_sig(self, vel, kind):
        if self.real:      # two recorded bass drums (kit + acoustic), the second adds low-end weight
            a = SM.drum(self.pal, 'kick', vel, dur=.35).mean(1) * 3.0
            b = SM.drum(self.pal, 'kick_ac', vel, kit=0, dur=.35).mean(1) * 3.0
            n = max(len(a), len(b)); x = np.pad(a, (0, n - len(a))) + .7 * np.pad(b, (0, n - len(b)))
            return np.tanh(1.3 * (x + .8 * filt(x, 110)))         # saturate/EQ the recording (processing, not synthesis)
        k = I.kick(vel, kind)
        if self.pal is None or not self.pal.kick_layer: return k
        smp = SM.drum(self.pal, 'kick', vel, dur=.3).mean(1) * 3.0
        smp = filt(smp, 90, 'high')                            # sampled kick adds knock/texture, the synth keeps the sub
        n = len(k); smp = np.pad(smp, (0, max(0, n - len(smp))))[:n]
        return k + self.pal.kick_layer * smp

    def voiced(self, notes):
        """v4 voice leading: choose the inversion of the chord closest to the previous voicing (no parallel
        root-position blocks), in the track's voicing style (close / open drop-2 / 3-note shell)."""
        pcs = [n % 12 for n in notes[:4]]
        if self.voicing == 'shell' and len(pcs) >= 4: pcs = [pcs[0], pcs[1], pcs[3]]
        cands = []
        for inv in range(len(pcs)):
            v = []; base = 50
            for pc in pcs[inv:] + pcs[:inv]:
                n = base + ((pc - base) % 12)
                while v and n <= v[-1]: n += 12
                v.append(n)
            for sh in (-12, 0, 12):
                w = [x + sh for x in v]
                if 48 <= min(w) and max(w) <= 79: cands.append(w)
        if not cands: return list(notes[:4])
        if self.prev_voicing is None:
            best = min(cands, key=lambda w: abs(np.mean(w) - 62))
        else:
            pv = self.prev_voicing
            best = min(cands, key=lambda w: sum(min(abs(x - y) for y in pv) for x in w) + .3 * abs(np.mean(w) - 62))
        self.prev_voicing = best
        if self.voicing == 'open' and len(best) >= 4:
            best = sorted([best[-2] - 12] + best[:-2] + best[-1:])
        return best

    def chord_hit(self, dst, kind, notes, t, dur, vel, pan=0.0, top=None):
        voices = (self.voiced(notes) if self.pal is not None else list(notes[:4])) if top is None else \
            [n for n in notes[:4] if n < top][-3:] + [top]
        spread = np.linspace(-.35, .35, len(voices))
        strum = .006 if kind in ('guitar', 'piano', 'rhodes') else .0              # tiny roll, like real hands
        for i, (v, p) in enumerate(zip(voices, spread)):
            tt = t + i * strum * (1 + .3 * self.rng.random())
            vv = vel * (.85 + .25 * self.rng.random())
            if kind == 'guitar':
                if self.pal is not None:
                    self.place(dst, SM.note(self.pal, 'guitar_mute', v + 12, dur, vv * .8) * 4.0, tt, pan + p)
                else:
                    self.place(dst, I.guitar_note(v + 12, dur, vv * .7), tt, pan + p)
            else:
                if self.pal is not None and self.pal.sampled(kind):    # real velocity for the sample, level via gain
                    self.place(dst, self.voice(kind, v + (12 if kind == 'pluck' else 0), dur, min(1.0, vv * .85)) * (2.0 / len(voices)), tt, pan + p)
                else:
                    self.place(dst, self.voice(kind, v + (12 if kind in ('stab', 'pluck') else 0), dur, vv / len(voices) * 2), tt, pan + p)

    # ------------------------------------------------------------ render
    SYNTH_VOICES = ('kick', 'clap', 'hat', 'shaker', 'conga', 'rim', 'bass_note', 'pad_chord', 'lead_note', 'snare', 'snap', 'tamb',
                    'tom', 'wood', 'bell', 'acid_note', 'funk_bass', 'piano_note', 'organ_note', 'strings_note', 'brass_note',
                    'guitar_note', 'stab_note', 'polysynth_note', 'topline_note', 'marimba_note', 'steel_note', 'rimsynth_note', 'note')

    def render(self):
        if not self.real: return self._render()
        # real-instruments mode: every synthesised voice is disabled for the duration of the render, so any
        # synth sound reaching the mix is an error, not a silent substitute
        saved = {n: getattr(I, n) for n in self.SYNTH_VOICES}
        def refuse(name):
            def f(*a, **k): raise RuntimeError(f'synth voice {name}() used in real-instruments mode')
            return f
        try:
            for n in self.SYNTH_VOICES: setattr(I, n, refuse(n))
            return self._render()
        finally:
            for n, f in saved.items(): setattr(I, n, f)

    def _render(self):
        I._cache.clear(); SM.clear_cache()    # bounded memory across many renders in one process (renders are deterministic)
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
                    src = 'blend' if (P['pad'] == 'supersaw' and self.pad_src == 'strings' and not self.real) else self.pad_src
                    if self.real and P['pad'] == 'supersaw': src = 'choir'
                    if src == 'choir':           # real mode: strings + "ahh" choir instead of a synth pad
                        for j, v in enumerate(self.voiced(chord)):
                            pn = (-.45, -.15, .15, .45)[j % 4]; dd = self.bar * cl * .97
                            self.place(L['pad'], self.voice('strings', v, dd, .5) * .6, self.T(B, 0, self.hum(8)), pn)
                            self.place(L['pad'], SM.note(self.pal, 'choir', v + 12, dd, .45) * 4.0 * .45, self.T(B, 0, self.hum(8)), -pn)
                    if src in ('synth', 'blend'):
                        self.place(L['pad'], I.pad_chord(chord, self.bar * cl, c2, si), self.T(B), g=(.6 if src == 'blend' else 1.0))
                    if src in ('strings', 'blend'):
                        for j, v in enumerate(self.voiced(chord)):
                            self.place(L['pad'], self.voice('strings', v, self.bar * cl * .97, .5) * (.5 if name in ('intro', 'outro') else .75),
                                       self.T(B, 0, self.hum(8)), (-.45, -.15, .15, .45)[j % 4])
                elif P['pad'] == 'strings' and cst and (name in ('intro', 'break', 'break2', 'interlude', 'build') or d2 or name == 'hook'):
                    for v in chord[:4]:
                        self.place(L['pad'], self.voice('strings', v + 12, self.bar * cl * .95, .5) if self.pal is not None
                                   else I.strings_note(v + 12, self.bar * cl * .95, .5, attack=.4), self.T(B), np.random.default_rng(v).uniform(-.4, .4))
                elif P['pad'] is None and cst and name in ('intro', 'break', 'break2', 'interlude', 'build'):
                    # styles without a pad still need harmony in the intro and breakdowns (no silent body):
                    # piano styles restrike soft chords, the others get a dark filtered chord bed
                    if comp_inst == 'piano':
                        for q in (0, 2.5):
                            if q < 4 * cl: self.chord_hit(L['pad'], 'piano', chord, self.T(B, q), (4 * cl - q) * self.beat * .95, .55)
                    else:
                        if self.pad_src != 'synth' or self.real:
                            for j, v in enumerate(self.voiced(chord)):
                                self.place(L['pad'], self.voice('strings', v, self.bar * cl * .97, .4) * .6, self.T(B), (-.4, -.1, .1, .4)[j % 4])
                        else:
                            self.place(L['pad'], I.pad_chord(chord, self.bar * cl, 900 + 300 * (name == 'build'), si), self.T(B))
                # ---------------- kick
                if drums and not (name == 'outro' and k >= nb - 2):
                    kq = list(kpat)
                    if full and blk == 7 and (k // 8) % 2 == 1:          # v4 per-track kick variation at phrase ends
                        if self.kick_var == 'skip_bar8': kq = [q for q in kq if q < 3]
                        elif self.kick_var == 'pickup': kq = kq + [3.75]
                    for q in kq:
                        if P['fill'] == 'filter_drop' and fill_bar and q >= 2: continue
                        kv = (.95 if q % 2 == 0 else .88) if q == int(q) else .55
                        self.place(L['kick'], self.kick_sig(kv, P['kick']), self.T(B, q)); kick_t.append(self.T(B, q))
                # ---------------- bass
                if name in ('hook', 'groove', 'drop1', 'drop2') or (name == 'outro' and k < 8):
                    hn = self.hook_notes(k) if focal == 'bass' and name in ('hook', 'drop1', 'drop2') and (k % every) < 8 else []
                    if hn:                 # bass focal: the bass plays the hook (folded into the bass register)
                        for st, dd, m in hn:
                            self.bass_voice(L['bass'], C.fold(m - 24, 33, 52), min(dd, .75) * self.beat * .9, B, st, 1.0)
                    else:                  # bars without hook notes keep the style's bass pattern (no silent bars)
                        pat = list(bass_b if (d2 and 'bass_b' in drop2) else bass_a)
                        if (k // 8) % 2 == 1 and blk in (3, 7):              # v4 per-track bass variation, 2nd phrase
                            pat = self.vary_bass(pat, blk, cl)
                        for item in pat:
                            q, dd, o = item[:3]; vel = item[3] if len(item) > 3 else 1.0
                            self.bass_voice(L['bass'], h.roots[ci] + o, dd * self.beat * .95, B, q, vel * (.92 + .1 * self.rng.random()), bright=d2)
                elif name in ('interlude', 'break2') and cst:      # held for exactly one chord
                    if self.real: self.place(L['bass'], self.real_bass(h.roots[ci], cl * self.bar * .9, .5), self.T(B), g=.6)
                    else: self.place(L['bass'], I.bass_note(h.roots[ci], cl * self.bar * .9, .15), self.T(B), g=.6)
                # ---------------- hats / perc
                if drums or name in ('break', 'interlude', 'build'):
                    soft = .45 if not drums else 1.0
                    for (inst, q, v, pan) in PERC[P['perc']]:
                        if drums and fill_bar and q >= 3 and name != 'intro': continue
                        if not drums and inst not in ('shaker', 'tamb', 'bell_hi', 'bell_lo'): continue
                        if drums and (k // 8) % 2 == 1 and inst in ('conga_hi', 'conga_lo', 'bell_hi', 'bell_lo') and self.rng.random() < .25: continue
                        self.place(L['perc'], self.perc_hit(inst, v * soft * (.85 + .3 * self.rng.random())), self.T(B, q, self.hum(3) + self.feel / 1000), pan)
                    if drums:
                        hv = self.hat_vars[(k // 8) % 2] if full or name == 'groove' else HAT_VARIANTS[0]
                        hp = [x for x in HATS[P['hats']] if not any(abs(x[0] - d) < 1e-6 for d in hv['drop'])] + hv['add']
                        for (q, op, v) in hp:
                            if fill_bar and q >= 3: continue
                            if not full and not op and P['hats'] in ('offbeat_ghost',): continue
                            self.place(L['hats'], self.hat_sig(op, v * (.85 + .3 * self.rng.random())), self.T(B, q, self.hum(3) + self.feel / 1000), -.15 if op else .25)
                    if (d2 and 'extra_perc' in drop2) or (name == 'hook' and k >= 8 and 'extra_perc' in drop2):
                        for (inst, q, v, pan) in EXTRA_PERC.get(P['perc'], EXTRA_PERC['default']):
                            self.place(L['perc'], self.perc_hit(inst, v), self.T(B, q, self.hum(4)), pan)
                    if d2 and 'triplet_perc' in drop2:
                        for s3 in range(12):
                            if s3 % 3: self.place(L['perc'], self.perc_hit('wood', .22) if self.real else I.wood(2300, .22), self.T(B, s3 / 3, self.hum(2)), .55)
                # ---------------- backbeat + fills
                if drums and name != 'intro':
                    bb = P['backbeat']
                    for q in ((2,) if P.get('half_time') else (1, 3)):
                        if fill_bar and q == 3: continue
                        hv = .82 + .16 * self.rng.random()
                        if bb == 'clap': self.place(L['clap'], self.clap_sig(.9 * hv), self.T(B, q, self.hum(2)))
                        elif bb == 'snare': self.place(L['clap'], self.snare_sig(.85 * hv), self.T(B, q, self.hum(2)))
                        elif bb == 'snap':
                            if self.real: self.place(L['clap'], SM.drum(self.pal, 'side_stick', .8 * hv).mean(1) * 3.0 + 0, self.T(B, q, self.hum(2)))
                            else: self.place(L['clap'], I.snap(.8 * hv), self.T(B, q, self.hum(2)))
                        else: self.place(L['clap'], self.clap_sig(.55 * hv), self.T(B, q)); self.place(L['perc'], self.perc_hit('rim', .45), self.T(B, q + .02), -.4)
                    if fill_bar: self.fill(L, B)
                if name == 'build':
                    rel = k / nb; step = 1 if rel < .5 else (.5 if rel < .75 else .25)
                    for q in np.arange(0, 4, step):
                        bv = .25 + .7 * (k * 4 + q) / (nb * 4)
                        if self.real: hit = self.snare_sig(bv) if P['backbeat'] == 'snare' or q % 1 else self.clap_sig(bv)
                        else: hit = I.snare(bv, tail=False) if P['backbeat'] == 'snare' else I.clap(bv, tail=False)
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
                        self.comp_bar(L['comp'], comp_pat, comp_inst, chord, B, cv, d2, variant=(k // 8) % 2)
                    if d2 and 'organ_layer' in drop2 and cst:      # held for exactly one chord
                        for v in self.voiced(chord) if self.pal is not None else chord[:4]:
                            self.place(L['comp'], self.voice('organ', v, self.bar * cl * .95, .35), self.T(B), .2)
                    if d2 and 'strings_stab' in drop2:
                        for q in (1.5, 3.5):
                            for v in chord[1:4]:
                                self.place(L['pad'], SM.note(self.pal, 'brass' if self.b['seed'] % 2 else 'strings', v + 12, .3 * self.beat * 2, .6) * 4.0
                                           if self.pal is not None else I.strings_note(v + 12, .3 * self.beat * 2, .45, attack=.01), self.T(B, q, self.hum(4)), .3)
                    if d2 and 'arp_double' in drop2:
                        self.comp_bar(L['comp'], 'arp16', 'glass', [n + 12 for n in chord], B, .45, False, offset=.125)
                # ---------------- melody / hook
                self.melody(L, name, k, nb, B, lead_k, ans_k, focal, every, drop2)
                # ---------------- countermelody (guide tones, kept below the lead register)
                if d2 and 'counter' in drop2:
                    th, sv = h.guides(ci)
                    root = chord[0]
                    tone = C.fold(root + (sv if k % 2 == 0 else th), h.tonic - 5, h.tonic + 6)
                    self.place(L['counter'], self.voice('rhodes' if lead_k != 'rhodes' else 'glass', tone, 3 * self.beat, .55), self.T(B, .5, self.hum(6)), -.3, .6)
                # ---------------- fx
                if self.real:      # real cymbals instead of noise sweeps: reverse-cymbal swell into the drop, crash on it
                    if name == 'build' and k == nb - 1:
                        sw = SM.note(self.pal, 'cymbal_swell', 72, 2.2, .8).mean(1) * 4.0
                        nz = np.nonzero(np.abs(sw) > np.abs(sw).max() * .05)[0]
                        end = (nz[-1] if len(nz) else len(sw)) / SR
                        self.place(L['fx'], sw, self.T(B + 1) - end, .1, g=.8)
                    if name in ('drop1', 'drop2', 'hook') and k == 0:
                        self.place(L['fx'], SM.drum(self.pal, 'crash', .9, dur=1.5) * 3.0, self.T(B), 0, g=.7)
                elif name == 'build' and k == 0:
                    rs = int(nb * self.bar * SR); tr = np.arange(rs) / rs
                    self.place(L['fx'], filt(self.rng.standard_normal(rs), 2500, 'high') * tr ** 2, self.T(B), g=.3)
                if not self.real and name in ('drop1', 'drop2', 'hook') and k == 0:
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

    def vary_bass(self, pat, blk, cl):
        """Small, style-safe changes to the bass pattern in bars 4/8 of alternate phrases (seeded per track)."""
        v = self.bass_var
        if v == 'ghost':                       # a soft ghost note on the last 16th
            return pat + [(3.75, .2, 0, .45)] if not any(abs(p[0] - 3.75) < 1e-6 for p in pat) else pat
        if v == 'octave_push':                 # last note of the bar jumps an octave
            if not pat: return pat
            last = max(range(len(pat)), key=lambda i: pat[i][0]); p = list(pat[last])
            if p[2] >= 12: return pat
            p[2] = p[2] + 12
            return [tuple(p) if i == last else x for i, x in enumerate(pat)]
        if v == 'anticipate' and blk == 7 and cl <= 1:    # lead into the next phrase a 16th early
            return [x for x in pat if x[0] < 3.5] + [(3.5, .25, 7, .8), (3.75, .2, 0, .7)]
        return pat

    def real_bass(self, m, dur, vel):
        """A recorded bass (upright / finger / fretless / pick) with its own low end reinforced by EQ
        (a low-passed copy of the same recording, saturated) — no oscillator."""
        mm = m
        while mm < 28: mm += 12
        g = SM.note(self.pal, 'bass_real', mm, dur, min(1.0, vel)).mean(1) * 4.0
        x = np.tanh(1.2 * (g + .9 * filt(g, 140)))
        r = min(len(x), int(.008 * SR)); x[-r:] *= np.linspace(1, 0, r)
        return x

    def bass_voice(self, dst, m, dur, B, q, vel, bright=False):
        if self.real:
            self.place(dst, self.real_bass(m, dur, .7 * vel + (.15 if bright else 0)) * vel, self.T(B, q)); return
        kind = self.P['bass']
        if kind == 'acid': sig = I.acid_note(m, dur, min(1.0, vel + (.2 if bright else 0)))
        elif kind == 'funk':
            if self.pal is not None:     # recorded bass guitar + a clean sine underneath for club weight
                g = SM.note(self.pal, 'funk_bass', m + 12 if m < 40 else m, dur, .7 * vel + (.15 if bright else 0)).mean(1) * 4.0
                n = len(g); t = np.arange(n) / SR
                sub = np.sin(2 * np.pi * mtof(m) * t) * np.clip(t / .004, 0, 1) * np.where(t > dur, np.exp(-(t - dur) * 40), 1.0)
                sig = np.tanh(1.2 * (g + .55 * sub)) * vel
                r = min(n, int(.008 * SR)); sig[-r:] *= np.linspace(1, 0, r)      # no step at the end of the note
            else:
                sig = I.funk_bass(m, dur, vel)
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

    def comp_bar(self, dst, pat, inst, chord, B, cv, d2, offset=0.0, variant=0):
        if pat == 'arp16':
            tones = sorted(chord[:4]) + [n + 12 for n in sorted(chord[:4])]
            shape = ARP_SHAPES[(self.arp_shape + variant) % len(ARP_SHAPES)]
            for s16 in range(16):
                m = tones[shape[s16 % 8] % len(tones)] + 12
                self.place(dst, self.voice(inst, m, .22 * self.beat, .55 * cv * (1.0 if s16 % 4 == 0 else .82 + .12 * self.rng.random())),
                           self.T(B, s16 * .25 + offset, self.hum(2)), (-.35 if s16 % 2 else .35))
            return
        if pat == 'guitar16':
            for s16 in range(16):
                acc = s16 % 4 == 2; ghost = s16 % 2 == 1
                v = (1.0 if acc else (.35 if ghost else .55)) * cv
                if (s16 % 4 == 0) and self.rng.random() < (.35 if not variant else .6): continue
                if variant and s16 in (7, 15) and self.rng.random() < .5: continue
                self.chord_hit(dst, 'guitar', chord[1:4], self.T(B, s16 * .25, self.hum(2)), .12, v, pan=.35 if s16 % 2 else -.15)
            return
        rows = COMP[pat] if pat in COMP else []
        if pat == self.P['comp'] and self.comp_a is not None:
            rows = self.comp_b if (variant and self.comp_b) else self.comp_a
        for (q, dd, v) in rows:
            self.chord_hit(dst, inst, chord, self.T(B, q, self.hum(3) + self.feel / 1000), dd * self.beat, v * cv)

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
        if self.studio:                                   # studio mode: mastering-bus polish (glue, air, width above 300 Hz)
            mix = comp(mix, -14, 2.0, .02, .25)
            mix = mix + .19 * filt(mix, 10000, 'high')    # ~+1.5 dB high shelf ("air")
            mid = mix.mean(1, keepdims=True); side = (mix[:, :1] - mix[:, 1:]) / 2
            side = side + .12 * filt(side, 300, 'high')
            mix = np.concatenate([mid + side, mid - side], 1)
        fade = int(min(8.0, self.length * .1) * SR); mix[-fade:] *= (np.linspace(1, 0, fade) ** 2)[:, None]
        mix[:int(.02 * SR)] *= np.linspace(0, 1, int(.02 * SR))[:, None]
        out, achieved = master(mix, self.lufs)
        self.meta['achieved_lufs_master'] = achieved
        return out

    def fill(self, L, B):
        f = self.P['fill']
        if f in ('clap_conga', 'clap_roll', 'conga_run') and f != 'conga_run' and (f == 'clap_roll' or (B // 8) % 2 == 0):
            for i, q in enumerate(np.arange(3, 4, .25)): self.place(L['clap'], self.clap_sig(.35 + .15 * i) if self.real else I.clap(.35 + .15 * i, tail=False), self.T(B, q))
        elif f in ('clap_conga', 'conga_run'):
            for i, (q, f0) in enumerate(((3, 260), (3.25, 230), (3.5, 200), (3.75, 170))):
                hit = self.perc_hit(('conga_hi', 'conga_hi', 'conga_lo', 'conga_lo')[i], .6) if self.pal is not None else I.conga(f0, .6)
                self.place(L['perc'], hit, self.T(B, q, self.hum(3)), .5 - .3 * i)
        elif f == 'snare_roll':
            for i, q in enumerate(np.arange(3, 4, .25)): self.place(L['clap'], self.snare_sig(.3 + .15 * i, tail=False), self.T(B, q, self.hum(2)))
        elif f == 'tom_run':
            for i, (q, f0) in enumerate(((3, 190), (3.25, 160), (3.5, 130), (3.75, 100))):
                hit = SM.drum(self.pal, ('tom_hi', 'tom_mid', 'tom_lo', 'tom_lo')[i], .6 + .08 * i).mean(1) * 3.0 if self.pal is not None else I.tom(f0, .55)
                self.place(L['perc'], hit, self.T(B, q, self.hum(3)), .4 - .25 * i)
        elif f == 'marimba_run':
            tones = sorted(self.h.chords[self.ci(B)][:4])
            for i, q in enumerate((3, 3.25, 3.5, 3.75)): self.place(L['answer'], self.voice('marimba', tones[i % len(tones)] + 24, .2, .5), self.T(B, q, self.hum(3)), .3)
        elif f == 'perc_drop':
            for q in (3.25, 3.5, 3.75): self.place(L['perc'], self.perc_hit('rim', .45), self.T(B, q, self.hum(2)), -.4)
        elif f == 'filter_drop':
            for i, q in enumerate(np.arange(3, 4, .25)): self.place(L['clap'], self.clap_sig(.25 + .12 * i) if self.real else I.clap(.25 + .12 * i, tail=False), self.T(B, q))


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
