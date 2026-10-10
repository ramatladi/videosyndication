"""Fail-closed release gate. Publishing (Metricool) may ONLY happen if this exits 0.

    python3 release_gate.py <out_dir> <name>

Checks: manifest readable and status == pass; QC report passed; EVERY file bound in the manifest (track file,
photo, delivery WAV, MP3, AAC, MP4, QC/meta/export reports) still matches its sha256; the build code is the
code now in the repo (code_sha256) and was not built from uncommitted engine code (repo_dirty); engine
version present; the style (aliases resolved) is activated in styles_status.json.
Any missing, unreadable or mismatching input -> exit 5 with the reasons.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from manifest import sha256, code_sha256

STATUS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'styles_status.json')
REQUIRED = ('track_json', 'photo', 'delivery_wav', 'mp3', 'aac', 'mp4', 'qc_json', 'meta_json', 'export_json')


def check(out_dir, name, check_code=True):
    base = os.path.join(out_dir, name)
    reasons = []
    try:
        man = json.load(open(base + '.manifest.json'))
    except Exception as e:
        return False, [f'manifest missing or unreadable: {e}'], None
    try:
        qc = json.load(open(base + '.qc.json'))
        if qc.get('status') != 'pass': reasons.append(f"QC status is {qc.get('status')}")
    except Exception as e:
        reasons.append(f'QC report missing or unreadable: {e}')
    if man.get('status') != 'pass': reasons.append('manifest status is not pass')
    if not man.get('engine_version'): reasons.append('no engine version in manifest')
    hashes = man.get('sha256', {}); files = man.get('files', {})
    for k in REQUIRED:
        p = files.get(k) or {'mp4': base + '.mp4', 'mp3': base + '.mp3', 'aac': base + '.m4a', 'qc_json': base + '.qc.json'}.get(k)
        if k not in hashes: reasons.append(f'{k} not bound in manifest'); continue
        if not p or not os.path.exists(p): reasons.append(f'{k} missing ({p})'); continue
        if sha256(p) != hashes[k]: reasons.append(f'{k} changed after QC (hash mismatch)')
    if check_code:
        if man.get('repo_dirty'): reasons.append('built from uncommitted engine code (repo_dirty)')
        try:
            if man.get('code_sha256') != code_sha256(): reasons.append('build code changed since this release was built (code_sha256)')
        except Exception as e:
            reasons.append(f'cannot hash build code: {e}')
    try:
        import styles as S
        style = S.ALIASES.get(man.get('style'), man.get('style'))
        st = json.load(open(STATUS)).get('styles', {}).get(style, {})
        if st.get('status') not in ('active-technical', 'active-auditioned'):
            reasons.append(f"style '{style}' is not activated ({st.get('status', 'unknown')})")
    except Exception as e:
        reasons.append(f'styles_status.json unreadable: {e}')
    return not reasons, reasons, man


if __name__ == '__main__':
    ok, reasons, man = check(sys.argv[1], sys.argv[2])
    print(json.dumps({'release_allowed': ok, 'reasons': reasons, 'release_id': sys.argv[2],
                      'style': (man or {}).get('style'), 'assessment': 'technical only - not listened to'}))
    sys.exit(0 if ok else 5)
