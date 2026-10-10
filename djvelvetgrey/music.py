"""DJ Velvet Grey track generator.

    python3 music.py --style chill|deep --seed N --out track.wav [--title "Name"]

Two house styles taken from Sello's library (58% deep house, 17% melodic house):
  chill - melodic chill house: supersaw pads, plucky arp, four-on-the-floor, airy female vocal
  deep  - vocal deep house: Rhodes stabs, rolling bass, swung shakers/congas, flute or
          kalimba hook, female vocal (Paul Lock / Sharapov / Pete Bellis & Tommy school)
Every seed changes key, tempo, chord progression, melodies, patterns and lead sound.
Output is always exactly 179.0 s (2:59), 44.1 kHz stereo 16-bit.
"""
import argparse, json, numpy as np, scipy.signal as ss
from scipy.io import wavfile

SR = 44100
LEN = 179.0

# ---------------------------------------------------------------- helpers
def mtof(m): return 440 * 2 ** ((m - 69) / 12)

def filt(x, fc, kind='low', order=2):
    sos = ss.butter(order, fc, kind, fs=SR, output='sos')
    return ss.sosfilt(sos, x, axis=0)

def norm(x): return x / (np.abs(x).max() + 1e-9)

CHORD_TYPES = {'m9': [0, 3, 7, 10, 14], 'm7': [0, 3, 7, 10], 'maj9': [0, 4, 7, 11, 14],
               'maj7': [0, 4, 7, 11], 'add9': [0, 4, 7, 14]}
PROGRESSIONS = [
    [(0, 'm9'), (8, 'maj9'), (3, 'maj7'), (10, 'add9')],
    [(0, 'm7'), (5, 'm9'), (8, 'maj7'), (7, 'm7')],
    [(0, 'm9'), (8, 'maj7'), (5, 'm9'), (10, 'add9')],
    [(8, 'maj7'), (10, 'add9'), (0, 'm9'), (0, 'm7')],
    [(0, 'm9'), (3, 'maj7'), (10, 'add9'), (5, 'm7')],
    [(5, 'm9'), (10, 'add9'), (3, 'maj7'), (8, 'maj7')],
    [(0, 'm9'), (10, 'add9'), (8, 'maj7'), (10, 'add9')],
]
VOX_RHYTHMS = [
    [(0.5, 1.5), (2, 1), (3, 1.5), (4.5, 1), (5.5, 2.5), (8.5, 1.5), (10, 1), (11, 1), (12, 3.5)],
    [(0.5, 1), (1.5, 1), (2.5, 1.5), (4, 2), (6, 2), (8.5, 1), (9.5, 1), (10.5, 1.5), (12, 4)],
    [(0.5, 1), (1.5, 1.5), (3, 1), (4.5, 1.5), (6, 2), (8.5, 1), (9.5, 1), (10.5, 1.5), (12, 3.5)],
    [(0, 1.5), (1.5, .5), (2, 2), (4.5, 1), (5.5, 1), (6.5, 1.5), (8, 1.5), (9.5, .5), (10, 2), (12.5, 3)],
    [(0.75, .75), (1.5, 1.5), (3, 1), (4.75, .75), (5.5, 2.5), (8.75, .75), (9.5, 1.5), (11, 1), (12, 4)],
]
HOOK_RHYTHMS = [
    [(0, .75), (.75, .75), (1.5, .5), (2, 1.5), (3.5, .5), (4, .75), (4.75, .75), (5.5, .5), (6, 2),
     (8, .75), (8.75, .75), (9.5, .5), (10, 1.5), (11.5, .5), (12, .75), (12.75, .75), (13.5, 2.5)],
    [(0, .5), (.5, .5), (1, 1), (2, .5), (2.5, 1.5), (4, .5), (4.5, .5), (5, 1), (6, 2),
     (8, .5), (8.5, .5), (9, 1), (10, .5), (10.5, 1.5), (12, .75), (12.75, .75), (13.5, 2.5)],
    [(0.5, .5), (1, .5), (1.5, 1), (2.5, 1.5), (4.5, .5), (5, .5), (5.5, 1), (6.5, 1.5),
     (8.5, .5), (9, .5), (9.5, 1), (10.5, 1.5), (12.5, .5), (13, .5), (13.5, 2.5)],
]
VOWELS = ['a', 'a', 'a', 'o', 'o', 'e', 'u']


class Track:
    def __init__(self, style, seed):
        self.style, self.seed = style, seed
        self.rng = np.random.default_rng(seed)
        r = self.rng
        self.tonic = int(r.integers(55, 61))                     # G3..C4
        self.bpm = int(r.integers(118, 123)) if style == 'chill' else int(r.integers(120, 124))
        self.beat = 60 / self.bpm; self.bar = 4 * self.beat
        self.nbars = int(np.ceil(LEN / self.bar)) + 1
        self.N = int(SR * (self.nbars * self.bar + 4))
        self.swing = 0.0 if style == 'chill' else float(r.uniform(0.025, 0.045))
        prog = PROGRESSIONS[int(r.integers(len(PROGRESSIONS)))]
        self.scale_pcs = {(self.tonic + d) % 12 for d in (0, 2, 3, 5, 7, 8, 10)}
        self.chords, self.roots, self.chord_pcs = [], [], []
        for deg, typ in prog:
            root = self.tonic + deg
            notes = [root + i for i in CHORD_TYPES[typ]]
            while min(notes) > 56: notes = [n - 12 for n in notes]
            while min(notes) < 48: notes = [n + 12 for n in notes]
            self.chords.append(notes)
            b = root % 12 + 24
            while b < 28: b += 12
            self.roots.append(b)
            self.chord_pcs.append({n % 12 for n in notes[:3]} | {notes[0] % 12 + 0})
        self.scale = [m for m in range(36, 100) if m % 12 in self.scale_pcs]
        self.vox_pool = [m for m in self.scale if self.tonic + 8 <= m <= self.tonic + 21]
        self.lead = 'saw' if style == 'chill' else ['flute', 'kalimba'][int(r.integers(2))]
        self.info = {'style': style, 'seed': seed, 'bpm': self.bpm,
                     'key': ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B'][self.tonic % 12] + ' minor',
                     'progression': [f'{d}:{t}' for d, t in prog], 'lead': self.lead}

    # ------------------------------------------------ timing / placement
    def T(self, bar, beat=0.0):
        if self.swing and abs(beat % 0.5 - 0.25) < 1e-6: beat += self.swing
        return bar * self.bar + beat * self.beat

    def zeros(self): return np.zeros((self.N, 2))

    def place(self, dst, sig, t, pan=0.0, g=1.0):
        i = int(round(t * SR))
        if sig.ndim == 1:
            a = (pan + 1) * np.pi / 4
            sig = np.stack([sig * np.cos(a), sig * np.sin(a)], 1) * np.sqrt(2)
        n = min(len(sig), self.N - i)
        if n > 0: dst[i:i + n] += g * sig[:n]

    # ------------------------------------------------ melody writing
    def melody(self, rhythm, pool, start_hint=None):
        r = self.rng; notes = []
        prev = start_hint if start_hint else pool[len(pool) // 2]
        for k, (st, d) in enumerate(rhythm):
            ci = min(int(st // 4), 3)
            pcs = self.chord_pcs[ci]
            last = k == len(rhythm) - 1
            w = []
            for m in pool:
                ct = m % 12 in pcs
                if (d >= 1.5 or last) and not ct: w.append(0); continue
                s = (3.0 if ct else 1.0) * np.exp(-abs(m - prev) / 2.5) * (0.4 if m == prev else 1.0)
                if last and m % 12 != self.chords[ci][0] % 12: s *= 0.35
                w.append(s)
            w = np.array(w) + 1e-9
            m = pool[int(r.choice(len(pool), p=w / w.sum()))]
            notes.append((st, d, m)); prev = m
        return notes

    def vocal_phrases(self):
        r = self.rng
        ia, ib = r.choice(len(VOX_RHYTHMS), 2, replace=False)
        a = self.melody(VOX_RHYTHMS[ia], self.vox_pool)
        b = self.melody(VOX_RHYTHMS[ib], self.vox_pool, start_hint=max(self.vox_pool) - 3)
        add_v = lambda ph: [(st, d, m, VOWELS[int(r.integers(len(VOWELS)))]) for st, d, m in ph]
        return add_v(a), add_v(b)

    def third_below(self, m):
        i = self.scale.index(m); return self.scale[i - 2]

    # ------------------------------------------------ instruments
    def kick(self, soft):
        r = self.rng; t = np.arange(int(0.42 * SR)) / SR
        f = (50 if soft else 46) + (70 if soft else 95) * np.exp(-t * (38 if soft else 32))
        s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * (7.5 if soft else 6.5))
        click = filt(r.standard_normal(len(t)) * np.exp(-t * 600), 4000) * (0.15 if soft else 0.35)
        return np.tanh(1.4 * (s + click))

    def clap(self):
        r = self.rng; t = np.arange(int(0.32 * SR)) / SR
        env = np.exp(-t * 20)
        for d in (0.0, 0.01, 0.02):
            env = np.maximum(env, (t >= d) * np.exp(-np.clip(t - d, 0, None) * 130))
        return filt(filt(r.standard_normal(len(t)), 1000, 'high'), 5500) * env

    def noise_hit(self, dur, hp, dec, lp=None, order=4):
        t = np.arange(int(dur * SR)) / SR
        s = filt(self.rng.standard_normal(len(t)), hp, 'high', order)
        if lp: s = filt(s, lp)
        return s * np.clip(t / 0.003, 0, 1) * np.exp(-t * dec)

    def conga(self, f0):
        t = np.arange(int(0.3 * SR)) / SR
        f = f0 * (1 + 0.4 * np.exp(-t * 60))
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 14)

    def rim(self):
        t = np.arange(int(0.08 * SR)) / SR
        return (np.sin(2 * np.pi * 1750 * t) * .6 + filt(self.rng.standard_normal(len(t)), 2500, 'high') * .4) * np.exp(-t * 90)

    def pad(self, notes, dur, cutoff):
        r = self.rng; n = int((dur + 1.2) * SR); t = np.arange(n) / SR
        out = np.zeros((n, 2))
        for m in notes:
            f = mtof(m)
            for det, pan in ((-0.09, -0.8), (0.0, 0.0), (0.09, 0.8)):
                s = ss.sawtooth(2 * np.pi * (f * 2 ** (det / 12) * t + r.random()))
                a = (pan + 1) * np.pi / 4
                out[:, 0] += s * np.cos(a); out[:, 1] += s * np.sin(a)
        env = np.clip(t / 0.45, 0, 1) * np.where(t > dur, np.exp(-(t - dur) * 3.5), 1.0)
        return filt(out * env[:, None], cutoff) / (len(notes) * 2.2)

    def rhodes(self, m, dur, vel=1.0):
        n = int((dur + 0.8) * SR); t = np.arange(n) / SR; f = mtof(m)
        idx = 1.8 * np.exp(-t * 3.5) + 0.25
        s = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * t))
        s += 0.12 * np.sin(2 * np.pi * 14 * f * t) * np.exp(-t * 25)
        env = np.clip(t / 0.003, 0, 1) * np.exp(-t * 1.1) * np.where(t > dur, np.exp(-(t - dur) * 9), 1.0)
        trem = 1 + 0.18 * np.sin(2 * np.pi * 4.2 * t)
        sig = s * env * vel
        return np.stack([sig * trem, sig * (2 - trem)], 1)

    def chord_stab(self, notes, dur, vel=1.0, cutoff=4000):
        return filt(sum(self.rhodes(m, dur, vel) for m in notes) / len(notes), cutoff)

    def bass_note(self, m, dur, deep):
        n = int((dur + 0.05) * SR); t = np.arange(n) / SR; f = mtof(m)
        s = np.sin(2 * np.pi * f * t) + (0.45 if deep else 0.35) * filt(ss.sawtooth(2 * np.pi * f * t), 380)
        if deep: s = filt(s, 900)
        env = np.clip(t / 0.005, 0, 1) * np.clip((dur + 0.05 - t) / 0.04, 0, 1)
        env *= (0.55 + 0.45 * np.exp(-t * 12)) if deep else np.exp(-t * 2.5)
        return np.tanh(1.4 * s * env)

    def pluck(self, m, dur=0.6, cutoff=3500):
        n = int(dur * SR); t = np.arange(n) / SR; f = mtof(m)
        s = ss.sawtooth(2 * np.pi * f * t) + 0.5 * ss.square(2 * np.pi * f * 1.003 * t)
        return filt(s, cutoff) * np.exp(-t * 9) * np.clip(t / 0.003, 0, 1)

    def flute(self, m, dur):
        n = int((dur + 0.12) * SR); t = np.arange(n) / SR
        vib = 0.16 * np.sin(2 * np.pi * 5.0 * t) * np.clip((t - 0.15) / 0.25, 0, 1)
        f = mtof(m) * 2 ** ((vib - 0.25 * np.exp(-t / 0.03)) / 12)
        ph = np.cumsum(f) / SR
        tone = sum(a * np.sin(2 * np.pi * k * ph) for k, a in ((1, 1.0), (2, .35), (3, .14), (4, .05)))
        br = filt(filt(self.rng.standard_normal(n), mtof(m) * 1.5, 'high'), min(mtof(m) * 5, 18000))
        env = np.clip(t / 0.035, 0, 1) * np.clip((dur + 0.12 - t) / 0.12, 0, 1)
        return (tone + br * (0.3 * np.exp(-t * 18) + 0.07)) * env

    def kalimba(self, m, dur):
        n = int((min(dur, 1.0) + 0.8) * SR); t = np.arange(n) / SR; f = mtof(m)
        s = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 5.4 * f * t) * np.exp(-t * 18)
        s += 0.08 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 6)
        return s * np.clip(t / 0.002, 0, 1) * np.exp(-t * 3.2)

    FORM = {'a': [(850, 90, 1.0), (1220, 100, .55), (2810, 140, .28), (3900, 180, .10)],
            'o': [(520, 70, 1.0), (920, 90, .45), (2820, 140, .14), (3600, 180, .05)],
            'u': [(380, 60, 1.0), (950, 80, .28), (2700, 140, .08), (3500, 180, .04)],
            'e': [(430, 60, 1.0), (2250, 110, .40), (2950, 140, .22), (4000, 180, .08)]}

    def voice(self, m, dur, vowel):
        r = self.rng; n = int((dur + 0.2) * SR); t = np.arange(n) / SR
        scoop = -0.75 * np.exp(-t / 0.055)
        vib = 0.29 * np.sin(2 * np.pi * 5.2 * t) * np.clip((t - 0.23) / 0.35, 0, 1)
        jit = filt(r.standard_normal(n), 6) * 0.6
        f = mtof(m) * 2 ** ((scoop + vib + jit) / 12)
        ph = np.cumsum(f) / SR
        K = int(6000 / mtof(m))
        src = sum(np.sin(2 * np.pi * k * ph) / k ** 1.12 for k in range(1, K + 1))
        src = src + filt(r.standard_normal(n), 2500, 'high') * 0.065
        out = 0.13 * filt(src, 1100)
        for fc, bw, g in self.FORM[vowel]:
            b, a = ss.iirpeak(fc, fc / bw, fs=SR)
            out = out + g * ss.lfilter(b, a, src)
        env = np.clip(t / 0.065, 0, 1) * np.clip((dur + 0.2 - t) / 0.2, 0, 1) ** 1.5
        return out * env

    # ------------------------------------------------ effects
    def reverb(self, x, secs=2.8, decay=2.6, pre=0.03):
        n = int(secs * SR); t = np.arange(n) / SR
        ir = self.rng.standard_normal((n, 2)) * np.exp(-t * decay)[:, None]
        ir = filt(ir, 5500); ir[:int(pre * SR)] = 0
        ir /= np.sqrt((ir ** 2).sum(0))
        m = x.mean(1)
        return np.stack([ss.oaconvolve(m, ir[:, 0])[:self.N], ss.oaconvolve(m, ir[:, 1])[:self.N]], 1)

    def pingpong(self, x, dt, fb=0.38, taps=6):
        d = int(dt * SR); y = np.zeros_like(x); m = filt(x.mean(1), 3500)
        for i in range(1, taps + 1): y[i * d:, i % 2] += fb ** i * m[:self.N - i * d]
        return y

    def sidechain(self, times, depth, rel):
        sc = np.ones(self.N)
        seg = 1 - depth * np.exp(-np.arange(int(0.45 * SR)) / SR / rel)
        for tk in times:
            i = int(tk * SR); n = min(len(seg), self.N - i)
            sc[i:i + n] = np.minimum(sc[i:i + n], seg[:n])
        return sc[:, None]

    # ------------------------------------------------ arrangement
    def section(self, b):
        if b < 8: return 'intro'
        if b < 24: return 'verse'
        if b < 32: return 'build'
        if b < 48: return 'drop'
        if b < 60: return 'break'
        if b < 76: return 'drop2'
        return 'outro'

    def render(self):
        return self.render_chill() if self.style == 'chill' else self.render_deep()

    def sing_all(self, L, A, B):
        def sing(bar, ph, g=1.0, harm=False):
            for st, d, m, v in ph:
                self.place(L['vox'], self.voice(m, d * self.beat, v), self.T(bar, st), g=g)
                if harm:
                    self.place(L['vox'], self.voice(self.third_below(m), d * self.beat, v), self.T(bar, st), g=g * 0.42)
        for s in (8, 16): sing(s, A); sing(s + 4, B)
        for s in (32, 40): sing(s, A); sing(s + 4, B)
        sing(48, A, .82); sing(52, B, .82)
        for s in (60, 68): sing(s, A, 1, True); sing(s + 4, B, 1, True)
        last = A[-1]
        self.place(L['vox'], self.voice(last[2], 7 * self.beat, 'a'), self.T(80, 0.5), g=0.8)
        return sing

    def render_chill(self):
        r = self.rng
        L = {k: self.zeros() for k in ('kick', 'clap', 'hat', 'bass', 'pad', 'pluck', 'vox', 'fx')}
        K, C = self.kick(False), self.clap()
        H, HO = self.noise_hit(0.07, 7500, 55), self.noise_hit(0.25, 7500, 14)
        kick_t = []
        arp = [[0, 2, 4, 2, 1, 3, 4, 3], [0, 1, 2, 3, 4, 3, 2, 1], [0, 2, 1, 3, 2, 4, 3, 1]][int(r.integers(3))]
        bass_oct = bool(r.integers(2))
        for b in range(self.nbars):
            s = self.section(b); ci = b % 4
            cut = {'intro': 450 + 900 * min(b, 8) / 8, 'build': 1200 + 3000 * (b - 24) / 8, 'break': 1300,
                   'drop': 3200, 'drop2': 3200}.get(s, 1700)
            self.place(L['pad'], self.pad(self.chords[ci], self.bar, cut), self.T(b))
            on = s in ('verse', 'drop', 'drop2', 'outro') or (s == 'break' and b >= 56)
            if on:
                for q in range(4): self.place(L['kick'], K, self.T(b, q)); kick_t.append(self.T(b, q))
            if s in ('verse', 'drop', 'drop2', 'outro'):
                for q in (0.5, 1.5, 2.5, 3.5):
                    up = 12 if (q == 2.5 and bass_oct and s != 'verse') else 0
                    self.place(L['bass'], self.bass_note(self.roots[ci] + up, 0.42 * self.beat, False), self.T(b, q))
            if (s == 'intro' and b >= 4) or s in ('verse', 'drop', 'drop2', 'outro'):
                for q in range(4):
                    self.place(L['hat'], HO if s in ('drop', 'drop2') else H, self.T(b, q + .5), .2, .6 if s == 'intro' else 1)
                if s in ('drop', 'drop2'):
                    for q in range(8): self.place(L['hat'], H, self.T(b, q * .5 + .25), -.3, .45)
            if (s == 'verse' and b >= 16) or s in ('drop', 'drop2', 'outro'):
                for q in (1, 3): self.place(L['clap'], C, self.T(b, q))
            if s == 'build' or (s == 'break' and b >= 56):
                rel = (b - 24) if s == 'build' else (b - 56) * 2
                step = 1 if rel < 4 else (.5 if rel < 6 else .25)
                for q in np.arange(0, 4, step):
                    self.place(L['clap'], C, self.T(b, q), g=.3 + .7 * (rel * 4 + q) / 32)
            if s in ('drop', 'drop2', 'break') or (s == 'verse' and b >= 16):
                notes = [m + 12 for m in self.chords[ci]]
                for i, p in enumerate(arp):
                    self.place(L['pluck'], self.pluck(notes[p % len(notes)], cutoff=1800 if s == 'break' else 3500),
                               self.T(b, i * .5), pan=(-.4 if i % 2 else .4))
        A, B = self.vocal_phrases(); sing = self.sing_all(L, A, B)
        sing(24, A, .9)
        self.place(L['vox'], self.voice(B[1][2], 7.5 * self.beat, 'a'), self.T(28, .5), g=.9)
        self.fx(L)
        sc = self.sidechain(kick_t, 0.7, 0.09)
        vox = norm(filt(L['vox'], 180, 'high'))
        vox_wet = norm(self.reverb(vox) * .55 + self.pingpong(vox, .75 * self.beat) * .35)
        mix = (.95 * norm(L['kick']) + .30 * norm(L['clap']) + .10 * norm(self.reverb(L['clap'], 1.2, 5))
               + .13 * norm(L['hat']) + .50 * norm(L['bass']) * sc
               + (.32 * norm(L['pad']) + .18 * norm(self.reverb(L['pad'], 3.5, 1.8))) * sc
               + (.16 * norm(L['pluck']) + .10 * norm(self.pingpong(L['pluck'], .75 * self.beat, .45))) * sc
               + .50 * vox + .26 * vox_wet * sc ** .5 + .20 * norm(L['fx']))
        return self.master(mix)

    def render_deep(self):
        r = self.rng
        L = {k: self.zeros() for k in ('kick', 'clap', 'perc', 'bass', 'keys', 'lead', 'vox', 'fx')}
        K, C, SH, HO, RM = self.kick(True), self.clap(), self.noise_hit(.06, 5000, 70, 11000, 2), self.noise_hit(.2, 8000, 18), self.rim()
        CH, CL = self.conga(240), self.conga(170)
        kick_t = []
        bass_pats = [[(.5, .25, 0), (1.25, .25, 0), (1.5, .5, 0), (2.5, .25, 0), (2.75, .25, 12), (3.5, .5, 0)],
                     [(.5, .5, 0), (1.75, .25, 0), (2.5, .5, 0), (3.25, .25, 12), (3.5, .5, 0)],
                     [(.25, .25, 0), (.75, .5, 0), (1.5, .25, 12), (2.5, .5, 0), (3.25, .5, 0), (3.75, .25, 7)]]
        bp = bass_pats[int(r.integers(len(bass_pats)))]
        stabs = [[(0, 1.4), (1.75, .6), (2.75, 1.1)], [(0, .8), (1.5, .5), (2.5, 1.2), (3.75, .25)],
                 [(.5, 1.0), (2, .5), (2.75, 1.0)]][int(r.integers(3))]
        for b in range(self.nbars):
            s = self.section(b); ci = b % 4
            drums = s != 'break' or b >= 56
            if drums:
                for q in range(4): self.place(L['kick'], K, self.T(b, q)); kick_t.append(self.T(b, q))
            for k in range(16):
                acc = 1.0 if k % 4 == 2 else (.55 if k % 2 else .4)
                self.place(L['perc'], SH, self.T(b, k * .25), .35, acc * (.5 if not drums else 1))
            if drums and (s != 'intro' or b >= 4):
                for q in range(4): self.place(L['perc'], HO, self.T(b, q + .5), -.2, .55)
            if drums and s != 'intro':
                for q in (1, 3): self.place(L['clap'], C, self.T(b, q))
                for q in (.75, 2.25, 3.75): self.place(L['perc'], RM, self.T(b, q), -.5, .35)
            if s in ('build', 'drop', 'drop2'):
                for q, c in ((1.75, CH), (3.25, CL), (3.5, CH)): self.place(L['perc'], c, self.T(b, q), .6, .5)
            if s in ('verse', 'build', 'drop', 'drop2', 'outro'):
                for q, d, o in bp:
                    self.place(L['bass'], self.bass_note(self.roots[ci] + o, d * self.beat * .95, True), self.T(b, q))
            if (s == 'intro' and b >= 4) or s == 'outro':
                self.place(L['keys'], self.chord_stab(self.chords[ci], 1.2 * self.beat, .7, 1800), self.T(b))
            elif s == 'break':
                self.place(L['keys'], self.chord_stab(self.chords[ci], self.bar, .9, 3000), self.T(b))
            elif s in ('verse', 'build', 'drop', 'drop2'):
                for q, d in stabs:
                    self.place(L['keys'], self.chord_stab(self.chords[ci], d * self.beat, 1.0, 3500), self.T(b, q))
        A, B = self.vocal_phrases(); self.sing_all(L, A, B)
        hook_pool = [m for m in self.scale if self.tonic + 10 <= m <= self.tonic + 24]
        hook = self.melody(HOOK_RHYTHMS[int(r.integers(len(HOOK_RHYTHMS)))], hook_pool, start_hint=max(hook_pool) - 2)
        inst = self.flute if self.lead == 'flute' else self.kalimba
        def play(bar, g=1.0, o=0):
            for st, d, m in hook: self.place(L['lead'], inst(m + o, d * self.beat), self.T(bar, st), g=g)
        for s_ in (24, 28): play(s_)
        for s_ in (36, 44): play(s_, .7)
        play(56, .8, -12)
        for s_ in (64, 72, 76, 80): play(s_, .75)
        self.fx(L)
        sc = self.sidechain(kick_t, 0.5, 0.08)
        vox = norm(filt(L['vox'], 180, 'high'))
        vox_wet = norm(self.reverb(vox) * .6 + self.pingpong(vox, .75 * self.beat) * .35)
        ld = norm(filt(L['lead'], 250, 'high'))
        ld_wet = norm(self.reverb(ld, 2.5, 2.8) * .6 + self.pingpong(ld, .75 * self.beat, .4) * .5)
        keys = norm(L['keys'])
        mix = (.95 * norm(L['kick']) + .26 * norm(L['clap']) + .08 * norm(self.reverb(L['clap'], 1.0, 6))
               + .22 * norm(L['perc']) + .58 * norm(L['bass']) * sc
               + (.30 * keys + .12 * norm(self.reverb(keys, 2.2, 3.0))) * sc
               + .30 * ld + .14 * ld_wet * sc + .46 * vox + .22 * vox_wet * sc ** .5 + .18 * norm(L['fx']))
        return self.master(mix)

    def fx(self, L):
        r = self.rng
        t = np.arange(int(3 * SR)) / SR
        crash = filt(r.standard_normal(len(t)), 5200, 'high') * np.exp(-t * 1.5)
        for b in (8, 32, 60): self.place(L['fx'], crash, self.T(b), g=.45)
        rs = int(4 * self.bar * SR); tr = np.arange(rs) / rs
        for b in (28, 56):
            self.place(L['fx'], filt(r.standard_normal(rs), 2800, 'high') * tr ** 2, self.T(b), g=.3)

    def master(self, mix):
        mix = filt(mix, 28, 'high')[:int(LEN * SR)]
        fade = int(8 * SR); mix[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 2
        mix[:int(.03 * SR)] *= np.linspace(0, 1, int(.03 * SR))[:, None]
        mix = np.tanh(1.4 * mix / np.abs(mix).max())
        return mix / np.abs(mix).max() * 0.93


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--style', choices=['chill', 'deep'], required=True)
    ap.add_argument('--seed', type=int, required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    tr = Track(a.style, a.seed)
    mix = tr.render()
    wavfile.write(a.out, SR, (mix * 32767).astype(np.int16))
    tr.info['duration'] = len(mix) / SR
    print(json.dumps(tr.info))
