"""Blocking technical QC on the FINAL delivery files. Not a listening assessment.

    python3 qc.py --wav name.delivery.wav --mp3 name.mp3 --mp4 name.mp4 --meta name.meta.json [--out qc.json]

Decodes the final MP3 and the MP4's audio stream, and checks the WAV/MP3/MP4 trio.
Exit 0 = all blocking checks pass; exit 2 = at least one blocking failure; exit 4 = QC itself
could not run (missing/undecodable input) — both non-zero codes must stop publishing.
Each failure has a category so the caller can react correctly:
  master    true peak / loudness / clipping  -> fix export or mastering (do NOT retry a different hook)
  structure duration / silence / ending      -> engine or arrangement defect
  signal    click suspects / discontinuities -> engine defect (re-render once, then stop)
  decode    a final file does not decode     -> re-encode, then stop
  stereo    mono compatibility / low end     -> mix defect
"""
import argparse, json, os, subprocess, sys, tempfile
import numpy as np, scipy.signal as ss
from scipy.io import wavfile

SR = 44100
LENGTH = 179.0
TP_MAX = -1.0


def decode(path):
    with tempfile.NamedTemporaryFile(suffix='.wav') as f:
        r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', path, '-map', '0:a:0', '-c:a', 'pcm_f32le', '-ar', str(SR), f.name],
                           capture_output=True, text=True)
        errs = r.stderr.strip()
        if r.returncode != 0 or not os.path.getsize(f.name): raise RuntimeError(f'decode failed: {path}: {errs[:300]}')
        return wavfile.read(f.name)[1].astype(np.float64), errs


def true_peak_db(x):
    up = ss.resample_poly(x.astype(np.float32), 4, 1, axis=0)
    return float(20 * np.log10(np.abs(up).max() + 1e-12))


def report(wav, mp3, mp4, meta):
    import pyloudnorm as pyln
    fails = []
    def fail(cat, msg): fails.append({'category': cat, 'check': msg})
    sr, x = wavfile.read(wav); x = x.astype(np.float64) / (32768 if x.dtype == np.int16 else 1)
    m = json.load(open(meta))
    rep = {'label': 'Automated technical checks only — not a listening assessment', 'files': {}}
    meter = pyln.Meter(SR)
    target = m.get('target_lufs')
    finals = {'wav': x}
    for name, path in (('mp3', mp3), ('mp4_audio', mp4)):
        try:
            y, errs = decode(path); finals[name] = y
            rep['files'][name] = {'decode_errors': errs[:200] or None}
            if errs: fail('decode', f'{name} decode reported errors')
        except Exception as e:
            fail('decode', str(e)); rep['files'][name] = {'decode_failed': True}
    for name, y in finals.items():
        d = len(y) / SR
        f = rep['files'].setdefault(name, {})
        f['duration_s'] = round(d, 3)
        f['true_peak_dbtp'] = round(true_peak_db(y), 2)
        f['integrated_lufs'] = round(float(meter.integrated_loudness(y)), 2)
        f['samples_over_full_scale'] = int((np.abs(y) > 1.0).sum())
        if abs(d - LENGTH) > (0.06 if name == 'wav' else 0.12): fail('structure', f'{name} duration {d:.3f}s not 179.0s')
        if f['true_peak_dbtp'] > TP_MAX: fail('master', f"{name} true peak {f['true_peak_dbtp']} dBTP > {TP_MAX}")
        if f['samples_over_full_scale']: fail('master', f"{name} has samples over full scale")
    if target is not None:
        lu = rep['files']['wav']['integrated_lufs']
        rep['target_lufs'] = target
        if lu < target - 2.5 or lu > target + 1.0: fail('master', f'loudness {lu} LUFS far from documented target {target}')
    # clipping (hard-limited PCM)
    if int((np.abs(x) >= 0.9999).sum()): fail('master', 'clipped samples in delivery WAV')
    # silence in the body (cumulative-sum RMS, fast)
    w = int(.5 * SR); p = np.concatenate([[0], np.cumsum((x ** 2).mean(1))])
    r = np.sqrt(np.maximum((p[w::w] - p[:-w:w]) / w, 0))
    body = r[1: max(1, len(r) - int(9 / .5))]
    rep['silent_half_seconds_in_body'] = int((20 * np.log10(body + 1e-12) < -50).sum())
    if rep['silent_half_seconds_in_body']: fail('structure', 'silence inside the track body')
    # ending: the outro must start before the fade and be heard for at least 4 bars
    bar = 240 / m['bpm']
    if m.get('outro_start_s') is not None:
        heard = (LENGTH - m['outro_start_s']) / bar
        rep['outro_bars_heard'] = round(heard, 1)
        if heard < 4: fail('structure', f'outro only {heard:.1f} bars before the end (truncated ending)')
    # click suspects: spikes not repeated 1, 2, 8 or 16 bars earlier OR later
    lp = ss.sosfilt(ss.butter(4, 6000, 'low', fs=SR, output='sos'), x, axis=0)
    d2 = np.abs(np.diff(lp, 2, axis=0)).max(1)
    loc = ss.medfilt(d2[::32], 31).repeat(32)[:len(d2)] + 1e-6
    spikes = np.where(d2 > 40 * loc)[0]
    barN = int(bar * SR); clicks = []
    W = int(.008 * SR)      # +-8 ms: drum hits are humanised (~3 ms sd), so the same hit can move a few ms between bars
    for i in spikes[np.r_[True, np.diff(spikes) > SR // 100]] if len(spikes) else []:
        ref = []
        for k in (1, 2, 8, 16):
            for j in (i - k * barN, i + k * barN):
                if W < j < len(d2) - W: ref.append(d2[j - W:j + W].max())
        if ref and max(ref) < 0.5 * d2[i]: clicks.append(round(i / SR, 3))
    rep['click_suspects'] = clicks
    if clicks: fail('signal', f'{len(clicks)} click suspect(s) at {clicks[:5]} s')
    # stereo / low end
    corr = float(np.corrcoef(x[:, 0], x[:, 1])[0, 1]); rep['stereo_correlation'] = round(corr, 3)
    if corr <= 0.2: fail('stereo', f'mono compatibility (correlation {corr:.2f})')
    low = ss.sosfilt(ss.butter(8, 80, 'low', fs=SR, output='sos'), x, axis=0)
    side = (low[:, 0] - low[:, 1]) / 2; mid = (low[:, 0] + low[:, 1]) / 2
    lsd = 10 * np.log10((side ** 2).mean() / ((mid ** 2).mean() + 1e-15) + 1e-15)
    rep['low_end_side_vs_mid_db'] = round(float(lsd), 1)
    if lsd >= -30: fail('stereo', 'low end below 80 Hz is not mono')
    # informational (not blocking)
    rep.update({k: m.get(k) for k in ('style', 'engine_version', 'tease_s', 'full_hook_s', 'drop2_changes', 'focal', 'kick_pattern')})
    rep['arrangement'] = [s['name'] + f"({s['bars']})" for s in m.get('sections', [])]
    rep['failures'] = fails
    rep['status'] = 'pass' if not fails else 'fail'
    rep['listening_required'] = ['style authenticity', 'hook / focal point memorability', 'groove feel',
                                 'tone and mix balance at matched loudness', 'second-drop payoff', 'overall quality']
    return rep


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    for k in ('wav', 'mp3', 'mp4', 'meta'): ap.add_argument('--' + k, required=True)
    ap.add_argument('--out')
    a = ap.parse_args()
    try:
        rep = report(a.wav, a.mp3, a.mp4, a.meta)
    except Exception as e:
        rep = {'status': 'error', 'failures': [{'category': 'decode', 'check': f'QC could not run: {e}'}]}
    txt = json.dumps(rep, indent=1, default=float)
    if a.out: open(a.out, 'w').write(txt)
    print(txt)
    sys.exit(0 if rep['status'] == 'pass' else (4 if rep['status'] == 'error' else 2))
