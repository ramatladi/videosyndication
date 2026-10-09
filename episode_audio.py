#!/usr/bin/env python3
"""Voices (Festival), timeline, lip-sync envelopes, music bed and SFX for one episode.
usage: python3 episode_audio.py episodes/epNNN.json WORKDIR"""
import subprocess, json, math, os, sys, wave
import numpy as np

EP = json.load(open(sys.argv[1])); WD = sys.argv[2]
os.makedirs(f'{WD}/lines', exist_ok=True)
SR = 44100; FPS = 30
INTRO = 3.2; OUTRO = 4.0
VOICES = {  # festival voice, pitch shift (semitones), tempo, gain
    'M': ('voice_cmu_us_slt_arctic_hts', -1.5, 0.94, 1.0),
    'P': ('voice_kal_diphone', 6.5, 1.06, 0.95),
    'G': ('voice_us2_mbrola', -3.0, 0.88, 1.1),
}

def synth(spk, text, path):
    v, semi, tempo, _ = VOICES[spk]
    with open(f'{WD}/lines/tmp.txt', 'w') as f: f.write(text)
    subprocess.run(['text2wave', '-eval', f'({v})', f'{WD}/lines/tmp.txt', '-o', f'{WD}/lines/raw.wav'], check=True, capture_output=True)
    r = 2 ** (semi / 12)
    af = (f'aresample={SR},asetrate={SR}*{r:.5f},aresample={SR},atempo={tempo / r:.5f},'
          f'highpass=f=90,acompressor=threshold=0.12:ratio=3:attack=5:release=80,silenceremove=start_periods=1:start_threshold=-50dB,'
          f'areverse,silenceremove=start_periods=1:start_threshold=-50dB,areverse')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', f'{WD}/lines/raw.wav', '-af', af, '-ac', '1', '-ar', str(SR), path], check=True)
    with wave.open(path) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    return x / (np.max(np.abs(x)) + 1e-9) * 0.8

# ------------------------------------------------ timeline
t = INTRO
lines = []; voice_tracks = {}
fly_t = None; candle_t = None; stings = []; arms = []; flares = []
L = EP['lines']
for i, ln in enumerate(L):
    pre = ln.get('pre', 0.0)
    if i > 0 and L[i - 1].get('after') == 'fly': pre = max(pre, 3.4)
    t += pre
    spk = ln['spk']; spks = ['M', 'P'] if spk == 'MP' else [spk]
    clips = {s: synth(s, ln['text'], f'{WD}/lines/{i:02d}_{s}.wav') for s in spks}
    dur = max(len(c) for c in clips.values()) / SR
    rec = dict(i=i, spk=spk, text=ln['text'], shot=ln.get('shot', 'W'), start=round(t, 3), end=round(t + dur, 3))
    lines.append(rec)
    for s, c in clips.items(): voice_tracks.setdefault(s, []).append((t, c))
    if ln.get('during') == 'flare': flares.append([rec['start'], rec['end']])
    t += dur + ln.get('post', 0.5)
    a = ln.get('after')
    if a == 'sting': stings.append(rec['end'] + 0.25)
    if a == 'fly' and fly_t is None: fly_t = t
    if a == 'candle_out': candle_t = t
for i, ln in enumerate(L):
    if ln.get('during') == 'arms':
        s0 = lines[i]['start'] + (lines[i]['end'] - lines[i]['start']) * 0.62
        s1 = lines[i + 2]['start'] + 0.1 if i + 2 < len(lines) else lines[i]['end'] + 2
        arms.append([s0, s1])
TOTAL = t + OUTRO
end_t = candle_t if candle_t else TOTAL - OUTRO
N = int(TOTAL * SR)
dry = np.zeros((2, N)); wet = np.zeros((2, N))
rg = np.random.default_rng(EP.get('id', 1))

def add(t0, sig, g=1.0, pan=0.0, send=0.0):
    i = int(t0 * SR)
    if i >= N: return
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
def mbox(freq, d=1.8):
    t = tt(d)
    s = (np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * 2 * freq * t) * np.exp(-t * 5)
         + 0.18 * np.sin(2 * np.pi * 3.02 * freq * t) * np.exp(-t * 8))
    return s * np.minimum(1, t / 0.002) * np.exp(-t * 2.6)
def organ(freq, d=2.0, dec=1.2):
    t = tt(d)
    s = sum(np.sin(2 * np.pi * freq * k * t * (1 + 0.0015 * k)) / k ** 1.3 for k in range(1, 9))
    return s * np.minimum(1, t / 0.03) * np.exp(-t * dec)

# ------------------------------------------------ voices + lip-sync envelopes
pans = {'M': -0.2, 'P': 0.15, 'G': 0.35}
nfr = int(TOTAL * FPS) + 1; env = {}
for s, clips in voice_tracks.items():
    track = np.zeros(N)
    for t0, c in clips:
        i = int(t0 * SR); track[i:i + len(c)] += c[:max(0, N - i)]
    add(0, track, VOICES[s][3] * 0.85, pans[s], 0.18 if s != 'G' else 0.35)
    hop = SR // FPS
    rms = np.array([np.sqrt(np.mean(track[k * hop:(k + 1) * hop] ** 2)) if k * hop < N else 0 for k in range(nfr)])
    ref = np.percentile(rms[rms > 0.01], 90) if np.any(rms > 0.01) else 1
    e = np.convolve(np.clip(rms / ref, 0, 1.2), [0.25, 0.5, 0.25], mode='same')
    env[s] = np.clip(e, 0, 1)
np.savez(f'{WD}/env.npz', **env)

# ------------------------------------------------ music bed + ambience
t_all = np.arange(N) / SR
duck = np.ones(N)
for ln in lines: duck[int(ln['start'] * SR):int(ln['end'] * SR)] = 0.55
duck = np.convolve(duck, np.ones(4410) / 4410, mode='same')
dr = (np.sin(2 * np.pi * 73.42 * t_all) + 0.5 * np.sin(2 * np.pi * 110 * t_all + 1) + 0.3 * np.sin(2 * np.pi * 73.9 * t_all))
dr *= (0.75 + 0.25 * np.sin(2 * np.pi * 0.21 * t_all)) * np.minimum(1, t_all / 2)
cut = int(end_t * SR); dr[cut:] *= np.exp(-(t_all[cut:] - end_t) * 2)
add(0, dr * duck, 0.035)
barA = [74, 69, 77, 69, 76, 69, 73, 69]; barB = [74, 69, 77, 69, 79, 77, 76, 73]; barC = [74, 77, 81, 79, 77, 76, 74, None]
seq = barA + barB + barA + barC
gap = (fly_t + 0.6, fly_t + 2.6) if fly_t else (-1, -1)
tn, j = 0.2, 0
while tn < end_t - 0.5:
    m = seq[j % len(seq)]
    if m and not (gap[0] < tn < gap[1]):
        add(tn, mbox(mf(m)), 0.055 * duck[min(N - 1, int(tn * SR))], 0.3 * math.sin(j * 0.7), 0.6)
    tn += 0.5; j += 1
wind = bp(rg.standard_normal(N), 150, 900) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.07 * t_all + 1)) ** 2
add(0, wind, 0.05, -0.3)
cr = np.zeros(N)
for k in range(int(TOTAL * 1.6)):
    t0 = k / 1.6 + 0.2 * rg.random()
    ch = tt(0.12); chirp = np.sin(2 * np.pi * 4300 * ch) * (np.sin(2 * np.pi * 30 * ch) > 0) * np.exp(-ch * 8)
    i = int(t0 * SR)
    if i + len(chirp) < N: cr[i:i + len(chirp)] += chirp * (2.5 if gap[0] - 0.3 < t0 < gap[1] + 0.5 else 1)
add(0, cr, 0.012, 0.55, 0.3)
add(0.25, mbox(mf(62), 2.5), 0.12, 0, 0.6); add(0.25, mbox(mf(69), 2.5), 0.08, 0, 0.6)
for s_t in stings:
    for k, m in enumerate((50, 49, 46)):
        add(s_t + k * 0.32, organ(mf(m), 1.6 if k == 2 else 0.4, 1.0 if k == 2 else 5), 0.06 if k < 2 else 0.09, 0, 0.6)
        add(s_t + k * 0.32, organ(mf(m - 12), 1.6 if k == 2 else 0.4, 1.0 if k == 2 else 5), 0.05, 0, 0.4)
def flaps(t0, d):
    for k in range(int(d * 9)):
        f = tt(0.07); add(t0 + k / 9, bp(rg.standard_normal(len(f)), 300, 2500) * np.sin(np.pi * f / 0.07), 0.25, 0.4)
if fly_t: flaps(fly_t, 0.9); flaps(fly_t + 2.3, 0.8)
if candle_t:
    f = tt(0.6); add(candle_t, bp(rg.standard_normal(len(f)), 500, 4000) * np.sin(np.pi * f / 0.6) ** 2, 0.35, 0.35)
for m in (50, 53, 57):
    add(end_t + 0.5, organ(mf(m), 3.0, 0.9), 0.045, 0, 0.7)
add(end_t + 0.5, mbox(mf(74), 3.0), 0.12, 0, 0.8)

ir_t = tt(1.4)
for ch in range(2):
    ir = bp(rg.standard_normal(len(ir_t)), None, 5000) * np.exp(-ir_t * 3.6); ir /= np.sqrt(np.sum(ir ** 2))
    n2 = 1 << int(np.ceil(np.log2(N + len(ir))))
    dry[ch] += np.fft.irfft(np.fft.rfft(wet[ch], n2) * np.fft.rfft(ir, n2), n2)[:N] * 0.5
dry *= np.minimum(1, t_all / 0.05) * np.clip((TOTAL - t_all) / 1.0, 0, 1)
out = np.tanh(1.4 * dry / np.max(np.abs(dry))) / np.tanh(1.4) * 0.92
with wave.open(f'{WD}/audio.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((out.T * 32767).astype(np.int16).tobytes())
json.dump(dict(total=TOTAL, intro=INTRO, intro_text=EP.get('intro', []), lines=lines,
               events=dict(fly=fly_t, candle=candle_t, end=end_t, stings=stings, arms=arms, flares=flares)),
          open(f'{WD}/timeline.json', 'w'), indent=1)
print(f'audio ok: {TOTAL:.1f}s, {len(lines)} lines')
