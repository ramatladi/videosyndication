"""Build the listening page for take 2: python3 build_page.py"""
import json, glob, os, shutil, sys, numpy as np
from scipy.io import wavfile
V2 = '/home/claude/vs/djvelvetgrey/v2'; sys.path.insert(0, V2)
import styles as S

SRC = '/home/claude/dvg-take2'; PAGE = f'{SRC}/page'
os.makedirs(f'{PAGE}/audio', exist_ok=True)
take1 = json.load(open('/home/claude/vs/djvelvetgrey/sets/2026-10-21-real/palettes.json'))
NOTES = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
CAM_MIN = {'Ab': '1A', 'G#': '1A', 'Eb': '2A', 'D#': '2A', 'Bb': '3A', 'A#': '3A', 'F': '4A', 'C': '5A', 'G': '6A', 'D': '7A',
           'A': '8A', 'E': '9A', 'B': '10A', 'F#': '11A', 'Gb': '11A', 'Db': '12A', 'C#': '12A'}
CAM_MAJ = {'B': '1B', 'F#': '2B', 'Gb': '2B', 'Db': '3B', 'C#': '3B', 'Ab': '4B', 'G#': '4B', 'Eb': '5B', 'D#': '5B', 'Bb': '6B',
           'A#': '6B', 'F': '7B', 'C': '8B', 'G': '9B', 'D': '10B', 'A': '11B', 'E': '12B'}
MAJORISH = {'major', 'ionian', 'mixolydian', 'lydian'}


CRED = {}
for line in open('/home/claude/dvg-vocals/credits.tsv'):
    fid, title, user = line.rstrip('\n').split('\t'); CRED[fid] = (title, user)

def vocal_summary(m):
    if 'vocals' not in m: return ''
    pl = m['vocals'].get('plan')
    if not pl: return 'Vocal chop hook, a harmony chorus, "hey hey hey yeah", "woo hoo" and "oh yeah"'
    nm = pl.get('names', {}); parts = []
    for k in ('hook', 'layer', 'phrase', 'bed'):
        if pl.get(k) and nm.get(k): parts.append(nm[k][0].lower() + nm[k][1:] if not nm[k].startswith('"') else nm[k])
    ad = []
    for k in ('adlib_build', 'adlib_drop1', 'adlib_drop2'):
        if nm.get(k) and nm[k] not in ad: ad.append(nm[k])
    txt = ', '.join(parts)
    if ad: txt += ', plus ' + (' and '.join(ad) if len(ad) < 3 else ', '.join(ad[:-1]) + ' and ' + ad[-1])
    return txt[0].upper() + txt[1:]

def vocal_sources(m):
    if 'vocals' not in m: return []
    rep = m['vocals']['tuning']; files = []
    for k, v in rep.items():
        f = v.get('src', k) if isinstance(v, dict) else k
        if f.endswith('.mp3') and f not in files: files.append(f)
    out = []
    for f in files:
        fid = f.split('_')[0]; t_, u_ = CRED.get(fid, (f, '?')); out.append({'id': fid, 'title': t_, 'user': u_})
    return out

data = []
for jf in sorted(glob.glob(f'{SRC}/[0-9][0-9].json')):
    n = int(os.path.basename(jf)[:2])
    if os.path.exists(f'{SRC}/{n:02d}v.json'): jf = f'{SRC}/{n:02d}v.json'   # vocal version replaces the instrumental
    m = json.load(open(jf)); b = m['brief']; pal = m['palette']; P = S.STYLES[b['style']]
    tonic, mode = m['key'].split(' ', 1)
    cam = (CAM_MAJ if mode in MAJORISH else CAM_MIN)[tonic]
    sr, x = wavfile.read(jf[:-5] + '.wav'); x = np.abs(x.astype(np.float32) / 32768).max(1)
    bins = 180; seg = len(x) // bins
    pk = np.array([np.sqrt(np.mean(x[k * seg:(k + 1) * seg] ** 2)) for k in range(bins)])
    pk = (pk / pk.max()) ** 0.8
    bass = pal['bass_real'] + (f' + {pal["funk_bass"]}' if P.get('bass') == 'funk' and pal['funk_bass'] != pal['bass_real'] else '')
    pads = {'strings': pal['strings'], 'blend': f'{pal["strings"]} + {pal["choir"]}', 'choir': pal['choir']}.get(m['pad_source'], pal['strings'])
    t1 = take1[n - 1]; old = m['take1']
    mp3 = sorted(glob.glob(f'{SRC}/mp3/{n:02d}-*.mp3'))[0]; name = os.path.basename(mp3)
    shutil.copy(mp3, f'{PAGE}/audio/{name}')
    data.append({'title': m['title'], 'style': b['style'], 'styleLabel': P['label'], 'key': m['key'], 'camelot': cam,
                 'bpm': m['bpm'], 'dur': round(m['length_s'], 2), 'engine': m['engine_version'],
                 'lead': pal.get(b['lead'], b['lead']), 'answer': pal.get(b['answer'], b['answer']),
                 'wasLead': t1['palette'].get(old['lead'], old['lead']), 'bass': bass, 'kit': pal['drum_kit'], 'pads': pads,
                 'src': f'audio/{name}', 'peaks': [round(float(v), 3) for v in pk],
                 'vocals': vocal_summary(m), 'credits': vocal_sources(m)})
    if 'vocals' in m:
        data[-1]['lead'] += ' (pulled back for the voice)'
        if b['style'] == 'vocal': data[-1]['styleLabel'] = 'Vocal House'
assert len(data) == 12, len(data)
import html as H
rows = []
for d in data:
    if not d['credits']: continue
    cells = ''.join(f'<span class="rec">{H.escape(c["title"])} <span class="by">· {H.escape(c["user"])}</span> <a href="https://freesound.org/s/{c["id"]}/">#{c["id"]}</a></span>' for c in d['credits'])
    rows.append(f'<tr><td>{H.escape(d["title"])}</td><td>{cells}</td></tr>')
credits = '<table><thead><tr><th>Song</th><th>CC0 recordings used (Freesound)</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table>'
html = open('/home/claude/dvg-scripts/page_template.html').read().replace('__DATA__', json.dumps(data)).replace('__CREDITS__', credits)
open(f'{PAGE}/listening-room.html', 'w').write(html)
for d in data: print(d['title'], '|', d['styleLabel'], '|', d['key'], d['camelot'], '|', d['lead'], '->', d['answer'], '| was', d['wasLead'], '|', d['bass'], '|', d['pads'])
print('audio MB', round(sum(os.path.getsize(f) for f in glob.glob(f'{PAGE}/audio/*')) / 1e6, 1))
