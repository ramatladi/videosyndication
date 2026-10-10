"""DJ Velvet Grey engine v2 — sound design, groove, arrangement and mix.

Instrumental-first: the melody carries the track. Original synthesis throughout
(PolyBLEP oscillators, filter envelopes, FM bells), per-group mixing, sidechain,
low end kept mono below ~120 Hz, loudness chosen per brief and a true-peak limiter.
"""
import numpy as np, scipy.signal as ss
from scipy.ndimage import minimum_filter1d, uniform_filter1d
import compose as C

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
def cached(key, fn):
    if key not in _cache: _cache[key] = fn()
    return _cache[key]


# ---------------------------------------------------------------- drums (synthesised)
def kick(vel=1.0):
    def mk():
        t = np.arange(int(.5 * SR)) / SR
        f = 47 + 105 * np.exp(-t * 34) + 25 * np.exp(-t * 300)
        body = np.sin(2 * np.pi * np.cumsum(f) / SR)
        amp = np.where(t < .03, 1.0, np.exp(-(t - .03) * 6.0))
        rng = np.random.default_rng(1)
        click = filt(rng.standard_normal(len(t)), 1800, 'high') * np.exp(-t * 900) * .25
        click += np.sin(2 * np.pi * 2600 * t) * np.exp(-t * 600) * .12
        return np.tanh(1.6 * (body * amp + click)) * np.clip(t / .001, 0, 1)
    return cached(('kick',), mk) * vel


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
    return cached(('pad', tuple(notes), round(dur, 3), int(cutoff / 50), seed), mk)


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


# ---------------------------------------------------------------- track
class TrackV2:
    def __init__(self, brief, spec, template=None, length=None, lufs=None):
        self.b = brief; self.spec = spec
        self.bpm = brief['bpm']; self.beat = 60 / self.bpm; self.bar = 4 * self.beat
        self.h, self.hook = C.hook_from_spec(brief, spec)
        self.sections = template or C.TEMPLATES[brief['arc']]
        self.nbars = sum(n for _, n in self.sections)
        self.N = int(SR * (self.nbars * self.bar + 4))
        self.rng = np.random.default_rng(brief['seed'] + 7)
        self.swing = brief.get('groove', {}).get('swing', 0.0)
        self.length = length or LEN
        self.lufs = lufs if lufs is not None else brief.get('loudness_lufs', -10.0)
        self.meta = {'sections': [], 'drop2_changes': [], 'length_s': self.length, 'target_lufs': self.lufs}

    def T(self, bar, beat=0.0, jitter=0.0):
        if self.swing and abs(beat % .5 - .25) < 1e-6: beat += self.swing
        return bar * self.bar + beat * self.beat + jitter

    def zeros(self): return np.zeros((self.N, 2))

    def place(self, dst, sig, t, pan=0.0, g=1.0):
        i = int(round(t * SR))
        if i < 0: sig = sig[-i:]; i = 0
        if sig.ndim == 1:
            a = (pan + 1) * np.pi / 4
            sig = np.stack([sig * np.cos(a), sig * np.sin(a)], 1) * np.sqrt(2)
        n = min(len(sig), self.N - i)
        if n > 0: dst[i:i + n] += g * sig[:n]

    def hum(self, ms=4.0): return float(self.rng.normal(0, ms / 1000))

    def play_phrase(self, dst, notes, bar0, kind, g=1.0, octave=0, pan=0.0, only=None):
        for st, d, m in notes:
            if only is not None and not (only[0] <= st < only[1]): continue
            self.place(dst, lead_note(kind, m + octave, d * self.beat), self.T(bar0, st), pan, g * (.9 + .1 * self.rng.random()))

    def render(self):
        b, h = self.b, self.h
        L = {k: self.zeros() for k in ('kick', 'clap', 'hats', 'perc', 'bass', 'pad', 'lead', 'answer', 'counter', 'fx')}
        kick_t = []
        lead_k, ans_k = b['lead'], b.get('answer', 'flute')
        bass_a = C.GROOVES[b['groove']['bass_a']]; bass_b = C.GROOVES[b['groove'].get('bass_b', 'octave')]
        bar = 0
        for si, (name, nb) in enumerate(self.sections):
            self.meta['sections'].append({'name': name, 'start_bar': bar, 'bars': nb, 'start_s': round(bar * self.bar, 2)})
            for k in range(nb):
                B = bar + k; ci = B % 4; blk = k % 8; last_of_8 = blk == 7
                drums = name in ('hook', 'groove', 'drop1', 'drop2', 'outro') or (name == 'intro' and k >= 1)
                full = name in ('hook', 'drop1', 'drop2')
                # ---- pad
                cut = {'intro': 700 + 900 * k / max(nb, 1), 'build': 1200 + 3500 * k / nb, 'break': 1800, 'break2': 1800,
                       'interlude': 1500, 'groove': 2000, 'outro': 1700}.get(name, 3000)
                self.place(L['pad'], pad_chord(h.chords[ci], self.bar, cut, si), self.T(B))
                # ---- kick + bass
                if drums and not (name == 'outro' and k >= nb - 2):
                    for q in range(4):
                        self.place(L['kick'], kick(.95 if q % 2 == 0 else .88), self.T(B, q)); kick_t.append(self.T(B, q))
                if name in ('hook', 'groove', 'drop1', 'drop2') or (name == 'outro' and k < 8):
                    pat = bass_b if name == 'drop2' else bass_a
                    for q, d, o in pat:
                        self.place(L['bass'], bass_note(h.roots[ci] + o, d * self.beat * .95, .7 if name == 'drop2' else .5), self.T(B, q))
                elif name in ('interlude', 'break2') and k % 2 == 0:
                    self.place(L['bass'], bass_note(h.roots[ci], 2 * self.bar * .9, .15), self.T(B), g=.6)
                # ---- hats / perc with fills every 8 bars
                if drums or name in ('break', 'interlude', 'build'):
                    soft = .45 if not drums else 1.0
                    for s16 in range(16):
                        q = s16 * .25
                        if drums and last_of_8 and q >= 3 and name != 'intro': continue
                        acc = 1.0 if s16 % 4 == 2 else (.5 if s16 % 2 else .32)
                        self.place(L['perc'], shaker(acc * soft * (.85 + .3 * self.rng.random())), self.T(B, q, self.hum(3)), .35)
                    if drums:
                        for q in range(4):
                            if last_of_8 and q == 3: continue
                            self.place(L['hats'], hat(True, .55 + .1 * self.rng.random()), self.T(B, q + .5, self.hum(2)), -.15)
                        if full:
                            for q in (.25, 1.75, 2.25, 3.75):   # ghost closed hats
                                self.place(L['hats'], hat(False, .25 + .15 * self.rng.random()), self.T(B, q, self.hum(3)), .3)
                if drums and name != 'intro':
                    for q in (1, 3):
                        if not (last_of_8 and q == 3): self.place(L['clap'], clap(.9), self.T(B, q))
                    if name in ('drop1', 'drop2', 'groove'):
                        self.place(L['perc'], rim(.35), self.T(B, 2.75 if blk % 2 else .75, self.hum(3)), -.5)
                    if last_of_8:                       # fill: alternate clap roll / conga run
                        if (B // 8) % 2 == 0:
                            for i, q in enumerate(np.arange(3, 4, .25)):
                                self.place(L['clap'], clap(.35 + .15 * i, tail=False), self.T(B, q))
                        else:
                            for i, (q, f0) in enumerate(((3, 260), (3.25, 230), (3.5, 200), (3.75, 170))):
                                self.place(L['perc'], conga(f0, .6), self.T(B, q), .5 - .3 * i)
                if name in ('drop2',) or (name == 'hook' and k >= 8):
                    for q, f0 in ((1.75, 240), (3.25, 175), (3.5, 240)):
                        self.place(L['perc'], conga(f0, .45), self.T(B, q, self.hum(4)), .6)
                # ---- build snare roll
                if name == 'build':
                    rel = k / nb; step = 1 if rel < .5 else (.5 if rel < .75 else .25)
                    for q in np.arange(0, 4, step):
                        self.place(L['clap'], clap(.25 + .7 * (k * 4 + q) / (nb * 4), tail=False), self.T(B, q))
                # ---- melody
                hb = k % 8
                if name == 'intro' and k in (1, 2) and nb >= 4:          # tease: the call, softly, ~2-6 s in
                    self.play_phrase(L['lead'], self.hook['call'], bar + 1, lead_k, g=.55, only=((k - 1) * 4, k * 4))
                if name in ('hook', 'drop1', 'drop2', 'break', 'break2') and hb == 0:
                    oct_ = 12 if (name == 'drop2' and k >= 8) else 0
                    g = .75 if name.startswith('break') else 1.0
                    self.play_phrase(L['lead'], self.hook['lead'], B, lead_k, g=g, octave=oct_)
                    self.play_phrase(L['answer'], self.hook['answer'], B, ans_k, g=g * .8, pan=.25)
                if name == 'groove' and blk == 0:
                    self.play_phrase(L['lead'], self.hook['call'], B, lead_k, g=.8)
                if name == 'build' and k % 2 == 0:
                    self.play_phrase(L['lead'], self.hook['call'], B, lead_k, g=.5 + .4 * k / nb, only=(0, 4))
                if name == 'interlude' and hb == 0:
                    self.play_phrase(L['answer'], self.hook['call'], B, ans_k, g=.7, octave=-12, pan=-.2)
                if name == 'outro' and k in (0, 8):
                    self.play_phrase(L['lead'], self.hook['call'], B, lead_k, g=.6 if k else .8)
                if name == 'drop2':                    # countermelody: guide tones (3rd/7th) under the hook
                    ch = h.chords[ci]
                    guide = ch[1] if k % 2 else (ch[3] if len(ch) > 3 else ch[2])   # 3rd / 7th, below the lead
                    self.place(L['counter'], lead_note('rhodes' if lead_k != 'rhodes' else 'glass', guide, 3 * self.beat),
                               self.T(B, .5), -.3, .6)
                # ---- fx
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
        hb = first(('hook', 'drop1'))
        self.meta['tease_s'] = round(tb * self.bar, 1) if tb is not None else None
        self.meta['full_hook_s'] = round(hb * self.bar, 1) if hb is not None else None
        self.meta['drop2_changes'] = ['bass pattern ' + b['groove']['bass_a'] + ' -> ' + b['groove'].get('bass_b', 'octave'),
                                      'lead up an octave in second half', 'countermelody (guide tones)', 'conga layer']
        return self.mix(L, kick_t)

    # ------------------------------------------------------------ mix
    def mix(self, L, kick_t):
        N = self.N

        def sc(depth, rel):
            env = np.ones(N); seg = 1 - depth * np.exp(-np.arange(int(.4 * SR)) / SR / rel)
            for tk in kick_t:
                i = int(tk * SR); n = min(len(seg), N - i)
                env[i:i + n] = np.minimum(env[i:i + n], seg[:n])
            return env[:, None]

        def rms_db(x):
            a = np.abs(x).mean(1); w = int(.4 * SR)
            r = np.sqrt(np.maximum(uniform_filter1d(a ** 2, w), 0)); act = r[r > r.max() * .05]
            return 20 * np.log10(np.sqrt((act ** 2).mean()) + 1e-12) if len(act) else -120

        def stage(x, target_db): return x * 10 ** ((target_db - rms_db(x)) / 20) if np.abs(x).max() > 0 else x

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

        kick_ = stage(L['kick'], -14)
        bass = stage(np.tanh(1.2 * filt(L['bass'], 30, 'high')), -16.5) * sc(.55, .09)
        drums = comp(stage(L['clap'], -23) + stage(filt(L['hats'], 6000, 'high'), -27) + stage(L['perc'], -25.5), -20, 2)
        pad = stage(filt(L['pad'], 160, 'high'), -23) * sc(.5, .11)
        lead = stage(filt(L['lead'], 220, 'high'), -19)
        answer = stage(filt(L['answer'], 220, 'high'), -23.5)
        counter = stage(filt(L['counter'], 200, 'high'), -27) if np.abs(L['counter']).max() > 0 else L['counter']
        fx = stage(L['fx'], -29)
        send = lead * .35 + answer * .45 + pad * .25 + L['clap'] * .02
        rev = filt(filt(reverb(send, 2.6, 2.4, self.b['seed']), 300, 'high'), 9000) * sc(.3, .15)
        dly = delay(lead + answer * .5, .75) * .22
        mix = kick_ + bass + drums + pad + (lead + answer + counter) * sc(.2, .1) + stage(rev, -24) + stage(dly, -29) + fx
        # low end mono below ~120 Hz (complementary split, so nothing is lost)
        low = ss.sosfiltfilt(ss.butter(4, 120, 'low', fs=SR, output='sos'), mix, axis=0)
        mix = (mix - low) + low.mean(1, keepdims=True)
        mix = filt(mix, 25, 'high')[:int(self.length * SR)]
        fade = int(min(8.0, self.length * .1) * SR); mix[-fade:] *= (np.linspace(1, 0, fade) ** 2)[:, None]
        mix[:int(.02 * SR)] *= np.linspace(0, 1, int(.02 * SR))[:, None]
        return master(mix, self.lufs)


# ---------------------------------------------------------------- master
def true_peak_env(x, os_=4, chunk=1 << 20):
    out = np.zeros(len(x))
    for s in range(0, len(x), chunk):
        a, e = max(0, s - 64), min(len(x), s + chunk + 64)
        up = np.abs(ss.resample_poly(x[a:e].astype(np.float32), os_, 1, axis=0)).max(1)
        pk = up[: (len(up) // os_) * os_].reshape(-1, os_).max(1)
        out[s:min(len(x), s + chunk)] = pk[s - a: s - a + min(chunk, len(x) - s)]
    return out


def limit(x, ceiling_db=-1.5, look_ms=3.0):
    ceil = 10 ** (ceiling_db / 20)
    pk = true_peak_env(x)
    g = np.minimum(1.0, ceil / np.maximum(pk, 1e-9))
    W = int(look_ms / 1000 * SR)
    g = minimum_filter1d(g, size=4 * W + 1)
    g = uniform_filter1d(g, size=2 * W + 1)
    return x * g[:, None]


def master(mix, target_lufs):
    import pyloudnorm as pyln
    meter = pyln.Meter(SR)
    mix = mix * 10 ** ((target_lufs - meter.integrated_loudness(mix)) / 20)
    for _ in range(3):
        mix = limit(mix, -1.5)
        tp = 20 * np.log10(true_peak_env(mix).max() + 1e-12)
        if tp <= -1.3: break
    return mix
