"""Render one track of the all-real-instruments set: python3 render_one.py <index>"""
import sys, json, os, subprocess, numpy as np
sys.path.insert(0, '/home/claude/videosyndication/djvelvetgrey/v2')
import engine as E, compose as C, styles as S
from scipy.io import wavfile
SET = [  # (style, bpm, tonic, title)
    ('tropical', 108, 60, 'Coral Lanterns'), ('nudisco', 116, 57, 'Saffron Boulevard'), ('disco', 118, 62, 'Glitter Tidewater'),
    ('afro', 120, 57, 'Baobab Sundown'), ('deep', 121, 55, 'Velvet Harbour Lights'), ('soulful', 122, 58, 'Honeyed Promenade'),
    ('vocal', 122, 60, 'Open Sky Chorus'), ('melodic', 123, 62, 'Lagoon Reverie'), ('house', 124, 55, 'Pier Side Piano'),
    ('french', 124, 57, 'Riviera Shutters'), ('progressive', 126, 59, 'Cliffline Ascent'), ('tech', 126, 57, 'Midnight Driftwood')]
i = int(sys.argv[1]); st, bpm, tonic, title = SET[i]; P = S.STYLES[st]
r = np.random.default_rng(4040 + i)
prog = P['progressions'][int(r.integers(len(P['progressions'])))]
lead = P['leads'][int(r.integers(len(P['leads'])))]; ans = [a for a in P['answers'] if a != lead]
b = {'engine': 'v2', 'style': st, 'release': f'set-real-{i + 1:02d}', 'bpm': bpm, 'tonic': tonic,
     'progression': [list(x) for x in prog], 'mode': C.best_mode(prog, P['modes']), 'lead': lead, 'answer': ans[int(r.integers(len(ans)))],
     'groove': {'bass_a': P['bass_a'][int(r.integers(len(P['bass_a'])))], 'bass_b': P['bass_b'][int(r.integers(len(P['bass_b'])))],
                'swing': round(float(r.uniform(*P['swing'])), 3)},
     'arc': P['arcs'][int(r.integers(len(P['arcs'])))], 'loudness_lufs': P['lufs'], 'seed': int(r.integers(100000, 999999)),
     'instruments': 'real'}
cands = C.candidates(b, 6); pick = next((c for c in cands if not c['catalog']['flags']), cands[0])
b['motif'] = {'cell': pick['cell'], 'contour': pick['contour'], 'start': pick['start'], 'candidate': pick['id'],
              'selected_by': 'automatic - not a listening judgement'}
t = E.TrackV2(b, b['motif']); mix = t.render()
base = f'/tmp/set/{i + 1:02d}'
wavfile.write(base + '.wav', E.SR, (np.clip(mix, -1, 1) * 32767).astype(np.int16))
meta = dict(t.meta, title=title, bpm=bpm, key=C.key_name(tonic, b['mode']), brief=b)
json.dump(meta, open(base + '.json', 'w'), indent=1, default=str)
print(json.dumps({'n': i + 1, 'title': title, 'style': st, 'bpm': bpm, 'key': meta['key'], 'lead': lead, 'answer': b['answer'],
                  'lufs': meta.get('achieved_lufs_master'), 'instruments': meta['instruments']}))
