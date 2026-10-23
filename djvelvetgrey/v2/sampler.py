"""DJ Velvet Grey — sampled instruments (engine v4).

Plays recorded instruments from the FluidR3 GM SoundFont (MIT licence, Frank Wen; Ubuntu package
`fluid-soundfont-gm`) through FluidSynth (`pyfluidsynth`), one note at a time, into numpy arrays that the
engine places, mixes and masters exactly like its synthesised voices. FluidSynth's own reverb/chorus are off:
the engine's mix adds the space.

Each track picks its own *palette* (which piano, which EP, which organ, which bass guitar, which drum kit…)
from the seed, so two tracks of the same style do not share one sound set.
"""
import ctypes, hashlib, os
import numpy as np

SR = 44100
SF2_CANDIDATES = ['/usr/share/sounds/sf2/FluidR3_GM.sf2', '/usr/share/soundfonts/FluidR3_GM.sf2']
SF2_SHA256 = '74594e8f4250680adf590507a306655a299935343583256f3b722c48a1bc1cb0'   # FluidR3_GM.sf2 (Ubuntu fluid-soundfont-gm 3.1)

# kind -> candidate (bank, preset, release_s, octave_shift); None = keep the engine's synth voice.
# The palette chooses one per kind per track. Near-identical presets are not listed twice.
PRESETS = {
    'piano':    [(0, 0, .9, 0), (0, 2, .8, 0)],                       # Yamaha Grand, Electric (stage) Piano
    'rhodes':   [(0, 4, .7, 0), (0, 5, .7, 0), (8, 4, .7, 0)],        # Rhodes EP, Legend EP 2, Detuned EP 1
    'organ':    [(0, 17, .12, 0), (0, 16, .12, 0), (0, 18, .12, 0)],  # Percussive, Drawbar, Rock organ
    'strings':  [(0, 48, .45, 0), (0, 50, .5, 0), (8, 48, .6, 0)],    # Strings, Synth Strings 1, Orchestral Pad
    'brass':    [(0, 61, .2, 0), (8, 61, .2, 0)],                     # Brass Section, Brass 2
    'flute':    [(0, 73, .2, 0), (0, 75, .2, 0)],                     # Flute, Pan Flute
    'guitar':   [(0, 27, .5, 0), (0, 26, .5, 0)],                     # Clean, Jazz guitar
    'guitar_mute': [(0, 28, .08, 0), (8, 28, .08, 0)],                # Palm Muted, Funk Guitar
    'marimba':  [(0, 12, .5, 0), (0, 13, .4, 0)],                     # Marimba, Xylophone
    'steel':    [(0, 114, .6, 0)],
    'kalimba':  [(0, 108, .6, 0)],
    'mallet':   [(0, 11, .8, 0)],                                     # Vibraphone
    'topline':  [(0, 65, .2, 0), (0, 66, .2, -12)],                   # Alto / Tenor sax (instrumental topline)
    'pluck':    [None, (0, 46, .6, 0), (0, 24, .6, 0)],               # synth pluck, Harp, Nylon guitar
    'glass':    [None, (0, 8, .9, 0), (0, 10, .9, 0)],                # FM glass, Celesta, Music Box
    'funk_bass': [(0, 33, .06, 0), (0, 34, .06, 0), (0, 36, .06, 0), (0, 37, .06, 0)],  # Fingered, Picked, Slap, Pop
}
SAMPLED_KINDS = {'piano', 'rhodes', 'organ', 'strings', 'brass', 'flute', 'guitar', 'marimba', 'steel', 'kalimba', 'mallet',
                 'topline', 'pluck', 'glass'}

# "Real instruments only" mode (brief "instruments": "real"): every voice is a recording of an acoustic or
# electro-acoustic instrument. Synth presets (Synth Strings, Orchestral/Detuned pads) and the drum-machine kits
# (Electronic, TR-808) are excluded; the engine's synth parts get real substitutes.
PRESETS_REAL = dict(PRESETS, **{
    'piano':    [(0, 0, .9, 0), (0, 1, .9, 0)],                       # Grand, Bright Grand
    'rhodes':   [(0, 4, .7, 0), (0, 5, .7, 0)],                       # Rhodes EP, Legend EP 2 (electro-mechanical)
    'organ':    [(0, 17, .12, 0), (0, 16, .12, 0), (0, 18, .12, 0)],  # tonewheel organs
    'strings':  [(0, 48, .45, 0), (0, 49, .55, 0)],                   # Strings, Slow Strings
    'pluck':    [(0, 46, .6, 0), (0, 24, .6, 0), (0, 45, .3, 0)],     # Harp, Nylon guitar, Pizzicato strings
    'glass':    [(0, 8, .9, 0), (0, 10, .9, 0), (0, 11, .8, 0)],      # Celesta, Music Box, Vibraphone
    'polysynth': [(0, 4, .7, 0), (0, 61, .2, 0), (0, 48, .45, 0)],    # -> Rhodes, Brass Section, Strings
    'stab':     [(0, 61, .15, 0), (0, 45, .2, 0), (0, 0, .4, 0)],     # -> Brass stab, Pizzicato, Piano
    'rim_synth': [(0, 115, .2, 0), (0, 13, .3, 0)],                   # -> Woodblock, Xylophone
    'choir':    [(0, 52, .8, 0)],                                     # Ahh choir (pads)
    'bass_real': [(0, 32, .08, 0), (0, 33, .06, 0), (0, 35, .08, 0), (0, 34, .06, 0)],  # Upright, Finger, Fretless, Pick
    'kalimba':  [(0, 108, .6, 0)], 'mallet': [(0, 11, .8, 0)], 'marimba': [(0, 12, .5, 0), (0, 13, .4, 0)],
    'cymbal_swell': [(0, 119, .3, 0)],                                # Reverse cymbal (a recorded cymbal, reversed)
})

# "Studio" mode (brief "instruments": "studio"): real mode + the CC0 studio pack (studio.py) wherever it has the
# instrument. ('lib', instrument, release_s, octave_shift). Kinds without a pack instrument keep their FluidR3 recording.
PRESETS_STUDIO = dict(PRESETS_REAL, **{
    'piano':    [('lib', 'piano_steinway', .5, 0)],
    'strings':  [('lib', 'string_section', .6, 0)],
    'brass':    [('lib', 'brass_section', .3, 0)],
    'flute':    [('lib', 'flute', .3, 0), ('lib', 'clarinet', .3, 0)],
    'marimba':  [('lib', 'marimba', .5, 0), ('lib', 'xylophone', .4, 0)],
    'kalimba':  [('lib', 'kalimba', .6, 0)],
    'mallet':   [('lib', 'vibraphone', .8, 0)],
    'topline':  [('lib', 'tenor_sax', .25, 0), (0, 65, .2, 0)],                    # tenor sax (VCSL), alto sax
    'pluck':    [('lib', 'harp', .6, 0), ('lib', 'violin_pizz', .3, 0), (0, 24, .6, 0)],
    'glass':    [('lib', 'glockenspiel', .9, 0), (0, 8, .9, 0), ('lib', 'vibraphone', .8, 0)],
    'polysynth': [(0, 4, .7, 0), ('lib', 'brass_section', .25, 0), ('lib', 'string_section', .5, 0)],
    'stab':     [('lib', 'trumpet_stac', .15, 0), ('lib', 'violin_pizz', .2, 0), ('lib', 'piano_steinway', .3, 0)],
    'rim_synth': [(0, 115, .2, 0), ('lib', 'xylophone', .3, 0)],
    'bass_real': [(0, 32, .08, 0), (0, 33, .06, 0), (0, 35, .08, 0), (0, 34, .06, 0), ('lib', 'upright_bass', .08, 0)],
    'cymbal_swell': [('lib', 'cymbal_swell', .3, 0)],
})
# engine percussion name -> studio-pack one-shot (the kick stays on the FluidR3 kit recordings)
STUDIO_DRUMS = {'clap': 'clap', 'hat': 'hat', 'hat_open': 'hat_open', 'shaker': 'shaker', 'tamb': 'tamb', 'cowbell': 'cowbell',
                'claves': 'claves', 'wood': 'wood', 'wood_lo': 'wood', 'agogo_hi': 'bell_hi', 'agogo_lo': 'bell_lo', 'cabasa': 'cabasa',
                'conga_hi': 'conga_hi', 'conga_lo': 'conga_lo', 'conga_mute': 'conga_hi', 'bongo_hi': 'bongo_hi', 'bongo_lo': 'bongo_lo',
                'snare': 'snare', 'snare2': 'snare', 'snare_ac': 'snare', 'side_stick': 'side_stick', 'rim': 'side_stick',
                'tom_mid': 'tom_mid', 'crash': 'crash', 'crash2': 'crash'}

# GM drum map (channel 10) notes used by the engine's percussion names
DRUM_NOTES = {'kick': 36, 'rim': 37, 'snare': 38, 'clap': 39, 'snare2': 40, 'hat': 42, 'hat_pedal': 44, 'hat_open': 46,
              'tom_lo': 45, 'tom_mid': 47, 'tom_hi': 50, 'tamb': 54, 'cowbell': 56, 'bongo_hi': 60, 'bongo_lo': 61,
              'conga_mute': 62, 'conga_hi': 63, 'conga_lo': 64, 'timbale_hi': 65, 'agogo_hi': 67, 'agogo_lo': 68,
              'cabasa': 69, 'shaker': 70, 'claves': 75, 'wood': 76, 'wood_lo': 77, 'kick_ac': 35, 'snare_ac': 38,
              'crash': 49, 'ride': 51, 'splash': 55, 'crash2': 57, 'side_stick': 37}
KITS = {'standard': [0, 1, 2, 3, 4, 5, 6, 7], 'room': [8, 9, 10, 11], 'electronic': [24], 'tr808': [25], 'jazz': [32, 33, 34]}
# In FluidR3 the hand percussion, clap and hats are the same recordings in every acoustic kit; only TR-808 differs.
# So the audible choices are: acoustic (kit 0) vs 808 (kit 25) vs the engine's synth voice.
REAL_KITS = KITS['standard'] + KITS['room'] + KITS['jazz'] + [16, 17]   # acoustic kits only (+ Power)
BLOCK = 64                                   # FluidSynth renders in 64-sample blocks; every read is block-aligned

_fs = None; _sf = None; _cache = {}


def sf2_path():
    for p in SF2_CANDIDATES:
        if os.path.exists(p): return p
    raise RuntimeError('FluidR3_GM.sf2 not found: apt-get install -y fluid-soundfont-gm fluidsynth')


def available():
    try:
        import fluidsynth  # noqa: F401
        sf2_path(); return True
    except Exception:
        return False


def sf2_sha256():
    h = hashlib.sha256()
    with open(sf2_path(), 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''): h.update(c)
    return h.hexdigest()


_checked = False


def check_soundfont():
    """Fail closed: the exact SoundFont the engine was qualified with (reproducible renders)."""
    global _checked
    if _checked: return
    h = sf2_sha256()
    if h != SF2_SHA256: raise RuntimeError(f'unexpected SoundFont {sf2_path()} (sha256 {h[:12]}..., expected {SF2_SHA256[:12]}...)')
    _checked = True


def _synth():
    global _fs, _sf, _wf
    if _fs is None:
        import fluidsynth
        _fs = fluidsynth.Synth(gain=0.5, samplerate=float(SR), **{'synth.reverb.active': 0, 'synth.chorus.active': 0,
                                                                   'synth.polyphony': 64})
        _sf = _fs.sfload(sf2_path())
        _wf = fluidsynth._fl.fluid_synth_write_float          # float output: no dither, no hidden state between notes
        _wf.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                        ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
        _wf.restype = ctypes.c_int
    return _fs, _sf


_wf = None


def _fresh_synth():
    """FluidSynth keeps internal state between notes (block phase, voice allocation), so a cached note could
    depend on what was rendered before it. A new synth per note (~30 ms; the SoundFont is memory-mapped)
    makes every note a pure function of (preset, key, duration, velocity)."""
    import fluidsynth
    _synth()                                                    # binds write_float once
    fs = fluidsynth.Synth(gain=0.5, samplerate=float(SR), **{'synth.reverb.active': 0, 'synth.chorus.active': 0,
                                                              'synth.polyphony': 64})
    return fs, fs.sfload(sf2_path())


def _take(fs, n):
    """Render n samples (rounded up to whole 64-sample blocks) as float32 stereo."""
    n = int(-(-int(n) // BLOCK) * BLOCK)
    buf = np.zeros((n, 2), np.float32)
    p = buf.ctypes.data
    _wf(fs.synth, n, p, 0, 2, p, 1, 2)
    return buf


def render(bank, preset, key, dur, vel, release=.5, chan=0):
    """One note (or drum hit) -> float32 stereo array. Cached per (preset, key, ~10 ms dur, velocity)."""
    key = int(np.clip(key, 0, 127)); v = int(np.clip(vel, 1, 127)); dq = round(float(dur), 2)
    ck = (bank, preset, chan, key, dq, v, release)
    if ck in _cache: return _cache[ck]
    fs, sf = _fresh_synth()                                   # a brand-new synth per note: same note -> same audio, always
    try:
        fs.program_select(chan, sf, bank, preset)
        fs.noteon(chan, key, v)
        on = _take(fs, max(1, dq * SR))
        fs.noteoff(chan, key)
        tail = _take(fs, release * SR + BLOCK)
    finally:
        fs.delete()
    x = np.concatenate([on, tail])
    r = min(len(tail), int(.02 * SR))                         # short fade at the very end (no truncation click)
    if r > 0: x[-r:] *= np.linspace(1, 0, r)[:, None]
    if len(x) > 32: x[:32] *= np.linspace(0, 1, 32)[:, None]
    global _bytes
    _cache[ck] = x; _bytes += x.nbytes
    if _bytes > 600e6: clear_cache()                          # bounded memory (renders are deterministic, so safe)
    return x


_bytes = 0


def clear_cache():
    global _bytes
    _cache.clear(); _bytes = 0


def midi_vel(vel):
    """Engine velocity (0..~1.2) -> MIDI velocity (sets timbre as well as level in the samples)."""
    return int(np.clip(round(28 + 88 * float(vel)), 12, 124))


class Palette:
    """Per-track sound choices, derived from the seed (recorded in the track meta)."""
    def __init__(self, seed, style, real=False, studio=False):
        r = np.random.default_rng(int(seed) * 7 + 3)
        self.studio = bool(studio); real = real or self.studio
        self.real = bool(real); self.table = PRESETS_STUDIO if self.studio else PRESETS_REAL if real else PRESETS
        self.choice = {k: int(r.integers(len(v))) for k, v in PRESETS.items()}
        drum_pref = {'tech': ['electronic', 'tr808', 'standard'], 'french': ['electronic', 'standard', 'room'],
                     'disco': ['standard', 'room', 'jazz'], 'nudisco': ['standard', 'electronic', 'room'],
                     'soulful': ['standard', 'room', 'jazz'], 'afro': ['standard', 'room'], 'tropical': ['standard', 'room']}
        fam = drum_pref.get(style, ['standard', 'room', 'electronic'])
        self.kit_family = fam[int(r.integers(len(fam)))]
        self.kit = int(r.choice(KITS[self.kit_family]))       # kick/snare/tom samples (these do differ per kit)
        electronic = style in ('tech', 'french', 'nudisco', 'progressive', 'melodic', 'deep', 'house')
        src = ['acoustic', 'synth', 'layer', '808'] if electronic else ['acoustic', 'synth', 'layer']
        self.hats = src[int(r.integers(len(src)))]           # top end: recorded / synth / both / 808 hats
        self.clap = src[int(r.integers(len(src)))]
        self.perc = '808' if (electronic and r.random() < .2) else 'acoustic'     # hand percussion source
        self.kick_layer = float(r.choice([0.0, .25, .4]))    # sampled kick blended under the synth kick
        if self.real:                                         # all-recorded palette (separate stream: v4 choices unchanged)
            rr = np.random.default_rng(int(seed) * 11 + 9)
            self.choice = {k: int(rr.integers(len(v))) for k, v in PRESETS_REAL.items()}
            self.kit = int(rr.choice(REAL_KITS)); self.kit_family = 'acoustic'
            self.hats = self.clap = self.perc = 'acoustic'; self.kick_layer = 1.0
        if self.studio:                                       # studio pack choices (own stream: real-mode choices unchanged)
            rs = np.random.default_rng(int(seed) * 13 + 5)
            self.choice = {k: int(rs.integers(len(v))) for k, v in PRESETS_STUDIO.items()}

    def preset(self, kind):
        return self.table[kind][self.choice[kind]]

    def sampled(self, kind):
        return kind in self.table and self.preset(kind) is not None

    def describe(self):
        fs, sf = _synth(); T = self.table
        name = lambda e: 'synth' if e is None else ('studio:' + e[1]) if e[0] == 'lib' else fs.sfpreset_name(sf, e[0], e[1])
        d = {k: name(T[k][i]) for k, i in self.choice.items()}
        d.update({'drum_kit': fs.sfpreset_name(sf, 128, self.kit), 'hats': self.hats, 'clap': self.clap, 'perc': self.perc,
                  'kick_layer': self.kick_layer})
        return d


def note(pal, kind, m, dur, vel=1.0):
    bank, preset, rel, octv = pal.preset(kind)
    if bank == 'lib':
        import studio
        return studio.render(preset, m + octv, dur, midi_vel(vel), rel)
    return render(bank, preset, m + octv, dur, midi_vel(vel), rel)


def drum(pal, name, vel=1.0, kit=None, dur=.25):
    if getattr(pal, 'studio', False) and name in STUDIO_DRUMS:
        import studio
        return studio.render(STUDIO_DRUMS[name], 60, dur, midi_vel(vel), .3)
    k = pal.kit if kit is None else kit
    return render(128, k, DRUM_NOTES[name], dur, midi_vel(vel), .35, chan=9)


def hand(pal, name, vel=1.0, dur=.25):
    """Hand percussion / hats / clap from the acoustic set (kit 0) or the 808 set (kit 25)."""
    return drum(pal, name, vel, kit=25 if pal.perc == '808' else (pal.kit if pal.real else 0), dur=dur)
