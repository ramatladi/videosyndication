"""Master a Creative Claw track (Sello approved Creative Claw on 1 Nov 2026) to the channel's 179 s delivery format, so the
same export + blocking QC + video steps run on it as on hand-written songs.

    python3 mirage/gen_master.py in.mp3 out/mtrNNN.master.wav out/mtrNNN.meta.json --style afro

- decodes to 44.1 kHz stereo; refuses a track shorter than 179 s (regenerate instead of looping or stretching)
- keeps the first 179 s, ending on a downbeat-aligned 8 s fade (the track's own intro is kept)
- folds everything below 110 Hz to mono, sets -11 LUFS and limits peaks to -3 dBFS (so the AAC/MP3 encodes stay under -1.3 dBTP without a gain trim) (look-ahead limiter)
- measures tempo and key from the audio (models do not always follow the requested key/tempo): the description uses these
"""
import argparse, json, subprocess, sys
import numpy as np
import scipy.signal as ss
from scipy.ndimage import maximum_filter1d, uniform_filter1d

SR, LENGTH, FADE, TARGET = 44100, 179.0, 8.0, -11.0
KEYS = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
MAJ = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MIN = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def decode(path):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32).reshape(-1, 2).astype(np.float64)


def key_of(m):
    import librosa
    c = librosa.feature.chroma_cqt(y=m.astype(np.float32), sr=SR).mean(1)
    best = max(((np.corrcoef(np.roll(p, k), c)[0, 1], k, q) for k in range(12) for p, q in ((MAJ, ''), (MIN, 'm'))))
    return KEYS[best[1]] + best[2], round(float(best[0]), 3)


def limiter(x, ceil_db=-3.0, look=0.005, rel=0.08):
    c = 10 ** (ceil_db / 20); a = np.abs(x).max(1)
    need = np.minimum(1.0, c / np.maximum(maximum_filter1d(a, int(look * SR) * 2 + 1), 1e-9))
    g = need.copy(); k = np.exp(-1 / (rel * SR))
    for i in range(1, len(g)): g[i] = min(need[i], k * g[i - 1] + (1 - k))      # instant attack (look-ahead), smooth release
    g = uniform_filter1d(g, int(look * SR))                                     # smooth the attack inside the look-ahead window
    d = int(look * SR / 2); g = np.concatenate([g[d:], np.full(d, g[-1])])
    return np.clip(x * g[:, None], -c, c)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('src'); ap.add_argument('wav'); ap.add_argument('meta'); ap.add_argument('--style', required=True)
    a = ap.parse_args()
    import librosa, pyloudnorm as pl, soundfile as sf
    x = decode(a.src); dur = len(x) / SR
    if dur < LENGTH: sys.exit(f'REFUSED: generated track is {dur:.1f}s, shorter than {LENGTH}s: generate it again')
    m = x.mean(1)
    m22 = librosa.resample(m[: int(150 * SR)].astype(np.float32), orig_sr=SR, target_sr=22050)
    tempo, beats = librosa.beat.beat_track(y=m22, sr=22050, units='time', hop_length=128)     # fine hop: +-0.5 BPM
    d = np.diff(beats); t0 = float(np.atleast_1d(tempo)[0]); d = d[np.abs(d - 60 / t0) < 0.15 * 60 / t0]
    bpm = 60 / float(d.mean()) if len(d) > 16 else t0; key, key_conf = key_of(m)
    # end on the bar line closest to 179 s: start the cut LENGTH s before it so the fade lands on a musical boundary
    bar = 240 / bpm; bt = np.asarray(beats); downs = bt[::4] if len(bt) else np.array([0.0])
    ends = downs + LENGTH; ok = ends[ends <= dur]
    start = float(downs[np.argmin(np.abs(ok - LENGTH))] if len(ok) and np.min(np.abs(ok - LENGTH)) < bar and downs[0] < 2 else 0.0)
    if start + LENGTH > dur: start = 0.0
    y = x[int(start * SR): int(start * SR) + int(LENGTH * SR)].copy()
    n = int(FADE * SR); y[-n:] *= np.cos(np.linspace(0, np.pi / 2, n))[:, None] ** 2
    fi = int(.02 * SR); y[:fi] *= np.linspace(0, 1, fi)[:, None]
    # mono low end
    sos = ss.butter(4, 110, 'low', fs=SR, output='sos'); lo = ss.sosfiltfilt(sos, y, axis=0)
    y = y - lo + lo.mean(1, keepdims=True)
    meter = pl.Meter(SR)
    for _ in range(3):
        y = limiter(y * 10 ** ((TARGET - meter.integrated_loudness(y)) / 20))
    y[-1] = 0
    sf.write(a.wav, y.astype(np.float32), SR, subtype='FLOAT')
    meta = {'style': a.style, 'bpm': round(bpm), 'bpm_measured': round(bpm, 2), 'key_measured': key, 'key_confidence': key_conf,
            'source_duration_s': round(dur, 2), 'cut_start_s': round(start, 2), 'sections': [], 'outro_start_s': LENGTH - FADE - 4 * bar,
            'engine_version': 'creative-claw', 'target_lufs': TARGET, 'length_s': LENGTH, 'lufs': round(meter.integrated_loudness(y), 2)}
    json.dump(meta, open(a.meta, 'w'), indent=1)
    print(json.dumps(meta))


if __name__ == '__main__':
    main()
