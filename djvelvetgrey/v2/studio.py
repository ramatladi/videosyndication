"""Studio mode (brief "instruments": "studio"): engine v4's real-instruments mode with the best free recordings.

Plays the curated CC0 "studio pack" (VSCO 2 Community Edition + Versilian Community Sample Library, built by
djvelvetgrey/tools/build_studio_pack.py and hosted on the repo's `samples` branch) wherever it has an instrument:
Steinway B grand, string sections, brass, flute, clarinet, tenor sax, harp, pizzicato, upright bass, vibraphone,
marimba, xylophone, glockenspiel, kalimba, hand percussion, hi-hats, claps, snare, cymbals. Everything else (electric
piano, organ, guitars, electric bass, kick drum, choir) stays on the FluidR3 recordings of real mode.

Every note is a pure function of (instrument, key, duration, velocity): region choice, round-robin and pitch shift
are deterministic, so renders are reproducible.
"""
import hashlib, json, os
from fractions import Fraction
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
PACK_CANDIDATES = [os.environ.get('DVG_STUDIO_PACK', ''), os.path.join(os.path.dirname(os.path.dirname(HERE)), 'studio_pack'),
                   '/home/claude/studio_pack', '/tmp/studio_pack']
# ensembles: one playable instrument built from section recordings, chosen by register (no big pitch shifts)
ENSEMBLES = {
    'string_section': [('celli', 0, 52), ('violas', 53, 63), ('violins', 64, 127)],
    'brass_section': [('trombone', 0, 57), ('horn', 58, 64), ('trumpet', 65, 127)],
}
# kinds that hold while the key is down (the rest ring out naturally and are damped at note-off)
SUSTAINED = {'violins', 'violas', 'celli', 'trumpet', 'horn', 'trombone', 'flute', 'clarinet', 'tenor_sax'}

_index = None; _root = None; _wav = {}; _shift = {}; _cache = {}; _bytes = 0


def pack_dir():
    for p in PACK_CANDIDATES:
        if p and os.path.exists(os.path.join(p, 'index.json')): return p
    return None


def available():
    return pack_dir() is not None


def index():
    global _index, _root
    if _index is None:
        _root = pack_dir()
        if _root is None:
            raise RuntimeError('studio pack not found: git clone --depth 1 -b samples https://github.com/ramatladi/videosyndication '
                               '/home/claude/studio_pack (or set DVG_STUDIO_PACK)')
        _index = json.load(open(os.path.join(_root, 'index.json')))
    return _index


def pack_sha():
    """Content hash of the pack index (recorded in track meta for reproducibility)."""
    index()
    return hashlib.sha256(open(os.path.join(_root, 'index.json'), 'rb').read()).hexdigest()


def instruments():
    return set(index()['instruments']) | set(ENSEMBLES)


def _load(rel):
    if rel not in _wav:
        x, sr = sf.read(os.path.join(_root, rel), always_2d=True, dtype='float32')
        _wav[rel] = x
    return _wav[rel]


def _shifted(rel, semis):
    """Sample transposed by `semis` semitones (exact rational resampling; cached)."""
    k = (rel, round(semis, 3))
    if k not in _shift:
        x = _load(rel)
        if abs(semis) < 1e-6: y = x
        else:
            fr = Fraction(2 ** (semis / 12)).limit_denominator(400)       # pitch ratio p/q -> resample by q/p
            y = resample_poly(x, fr.denominator, fr.numerator, axis=0).astype('float32')
        _shift[k] = y
    return _shift[k]


def _region(inst, key, vel):
    regs = index()['instruments'][inst]['regions']
    inkey = [r for r in regs if r['lokey'] <= key <= r['hikey']]
    if not inkey:                                          # outside the sampled range: nearest sampled note
        kc = min({r['key'] for r in regs}, key=lambda k: abs(k - key))
        inkey = [r for r in regs if r['key'] == kc]
    layer = [r for r in inkey if r['lovel'] <= vel <= r['hivel']]
    if not layer:
        lv = min({r['lovel'] for r in inkey}, key=lambda v: abs(v - vel))
        layer = [r for r in inkey if r['lovel'] == lv]
    layer.sort(key=lambda r: (r['key'], r['rr']))
    return layer


def resolve(inst, key):
    for name, lo, hi in ENSEMBLES.get(inst, []):
        if lo <= key <= hi: return name
    return inst


def render(inst, key, dur, vel, release=.4):
    """One note -> float32 stereo array (same contract as sampler.render). vel is MIDI 1..127."""
    global _bytes
    key = int(np.clip(key, 0, 127)); vel = int(np.clip(vel, 1, 127)); dq = round(float(dur), 2)
    ck = (inst, key, dq, vel, release)
    if ck in _cache: return _cache[ck]
    name = resolve(inst, key)
    kind = index()['instruments'][name]['kind']
    layer = _region(name, key, vel)
    h = int(hashlib.md5(f'{name}|{key}|{dq}|{vel}'.encode()).hexdigest(), 16)
    r = layer[h % len(layer)]
    x = _shifted(r['file'], 0 if kind == 'oneshot' else key - r['key'])
    span = max(1, r['hivel'] - r['lovel'])
    g = .72 + .28 * (vel - r['lovel']) / span               # within-layer dynamics (the layers carry the timbre)
    g *= index()['instruments'][name].get('gain', 1.0)
    if kind == 'oneshot':                                  # drums: natural decay, choked after dur + release
        n_on = int(dq * SR); n_rel = int(max(.03, release) * SR)
        y = x[:n_on + n_rel].copy()
        if len(y) > n_on: y[n_on:] *= np.exp(-np.arange(len(y) - n_on) / SR / (release / 3))[:, None]
    else:
        n_on = int(dq * SR); n_rel = int(max(.03, release) * SR)
        y = x[:n_on + n_rel].copy()
        if len(y) > n_on:                                  # note-off: release (sustained) or damping (struck/plucked)
            tail = len(y) - n_on
            t = np.arange(tail) / SR
            tau = release / 4 if name in SUSTAINED else max(.06, release / 6)
            y[n_on:] *= np.exp(-t / tau)[:, None]
    f = min(len(y) // 4, int(.01 * SR))
    if f > 0: y[-f:] *= np.linspace(1, 0, f)[:, None]
    if len(y) > 32: y[:32] *= np.linspace(0, 1, 32)[:, None]
    y *= g
    _cache[ck] = y; _bytes += y.nbytes
    if _bytes > 500e6: clear_cache()
    return y


def clear_cache():
    global _bytes
    _cache.clear(); _shift.clear(); _bytes = 0
