#!/usr/bin/env python3
"""Audio for a cast-engine episode: per-character voices (Festival), timeline, lip-sync envelopes, music mood, SFX.
usage: python3 engine/audio.py episodes/epNNN.json WORKDIR"""
import subprocess, json, math, os, sys, wave
import numpy as np

EP = json.load(open(sys.argv[1])); WD = sys.argv[2]
os.makedirs(f'{WD}/lines', exist_ok=True)
SR = 44100; FPS = 30; INTRO = 3.0; OUTRO = 3.0
BASES = {'slt': 'voice_cmu_us_slt_arctic_hts', 'us1': 'voice_us1_mbrola', 'kal': 'voice_kal_diphone',
         'us2': 'voice_us2_mbrola', 'us3': 'voice_us3_mbrola', 'en1': 'voice_en1_mbrola'}
CAST = {c['id']: c for c in EP['cast']}
rg = np.random.default_rng(EP.get('id', 1))

def synth(cid, text, path):
    v = CAST[cid].get('voice', {}); base = BASES.get(v.get('base', 'slt'), BASES['slt'])
    semi = float(v.get('pitch', 0)); tempo = float(v.get('tempo', 1.0))
    with open(f'{WD}/lines/tmp.txt', 'w') as f: f.write(text)
    subprocess.run(['text2wave', '-eval', f'({base})', f'{WD}/lines/tmp.txt', '-o', f'{WD}/lines/raw.wav'], check=True, capture_output=True)
    r = 2 ** (semi / 12)
    af = (f'aresample={SR},asetrate={SR}*{r:.5f},aresample={SR},atempo={max(0.5, min(2.0, tempo / r)):.5f},'
          f'highpass=f=90,acompressor=threshold=0.12:ratio=3:attack=5:release=80,silenceremove=start_periods=1:start_threshold=-50dB,'
          f'areverse,silenceremove=start_periods=1:start_threshold=-50dB,areverse')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', f'{WD}/lines/raw.wav', '-af', af, '-ac', '1', '-ar', str(SR), path], check=True)
    with wave.open(path) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    return x / (np.max(np.abs(x)) + 1e-9) * 0.8

def spk_list(s):
    if s == 'all': return list(CAST)
    return s if isinstance(s, list) else [s]

# ---------------------------------------------------------------- timeline
# Every episode is stretched to exactly TARGET seconds (default 175 = 2:55) by adding small pauses
# between lines and a longer outro. Scripts that run long or far too short fail with a clear message.
TARGET = float(EP.get('target_seconds', 175))
synth_all = []
for i, ln in enumerate(EP['lines']):
    ids = spk_list(ln['spk'])
    clips = {c: synth(c, ln['text'], f'{WD}/lines/{i:02d}_{c}.wav') for c in ids}
    synth_all.append((ln, ids, clips, max(len(c) for c in clips.values()) / SR))
natural = INTRO + OUTRO + sum(ln.get('pre', 0.0) + d + ln.get('post', 0.45) for ln, _, _, d in synth_all)
extra = TARGET - natural
nl = len(synth_all)
if extra < 0:
    sys.exit(f'SCRIPT TOO LONG: natural length {natural:.1f}s exceeds the {TARGET:.0f}s target by {-extra:.1f}s - cut lines or shorten them.')
per_gap = min(0.7, extra / nl)
outro_add = extra - per_gap * nl
if outro_add > 4.0:
    sys.exit(f'SCRIPT TOO SHORT: natural length {natural:.1f}s; needs about {outro_add - 4.0 + 0.1:.1f}s more dialogue to reach {TARGET:.0f}s - add lines.')
OUTRO += outro_add
t = INTRO; lines = []; tracks = {}; sfx = []
for i, (ln, ids, clips, dur) in enumerate(synth_all):
    t += ln.get('pre', 0.0)
    lines.append(dict(i=i, spk=ids, text=ln['text'], shot=ln.get('shot', 'CU'), gesture=ln.get('gesture'),
                      jump=bool(ln.get('jump')), start=round(t, 3), end=round(t + dur, 3)))
    for c, x in clips.items(): tracks.setdefault(c, []).append((t, x))
    t += dur + ln.get('post', 0.45) + per_gap
    if ln.get('after'):
        sfx.append((lines[-1]['end'] + 0.2, ln['after']))
END = t; TOTAL = TARGET
N = int(TOTAL * SR); dry = np.zeros((2, N)); wet = np.zeros((2, N)); t_all = np.arange(N) / SR

def add(t0, sig, g=1.0, pan=0.0, send=0.0):
    i = int(t0 * SR)
    if i >= N or i < 0: return
    j = min(N, i + len(sig)); a = (pan + 1) * math.pi / 4; seg = sig[:j - i] * g
    dry[0, i:j] += seg * math.cos(a); dry[1, i:j] += seg * math.sin(a)
    if send: wet[0, i:j] += seg * send * math.cos(a); wet[1, i:j] += seg * send * math.sin(a)
def tt(d): return np.arange(int(d * SR)) / SR
def bp(x, lo=None, hi=None):
    n = len(x); X = np.fft.rfft(x); f = np.fft.rfftfreq(n, 1 / SR); m = np.ones_like(f)
    if lo: m *= 1 / (1 + (lo / np.maximum(f, 1e-3)) ** 4)
    if hi: m *= 1 / (1 + (f / hi) ** 4)
    return np.fft.irfft(X * m, n)
mf = lambda m: 440 * 2 ** ((m - 69) / 12)
def pluck(freq, d=1.2, bright=1.0):
    t = tt(d)
    s = sum(np.sin(2 * np.pi * freq * k * t) * (bright ** (k - 1)) / k * np.exp(-t * (3 + 2 * k)) for k in range(1, 6))
    return s * np.minimum(1, t / 0.003)
def mbox(freq, d=1.8):
    t = tt(d)
    return (np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(4 * np.pi * freq * t) * np.exp(-t * 5)) * np.minimum(1, t / 0.002) * np.exp(-t * 2.6)
def pad(freqs, d, att=0.4):
    t = tt(d); s = sum(np.sin(2 * np.pi * f * t + k) + 0.3 * np.sin(2 * np.pi * f * 2.003 * t) for k, f in enumerate(freqs))
    env = np.minimum(1, t / att) * np.minimum(1, (d - t) / 0.4); return s * env / len(freqs)
def organ(freq, d=2.0, dec=1.2):
    t = tt(d); s = sum(np.sin(2 * np.pi * freq * k * t * (1 + 0.0015 * k)) / k ** 1.3 for k in range(1, 9))
    return s * np.minimum(1, t / 0.03) * np.exp(-t * dec)
def kick():
    t = tt(0.35); return np.sin(2 * np.pi * np.cumsum(45 + 90 * np.exp(-t * 30)) / SR) * np.exp(-t * 9)
def snare(d=0.2):
    t = tt(d); return bp(rg.standard_normal(len(t)), 800, 7000) * np.exp(-t * 22) + 0.4 * np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30)
def hat():
    t = tt(0.06); return bp(rg.standard_normal(len(t)), 6000, None) * np.exp(-t * 70)

# ---------------------------------------------------------------- voices + envelopes
nfr = int(TOTAL * FPS) + 1; env = {}
ids = list(CAST)
for k, (c, clips) in enumerate(tracks.items()):
    tr = np.zeros(N)
    for t0, x in clips:
        i = int(t0 * SR); tr[i:i + len(x)] += x[:max(0, N - i)]
    pan = (ids.index(c) / max(1, len(ids) - 1) - 0.5) * 0.5 if len(ids) > 1 else 0
    add(0, tr, 0.85, pan, 0.15)
    hop = SR // FPS
    rms = np.array([np.sqrt(np.mean(tr[q * hop:(q + 1) * hop] ** 2)) if q * hop < N else 0 for q in range(nfr)])
    ref = np.percentile(rms[rms > 0.01], 90) if np.any(rms > 0.01) else 1
    env[c] = np.clip(np.convolve(np.clip(rms / ref, 0, 1.2), [0.25, 0.5, 0.25], mode='same'), 0, 1)
np.savez(f'{WD}/env.npz', **env)

# ---------------------------------------------------------------- music
duck = np.ones(N)
for ln in lines: duck[int(ln['start'] * SR):int(ln['end'] * SR)] = 0.5
duck = np.convolve(duck, np.ones(4410) / 4410, mode='same')
mood = EP.get('music', 'upbeat')
music = np.zeros(N)
def mput(t0, sig, g):
    i = int(t0 * SR)
    if 0 <= i < N: j = min(N, i + len(sig)); music[i:j] += sig[:j - i] * g
if mood == 'spooky':
    seq = [74, 69, 77, 69, 76, 69, 73, 69, 74, 69, 77, 69, 79, 77, 76, 73]
    for j, tn in enumerate(np.arange(0.2, END, 0.5)): mput(tn, mbox(mf(seq[j % len(seq)])), 0.06)
    music += 0.03 * (np.sin(2 * np.pi * 73.42 * t_all) + 0.5 * np.sin(2 * np.pi * 110 * t_all)) * np.minimum(1, t_all / 2)
elif mood == 'dramatic':
    chords = [[50, 53, 57, 62], [46, 50, 53, 58], [53, 57, 60, 65], [48, 52, 55, 60]]
    for j, tn in enumerate(np.arange(0.0, END, 4.0)):
        mput(tn, pad([mf(m) for m in chords[j % 4]], 4.3, 1.2), 0.05)
        mput(tn, kick(), 0.18)
    for j, tn in enumerate(np.arange(0.0, END, 1.0)): mput(tn, pluck(mf(74 + [0, 3, 7, 3][j % 4]), 1.0, 0.5), 0.025)
elif mood == 'lofi':
    chords = [[53, 57, 60, 64], [52, 55, 59, 62], [50, 53, 57, 60], [48, 52, 55, 59]]
    beat = 60 / 80
    for j, tn in enumerate(np.arange(0.0, END, beat * 4)):
        for m in chords[j % 4]: mput(tn, pluck(mf(m), 3.0, 0.4), 0.035)
        for b in range(4):
            if b in (0, 2): mput(tn + b * beat, kick(), 0.16)
            if b in (1, 3): mput(tn + b * beat, snare(), 0.07)
            mput(tn + b * beat + beat / 2, hat(), 0.04)
    music += bp(rg.standard_normal(N), 1000, 6000) * 0.004 * (rg.random(N) > 0.9995) * 30 + bp(rg.standard_normal(N), 200, 3000) * 0.003
else:  # upbeat
    beat = 60 / 112; prog = [[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]]
    for j, tn in enumerate(np.arange(0.0, END, beat * 4)):
        ch = prog[j % 4]
        for b in range(8):
            mput(tn + b * beat / 2, pluck(mf(ch[[0, 1, 2, 1, 0, 2, 1, 2][b]] + 12), 0.6, 0.7), 0.04)
        mput(tn, pluck(mf(ch[0] - 12), 1.5, 0.3), 0.09); mput(tn + 2 * beat, pluck(mf(ch[0] - 12), 1.5, 0.3), 0.07)
        for b in range(4):
            mput(tn + b * beat, kick(), 0.10 if b % 2 == 0 else 0)
            if b % 2: mput(tn + b * beat, snare(0.12), 0.045)
cut = int(END * SR); music[cut:] *= np.exp(-(t_all[cut:] - END) * 3)
add(0, music * duck * np.minimum(1, t_all / 0.8), 1.0, 0, 0.3)

# ---------------------------------------------------------------- SFX
for t0, kind in sfx:
    if kind == 'sting':
        for k, m in enumerate((50, 49, 46)):
            add(t0 + k * 0.32, organ(mf(m), 1.6 if k == 2 else 0.4, 1.0 if k == 2 else 5), 0.07 if k < 2 else 0.1, 0, 0.6)
    elif kind == 'boing':
        x = tt(0.5); add(t0, np.sin(2 * np.pi * np.cumsum(180 + 220 * np.sin(x * 14) * np.exp(-x * 4)) / SR) * np.exp(-x * 5), 0.35)
    elif kind == 'whoosh':
        x = tt(0.45); add(t0, bp(rg.standard_normal(len(x)), 400, 3000) * np.sin(np.pi * x / 0.45) ** 2, 0.4)
    elif kind == 'applause':
        x = tt(2.2); s = bp(rg.standard_normal(len(x)), 800, 6000) * (0.5 + 0.5 * (rg.random(len(x)) > 0.7))
        add(t0, s * np.minimum(1, x / 0.2) * np.clip((2.2 - x) / 0.8, 0, 1), 0.25, 0, 0.4)
    elif kind == 'rimshot':
        add(t0, snare(), 0.5); add(t0 + 0.25, snare(), 0.5); add(t0 + 0.5, bp(rg.standard_normal(SR), 5000, None) * np.exp(-tt(1.0) * 3), 0.2)
    elif kind == 'record_scratch':
        x = tt(0.4); f = 300 + 1200 * np.abs(np.sin(x * 20))
        add(t0, np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * bp(rg.standard_normal(len(x)), 500, 4000) * 0.5 * np.exp(-x * 4), 0.3)
    elif kind == 'ding':
        x = tt(1.5); add(t0, (np.sin(2 * np.pi * 1568 * x) + 0.4 * np.sin(2 * np.pi * 3920 * x)) * np.exp(-x * 3), 0.2, 0, 0.5)
add(0.2, pluck(mf(72), 1.2), 0.15, 0, 0.5); add(0.2, pluck(mf(79), 1.2), 0.1, 0, 0.5)
add(END + 0.2, pluck(mf(72), 2.0), 0.15, 0, 0.6); add(END + 0.2, pluck(mf(76), 2.0), 0.12, 0, 0.6); add(END + 0.2, pluck(mf(79), 2.0), 0.12, 0, 0.6)

ir_t = tt(1.2)
for ch in range(2):
    ir = bp(rg.standard_normal(len(ir_t)), None, 5000) * np.exp(-ir_t * 4.5); ir /= np.sqrt(np.sum(ir ** 2))
    n2 = 1 << int(np.ceil(np.log2(N + len(ir))))
    dry[ch] += np.fft.irfft(np.fft.rfft(wet[ch], n2) * np.fft.rfft(ir, n2), n2)[:N] * 0.45
dry *= np.minimum(1, t_all / 0.05) * np.clip((TOTAL - t_all) / 0.8, 0, 1)
out = np.tanh(1.4 * dry / np.max(np.abs(dry))) / np.tanh(1.4) * 0.92
with wave.open(f'{WD}/audio.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((out.T * 32767).astype(np.int16).tobytes())
json.dump(dict(total=TOTAL, intro=INTRO, end=END, lines=lines), open(f'{WD}/timeline.json', 'w'), indent=1)
print(f'audio ok: {TOTAL:.1f}s, {len(lines)} lines, mood {mood}')
