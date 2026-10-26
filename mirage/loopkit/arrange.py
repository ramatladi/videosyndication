"""Mirage loop arranger: builds a 2:59 instrumental from loops played by real producers (Looperman library).

Replaces the note-by-note engine for Mirage (Sello, 26 Oct 2026: "it sounds AI-ish" / "it's bad"). Human-played
drum, bass, chord, melody and pad loops carry the groove; this script only chooses, time-stretches (Rubber Band R3),
key-matches (pitch shift of at most +-3 semitones), levels, arranges, ducks and masters them.

Library layout (private: Looperman forbids redistributing loops "as is"; never commit loops to a public repo):
    <lib>/<category>/<category>_<bpm>bpm_<key|nokey>_looperman-....wav  (+ optional loops-<category>.csv)
    categories: drums, bass, keys, melody, pad, fx

    python3 mirage/loopkit/arrange.py --lib /home/claude/loops --seed 7 --out out/test.wav [--bpm 122] [--key Am]
Writes the master WAV plus <out>.json (loops used with Looperman ids/urls, key, bpm, sections, LUFS).
"""
import argparse, glob, hashlib, json, os, re, subprocess, tempfile
import numpy as np, scipy.signal as ss, soundfile as sf
from scipy.ndimage import minimum_filter1d, uniform_filter1d

SR = 44100
LEN = 179.0
CATS = ['drums', 'bass', 'keys', 'melody', 'melody2', 'pad', 'vocals', 'fx']
NOTES = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
TARGET_RMS = {'drums': -14.0, 'tops': -23.0, 'bass': -16.5, 'keys': -21.0, 'melody': -18.5, 'pad': -23.0, 'fx': -24.0, 'melody2': -20.0, 'vocals': -20.0}


# ---------------------------------------------------------------- library
def parse_key(tok):
    """'Am', 'A#m', 'Cmaj', 'F#', 'Bbmin', 'nokey' -> (pc, 'minor'|'major') or None"""
    m = re.fullmatch(r'([A-Ga-g])([#b]?)(m|min|minor|maj|major)?', tok.strip())
    if not m: return None
    pc = (NOTES[m.group(1).upper()] + {'#': 1, 'b': -1, '': 0}[m.group(2)]) % 12
    q = (m.group(3) or 'maj').lower()
    return pc, ('minor' if q in ('m', 'min', 'minor') else 'major')


def library(root):
    meta = {}
    for csvf in glob.glob(os.path.join(root, '*', 'loops-*.csv')):
        import csv
        for r in csv.DictReader(open(csvf)): meta[r['file']] = r
    lib = {c: [] for c in CATS}
    for f in sorted(glob.glob(os.path.join(root, '*', '*.wav'))):
        if os.sep + '_' in f[len(root):]: continue          # _unverified/ and other set-aside folders
        b = os.path.basename(f); parts = b.split('_')
        cat = parts[0]
        if cat not in lib or len(parts) < 3: continue
        try: bpm = float(parts[1].replace('bpm', ''))
        except ValueError: continue
        info = sf.info(f)
        beats = info.frames / info.samplerate * bpm / 60
        nb = int(round(beats))
        if abs(beats - nb) > .08 or nb % 4: continue           # only bar-exact loops
        m = meta.get(b, {})
        lib[cat].append({'file': f, 'name': b, 'cat': cat, 'bpm': bpm, 'key': parse_key(parts[2]), 'beats': nb,
                         'id': m.get('looperman_id', ''), 'title': m.get('title', ''), 'uploader': m.get('uploader', ''),
                         'url': m.get('url', '')})
    return lib


def kick_ratio(x):
    """share of energy below 120 Hz: tells full drum loops (with kick) from top loops."""
    sos = ss.butter(4, 120, 'lp', fs=SR, output='sos')
    lo = ss.sosfilt(sos, x.mean(1))
    return float(np.mean(lo ** 2) / (np.mean(x.mean(1) ** 2) + 1e-12))


# ---------------------------------------------------------------- DSP
def stretch(item, bpm, semis=0, cache='/tmp/loopkit_cache'):
    """Loop at the target tempo (and key): Rubber Band R3, then cut to the exact bar length so it loops seamlessly."""
    os.makedirs(cache, exist_ok=True)
    h = hashlib.md5(f"{item['file']}|{bpm}|{semis}".encode()).hexdigest()[:16]
    out = os.path.join(cache, h + '.wav')
    if not os.path.exists(out) and abs(item['bpm'] - bpm) < 1e-6 and semis == 0:
        out = item['file']                                   # already at tempo and in key: untouched
    if not os.path.exists(out):
        ratio = item['bpm'] / bpm
        cmd = ['rubberband', '-q', '-3', '-T', f'{1 / ratio:.6f}', '-p', str(semis)]
        subprocess.run(cmd + [item['file'], out], check=True, capture_output=True)
    x, sr = sf.read(out, always_2d=True, dtype='float32')
    if sr != SR: x = ss.resample_poly(x, SR, sr, axis=0).astype('float32')
    if x.shape[1] == 1: x = np.repeat(x, 2, 1)
    n = int(round(item['beats'] * 60 / bpm * SR))
    x = x[:n] if len(x) >= n else np.pad(x, ((0, n - len(x)), (0, 0)))
    f = 64; x[-f:] *= np.linspace(1, .0, f)[:, None] ** .5; x[:f] *= np.linspace(0, 1, f)[:, None] ** .5   # click-free seam
    return x


def rms_db(x):
    return float(20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9))


def level(x, target):
    return x * 10 ** ((target - rms_db(x)) / 20)


def filt(x, kind, fc, order=2):
    fc = float(np.clip(fc, 20, SR / 2 - 100))
    return ss.sosfilt(ss.butter(order, fc, kind, fs=SR, output='sos'), x, axis=0).astype('float32')


def sweep(x, kind, f0, f1, steps=32):
    """time-varying filter in short steps (log sweep f0 -> f1)."""
    y = np.zeros_like(x); n = len(x); edges = np.linspace(0, n, steps + 1).astype(int)
    for i in range(steps):
        fc = f0 * (f1 / f0) ** (i / max(1, steps - 1))
        a, b = max(0, edges[i] - 2048), edges[i + 1]
        y[edges[i]:b] = filt(x[a:b], kind, fc)[edges[i] - a:]
    return y


def true_peak_env(x, os_=4):
    up = np.abs(ss.resample_poly(x.astype(np.float32), os_, 1, axis=0)).max(1)
    return up[: (len(up) // os_) * os_].reshape(-1, os_).max(1)[:len(x)]


def limit(x, ceiling_db=-2.8, look_ms=3.0, release_ms=60.0):
    ceil = 10 ** (ceiling_db / 20)
    pk = true_peak_env(x)
    g = np.minimum(1.0, ceil / np.maximum(pk, 1e-9))
    W = int(look_ms / 1000 * SR)
    g = minimum_filter1d(g, size=4 * W + 1)
    a = np.exp(-1 / (release_ms / 1000 * SR))
    g = np.minimum(g, ss.lfilter([1 - a], [1, -a], g, zi=[g[0] * a])[0])
    g = uniform_filter1d(g, size=2 * W + 1)
    return x * g[:, None]


def glue(x, thr_db=-10, ratio=1.6, att=.01, rel=.15):
    env = np.abs(x).max(1)
    a1, a2 = np.exp(-1 / (att * SR)), np.exp(-1 / (rel * SR))
    e = ss.lfilter([1 - a2], [1, -a2], env)
    e = np.maximum(e, ss.lfilter([1 - a1], [1, -a1], env))
    lvl = 20 * np.log10(e + 1e-9)
    gr = np.minimum(0, (thr_db - lvl) * (1 - 1 / ratio))
    return x * (10 ** (gr / 20))[:, None]


def master(mix, target_lufs):
    import pyloudnorm as pyln
    meter = pyln.Meter(SR)
    mix = glue(mix)
    for _ in range(4):
        cur = meter.integrated_loudness(mix)
        mix = mix * 10 ** ((target_lufs - cur) / 20)
        mix = limit(mix)
        ach = meter.integrated_loudness(mix)
        if abs(ach - target_lufs) < .3: break
    return mix.astype('float32'), round(float(ach), 2)


# ---------------------------------------------------------------- arrangement
FORMS = {   # arrangement shapes (bars); drops and outro absorb the 2:59 remainder
    'classic':      [('intro', 16), ('build', 8), ('drop1', 16), ('break', 16), ('build2', 8), ('drop2', 16)],
    'early_drop':   [('intro', 8), ('drop1', 16), ('break', 8), ('build2', 8), ('drop2', 24)],
    'hook_first':   [('tease', 4), ('build', 4), ('drop1', 16), ('break', 16), ('build2', 8), ('drop2', 16)],
    'long_groove':  [('intro', 16), ('drop1', 24), ('break', 8), ('build2', 8), ('drop2', 16)],
    'double_break': [('intro', 8), ('build', 8), ('drop1', 16), ('break', 8), ('drop1', 8), ('break', 8), ('build2', 8), ('drop2', 16)],
}
STYLE_FORMS = {'deep': ['classic', 'long_groove', 'double_break'], 'melodic': ['classic', 'double_break', 'long_groove'],
               'afro': ['long_groove', 'classic', 'double_break'], 'tech': ['long_groove', 'classic'],
               'progressive': ['classic', 'double_break', 'hook_first'], 'trance': ['classic', 'double_break', 'hook_first'],
               'futurebass': ['hook_first', 'classic', 'early_drop'], 'tropical': ['early_drop', 'hook_first', 'classic']}
DEFAULT_FORMS = ['classic', 'early_drop', 'hook_first']      # house, nu-disco, disco, French, soulful, vocal, indie dance


def form_for(style, song_id):
    opts = STYLE_FORMS.get(style, DEFAULT_FORMS)
    return opts[int(hashlib.md5(str(song_id).encode()).hexdigest(), 16) % len(opts)]


def sections(nbars, form='classic'):
    """2:59 form in bars; slower tempos (tropical 98-112 BPM) have fewer bars: the longest intro/break/drop is cut by 4
    until the outro keeps >= 4 bars."""
    s = list(FORMS[form])
    while nbars - sum(b for _, b in s) < 4:
        i = max(range(len(s)), key=lambda j: (s[j][0] in ('intro', 'break', 'drop1', 'drop2', 'tease'), s[j][1]))
        if s[i][1] <= 4: break
        s[i] = (s[i][0], s[i][1] - 4)
    turn = 0                                       # fast tempos have more bars: grow the drops by 8 so the outro stays 4-15 bars
    while nbars - sum(b for _, b in s) >= 16:
        names = [n for n, _ in s]; tgt = 'drop2' if turn % 2 == 0 or 'drop1' not in names else 'drop1'
        i = len(names) - 1 - names[::-1].index(tgt); s[i] = (tgt, s[i][1] + 8); turn += 1
    s.append(('outro', max(4, nbars - sum(b for _, b in s))))
    return s


# which layers play in each section (and how)
PLAN = {
    'tease':  {'keys': 'lp', 'melody': 'lp', 'pad': 1},
    'intro':  {'tops': 1, 'drums': 'late', 'keys': 'lp', 'pad': 1},
    'build':  {'tops': 1, 'drums': 1, 'bass': 'hp', 'keys': 1, 'pad': 1, 'riser': 1},
    'drop1':  {'tops': 1, 'drums': 1, 'bass': 1, 'keys': 1, 'melody': 'half'},
    'break':  {'keys': 1, 'pad': 1, 'melody': 1, 'tops': 'tail'},
    'build2': {'tops': 1, 'drums': 'hp', 'keys': 1, 'melody': 1, 'vocals': 'half', 'pad': 1, 'riser': 1},
    'drop2':  {'tops': 1, 'drums': 1, 'bass': 1, 'keys': 1, 'melody': 1, 'melody2': 1, 'vocals': 'lo', 'pad': 'lo'},
    'outro':  {'tops': 1, 'drums': 1, 'bass': 'fade', 'keys': 'fade', 'melody2': 'fade'},
}


def choose(lib, rng, key=None, bpm=None, force=None):
    drums = [d for d in lib['drums']]
    if not drums: raise SystemExit('no drum loops')
    for d in drums:
        x, _ = sf.read(d['file'], always_2d=True, dtype='float32'); d['kick'] = kick_ratio(x)
    full = [d for d in drums if d['kick'] > .18] or drums
    tops = [d for d in drums if d['kick'] <= .18]
    force = force or {}
    pickf = lambda pool, k: next((d for d in drums if force.get(k) and force[k] in d['name']), None) or (pool[rng.integers(len(pool))] if pool else None)
    main = pickf(full, 'main')
    altp = [d for d in full if d is not main]
    alt = pickf(altp, 'alt')
    top = pickf(tops, 'top')
    tonal = {c: lib[c] for c in ('bass', 'keys', 'melody', 'melody2', 'pad', 'vocals') if lib.get(c)}
    # key: the requested one, else the key of a randomly chosen chord loop (keys > melody > bass > pad)
    if key is None:
        for c in ('keys', 'melody', 'bass', 'pad'):
            ks = [i for i in tonal.get(c, []) if i['key']]
            if ks: key = ks[rng.integers(len(ks))]['key']; break
    pick = {}
    for c, items in tonal.items():
        ok = []
        for i in items:
            if not i['key'] or not key: ok.append((i, 0)); continue
            if i['key'][1] != key[1]:                  # relative major/minor counts as same key
                rel = (i['key'][0] + (3 if i['key'][1] == 'minor' else -3)) % 12
                d = ((key[0] - rel + 6) % 12) - 6
            else:
                d = ((key[0] - i['key'][0] + 6) % 12) - 6
            if abs(d) <= 3: ok.append((i, d))
        forced = [o for o in ok if force.get(c) and force[c] in o[0]['name']]
        if forced: pick[c] = forced[0]
        elif ok and not force.get(c): pick[c] = ok[rng.integers(len(ok))]
    if bpm is None:
        bpm = float(np.median([main['bpm']] + [p[0]['bpm'] for p in pick.values()]))
        bpm = float(np.clip(round(bpm), 118, 125))
    return main, alt, top, pick, key, bpm


def arrange(lib, seed, bpm=None, key=None, lufs=-11.0, force=None, form='classic'):
    rng = np.random.default_rng(seed)
    main, alt, top, pick, key, bpm = choose(lib, rng, key, bpm, force)
    bar = 4 * 60 / bpm; nbars = int(LEN / bar); N = int(LEN * SR)
    S = sections(nbars, form)
    layers = {}
    layers['drums'] = level(stretch(main, bpm), TARGET_RMS['drums'])
    layers['drums_b'] = level(stretch(alt, bpm), TARGET_RMS['drums']) if alt else layers['drums']
    if top: layers['tops'] = level(filt(stretch(top, bpm), 'lowpass', 13000), TARGET_RMS['tops'])
    for c, (item, d) in pick.items(): layers[c] = level(stretch(item, bpm, d), TARGET_RMS[c])
    mix = {k: np.zeros((N, 2), np.float32) for k in ('drums', 'tops', 'bass', 'keys', 'melody', 'melody2', 'pad', 'vocals', 'fx')}

    def tile(x, a, b):
        """loop x (aligned to bar 0 of the song) from sample a to b"""
        L = len(x); out = np.zeros((b - a, 2), np.float32); p = a
        while p < b:
            o = p % L; n = min(L - o, b - p); out[p - a:p - a + n] = x[o:o + n]; p += n
        return out

    t = 0; sec_log = []
    for si, (name, nb) in enumerate(S):
        a = int(t * bar * SR); b = min(N, int((t + nb) * bar * SR)); sec_log.append({'section': name, 'bar': t, 'bars': nb})
        plan = PLAN[name]
        for lay, how in plan.items():
            if lay == 'riser': continue
            src = layers.get(lay)
            if lay == 'drums':
                src = layers['drums_b'] if name in ('drop2',) else layers['drums']
            if src is None: continue
            seg = tile(src, a, b)
            if how == 'lp': seg = sweep(seg, 'lowpass', 300, 6000)
            elif how == 'hp': seg = sweep(seg, 'highpass', 30, 600)
            elif how == 'fade': seg *= np.linspace(1, 0, len(seg))[:, None] ** 1.5
            elif how == 'late':                       # drums enter half-way through the intro, filtered open
                h = len(seg) // 2; seg[:h] = 0; seg[h:] = sweep(seg[h:], 'lowpass', 400, 8000, 16)
            elif how == 'half':                       # melody only in the second half of drop1
                seg[: len(seg) // 2] = 0
            elif how == 'tail':                       # tops fade out over the first 2 bars of the break
                n2 = min(len(seg), int(2 * bar * SR)); seg[n2:] = 0; seg[:n2] *= np.linspace(1, 0, n2)[:, None]
            elif how == 'lo': seg *= .6
            mix['drums' if lay == 'drums' else lay][a:b] += seg
        # transitions: drums drop out for the last beat before each drop; 8-bar phrase-end kick lift in long sections
        if name in ('build', 'build2'):
            gap = int(bar / 4 * SR)
            for k in ('drums', 'tops', 'bass'): mix[k][b - gap:b] = 0
            if 'pad' in layers or 'keys' in layers:        # riser: reversed tail of the pad/keys (a real sound)
                src = layers.get('pad', layers.get('keys'))
                n = min(len(src), int(4 * bar * SR)); r = src[:n][::-1].copy()
                r = filt(r, 'highpass', 400) * np.linspace(0, 1, n)[:, None] ** 2
                mix['fx'][max(0, b - n):b] += r[-(b - max(0, b - n)):] * .7
        if name in ('drop1', 'drop2', 'outro') and nb >= 16:
            for k8 in range(8, nb, 8):               # bar before each new 8: low cut on drums (a classic DJ lift)
                p0 = a + int((k8 - 1) * bar * SR); p1 = a + int(k8 * bar * SR)
                if p1 <= N: mix['drums'][p0:p1] = filt(mix['drums'][p0:p1], 'highpass', 250)
        # variation inside long sections: a one-beat stop before bar 9 of drop 2, a filter dip on the keys in drop 1
        if name == 'drop2' and nb >= 16:
            p1 = a + int(8 * bar * SR); p0 = p1 - int(bar / 4 * SR)
            for k in ('drums', 'tops', 'bass'): mix[k][p0:p1] *= 0.0
        if name == 'drop1' and nb >= 16:
            p0 = a + int(8 * bar * SR); p1 = min(b, a + int(12 * bar * SR))
            mix['keys'][p0:p1] = sweep(mix['keys'][p0:p1], 'lowpass', 1400, 9000, 16)
        t += nb
    # sidechain-style ducking of bass/keys/pad on every beat where the kick plays
    beat = 60 / bpm; env = np.ones(N, np.float32); tt = np.arange(N) / SR
    ph = (tt % beat) / beat
    duck = 1 - .45 * np.exp(-ph * 9)
    kick_on = (np.abs(mix['drums']).max(1) > 1e-4).astype('float32')
    kick_on = uniform_filter1d(kick_on, int(beat * SR))
    env = 1 - (1 - duck) * np.clip(kick_on, 0, 1)
    for k, depth in (('bass', 1.0), ('pad', 1.0), ('keys', .6)): mix[k] *= (1 - depth * (1 - env))[:, None]
    # tonal balance: bass mono below 150 Hz, keys/melody/pad cleared below 180 Hz
    mono = mix['bass'].mean(1, keepdims=True); lo = filt(mono, 'lowpass', 150); mix['bass'] = filt(mix['bass'], 'highpass', 150) + np.repeat(lo, 2, 1)
    for k in ('keys', 'melody', 'melody2', 'pad', 'vocals', 'fx'): mix[k] = filt(mix[k], 'highpass', 180)
    out = sum(mix.values())
    # everything below 120 Hz mono (club/vinyl practice; QC requires side < -30 dB vs mid under 80 Hz)
    lo = ss.sosfiltfilt(ss.butter(4, 140, 'low', fs=SR, output='sos'), out, axis=0).astype('float32'); m = lo.mean(1, keepdims=True)
    out = out - lo + np.repeat(m, 2, 1)
    fade = int(3 * SR); out[-fade:] *= np.linspace(1, 0, fade)[:, None]; out[:int(.02 * SR)] *= np.linspace(0, 1, int(.02 * SR))[:, None]
    pre = out.copy()
    out, ach = master(out, lufs)
    used = {'drums': main, 'drums_b': alt, 'tops': top, **{c: p[0] for c, p in pick.items()}}
    meta = {'seed': seed, 'form': form, 'bpm': bpm, 'key': key, 'target_lufs': lufs, 'achieved_lufs_master': ach, 'length_s': LEN,
            'sections': sec_log,
            'loops': {k: ({kk: v[kk] for kk in ('name', 'id', 'title', 'uploader', 'url', 'bpm', 'key')} | ({'semitones': pick[k][1]} if k in pick else {}))
                      for k, v in used.items() if v},
            'source': 'Looperman loops (royalty-free for use inside original tracks; not redistributed)'}
    return out, meta


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--lib', default='/home/claude/loops'); ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--bpm', type=float); ap.add_argument('--key'); ap.add_argument('--lufs', type=float, default=-11.0)
    ap.add_argument('--out', required=True)
    for k in ('main', 'alt', 'top'): ap.add_argument('--' + k)
    a = ap.parse_args()
    lib = library(a.lib)
    print({c: len(v) for c, v in lib.items()})
    out, meta = arrange(lib, a.seed, a.bpm, parse_key(a.key) if a.key else None, a.lufs, {k: getattr(a, k) for k in ('main', 'alt', 'top')})
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    sf.write(a.out, out, SR, subtype='PCM_16')
    json.dump(meta, open(os.path.splitext(a.out)[0] + '.json', 'w'), indent=1)
    print(json.dumps({k: meta[k] for k in ('bpm', 'key', 'achieved_lufs_master')}), {k: v['name'][:50] for k, v in meta['loops'].items()})
