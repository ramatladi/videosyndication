"""Style qualification (agreed rollout gate): 3 full renders per style from distinct briefs across the
style's supported tempo range (low / mid / high), each through the real export + blocking QC.

    python3 qualify.py <work_dir> [style ...] [--workers 2]

For speed the MP4 used here wraps the exact final AAC stream (-c:a copy) in a minimal video track;
the full visual MP4 path is exercised by the end-to-end build and by every real release (make.sh).
Writes <work_dir>/qualification.json. Automated technical checks only — not a listening assessment.
"""
import json, os, subprocess, sys, time
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)


def briefs(style):
    import styles as S, compose as C
    P = S.STYLES[style]
    lo, hi = P['bpm']; tempos = [lo, (lo + hi) // 2, hi]
    out = []
    for i, bpm in enumerate(tempos):
        out.append({'engine': 'v2', 'style': style, 'release': f'q-{style}-{i + 1}', 'bpm': bpm,
                    'tonic': [55, 58, 61][i], 'mode': C.best_mode(P['progressions'][i % len(P['progressions'])], P['modes']),
                    'progression': [list(x) for x in P['progressions'][i % len(P['progressions'])]],
                    'lead': P['leads'][i % len(P['leads'])],
                    'answer': [a for a in P['answers'] if a != P['leads'][i % len(P['leads'])]][i % max(1, len([a for a in P['answers'] if a != P['leads'][i % len(P['leads'])]]))],
                    'groove': {'bass_a': P['bass_a'][i % len(P['bass_a'])],
                               'bass_b': [b for b in P['bass_b'] if b != P['bass_a'][i % len(P['bass_a'])]][0] if any(b != P['bass_a'][i % len(P['bass_a'])] for b in P['bass_b']) else P['bass_b'][0],
                               'swing': round(P['swing'][0] + (P['swing'][1] - P['swing'][0]) * i / 2, 3)},
                    'arc': P['arcs'][i % len(P['arcs'])], 'loudness_lufs': P['lufs'], 'seed': 310000 + 97 * i + len(style) * 13})
    return out


def run_one(args):
    work, b = args
    import compose as C, engine as E, numpy as np
    from scipy.io import wavfile
    name = b['release']; base = os.path.join(work, name)
    t0 = time.time(); res = {'release': name, 'style': b['style'], 'bpm': b['bpm'], 'arc': b['arc'], 'mode': b['mode'], 'lead': b['lead']}
    try:
        cands = C.candidates(b, 6)
        pick = next((c for c in cands if not c['catalog']['flags']), cands[0])
        b['motif'] = {'cell': pick['cell'], 'contour': pick['contour'], 'start': pick['start'], 'candidate': pick['id'],
                      'selected_by': 'automatic (qualification) - not a listening judgement'}
        res['motif'] = f"{pick['cell']}/{pick['contour']}"; res['catalog_flags'] = pick['catalog']['flags']
        json.dump({'title': name, 'engine': 'v2', 'brief': b}, open(base + '.json', 'w'), indent=1)
        tr = E.TrackV2(b, b['motif']); mix = tr.render()
        wavfile.write(base + '.master.wav', E.SR, (np.clip(mix, -1, 1) * 32767).astype(np.int16))
        meta = dict(tr.meta, bpm=b['bpm'], key=C.key_name(b['tonic'], b['mode']), arc=b['arc'])
        json.dump(meta, open(base + '.meta.json', 'w'), indent=1)
        res['render_s'] = round(time.time() - t0, 1)
        r = subprocess.run([sys.executable, os.path.join(HERE, 'export.py'), base + '.master.wav', work, name, '--title', name], capture_output=True, text=True)
        res['export'] = json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() else {'ok': False, 'err': r.stderr[-300:]}
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=black:s=64x64:r=1', '-i', base + '.m4a',
                        '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-c:a', 'copy', '-shortest', base + '.mp4'], check=True)
        r = subprocess.run([sys.executable, os.path.join(HERE, 'qc.py'), '--wav', base + '.delivery.wav', '--mp3', base + '.mp3',
                            '--mp4', base + '.mp4', '--meta', base + '.meta.json', '--out', base + '.qc.json'], capture_output=True, text=True)
        q = json.load(open(base + '.qc.json'))
        res.update({'qc_exit': r.returncode, 'qc_status': q.get('status'), 'failures': q.get('failures'),
                    'mp3_tp': q['files']['mp3']['true_peak_dbtp'], 'aac_tp': q['files']['mp4_audio']['true_peak_dbtp'],
                    'lufs': q['files']['wav']['integrated_lufs'], 'target_lufs': b['loudness_lufs'],
                    'gain_trim_db': res['export'].get('gain_trim_db'), 'outro_bars_heard': q.get('outro_bars_heard'),
                    'clicks': q.get('click_suspects'), 'corr': q.get('stereo_correlation'), 'low_side_db': q.get('low_end_side_vs_mid_db'),
                    'focal': meta.get('focal'), 'kick_pattern': meta.get('kick_pattern'), 'comp': meta.get('comp'), 'perc': meta.get('perc'),
                    'hats': meta.get('hats'), 'arrangement': q.get('arrangement'), 'tease_s': meta.get('tease_s'), 'full_hook_s': meta.get('full_hook_s')})
        for ext in ('.master.wav',): os.remove(base + ext)
    except Exception as e:
        res['qc_status'] = 'error'; res['error'] = repr(e)[:400]
    res['total_s'] = round(time.time() - t0, 1)
    return res


if __name__ == '__main__':
    import styles as S
    work = sys.argv[1]; os.makedirs(work, exist_ok=True)
    wk = 2
    if '--workers' in sys.argv: i = sys.argv.index('--workers'); wk = int(sys.argv[i + 1]); del sys.argv[i:i + 2]
    sel = sys.argv[2:] or S.ORDER
    jobs = [(work, b) for st in sel for b in briefs(st)]
    out_path = os.path.join(work, 'qualification.json')
    done = json.load(open(out_path)) if os.path.exists(out_path) else []
    done_ids = {d['release'] for d in done if d.get('qc_status') in ('pass', 'fail')}
    jobs = [j for j in jobs if j[1]['release'] not in done_ids]
    with ProcessPoolExecutor(wk) as ex:
        for res in ex.map(run_one, jobs):
            done = [d for d in done if d['release'] != res['release']] + [res]
            json.dump(done, open(out_path, 'w'), indent=1)
            print(json.dumps({k: res.get(k) for k in ('release', 'qc_status', 'bpm', 'arc', 'mp3_tp', 'aac_tp', 'lufs', 'gain_trim_db', 'outro_bars_heard', 'total_s')}), flush=True)
            if res.get('failures'): print('   failures:', res['failures'], flush=True)
            if res.get('error'): print('   error:', res['error'], flush=True)
