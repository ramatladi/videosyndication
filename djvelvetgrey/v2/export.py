"""Final export with codec headroom: makes the delivery MP3 and AAC, decodes them, measures their
true peak (4x oversampled) and trims gain until BOTH decoded finals are at or below the ceiling.

    python3 export.py master.wav out_dir name [--title T] [--ceiling -1.3]

Writes out_dir/name.delivery.wav (trimmed PCM), name.mp3 (320k) and name.m4a (AAC 256k, fast coder - measured to behave near-monotonically; the exact
stream later copied into the MP4) plus name.export.json. Exit 3 if the ceiling cannot be met.
"""
import argparse, json, os, subprocess, sys, tempfile
import numpy as np, scipy.signal as ss
from scipy.io import wavfile

SR = 44100


def decode(path):
    with tempfile.NamedTemporaryFile(suffix='.wav') as f:
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', path, '-c:a', 'pcm_f32le', '-ar', str(SR), f.name], check=True)
        return wavfile.read(f.name)[1].astype(np.float64)


def true_peak_db(x):
    up = ss.resample_poly(x.astype(np.float32), 4, 1, axis=0)
    return float(20 * np.log10(np.abs(up).max() + 1e-12))


def encode(wav, mp3, m4a, title):
    meta = ['-metadata', f'title={title}', '-metadata', 'artist=DJ Velvet Grey']
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', wav, '-c:a', 'libmp3lame', '-b:a', '320k'] + meta + [mp3], check=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', wav, '-c:a', 'aac', '-aac_coder', 'fast', '-b:a', '256k'] + meta + [m4a], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('master'); ap.add_argument('out_dir'); ap.add_argument('name')
    ap.add_argument('--title', default=''); ap.add_argument('--ceiling', type=float, default=-1.3)
    a = ap.parse_args()
    sr, x = wavfile.read(a.master)
    x = x.astype(np.float64) / (32768 if x.dtype == np.int16 else 1)
    base = os.path.join(a.out_dir, a.name)
    dwav, mp3, m4a = base + '.delivery.wav', base + '.mp3', base + '.m4a'
    gain_db, log = 0.0, []
    for it in range(10):
        y = np.clip(x * 10 ** (gain_db / 20), -1, 1)
        wavfile.write(dwav, SR, (y * 32767).astype(np.int16))
        encode(dwav, mp3, m4a, a.title)
        tp = {'mp3': true_peak_db(decode(mp3)), 'aac': true_peak_db(decode(m4a)), 'pcm': true_peak_db(y)}
        worst = max(tp.values())
        log.append({'iteration': it, 'gain_db': round(gain_db, 2), **{k: round(v, 2) for k, v in tp.items()}})
        if worst <= a.ceiling: break
        gain_db -= min(1.0, (worst - a.ceiling) + 0.1)   # small steps: AAC peaks are not perfectly linear in gain
    ok = worst <= a.ceiling
    rep = {'ceiling_dbtp': a.ceiling, 'gain_trim_db': round(gain_db, 2), 'iterations': log, 'ok': ok,
           'files': {'delivery_wav': dwav, 'mp3': mp3, 'aac': m4a}}
    json.dump(rep, open(base + '.export.json', 'w'), indent=1)
    print(json.dumps({'ok': ok, 'gain_trim_db': rep['gain_trim_db'], 'final': log[-1]}))
    sys.exit(0 if ok else 3)


if __name__ == '__main__':
    main()
