"""Instrumental (no vocals) render of one of the 10 hit-style songs from /tmp/vox2/hits2.json: python3 render_inst.py <i>"""
import sys, json, subprocess, numpy as np
sys.path.insert(0, '/home/claude/videosyndication/djvelvetgrey/v2')
import engine as E, compose as C
from scipy.io import wavfile
i = int(sys.argv[1]); p = json.load(open('/tmp/vox2/hits2.json'))[i]; b = p['brief']
t = E.TrackV2(b, b['motif']); mix = t.render()
n = f'{i + 1:02d}'; base = f'/tmp/mirage/out/{n}'
wavfile.write(base + '.master.wav', E.SR, (np.clip(mix, -1, 1) * 32767).astype(np.int16))
meta = dict(t.meta, title=p['title'], bpm=b['bpm'], key=C.key_name(b['tonic'], b['mode']), brief=b, style_reference=p['reference'],
            instruments=p['instruments'])
json.dump(meta, open(base + '.meta.json', 'w'), indent=1, default=str)
r = subprocess.run([sys.executable, '/home/claude/videosyndication/djvelvetgrey/v2/export.py', base + '.master.wav', '/tmp/mirage/out', n, '--title', p['title']], capture_output=True, text=True)
print(n, p['title'], meta['achieved_lufs_master'], r.stdout.strip().splitlines()[-1][:80] if r.stdout.strip() else r.stderr[-200:])
