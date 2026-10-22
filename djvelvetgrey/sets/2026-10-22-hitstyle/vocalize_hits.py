"""Put CC0 vocals on one take-2 song: python3 vocalize.py <index 0-11>
Reads the song's vocal plan from /home/claude/dvg-take2/vocal_plans.json, re-renders the song's take-2 brief with
the lead pulled back and captures the pre-master mix, tunes every vocal to the song's key and locks loops to its
tempo (Rubber Band, formants preserved), arranges them on the song's own section map, mixes, and masters with the
engine's own master() at the style's loudness. Writes NNv.wav, NNv.json, NNv_vocals_only.wav, mp3/NN-<slug>.mp3."""
import sys, json, os, subprocess, tempfile, hashlib, numpy as np, librosa, soundfile as sf
import scipy.signal as ss
from scipy.ndimage import uniform_filter1d
V2 = '/home/claude/videosyndication/djvelvetgrey/v2'; sys.path.insert(0, V2)
import engine as E, styles as S, compose as C

OUT = '/tmp/vox/out'; SRC = '/tmp/vox/src'; CACHE = '/tmp/vox/cache'; SR = E.SR
os.makedirs(CACHE, exist_ok=True)
MODES = {'major': [0, 2, 4, 5, 7, 9, 11], 'minor': [0, 2, 3, 5, 7, 8, 10], 'dorian': [0, 2, 3, 5, 7, 9, 10],
         'mixolydian': [0, 2, 4, 5, 7, 9, 10], 'phrygian': [0, 1, 3, 5, 7, 8, 10], 'lydian': [0, 2, 4, 6, 7, 9, 11]}

I = int(sys.argv[1]); NN = f'{I + 1:02d}'
HITS = json.load(open('/tmp/vox/work/hits.json'))
plan = HITS[I]; VP = plan['vocals']; b = plan['brief']
cands = C.candidates(b, 6); pick = next((c for c in cands if not c['catalog']['flags']), cands[0])
b['motif'] = {'cell': pick['cell'], 'contour': pick['contour'], 'start': pick['start'], 'candidate': pick['id'],
              'selected_by': 'automatic - not a listening judgement'}
BPM = b['bpm']; BAR = 240 / BPM; BEAT = 60 / BPM
SCALE = {(b['tonic'] + iv) % 12 for iv in MODES[b['mode']]}
style = b['style']; P = S.STYLES[style]

# ---------------------------------------------------------------- 1. instrumental, pre-master, lead pulled back
off = dict(P.get('mix', {})); off['lead'] = off.get('lead', 0) - VP.get('lead_cut_db', 3.5); off['answer'] = off.get('answer', 0) - 1.0
S.STYLES[style]['mix'] = off
_master = E.master; cap = {}
def grab(mix, lufs, ceiling_db=-2.8):
    cap['mix'] = mix.copy(); cap['lufs'] = lufs
    return _master(mix, lufs, ceiling_db)
E.master = grab
t = E.TrackV2(b, b['motif']); t.render(); E.master = _master
band = cap['mix'].astype(np.float32); N = len(band); LUFS = cap['lufs']; cap.clear()
SECTIONS = t.meta['sections']; TMETA = dict(t.meta)
import gc; del t; gc.collect()
def bar_t(bar): return bar * BAR

# ---------------------------------------------------------------- 2. sources: analysis cache, tuning, fitting
def load(name):
    y, _ = librosa.load(os.path.join(SRC, name), sr=SR, mono=True)
    return y / (np.abs(y).max() + 1e-9) * 0.8

def analysis(name):
    cf = os.path.join(CACHE, name + '.json')
    if os.path.exists(cf): return json.load(open(cf))
    y = load(name)
    f0, v, _ = librosa.pyin(y, fmin=70, fmax=1100, sr=SR, frame_length=2048)
    f = f0[v & ~np.isnan(f0)]
    a = {'dur': len(y) / SR, 'voiced': float(v.mean()), 'n_voiced': int(len(f))}
    if len(f) >= 20:
        midi = librosa.hz_to_midi(f); cents = float(np.median(midi - np.round(midi)))
        pcs = np.round(midi - cents).astype(int) % 12
        a.update(cents=cents, hist=np.bincount(pcs, minlength=12).tolist(), times=None)
    json.dump(a, open(cf, 'w')); return a

def region_hist(name, r0, r1):
    """pitch-class histogram of one region (for long sources whose regions sit in different keys)"""
    y = load(name)[int(r0 * SR):int(r1 * SR)]
    f0, v, _ = librosa.pyin(y, fmin=70, fmax=1100, sr=SR, frame_length=2048)
    f = f0[v & ~np.isnan(f0)]
    if len(f) < 20: return None, 0.0
    midi = librosa.hz_to_midi(f); cents = float(np.median(midi - np.round(midi)))
    return np.bincount(np.round(midi - cents).astype(int) % 12, minlength=12), cents

def best_shift(hist):
    if hist is None or np.sum(hist) == 0: return 0, None
    hist = np.asarray(hist, float)
    score = {k: sum(hist[p] for p in range(12) if (p + k) % 12 in SCALE) / hist.sum() - .012 * abs(k) for k in range(-6, 6)}
    k = max(score, key=score.get)
    return k, round(score[k] + .012 * abs(k), 2)

def rubber(y, time_ratio=1.0, semis=0.0):
    if abs(time_ratio - 1) < 1e-3 and abs(semis) < 0.01: return y.astype(np.float32)
    with tempfile.TemporaryDirectory() as d:
        sf.write(f'{d}/i.wav', y, SR)
        subprocess.run(['rubberband', '-q', '-3', '-F', '-t', f'{time_ratio:.6f}', '-p', f'{semis:.4f}', f'{d}/i.wav', f'{d}/o.wav'],
                       check=True, stderr=subprocess.DEVNULL)
        o, _ = sf.read(f'{d}/o.wav')
    return o.astype(np.float32)

report = {}
def prep(spec, role):
    """spec: {src, region:[a,b]?, bpm?, trim?, shift? ('none' for shouts)}"""
    name = spec['src']; y = load(name)
    r0, r1 = spec.get('region', [0, len(y) / SR])
    y = y[int(r0 * SR):int(r1 * SR)]
    if spec.get('shift') == 'none': k, c, fit = 0, 0.0, None
    elif 'region' in spec:
        hist, c = region_hist(name, r0, r1); k, fit = best_shift(hist); c = -c
    else:
        a = analysis(name); k, fit = best_shift(a.get('hist')); c = -a.get('cents', 0.0)
    ratio = spec['bpm'] / BPM if spec.get('bpm') else 1.0
    z = rubber(y, ratio, k + c)
    z = z[int(spec.get('trim', 0.0) * ratio * SR):]
    report[role] = {'src': name, 'region': [round(r0, 2), round(r1, 2)], 'semitones': k, 'tuning_cents': round(c * 100, 1),
                    'scale_fit': fit, 'time_ratio': round(ratio, 4)}
    return z

def hp(x, f, order=2): return ss.sosfiltfilt(ss.butter(order, f, 'high', fs=SR, output='sos'), x, axis=0)
def lp(x, f, order=2): return ss.sosfiltfilt(ss.butter(order, f, 'low', fs=SR, output='sos'), x, axis=0)
def bp(x, lo, hi): return lp(hp(x, lo), hi)
def comp(x, thr_db=-20, ratio=3.0, att=.004, rel=.1):
    env = np.sqrt(np.maximum(uniform_filter1d(x ** 2, int(att * SR) + 1), 0))
    env = ss.lfilter([1 - np.exp(-1 / (rel * SR))], [1, -np.exp(-1 / (rel * SR))], env)
    return x * 10 ** (-np.maximum(20 * np.log10(env + 1e-9) - thr_db, 0) * (1 - 1 / ratio) / 20)
def air(x): return x + hp(np.tanh(4 * hp(x, 3000)), 8000, 4) * 0.12
def fade(x, a=0.006, r=0.04):
    x = x.copy(); na, nr = min(int(a * SR), len(x) // 4), min(int(r * SR), len(x) // 3)
    if na: x[:na] *= np.linspace(0, 1, na)
    if nr: x[-nr:] *= np.linspace(1, 0, nr)
    return x
def swell(x, up=1.5, down=2.0):
    n = len(x); u, d = min(int(up * SR), n // 2), min(int(down * SR), n // 2)
    env = np.ones(n); env[:u] = np.linspace(0, 1, u); env[n - d:] = np.linspace(1, 0, d); return x * env

def make_unit(spec, role):
    """A hook unit: an integer number of bars of vocal, either a fitted loop or syllables re-sequenced on a grid."""
    if spec['type'] == 'phrase':
        y = load(spec['src']); r0, r1 = spec.get('region', [0, len(y) / SR]); dur = r1 - r0
        # unit of 1/2/4/8 bars: a phrase that fits is kept at its natural speed (words untouched, padded with
        # silence to the bar line); one up to 12% too long is tightened onto the bars
        bars = spec.get('bars') or next(n for n in (1, 2, 4, 8, 16) if dur <= n * BAR / .88)
        sp = dict(spec)
        if dur > bars * BAR: sp['bpm'] = BPM * (bars * BAR) / dur
        else: sp.pop('bpm', None)
        z = prep(sp, role); report[role]['bars'] = bars
        u = np.zeros(int(bars * BAR * SR)); n = min(len(u), len(z)); u[:n] = z[:n]
        return fade(u, .004, .05)
    z = prep(spec, role)
    bars = spec.get('bars', 2)
    if spec['type'] == 'loop':
        u = np.zeros(int(bars * BAR * SR)); n = min(len(u), len(z)); u[:n] = z[:n]
        return fade(u, .003, .02)
    # re-sequence: slice at onsets, keep voiced syllables, lay them on the pattern (16th steps)
    on = librosa.onset.onset_detect(y=z, sr=SR, units='samples', backtrack=True)
    sl = []
    mx = spec.get('slice_max', .3)
    for a_, b_ in zip(on, list(on[1:]) + [len(z)]):
        s_ = z[a_:min(b_, a_ + int(mx * SR))]
        if len(s_) < .09 * SR or np.sqrt((s_ ** 2).mean()) <= .025: continue
        env_ = uniform_filter1d(np.abs(s_), int(.004 * SR))          # start each syllable right at its attack
        k0 = int(np.argmax(env_ > .2 * env_.max())); s_ = s_[max(0, k0 - int(.005 * SR)):]
        if len(s_) > .08 * SR: sl.append(s_)
    pick = spec.get('pick')
    if pick: sl = [sl[i % len(sl)] for i in pick]
    if spec.get('snap', spec.get('shift') != 'none'):   # snap every syllable to the nearest note of the song's scale
        snapped = 0
        for j, s_ in enumerate(sl):
            f0, vf, _ = librosa.pyin(s_, fmin=70, fmax=1100, sr=SR, frame_length=2048, hop_length=256)
            f = f0[vf & ~np.isnan(f0)]
            if len(f) < 3: continue
            mid = float(np.median(librosa.hz_to_midi(f)))
            cands = [mm for mm in range(int(mid) - 2, int(mid) + 3) if mm % 12 in SCALE]
            tgt = min(cands, key=lambda mm: abs(mm - mid)); dlt = tgt - mid
            if abs(dlt) > .15: sl[j] = rubber(s_, 1.0, dlt)[:len(s_)]; snapped += 1
        report[role]['snapped_syllables'] = f'{snapped}/{len(sl)}'
    if not sl: raise RuntimeError(f'no usable slices for {role}')
    u = np.zeros(int(bars * BAR * SR) + SR); step = BAR / 16
    for j, pos in enumerate(spec['pattern']):
        s_ = sl[j % len(sl)][:int(spec.get('hold', 2.5) * step * SR)]
        if spec.get('rev') and j in spec['rev']: s_ = s_[::-1]
        i_ = int(round(pos * step * SR)); s_ = fade(s_, .002, .025); u[i_:i_ + len(s_)] += s_
    report[role]['slices'] = len(sl); report[role]['pattern_16ths'] = spec['pattern']
    return u[:int(bars * BAR * SR)]

hook = make_unit(VP['hook'], 'hook')
layer = make_unit(VP['layer'], 'layer') if VP.get('layer') else None
bed = swell(prep(VP['bed'], 'bed')) if VP.get('bed') else None
phrase = prep(VP['phrase'], 'phrase') if VP.get('phrase') else None
adl = {k: prep({'src': s, 'shift': VP.get('adlib_shift', {}).get(k, 'none')}, 'adlib_' + k) for k, s in VP.get('adlibs', {}).items()}

# ---------------------------------------------------------------- 3. arrangement on the song's own sections
lead_v = np.zeros((N, 2), np.float32); bed_v = np.zeros((N, 2), np.float32); shout_v = np.zeros((N, 2), np.float32); cues = []
def place(stem, x, t0, gain_db=0.0, pan=0.0, label=None):
    i = int(round(t0 * SR)); x = fade(x) * 10 ** (gain_db / 20)
    if i < 0: x = x[-i:]; i = 0
    n = min(len(x), N - i)
    if n <= 0: return
    stem[i:i + n, 0] += x[:n] * np.sqrt(0.5 * (1 - pan)); stem[i:i + n, 1] += x[:n] * np.sqrt(0.5 * (1 + pan))
    if label: cues.append({'t': round(max(t0, 0), 2), 'what': label})
def run(stem, unit, bar0, bars, gain, pan=0.0, label=None, every=None, pan_alt=False, hpf=None):
    ub = int(round(len(unit) / SR / BAR)); every = every or ub; u = hp(unit, hpf) if hpf else unit
    for j, k in enumerate(range(0, bars, every)):
        if k + ub > bars + .01 and k > 0: u2 = u[:int((bars - k) * BAR * SR)]
        else: u2 = u
        place(stem, u2, bar_t(bar0 + k), gain, (pan if not pan_alt else (pan if j % 2 == 0 else -pan)), label if j == 0 else None)

names = VP.get('names', {})
nm = lambda k, d: names.get(k, d)
drops = [s for s in SECTIONS if s['name'].startswith('drop')]
for si, s in enumerate(SECTIONS):
    n, b0, nb = s['name'], s['start_bar'], s['bars']; nxt = SECTIONS[si + 1] if si + 1 < len(SECTIONS) else None
    if n == 'intro' and bed is not None:
        x = bed[:int(nb * BAR * SR)]; x = x * np.linspace(0, 1, len(x)) ** 1.5
        place(bed_v, x, bar_t(b0), -5, label=nm('bed', 'Vocal pad') + ' swell')
    elif n == 'hook':
        h0 = b0 + nb // 2
        run(bed_v, hook, h0, nb - nb // 2, -9, hpf=500, label=nm('hook', 'Vocal hook') + ' (teased, filtered)')
    elif n == 'groove':
        run(lead_v, hook, b0, nb, -3, label=nm('hook', 'Vocal hook'))
    elif n in ('break', 'break2', 'interlude'):
        if bed is not None:
            off0 = (si * 7.3) % max(1.0, len(bed) / SR - nb * BAR - .5)
            x = bed[int(off0 * SR):int(off0 * SR + nb * BAR * SR)]
            place(bed_v, swell(hp(x, 200)), bar_t(b0), -4, label=nm('bed', 'Vocal pad'))
        if phrase is not None:
            place(bed_v, swell(hp(phrase, 180), .05, 1.0), bar_t(b0 + min(2, nb // 4)), -3, pan=.15, label=nm('phrase', 'Sung phrase'))
    elif n == 'build':
        if 'build' in adl: place(shout_v, adl['build'], bar_t(b0 + max(0, nb - 4)), -3, label=nm('adlib_build', 'Ad-lib'))
        one = hook[:int(BAR * SR)]; last = b0 + nb
        stut = [(last - 3, 1.0)] + [(last - 2 + .5 * r, .5) for r in range(2)] + [(last - 1 + .125 * r, .125) for r in range(4)]
        if nb < 6: stut = [(last - 2 + .5 * r, .5) for r in range(2)] + [(last - 1 + .125 * r, .125) for r in range(4)]
        for j, (st_bar, ln) in enumerate(stut):
            place(lead_v, hp(one[:int(ln * BAR * SR)], 300 + 120 * j), bar_t(st_bar), -4 + .5 * j)
        cues.append({'t': round(bar_t(stut[0][0]), 2), 'what': 'Vocal stutter build'})
    elif n.startswith('drop'):
        first = s is drops[0]
        key = 'drop1' if first else 'drop2'
        if key in adl: place(shout_v, adl[key], bar_t(b0) - 2 * BEAT, -2, label=nm('adlib_' + key, 'Ad-lib'))
        run(lead_v, hook, b0, nb, 0, label=nm('hook', 'Vocal hook'))
        if layer is not None:
            l0 = b0 + (nb // 2 if first else 0); lb = nb - (nb // 2 if first else 0)
            run(lead_v, layer, l0, lb, -7 if first else -6, pan=.25, pan_alt=True, hpf=250, label=nm('layer', 'Second vocal layer'))
    elif n == 'outro':
        run(lead_v, hook, b0, min(4, nb), -4, label=nm('hook', 'Vocal hook') + ' fading out')
        if nb > 4: run(lead_v, hook, b0 + 4, min(4, nb - 4), -10)
        if bed is not None and nb >= 8:
            x = bed[:int(min(6, nb - 4) * BAR * SR)]
            place(bed_v, swell(x, .5, 2.5), bar_t(b0 + nb - min(6, nb - 4) - 1), -6, label=nm('bed', 'Vocal pad'))

# ---------------------------------------------------------------- 4. processing + mix + master
def rms_db(x):
    a = np.abs(x).mean(1); w = int(.4 * SR); r = np.sqrt(np.maximum(uniform_filter1d(a ** 2, w), 0)); act = r[r > r.max() * .05]
    return 20 * np.log10(np.sqrt((act ** 2).mean()) + 1e-12) if len(act) else -120
def stage(x, target_db): return x * 10 ** ((target_db - rms_db(x)) / 20) if np.abs(x).max() > 0 else x
def proc(x, hpf, thr): return np.stack([air(comp(hp(x[:, c], hpf), thr)) for c in (0, 1)], 1)
lv = VP.get('levels', {})
lead_p = stage(proc(lead_v, 160, -22), lv.get('lead', -18.5))
bed_p = stage(proc(bed_v, 200, -26), lv.get('bed', -24.0))
shout_p = stage(proc(shout_v, 150, -20), lv.get('shout', -19.5))
send = lead_p * .3 + bed_p * .55 + shout_p * .35
n_ = int(2.4 * SR); tt = np.arange(n_) / SR; rng = np.random.default_rng(b['seed'])
ir = rng.standard_normal((n_, 2)) * np.exp(-tt * 2.6)[:, None]; ir = lp(ir, 7500); ir[:int(.03 * SR)] = 0; ir /= np.sqrt((ir ** 2).sum(0))
m = send.mean(1); rev = hp(np.stack([ss.oaconvolve(m, ir[:, c])[:N] for c in (0, 1)], 1), 300)
d = int(VP.get('delay_beats', .75) * BEAT * SR); dly = np.zeros((N, 2)); mm = lp(lead_p.mean(1), 5000)
for i in range(1, 5): dly[i * d:, i % 2] += .33 ** i * mm[:N - i * d]
vox = lead_p + bed_p + shout_p + rev * 10 ** (-9 / 20) + dly * 10 ** (VP.get('delay_db', -12) / 20)
if VP.get('filter_vox'):                             # e.g. French house: vocals through a band-pass "filter house" sweep
    lo, hi = VP['filter_vox']; vox = bp(vox, lo, hi) * 1.6
env = uniform_filter1d(np.abs(lead_p + shout_p).mean(1), int(.15 * SR)); env = env / (env.max() + 1e-9)
mix = band * (10 ** (-2.0 * np.clip(env * 3, 0, 1) / 20))[:, None] + vox
fade_n = int(8 * SR); mix[-fade_n:] *= (np.linspace(1, 0, fade_n) ** 2)[:, None]
out, achieved = E.master(mix, LUFS)
sf.write(f'{OUT}/{NN}v.wav', (np.clip(out, -1, 1) * 32767).astype(np.int16), SR, subtype='PCM_16')
sf.write(f'{OUT}/{NN}v_vocals_only.wav', np.clip(vox / (np.abs(vox).max() + 1e-9) * .9, -1, 1), SR, subtype='PCM_16')
title = plan['title']; slug = title.lower().replace(' ', '-').replace("'", '')
meta = dict(TMETA, title=title, bpm=BPM, key=C.key_name(b['tonic'], b['mode']), brief=b, style_reference=plan['reference'],
            vocals={'plan': VP, 'tuning': report, 'cues': sorted(cues, key=lambda c: c['t']), 'lead_cut_db': VP.get('lead_cut_db', 3.5),
                    'achieved_lufs': achieved})
json.dump(meta, open(f'{OUT}/{NN}v.json', 'w'), indent=1, default=str)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', f'{OUT}/{NN}v.wav', '-b:a', '192k', '-metadata', f'title={title}',
                '-metadata', 'artist=DJ Velvet Grey', '-metadata', 'album=Hit-Style Samples (listening copy)', '-metadata', f'track={I + 1}/10',
                f'{OUT}/mp3/{NN}-{slug}.mp3'], check=True)
print(json.dumps({'n': I + 1, 'title': title, 'achieved_lufs': achieved, 'cues': len(cues),
                  'tuning': {k: (v['semitones'], v['scale_fit']) for k, v in report.items()}}))
