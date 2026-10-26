"""Save Looperman loops downloaded from Sello's Google Drive into the local loop library under their verified names.

The Google Drive connector's download_file_content returns base64 JSON; large results are saved by the harness to a
tool-results file. Pass those files (or a directory to scan):

    python3 mirage/loopkit/fetch.py <tool-result.txt> [...]      -> /home/claude/loops/<cat>/<verified name>.wav
Each file is matched to mirage/loops/index.json by its Looperman id and saved under the index name (verified key), then
re-checked for completeness (bar-exact, not silent).
"""
import base64, glob, json, os, re, sys
import numpy as np, soundfile as sf
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(os.path.dirname(HERE))
LIB = os.environ.get('MIRAGE_LOOPS', '/home/claude/loops')
IDX = {e['looperman_id']: e for e in json.load(open(os.path.join(REPO, 'mirage', 'loops', 'index.json')))['loops']}


def main(paths):
    files = []
    for p in paths: files += glob.glob(os.path.join(p, '*download_file_content*.txt')) if os.path.isdir(p) else [p]
    for f in files:
        try: d = json.load(open(f))
        except Exception: continue
        m = re.search(r'looperman-l-\d+-(\d+)-', d.get('title', ''))
        if not m or m.group(1) not in IDX: continue
        e = IDX[m.group(1)]; out = os.path.join(LIB, e['cat'], e['name'])
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, 'wb').write(base64.b64decode(d['content']))
        x, sr = sf.read(out, always_2d=True); beats = len(x) / sr * e['bpm'] / 60
        ok = abs(beats - round(beats)) < .08 and round(beats) % 4 == 0 and np.abs(x).max() > 1e-3
        if not ok: os.remove(out)
        print(('saved ' if ok else 'REJECTED ') + e['cat'] + ' ' + e['name'])


if __name__ == '__main__':
    main(sys.argv[1:])
