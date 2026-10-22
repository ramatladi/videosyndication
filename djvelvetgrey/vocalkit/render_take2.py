"""New takes of the 21 Oct Real Instruments set: python3 render_take2.py <index 0-11>
Same titles, styles, keys and tempos as take 1; new seed, and progression / lead / answer / arc / bass
re-drawn so each differs from take 1 wherever the style offers another choice. Recorded instruments only."""
import sys, json, subprocess, numpy as np
V2 = '/home/claude/vs/djvelvetgrey/v2'
sys.path.insert(0, V2)
import engine as E, compose as C, styles as S
from scipy.io import wavfile

OUT = '/home/claude/dvg-take2'
SET = [  # (style, bpm, tonic, title) -- identical to sets/2026-10-21-real/render_one.py
    ('tropical', 108, 60, 'Coral Lanterns'), ('nudisco', 116, 57, 'Saffron Boulevard'), ('disco', 118, 62, 'Glitter Tidewater'),
    ('afro', 120, 57, 'Baobab Sundown'), ('deep', 121, 55, 'Velvet Harbour Lights'), ('soulful', 122, 58, 'Honeyed Promenade'),
    ('vocal', 122, 60, 'Open Sky Chorus'), ('melodic', 123, 62, 'Lagoon Reverie'), ('house', 124, 55, 'Pier Side Piano'),
    ('french', 124, 57, 'Riviera Shutters'), ('progressive', 126, 59, 'Cliffline Ascent'), ('tech', 126, 57, 'Midnight Driftwood')]


def take1(i, P):
    """Re-derive take 1's choices exactly as render_one.py drew them."""
    r = np.random.default_rng(4040 + i)
    prog = P['progressions'][int(r.integers(len(P['progressions'])))]
    lead = P['leads'][int(r.integers(len(P['leads'])))]
    ans = [a for a in P['answers'] if a != lead]; answer = ans[int(r.integers(len(ans)))]
    bass_a = P['bass_a'][int(r.integers(len(P['bass_a'])))]; bass_b = P['bass_b'][int(r.integers(len(P['bass_b'])))]
    r.uniform(*P['swing'])
    arc = P['arcs'][int(r.integers(len(P['arcs'])))]
    seed = int(r.integers(100000, 999999))
    return dict(prog=prog, lead=lead, answer=answer, bass_a=bass_a, bass_b=bass_b, arc=arc, seed=seed)


def pick_other(r, options, prev):
    pool = [o for o in options if o != prev] or list(options)
    return pool[int(r.integers(len(pool)))]


i = int(sys.argv[1]); st, bpm, tonic, title = SET[i]; P = S.STYLES[st]
plan = json.load(open(f'{OUT}/briefs.json'))[i]
b = plan['brief']; old = plan['take1']; lead = b['lead']; answer = b['answer']; seed = b['seed']
assert b['style'] == st and b['bpm'] == bpm and b['tonic'] == tonic
cands = C.candidates(b, 6); pick = next((c for c in cands if not c['catalog']['flags']), cands[0])
b['motif'] = {'cell': pick['cell'], 'contour': pick['contour'], 'start': pick['start'], 'candidate': pick['id'],
              'selected_by': 'automatic - not a listening judgement'}
t = E.TrackV2(b, b['motif']); mix = t.render()
base = f'{OUT}/{i + 1:02d}'
wavfile.write(base + '.wav', E.SR, (np.clip(mix, -1, 1) * 32767).astype(np.int16))
key = C.key_name(tonic, b['mode'])
meta = dict(t.meta, title=title, bpm=bpm, key=key, brief=b, take1=old)
json.dump(meta, open(base + '.json', 'w'), indent=1, default=str)
slug = title.lower().replace(' ', '-')
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', base + '.wav', '-b:a', '192k', '-metadata', f'title={title}',
                '-metadata', 'artist=DJ Velvet Grey', '-metadata', 'album=Real Instruments Set (Take 2)',
                '-metadata', f'track={i + 1}/12', f'{OUT}/mp3/{i + 1:02d}-{slug}.mp3'], check=True)
print(json.dumps({'n': i + 1, 'title': title, 'style': st, 'bpm': bpm, 'key': key, 'lead': lead, 'answer': answer,
                  'arc': b['arc'], 'seed': seed, 'take1': {k: old[k] for k in ('lead', 'answer', 'arc', 'seed')},
                  'lufs': meta.get('achieved_lufs_master'), 'instruments': meta['instruments']}))
