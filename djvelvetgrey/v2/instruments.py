"""DJ Velvet Grey — instruments (all original synthesis; no samples).

Instrumental-first: the melody carries the track. Original synthesis throughout
(PolyBLEP oscillators, filter envelopes, FM bells), per-group mixing, sidechain,
low end kept mono below ~120 Hz, loudness chosen per brief and a true-peak limiter.
"""
import numpy as np, scipy.signal as ss
from scipy.ndimage import minimum_filter1d, uniform_filter1d

SR = 44100
LEN = 179.0


def mtof(m): return 440.0 * 2 ** ((m - 69) / 12)


def filt(x, fc, kind='low', order=2):
    return ss.sosfilt(ss.butter(order, fc, kind, fs=SR, output='sos'), x, axis=0)


# ---------------------------------------------------------------- oscillators & filters
def blep_saw(f, n, phase0=0.0):
    if np.isscalar(f):
        dt = np.full(n, f / SR); ph = (phase0 + np.arange(n) * (f / SR)) % 1.0
    else:
        dt = f / SR; ph = (phase0 + np.cumsum(dt)) % 1.0
    s = 2 * ph - 1
    m = ph < dt; t = ph[m] / dt[m]; s[m] -= (2 * t - t * t - 1)
    m = ph > 1 - dt; t = (ph[m] - 1) / dt[m]; s[m] -= (t * t + 2 * t + 1)
    return s


def blep_square(f, n, phase0=0.0):
    return 0.5 * (blep_saw(f, n, phase0) - blep_saw(f, n, phase0 + 0.5))


def rbj_lp(fc, q):
    w = 2 * np.pi * min(fc, SR * 0.45) / SR; al = np.sin(w) / (2 * q); c = np.cos(w)
    b = np.array([(1 - c) / 2, 1 - c, (1 - c) / 2]); a = np.array([1 + al, -2 * c, 1 - al])
    return b / a[0], a / a[0]


def lp_env(x, fc_env, q=0.8, block=128):
    """Low-pass whose cutoff follows an envelope (block-wise coefficient update)."""
    out = np.empty_like(x); zi = np.zeros(2)
    for i in range(0, len(x), block):
        b, a = rbj_lp(float(max(fc_env[min(i, len(fc_env) - 1)], 40)), q)
        out[i:i + block], zi = ss.lfilter(b, a, x[i:i + block], zi=zi)
    return out


def adsr(n, a, d, s, rel, gate):
    t = np.arange(n) / SR
    e = np.where(t < a, t / max(a, 1e-4), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4)))
    return e * np.where(t > gate, np.exp(-(t - gate) / max(rel, 1e-4)), 1.0)


_cache = {}
ONSET_RAMP = 32                     # 0.7 ms fade-in: noise-onset one-shots must not start with a sample jump (click)
PERC_KEYS = {'rim', 'wood', 'tamb', 'shk', 'hat', 'clap', 'snare', 'snap', 'conga', 'tom', 'bell'}


def cached(key, fn):
    if key not in _cache:
        x = fn()
        if key and key[0] in PERC_KEYS and len(x) > ONSET_RAMP:
            x = np.array(x, copy=True); r = np.linspace(0, 1, ONSET_RAMP)
            x[:ONSET_RAMP] *= r if x.ndim == 1 else r[:, None]
        _cache[key] = x
    return _cache[key]


# ---------------------------------------------------------------- drums (synthesised)
def kick(vel=1.0, kind='four'):
    base, sweep, dec, clk = {'four_soft': (49, 95, 6.5, .2), 'four': (47, 105, 6.0, .25), 'four_hard': (44, 125, 5.0, .38),
                             'afro': (50, 90, 6.8, .18)}.get(kind, (47, 105, 6.0, .25))
    def mk():
        t = np.arange(int(.5 * SR)) / SR
        f = base + sweep * np.exp(-t * 34) + 25 * np.exp(-t * 300)
        body = np.sin(2 * np.pi * np.cumsum(f) / SR)
        amp = np.where(t < .03, 1.0, np.exp(-(t - .03) * dec))
        rng = np.random.default_rng(1)
        click = filt(rng.standard_normal(len(t)), 1800, 'high') * np.exp(-t * 900) * clk
        click += np.sin(2 * np.pi * 2600 * t) * np.exp(-t * 600) * .12
        return np.tanh(1.6 * (body * amp + click)) * np.clip(t / .001, 0, 1)
    return cached(('kick', kind), mk) * vel


def clap(vel=1.0, tail=True):
    def mk():
        rng = np.random.default_rng(2); t = np.arange(int(.4 * SR)) / SR
        env = np.zeros_like(t)
        for d in (0, .008, .017, .027):
            env = np.maximum(env, (t >= d) * np.exp(-np.clip(t - d, 0, None) * 160))
        env = np.maximum(env, (t >= .027) * .35 * np.exp(-np.clip(t - .027, 0, None) * (14 if tail else 40)))
        n = rng.standard_normal(len(t))
        return ss.sosfilt(ss.butter(2, [900, 5200], 'band', fs=SR, output='sos'), n) * env
    return cached(('clap', tail), mk) * vel


def hat(open_=False, vel=1.0):
    def mk():
        t = np.arange(int((.28 if open_ else .07) * SR)) / SR
        s = sum(blep_square(f, len(t)) for f in (205.3, 304.4, 369.6, 522.7, 540.0, 800.0))
        s = ss.sosfilt(ss.butter(4, [7000, 15000], 'band', fs=SR, output='sos'), s)
        return s * np.exp(-t * (13 if open_ else 60)) * np.clip(t / .0008, 0, 1) / 3
    return cached(('hat', open_), mk) * vel


def shaker(vel=1.0):
    def mk():
        rng = np.random.default_rng(3); t = np.arange(int(.07 * SR)) / SR
        s = ss.sosfilt(ss.butter(2, [5000, 12000], 'band', fs=SR, output='sos'), rng.standard_normal(len(t)))
        return s * np.clip(t / .006, 0, 1) * np.exp(-t * 55)
    return cached(('shk',), mk) * vel


def conga(f0, vel=1.0):
    def mk():
        t = np.arange(int(.3 * SR)) / SR; f = f0 * (1 + .45 * np.exp(-t * 55))
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 13)
    return cached(('conga', f0), mk) * vel


def rim(vel=1.0):
    def mk():
        rng = np.random.default_rng(4); t = np.arange(int(.07 * SR)) / SR
        return (np.sin(2 * np.pi * 1700 * t) * .6 + filt(rng.standard_normal(len(t)), 2500, 'high') * .4) * np.exp(-t * 95)
    return cached(('rim',), mk) * vel


# ---------------------------------------------------------------- tonal instruments
def bass_note(m, dur, tone=0.5):
    def mk():
        n = int((dur + .06) * SR); t = np.arange(n) / SR; f = mtof(m)
        sub = np.sin(2 * np.pi * f * t)
        saw = lp_env(blep_saw(f, n), 180 + tone * 1600 * np.exp(-t * 16) + 120, q=1.1)
        env = adsr(n, .004, .18, .65, .03, dur)
        return np.tanh(1.4 * (sub * .9 + saw * .55) * env)
    return cached(('bass', m, round(dur, 3), tone), mk)


def pad_chord(notes, dur, cutoff, seed=0):
    def mk():
        n = int((dur + 1.4) * SR); t = np.arange(n) / SR; rng = np.random.default_rng(seed + 11)
        L = np.zeros(n); R = np.zeros(n)
        for m in notes:
            for k, det in enumerate((-.13, -.06, 0, .06, .13)):
                s = blep_saw(mtof(m) * 2 ** (det / 12), n, rng.random())
                pan = (k - 2) / 2 * .85; a = (pan + 1) * np.pi / 4
                L += s * np.cos(a); R += s * np.sin(a)
        fc = cutoff * (1 + .22 * np.sin(2 * np.pi * .11 * t + seed))
        L, R = lp_env(L, fc, .7), lp_env(R, fc, .7)
        env = adsr(n, .5, 1.0, .9, 1.1, dur)
        return np.stack([L * env, R * env], 1) / (len(notes) * 3.5)
    return cached(('pad', tuple(notes), round(dur, 3), round(float(cutoff), 1), seed), mk)


def lead_note(kind, m, dur, vel=1.0):
    def mk():
        f = mtof(m)
        if kind == 'mallet':          # FM marimba/bell hybrid
            n = int((min(dur, 1.6) + .7) * SR); t = np.arange(n) / SR
            idx = 2.4 * np.exp(-t * 14) + .25
            s = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * 4.0 * f * t))
            s += .35 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 7)
            return s * np.clip(t / .002, 0, 1) * np.exp(-t * 3.0)
        if kind == 'glass':
            n = int((min(dur, 2) + 1.0) * SR); t = np.arange(n) / SR
            s = np.sin(2 * np.pi * f * t + 1.2 * np.exp(-t * 4) * np.sin(2 * np.pi * 7.02 * f * t))
            s += .3 * np.sin(2 * np.pi * 3.01 * f * t) * np.exp(-t * 5)
            return s * np.clip(t / .004, 0, 1) * np.exp(-t * 1.9)
        if kind == 'pluck':
            n = int((dur + .35) * SR); t = np.arange(n) / SR
            s = blep_saw(f, n) + blep_saw(f * 1.0035, n, .3)
            s = lp_env(s, 500 + 5200 * np.exp(-t * 13), .9)
            return s * .5 * adsr(n, .003, .25, .35, .12, dur)
        if kind == 'kalimba':
            n = int((min(dur, 1) + .8) * SR); t = np.arange(n) / SR
            s = np.sin(2 * np.pi * f * t) + .25 * np.sin(2 * np.pi * 5.4 * f * t) * np.exp(-t * 18)
            return s * np.clip(t / .002, 0, 1) * np.exp(-t * 3.2)
        if kind == 'rhodes':
            n = int((dur + .8) * SR); t = np.arange(n) / SR
            idx = 1.8 * np.exp(-t * 3.5) + .25
            s = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * t))
            s += .12 * np.sin(2 * np.pi * 14 * f * t) * np.exp(-t * 25)
            return s * adsr(n, .003, 1.0, .5, .25, dur)
        # flute
        n = int((dur + .14) * SR); t = np.arange(n) / SR; rng = np.random.default_rng(m)
        vib = .15 * np.sin(2 * np.pi * 5 * t) * np.clip((t - .18) / .25, 0, 1)
        ff = f * 2 ** ((vib - .25 * np.exp(-t / .03)) / 12); ph = np.cumsum(ff) / SR
        tone = sum(a * np.sin(2 * np.pi * k * ph) for k, a in ((1, 1), (2, .33), (3, .12), (4, .04)))
        br = ss.sosfilt(ss.butter(2, [min(f * 1.5, 15000), min(f * 5, 18000)], 'band', fs=SR, output='sos'), rng.standard_normal(n))
        return (tone + br * (.28 * np.exp(-t * 16) + .06)) * adsr(n, .035, .3, .85, .1, dur)
    return cached(('lead', kind, m, round(dur, 3)), mk) * vel




# ================================================================ new instruments (style modules)
def noise(n, seed): return np.random.default_rng(seed).standard_normal(n)


def snare(vel=1.0, tail=True):
    def mk():
        t = np.arange(int(.3 * SR)) / SR
        body = np.sin(2 * np.pi * np.cumsum(185 + 60 * np.exp(-t * 40)) / SR) * np.exp(-t * 22)
        sn = ss.sosfilt(ss.butter(2, [1500, 9000], 'band', fs=SR, output='sos'), noise(len(t), 21)) * np.exp(-t * (16 if tail else 35))
        return np.tanh(1.3 * (.55 * body + .9 * sn)) * np.clip(t / .001, 0, 1)
    return cached(('snare', tail), mk) * vel


def snap(vel=1.0):
    def mk():
        t = np.arange(int(.12 * SR)) / SR
        env = np.maximum(np.exp(-t * 90), (t >= .006) * np.exp(-np.clip(t - .006, 0, None) * 60))
        return ss.sosfilt(ss.butter(2, [1800, 7500], 'band', fs=SR, output='sos'), noise(len(t), 22)) * env
    return cached(('snap',), mk) * vel


def tamb(vel=1.0):
    def mk():
        t = np.arange(int(.12 * SR)) / SR
        jing = sum(np.sin(2 * np.pi * f * t) for f in (6800, 8300, 9700, 11200)) / 4
        n = ss.sosfilt(ss.butter(2, [6000, 14000], 'band', fs=SR, output='sos'), noise(len(t), 23))
        return (n * .7 + jing * .5) * np.clip(t / .002, 0, 1) * np.exp(-t * 38)
    return cached(('tamb',), mk) * vel


def tom(f0, vel=1.0):
    def mk():
        t = np.arange(int(.45 * SR)) / SR
        f = f0 * (1 + .6 * np.exp(-t * 30))
        s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)
        s += filt(noise(len(t), int(f0)), 3000) * np.exp(-t * 60) * .15
        return np.tanh(1.2 * s)
    return cached(('tom', f0), mk) * vel


def wood(f0=1900, vel=1.0):
    def mk():
        t = np.arange(int(.06 * SR)) / SR
        return (np.sin(2 * np.pi * f0 * t) + .4 * np.sin(2 * np.pi * f0 * 2.7 * t)) * np.exp(-t * 110)
    return cached(('wood', f0), mk) * vel


def bell(f0, vel=1.0):
    def mk():
        t = np.arange(int(.35 * SR)) / SR
        s = np.sin(2 * np.pi * f0 * t + 1.6 * np.exp(-t * 20) * np.sin(2 * np.pi * f0 * 1.41 * t))
        return s * np.exp(-t * 12) * np.clip(t / .001, 0, 1)
    return cached(('bell', f0), mk) * vel


def acid_note(m, dur, accent=1.0):
    def mk():
        n = int((dur + .05) * SR); t = np.arange(n) / SR; f = mtof(m)
        s = blep_saw(f, n) * .7 + blep_square(f, n) * .3
        fc = 220 + 2600 * accent * np.exp(-t * (14 - 6 * accent))
        y = lp_env(s, fc, q=4.5 + 2 * accent)
        return np.tanh(1.6 * y * adsr(n, .003, .12, .7, .02, dur))
    return cached(('acid', m, round(dur, 3), round(accent, 2)), mk)


def funk_bass(m, dur, vel=1.0):
    def mk():
        n = int((dur + .05) * SR); t = np.arange(n) / SR; f = mtof(m)
        sub = np.sin(2 * np.pi * f * t)
        body = lp_env(blep_saw(f, n) * .6 + blep_square(f, n) * .4, 300 + 3200 * np.exp(-t * 22), q=1.6)
        pop = np.sin(2 * np.pi * 4 * f * t) * np.exp(-t * 60) * .25
        return np.tanh(1.5 * (sub * .8 + body * .6 + pop) * adsr(n, .002, .14, .55, .03, dur))
    return cached(('funk', m, round(dur, 3)), mk) * vel


def piano_note(m, dur, vel=1.0):
    def mk():
        n = int((min(dur, 2.5) + .6) * SR); t = np.arange(n) / SR; f = mtof(m)
        B = 0.0004
        s = sum((1 / k ** 1.1) * np.sin(2 * np.pi * f * k * np.sqrt(1 + B * k * k) * t) * np.exp(-t * (1.2 + .55 * k)) for k in range(1, 9))
        s += filt(noise(n, m), 4000) * np.exp(-t * 120) * .08
        return s * np.where(t > dur, np.exp(-(t - dur) * 12), 1.0) * np.clip(t / .002, 0, 1)
    return cached(('piano', m, round(dur, 3)), mk) * vel


def organ_note(m, dur, vel=1.0):
    def mk():
        n = int((dur + .1) * SR); t = np.arange(n) / SR; f = mtof(m)
        vib = 1 + .003 * np.sin(2 * np.pi * 6.5 * t)
        s = sum(a * np.sin(2 * np.pi * f * h * vib * t) for h, a in ((.5, .5), (1, 1), (2, .6), (3, .35), (4, .25), (6, .12)))
        s += np.sin(2 * np.pi * f * 3 * t) * np.exp(-t * 25) * .3            # percussion click
        return s * adsr(n, .005, .2, .85, .05, dur) * .5
    return cached(('organ', m, round(dur, 3)), mk) * vel


def strings_note(m, dur, vel=1.0, attack=.25):
    def mk():
        n = int((dur + .5) * SR); t = np.arange(n) / SR; f = mtof(m); rng = np.random.default_rng(m)
        vib = 2 ** ((.08 * np.sin(2 * np.pi * 5.2 * t + rng.random() * 6)) / 12)
        s = sum(blep_saw(f * vib * 2 ** (d / 1200), n, rng.random()) for d in (-9, -3, 3, 9)) / 4
        s = lp_env(s, 2200 + 1800 * np.clip(t / max(attack, .01), 0, 1), q=.7)
        return s * adsr(n, attack, .5, .9, .35, dur)
    return cached(('strings', m, round(dur, 3), attack), mk) * vel


def brass_note(m, dur, vel=1.0):
    def mk():
        n = int((dur + .15) * SR); t = np.arange(n) / SR; f = mtof(m)
        s = blep_saw(f, n) + .6 * blep_saw(f * 1.004, n, .3)
        s = lp_env(s, 600 + 3800 * (1 - np.exp(-t * 30)) * np.exp(-t * 2.5), q=1.1)
        return s * adsr(n, .02, .2, .75, .08, dur) * .6
    return cached(('brass', m, round(dur, 3)), mk) * vel


def guitar_note(m, dur, vel=1.0, mute=True):
    """Karplus-Strong plucked string; muted = short funk 'chick'."""
    def mk():
        f = mtof(m); N = int(SR / f); n = int((min(dur, .4 if mute else 1.2) + .05) * SR)
        buf = noise(N, m) * .5; out = np.zeros(n); damp = .45 if mute else .497
        for i in range(n):
            out[i] = buf[i % N]
            buf[i % N] = damp * (buf[i % N] + buf[(i + 1) % N])
        return filt(out, 4500) * (np.exp(-np.arange(n) / SR * (28 if mute else 3)))
    return cached(('gtr', m, round(dur, 2), mute), mk) * vel


def stab_note(m, dur, vel=1.0):
    def mk():
        n = int((dur + .1) * SR); t = np.arange(n) / SR; f = mtof(m)
        s = blep_saw(f, n) + blep_saw(f * 1.006, n, .5) + .5 * blep_square(f * .5, n)
        return lp_env(s, 300 + 4200 * np.exp(-t * 18), q=2.2) * adsr(n, .002, .1, .3, .05, dur) * .5
    return cached(('stab', m, round(dur, 3)), mk) * vel


def polysynth_note(m, dur, vel=1.0):
    def mk():
        n = int((dur + .25) * SR); t = np.arange(n) / SR; f = mtof(m)
        s = sum(blep_saw(f * 2 ** (d / 1200), n, i * .21) for i, d in enumerate((-12, -4, 4, 12))) / 3
        s = lp_env(s, 900 + 3000 * np.exp(-t * 5), q=1.0)
        return s * adsr(n, .01, .3, .7, .15, dur)
    return cached(('poly', m, round(dur, 3)), mk) * vel


def topline_note(m, dur, vel=1.0):
    """Legato, voice-like lead line (an instrumental topline, not a vocal)."""
    def mk():
        n = int((dur + .2) * SR); t = np.arange(n) / SR
        vib = .25 * np.sin(2 * np.pi * 5.3 * t) * np.clip((t - .2) / .3, 0, 1)
        ff = mtof(m) * 2 ** ((vib - .4 * np.exp(-t / .05)) / 12); ph = np.cumsum(ff) / SR
        s = sum(a * np.sin(2 * np.pi * k * ph) for k, a in ((1, 1), (2, .5), (3, .3), (4, .18), (5, .1)))
        s = ss.lfilter(*ss.iirpeak(1100, 2.5, fs=SR), s) * .6 + s * .5
        return s * adsr(n, .06, .4, .85, .15, dur) * .7
    return cached(('top', m, round(dur, 3)), mk) * vel


def marimba_note(m, dur, vel=1.0):
    def mk():
        n = int((min(dur, .8) + .5) * SR); t = np.arange(n) / SR; f = mtof(m)
        s = np.sin(2 * np.pi * f * t) + .45 * np.sin(2 * np.pi * 3.93 * f * t) * np.exp(-t * 25) + .2 * np.sin(2 * np.pi * 9.2 * f * t) * np.exp(-t * 60)
        return s * np.exp(-t * 5.5) * np.clip(t / .001, 0, 1)
    return cached(('marimba', m, round(dur, 3)), mk) * vel


def steel_note(m, dur, vel=1.0):
    def mk():
        n = int((min(dur, 1.0) + .7) * SR); t = np.arange(n) / SR; f = mtof(m)
        s = np.sin(2 * np.pi * f * t + 1.1 * np.exp(-t * 6) * np.sin(2 * np.pi * f * 2.0 * t))
        s += .35 * np.sin(2 * np.pi * f * 2.99 * t) * np.exp(-t * 7) + .2 * np.sin(2 * np.pi * f * 4.1 * t) * np.exp(-t * 12)
        return s * np.exp(-t * 3.2) * np.clip(t / .002, 0, 1)
    return cached(('steel', m, round(dur, 3)), mk) * vel


def rimsynth_note(m, dur, vel=1.0):
    def mk():
        n = int(.18 * SR); t = np.arange(n) / SR; f = mtof(m)
        return (np.sin(2 * np.pi * f * t) + .5 * np.sin(2 * np.pi * 2.76 * f * t)) * np.exp(-t * 28)
    return cached(('rimsyn', m), mk) * vel


NEW_LEADS = {'piano': piano_note, 'organ': organ_note, 'strings': strings_note, 'brass': brass_note,
             'polysynth': polysynth_note, 'topline': topline_note, 'marimba': marimba_note, 'steel': steel_note,
             'stab': stab_note, 'rim_synth': rimsynth_note, 'guitar': lambda m, d, v=1.0: guitar_note(m, d, v, mute=False)}


def note(kind, m, dur, vel=1.0):
    """Any melodic instrument by name (original v2 voices + new style voices)."""
    if kind in NEW_LEADS: return NEW_LEADS[kind](m, dur, vel)
    if kind not in LEAD_KINDS: raise ValueError(f'unknown instrument {kind!r} (known: {sorted(KNOWN)})')
    return lead_note(kind, m, dur, vel)


LEAD_KINDS = {'mallet', 'glass', 'pluck', 'kalimba', 'rhodes', 'flute'}
KNOWN = LEAD_KINDS | set(NEW_LEADS)
