"""Immutable per-track manifest, written only after blocking QC has passed.

    python3 manifest.py <track.json> <out_dir> <name>

Binds the release to exact file hashes, code version, tool versions, the brief, the selected motif
(and how it was selected), the export report and the QC report.
"""
import datetime, hashlib, json, os, platform, subprocess, sys


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''): h.update(chunk)
    return h.hexdigest()


def git(root, *args):
    try: return subprocess.run(['git', '-C', root] + list(args), capture_output=True, text=True).stdout.strip()
    except Exception: return None


def versions():
    import numpy, scipy
    v = {'python': platform.python_version(), 'numpy': numpy.__version__, 'scipy': scipy.__version__}
    try:
        import pyloudnorm; v['pyloudnorm'] = getattr(pyloudnorm, '__version__', 'installed')
    except Exception: pass
    ff = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True).stdout.splitlines()
    v['ffmpeg'] = ff[0] if ff else None
    return v


CODE_FILES = ['make.sh', 'video.py'] + ['v2/' + f for f in ('compose.py', 'engine.py', 'instruments.py', 'styles.py', 'export.py',
                                                              'qc.py', 'manifest.py', 'release_gate.py', 'make_track.py')]


def code_sha256():
    """One hash over the build code, so the gate can prove the release was built by the code now in the repo."""
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    h = hashlib.sha256()
    for f in CODE_FILES:
        h.update(f.encode()); h.update(open(os.path.join(here, f), 'rb').read())
    return h.hexdigest()


def hashed_files(track_json, image, base):
    track_json, image, base = (os.path.abspath(p) for p in (track_json, image, base))
    return {'track_json': track_json, 'photo': image, 'delivery_wav': base + '.delivery.wav', 'mp3': base + '.mp3',
            'aac': base + '.m4a', 'mp4': base + '.mp4', 'qc_json': base + '.qc.json', 'meta_json': base + '.meta.json',
            'export_json': base + '.export.json'}


def build(track_json, out_dir, name):
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    t = json.load(open(track_json))
    base = os.path.join(out_dir, name)
    qc = json.load(open(base + '.qc.json'))
    if qc.get('status') != 'pass': raise SystemExit('refusing to write a manifest: QC status is not pass')
    meta = json.load(open(base + '.meta.json'))
    exp = json.load(open(base + '.export.json'))
    if meta.get('code_sha256_at_render') != code_sha256():
        raise SystemExit('refusing to write a manifest: build code changed between render and manifest')
    files = hashed_files(track_json, t['image'], base)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import styles as S
    man = {
        'release_id': name, 'title': t['title'], 'style': S.ALIASES.get(t['brief']['style'], t['brief']['style']),
        'style_as_written': t['brief']['style'], 'status': 'pass',
        'created_utc': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'engine_version': meta.get('engine_version'), 'code_sha256': code_sha256(),
        'files': files,
        'repo_commit': git(root, 'rev-parse', 'HEAD'), 'repo_dirty': bool(git(root, 'status', '--porcelain', '--', 'djvelvetgrey/v2', 'djvelvetgrey/make.sh', 'djvelvetgrey/video.py')),
        'tools': versions(),
        'brief': t['brief'], 'motif_selection': t['brief'].get('motif'),
        'sha256': {k: sha256(p) for k, p in files.items()},
        'export': {'gain_trim_db': exp['gain_trim_db'], 'final': exp['iterations'][-1]},
        'qc': {'status': qc['status'], 'files': qc['files'], 'click_suspects': qc.get('click_suspects'),
               'outro_bars_heard': qc.get('outro_bars_heard'), 'stereo_correlation': qc.get('stereo_correlation')},
        'assessment': 'Automated technical checks only. Not listened to unless "auditioned_by" is set.',
        'auditioned_by': None,
    }
    json.dump(man, open(base + '.manifest.json', 'w'), indent=1)
    return man


if __name__ == '__main__':
    m = build(*sys.argv[1:4])
    print(json.dumps({'release_id': m['release_id'], 'status': m['status'], 'mp4_sha256': m['sha256']['mp4'][:16]}))
