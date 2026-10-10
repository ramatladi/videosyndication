"""Automated technical checks for a rendered track. NOT a listening assessment.

    python3 qc.py track.wav [encoded.mp3|.mp4] [meta.json]

Prints a JSON report. Items under "listening_required" can only be judged by a person.
"""
import json, subprocess, sys, re, numpy as np, scipy.signal as ss
from scipy.io import wavfile


def ffmpeg_true_peak(path):
    out = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', path, '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    summ = out[out.rfind('Summary'):]
    i = re.search(r'I:\s+(-?[\d.]+) LUFS', summ); p = re.search(r'Peak:\s+(-?[\d.inf]+) dBFS', summ)
    return (float(i.group(1)) if i else None), (float(p.group(1)) if p else None)


def report(wav, encoded=None, meta=None):
    import pyloudnorm as pyln
    sr, x = wavfile.read(wav); x = x.astype(np.float64) / (32768 if x.dtype == np.int16 else 1)
    dur = len(x) / sr
    lufs = pyln.Meter(sr).integrated_loudness(x)
    up = ss.resample_poly(x[: sr * 60 * 3].astype(np.float32), 4, 1, axis=0)
    tp_wav = float(20 * np.log10(np.abs(up).max() + 1e-12))
    clipped = int((np.abs(x) >= 0.9999).sum())
    # click suspects: band-limited (<6 kHz) second-difference spikes that are NOT repeated one bar earlier
    # (kick/hat attacks repeat every bar, real clicks do not). Needs bpm from meta; else informational only.
    lp = ss.sosfilt(ss.butter(4, 6000, 'low', fs=sr, output='sos'), x, axis=0)
    d2 = np.abs(np.diff(lp, 2, axis=0)).max(1)
    loc = ss.medfilt(d2[::32], 31).repeat(32)[:len(d2)] + 1e-6
    spikes = np.where(d2 > 40 * loc)[0]
    w = int(.5 * sr); r = np.sqrt(np.maximum(np.convolve((x ** 2).mean(1), np.ones(w) / w, 'valid')[::w], 0))
    body = r[1: max(1, len(r) - int(9 / .5))]          # skip the first window and the 8 s fade-out
    silent = int((20 * np.log10(body + 1e-12) < -50).sum())
    corr = float(np.corrcoef(x[:, 0], x[:, 1])[0, 1])
    low = ss.sosfilt(ss.butter(8, 80, 'low', fs=sr, output='sos'), x, axis=0)
    side = (low[:, 0] - low[:, 1]) / 2; mid = (low[:, 0] + low[:, 1]) / 2
    low_side_db = 10 * np.log10((side ** 2).mean() / ((mid ** 2).mean() + 1e-15) + 1e-15)
    rep = {'label': 'Automated technical checks only — not a listening assessment',
           'duration_s': round(dur, 3), 'duration_ok': abs(dur - 179.0) <= .05,
           'integrated_lufs_wav': round(lufs, 1),
           'true_peak_wav_dbtp': round(tp_wav, 2),
           'clipped_samples': clipped,
           'silent_half_seconds_in_body': silent,
           'stereo_correlation': round(corr, 3), 'mono_compatible': bool(corr > 0.2),
           'low_end_below_80hz_side_vs_mid_db': round(float(low_side_db), 1), 'low_end_mono': bool(low_side_db < -30)}
    if encoded:
        li, pk = ffmpeg_true_peak(encoded)
        rep.update({'encoded_file': encoded, 'integrated_lufs_encoded': li, 'true_peak_encoded_dbtp': pk,
                    'true_peak_target_met': bool(pk is not None and pk <= -1.0)})
    clicks = None
    if meta:
        m = json.load(open(meta))
        barN = int(4 * 60 / m['bpm'] * sr)
        clicks = 0
        for i in spikes[np.r_[True, np.diff(spikes) > sr // 100]]:
            ref = [d2[max(0, i - k * barN - 200): i - k * barN + 200].max() if i - k * barN > 200 else 0 for k in (1, 2, 8, 16)]
            if max(ref) < 0.5 * d2[i]: clicks += 1
        rep['click_suspects'] = clicks
        rep.update({'tease_at_s': m.get('tease_s'), 'full_hook_at_s': m.get('full_hook_s'),
                    'second_drop_changes': m.get('drop2_changes'), 'arrangement': [s['name'] for s in m.get('sections', [])]})
    rep['listening_required'] = ['hook memorability', 'groove feel', 'tone and mix balance at matched loudness',
                                 'whether the second drop pays off', 'overall quality and distinctiveness']
    return rep


if __name__ == '__main__':
    a = sys.argv[1:]
    print(json.dumps(report(a[0], a[1] if len(a) > 1 else None, a[2] if len(a) > 2 else None), indent=1, default=float))
