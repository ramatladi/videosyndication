"""Open Sky Chorus (take 2) with CC0 vocals.
python3 vocal_osc.py  -> /home/claude/dvg-take2/07v.wav, 07v.json, mp3/07-open-sky-chorus.mp3 (vocal version)
1. Re-render the take-2 brief with the lead sax 4.5 dB lower (room for the voice) and capture the pre-master mix.
2. Tune every vocal to C major (pyin pitch-class fit + cents correction), fit loops to 122 BPM with Rubber Band.
3. Arrange the vocals on the song's own section map, process (HPF, comp, air, reverb, delay), duck the band slightly.
4. Master with the engine's own master() at the style's loudness target."""
import sys, json, os, subprocess, tempfile, numpy as np, librosa, soundfile as sf
import scipy.signal as ss
from scipy.ndimage import uniform_filter1d
V2 = '/home/claude/vs/djvelvetgrey/v2'; sys.path.insert(0, V2)
import engine as E, styles as S, compose as C

OUT = '/home/claude/dvg-take2'; SRC = '/home/claude/dvg-vocals/src'; SR = E.SR
plan = json.load(open(f'{OUT}/briefs.json'))[6]; b = plan['brief']
take = json.load(open(f'{OUT}/07.json')); b['motif'] = take['brief']['motif']
BPM = b['bpm']; BAR = 240 / BPM; BEAT = 60 / BPM
SCALE = {0, 2, 4, 5, 7, 9, 11}                      # C major

# ---------------------------------------------------------------- 1. instrumental, pre-master
S.STYLES['vocal']['mix'] = dict(S.STYLES['vocal'].get('mix', {}), lead=-3.0, answer=-1.0)
_master = E.master; cap = {}
def grab(mix, lufs, ceiling_db=-2.8):
    cap['mix'] = mix.copy(); cap['lufs'] = lufs
    return _master(mix, lufs, ceiling_db)
E.master = grab
t = E.TrackV2(b, b['motif']); t.render(); E.master = _master
band = cap['mix']; N = len(band); LUFS = cap['lufs']
sections = {s['name']: s for s in t.meta['sections']}

def bar_t(bar): return bar * BAR

# ---------------------------------------------------------------- 2. tuning / fitting
def load(name):
    y, _ = librosa.load(os.path.join(SRC, name), sr=SR, mono=True)
    return y / (np.abs(y).max() + 1e-9) * 0.8

def best_shift(y):
    f0, v, _ = librosa.pyin(y, fmin=70, fmax=1100, sr=SR, frame_length=2048)
    f = f0[v & ~np.isnan(f0)]
    if len(f) < 20: return 0.0, 0.0, None
    midi = librosa.hz_to_midi(f); cents = float(np.median((midi - np.round(midi)))) # tuning offset (semitones)
    pcs = np.round(midi - cents).astype(int) % 12
    score = {k: np.mean([(p + k) % 12 in SCALE for p in pcs]) for k in range(-6, 6)}
    top = max(score.values()); k = min((k for k in score if score[k] >= top - 0.02), key=abs)
    return float(k), -cents, round(top, 2)

def rubber(y, time_ratio=1.0, semis=0.0):
    if abs(time_ratio - 1) < 1e-3 and abs(semis) < 0.01: return y
    with tempfile.TemporaryDirectory() as d:
        sf.write(f'{d}/i.wav', y, SR)
        subprocess.run(['rubberband', '-q', '-3', '-F', '-t', f'{time_ratio:.6f}', '-p', f'{semis:.4f}', f'{d}/i.wav', f'{d}/o.wav'], check=True)
        o, _ = sf.read(f'{d}/o.wav')
    return o.astype(np.float32)

report = {}
def prep(name, src_bpm=None, loop_bars=None, shift=None, trim_s=0.0):
    y = load(name)
    k, c, fit = best_shift(y) if shift is None else (shift, 0.0, None)
    ratio = 1.0
    if src_bpm: ratio = src_bpm / BPM                  # output duration / input duration
    z = rubber(y, ratio, k + c)
    report[name] = {'semitones': k, 'tuning_cents': round(c * 100, 1), 'scale_fit': fit, 'time_ratio': round(ratio, 4)}
    z = z[int(trim_s * SR):]                          # put the loop's own downbeat at sample 0
    if loop_bars: z = z[:int(loop_bars * BAR * SR)]
    return z

def hp(x, f, order=2): return ss.sosfiltfilt(ss.butter(order, f, 'high', fs=SR, output='sos'), x)
def lp(x, f, order=2): return ss.sosfiltfilt(ss.butter(order, f, 'low', fs=SR, output='sos'), x)
def comp(x, thr_db=-20, ratio=3.0, att=.004, rel=.1):
    env = np.sqrt(np.maximum(uniform_filter1d(x ** 2, int(att * SR) + 1), 0))
    env = ss.lfilter([1 - np.exp(-1 / (rel * SR))], [1, -np.exp(-1 / (rel * SR))], env)
    over = np.maximum(20 * np.log10(env + 1e-9) - thr_db, 0)
    return x * 10 ** (-over * (1 - 1 / ratio) / 20)
def air(x):                                          # sources are 24 kHz: regenerate a little top end
    return x + hp(np.tanh(4 * hp(x, 3000)), 8000, 4) * 0.12
def fade(x, a=0.01, r=0.05):
    x = x.copy(); na, nr = int(a * SR), int(r * SR)
    x[:na] *= np.linspace(0, 1, na); x[-nr:] *= np.linspace(1, 0, nr); return x

# ---------------------------------------------------------------- material
chop = prep('387185_ai-vox-chop.mp3', src_bpm=128.0, loop_bars=4, trim_s=0.010)   # 4-bar loop, 128 BPM (grid fit)
fchop = prep('437584_female-vocal-chops.mp3', src_bpm=159.25, trim_s=0.13)  # 8 bars at 159.25 BPM, downbeat 0.1 s in
fchop = fchop[:int(8 * BAR * SR + 1.0 * SR)]
# re-sequenced chops: slice the female chops at their onsets and lay the syllables on a tight 16th grid
_on = librosa.onset.onset_detect(y=fchop, sr=SR, units='samples', backtrack=True)
slices = []
for a_, b_ in zip(_on, list(_on[1:]) + [len(fchop)]):
    seg_ = fchop[a_:min(b_, a_ + int(.32 * SR))]
    if len(seg_) > .12 * SR and np.sqrt((seg_ ** 2).mean()) > .02: slices.append(seg_)
slices = slices[:10]
PATTERN = [0, 3, 6, 8, 10, 14, 16, 19, 22, 24, 26, 30]        # 16th steps over two bars
seqc = np.zeros(int(2 * BAR * SR) + SR)
for j, pos in enumerate(PATTERN):
    sl_ = slices[j % len(slices)][:int(2.5 * BAR / 16 * SR)]
    sl_ = sl_ * np.r_[np.ones(len(sl_) - int(.03 * SR)), np.linspace(1, 0, int(.03 * SR))]
    i_ = int(round(pos * BAR / 16 * SR)); seqc[i_:i_ + len(sl_)] += sl_
seqc = seqc[:int(2 * BAR * SR)]
report['resequenced_chops'] = {'slices': len(slices), 'pattern_16ths': PATTERN}
harm = prep('131094_vocal-harmony.mp3')
sisters = prep('331130_sisters-voices.mp3')
aah = prep('211628_aaahh.mp3')
hey = prep('448705_hey-hey-hey-yeah.mp3')
woo = prep('341488_woo-hoo.mp3', shift=0)
ohy = prep('387947_oh-yeah.mp3', shift=0)

# ---------------------------------------------------------------- 3. arrangement
lead_v = np.zeros((N, 2)); bed_v = np.zeros((N, 2)); shout_v = np.zeros((N, 2)); cues = []
def place(stem, x, t0, gain_db=0.0, pan=0.0, label=None):
    i = int(round(t0 * SR)); x = fade(x) * 10 ** (gain_db / 20); n = min(len(x), N - i)
    if n <= 0: return
    stem[i:i + n, 0] += x[:n] * np.sqrt(0.5 * (1 - pan)); stem[i:i + n, 1] += x[:n] * np.sqrt(0.5 * (1 + pan))
    if label: cues.append({'t': round(t0, 2), 'what': label})

sec = lambda n: sections[n]['start_bar']
# intro: a sung "aaahh" swelling in
a = aah[:int(4 * BAR * SR)]; a = a * np.linspace(0, 1, len(a)) ** 1.5
place(bed_v, a, bar_t(sec('intro')), -4, label='Aaahh swell')
# hook: soft female chops behind the sax hook
place(bed_v, hp(fchop, 400), bar_t(sec('hook')), -8, pan=-.15, label='Female chops (soft, in the background)')
# groove: the main chop loop twice
for k in (0, 4): place(lead_v, chop, bar_t(sec('groove') + k), -2, label='Vocal chop loop' if k == 0 else None)
# break: harmony "chorus" pad, then the sisters' voices
h = harm[int(10.43 * SR):int(10.43 * SR + 9 * BAR * SR)]; h = h * np.r_[np.linspace(0, 1, int(1.5 * SR)), np.ones(len(h) - int(3.5 * SR)), np.linspace(1, 0, int(2 * SR))]
place(bed_v, hp(h, 220), bar_t(sec('break')), -3, label='Vocal harmony chorus')
place(bed_v, hp(sisters, 200), bar_t(sec('break') + 4), -5, pan=.2, label="Sisters' voices")
# build: hey hey hey yeah, chop stutter, woo hoo into the drop
bb = sec('build')
place(shout_v, hey, bar_t(bb + 4), -3, label='"Hey hey hey yeah"')
one = chop[:int(BAR * SR)]
stutter = [(bb + 5, 1.0)] + [(bb + 6 + .5 * r, .5) for r in range(2)] + [(bb + 7 + .125 * r, .125) for r in range(4)]
for j, (st_bar, ln) in enumerate(stutter):
    place(lead_v, hp(one[:int(ln * BAR * SR)], 300 + 120 * j), bar_t(st_bar), -4 + .5 * j)
cues.append({'t': round(bar_t(bb + 5), 2), 'what': 'Chop stutter build'})
place(shout_v, woo, bar_t(sec('drop1')) - 2 * BEAT, -2, label='"Woo hoo"')
# drop 1: chop loop throughout, female chops join for the second half
d1 = sec('drop1')
for k in range(0, 16, 4): place(lead_v, chop, bar_t(d1 + k), 0, label='Vocal chop hook' if k == 0 else None)
for k in range(8, 16, 2): place(lead_v, hp(seqc, 250), bar_t(d1 + k), -7, pan=.25 if k % 4 == 0 else -.25, label='Re-sequenced female chops' if k == 8 else None)
# break 2: sisters + harmony, "oh yeah" into drop 2
b2 = sec('break2')
h2 = harm[int(30.49 * SR):int(30.49 * SR + 8 * BAR * SR)]; h2 = h2 * np.r_[np.linspace(0, 1, int(1.5 * SR)), np.ones(len(h2) - int(3 * SR)), np.linspace(1, 0, int(1.5 * SR))]
place(bed_v, hp(h2, 220), bar_t(b2), -4, label='Vocal harmony chorus')
place(bed_v, hp(sisters, 200), bar_t(b2 + 2), -4, pan=-.2, label="Sisters' voices")
place(shout_v, ohy, bar_t(sec('drop2')) - 2 * BEAT, 0, label='"Oh yeah"')
# drop 2: chop loop + female chops all the way
d2 = sec('drop2')
for k in range(0, 16, 4): place(lead_v, chop, bar_t(d2 + k), 0, label='Vocal chop hook + female chops' if k == 0 else None)
for k in range(0, 16, 2): place(lead_v, hp(seqc, 250), bar_t(d2 + k), -6, pan=.25 if k % 4 == 0 else -.25)
# outro: chops fade out, aaahh to close
o = sec('outro')
place(lead_v, chop, bar_t(o), -4, label='Chops fading out'); place(lead_v, chop, bar_t(o + 4), -9)
place(bed_v, aah[:int(5 * BAR * SR)], bar_t(o + 8), -6, label='Aaahh')

# ---------------------------------------------------------------- 4. processing + mix
def rms_db(x):
    a = np.abs(x).mean(1); w = int(.4 * SR); r = np.sqrt(np.maximum(uniform_filter1d(a ** 2, w), 0)); act = r[r > r.max() * .05]
    return 20 * np.log10(np.sqrt((act ** 2).mean()) + 1e-12)
def stage(x, target_db): return x * 10 ** ((target_db - rms_db(x)) / 20)
def proc(x, hpf, thr):
    y = np.stack([air(comp(hp(x[:, c], hpf), thr)) for c in (0, 1)], 1)
    return y
lead_p = stage(proc(lead_v, 160, -22), -18.5)
bed_p = stage(proc(bed_v, 200, -26), -24.0)
shout_p = stage(proc(shout_v, 150, -20), -19.5)
send = lead_p * .3 + bed_p * .55 + shout_p * .35
n = int(2.4 * SR); tt = np.arange(n) / SR; rng = np.random.default_rng(122)
ir = rng.standard_normal((n, 2)) * np.exp(-tt * 2.6)[:, None]; ir = np.stack([lp(ir[:, c], 7500) for c in (0, 1)], 1)
ir[:int(.03 * SR)] = 0; ir /= np.sqrt((ir ** 2).sum(0))
m = send.mean(1); rev = np.stack([ss.oaconvolve(m, ir[:, c])[:N] for c in (0, 1)], 1)
rev = np.stack([hp(rev[:, c], 300) for c in (0, 1)], 1)
d = int(.75 * BEAT * SR); dly = np.zeros((N, 2)); mm = lp(lead_p.mean(1), 5000)
for i in range(1, 5): dly[i * d:, i % 2] += .33 ** i * mm[:N - i * d]
vox = lead_p + bed_p + shout_p + rev * 10 ** (-9 / 20) + dly * 10 ** (-12 / 20)
# duck the band up to 2 dB under the lead vocal
env = uniform_filter1d(np.abs(lead_p + shout_p).mean(1), int(.15 * SR)); env = env / (env.max() + 1e-9)
band_d = band * (10 ** (-2.0 * np.clip(env * 3, 0, 1) / 20))[:, None]
mix = band_d + vox
fade_n = int(8 * SR); mix[-fade_n:] *= (np.linspace(1, 0, fade_n) ** 2)[:, None]
out, achieved = E.master(mix, LUFS)
sf.write(f'{OUT}/07v.wav', (np.clip(out, -1, 1) * 32767).astype(np.int16), SR, subtype='PCM_16')
sf.write(f'{OUT}/07v_vocals_only.wav', np.clip(vox / (np.abs(vox).max() + 1e-9) * .9, -1, 1), SR, subtype='PCM_16')
meta = dict(t.meta, title='Open Sky Chorus', bpm=BPM, key=C.key_name(b['tonic'], b['mode']), brief=b, take1=plan['take1'],
            vocals={'tuning': report, 'cues': sorted(cues, key=lambda c: c['t']), 'lead_offset_db': -3.0, 'achieved_lufs': achieved})
json.dump(meta, open(f'{OUT}/07v.json', 'w'), indent=1, default=str)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', f'{OUT}/07v.wav', '-b:a', '192k', '-metadata', 'title=Open Sky Chorus',
                '-metadata', 'artist=DJ Velvet Grey', '-metadata', 'album=Real Instruments Set (Take 2)', '-metadata', 'track=7/12',
                f'{OUT}/mp3/07-open-sky-chorus.mp3'], check=True)
print(json.dumps({'achieved_lufs': achieved, 'tuning': report, 'cues': len(cues)}, indent=1))
