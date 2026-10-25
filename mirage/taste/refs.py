"""Reference store: public musical metadata (tempo, key, genre) for artists and songs in Sello's Apple Music library.

The planner (make_release.py plan) takes one reference per release - a song his library points to, in the chosen
style - and follows its tempo and key colour. Melodies, hooks and arrangements are always original (screened for
uniqueness); references never appear in titles or descriptions.

    python3 mirage/taste/refs.py add --artist "Jerro" --source URL --rows "Give It Up|123|6A|Deep House" "Pantheon|122|4B|Progressive House"
    python3 mirage/taste/refs.py next-artists [N]       # library artists not researched yet, most-played first
    python3 mirage/taste/refs.py stats
"""
import argparse, json, os, re, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__))
REFS = os.path.join(HERE, 'refs.json')
NOTES = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
CAMELOT_A = {1: 8, 2: 3, 3: 10, 4: 5, 5: 0, 6: 7, 7: 2, 8: 9, 9: 4, 10: 11, 11: 6, 12: 1}     # minor tonic pitch class
CAMELOT_B = {1: 11, 2: 6, 3: 1, 4: 8, 5: 3, 6: 10, 7: 5, 8: 0, 9: 7, 10: 2, 11: 9, 12: 4}     # major tonic pitch class
GENRE = {'deep house': 'deep', 'melodic house & techno': 'melodic', 'melodic house': 'melodic', 'organic house': 'melodic',
         'progressive house': 'progressive', 'mainstage': 'progressive', 'afro house': 'afro', 'future house': 'deep',
         'house': 'house', 'dance': 'melodic',   # Beatport 'Dance' in this library = melodic house-pop (Le Youth, Lane 8)
         'funky house': 'nudisco', 'nu disco': 'nudisco', 'nu-disco': 'nudisco',
         'disco': 'disco', 'indie dance': 'indiedance', 'tech house': 'tech', 'trance': 'trance', 'trance (main floor)': 'trance',
         'progressive trance': 'trance', 'future bass': 'futurebass', 'tropical house': 'tropical', 'soulful house': 'soulful',
         'deep tech': 'deep', 'minimal / deep tech': 'deep', 'amapiano': 'afro', 'afro tech': 'afro'}


def parse_key(k):
    """'6A', '6A (G min)', 'G minor', 'F# min', 'Ab maj' -> (pitch class, 'minor'|'major') or None."""
    k = k.strip()
    m = re.match(r'(\d{1,2})\s*([AB])\b', k)
    if m:
        n = int(m.group(1)); return (CAMELOT_A[n], 'minor') if m.group(2) == 'A' else (CAMELOT_B[n], 'major')
    m = re.search(r'([A-G])\s*([#♯b♭]?)\s*(min|minor|m\b|maj|major)', k, re.I)
    if m:
        pc = (NOTES[m.group(1).upper()] + (1 if m.group(2) in '#♯' and m.group(2) else -1 if m.group(2) in 'b♭' and m.group(2) else 0)) % 12
        return pc, 'minor' if m.group(3).lower().startswith('m') and not m.group(3).lower().startswith('maj') else 'major'
    return None


def load():
    return json.load(open(REFS))


def save(d):
    json.dump(d, open(REFS, 'w'), indent=1, ensure_ascii=False)


def add(artist, rows, source):
    d = load(); have = {(r['artist'].lower(), r['title'].lower()) for r in d['refs']}; n = 0
    for row in rows:
        parts = [p.strip() for p in row.split('|')]
        if len(parts) < 4: continue
        title, bpm, key, genre = parts[:4]
        try: bpm = float(bpm)
        except ValueError: continue
        if bpm < 100: bpm *= 2 if bpm < 75 else 1          # half-time readings
        if not 100 <= bpm <= 150: continue
        k = parse_key(key); style = GENRE.get(genre.lower())
        if k is None or style is None or (artist.lower(), title.lower()) in have: continue
        d['refs'].append({'artist': artist, 'title': title, 'bpm': round(bpm), 'tonic_pc': k[0], 'mode': k[1], 'genre': genre,
                          'style': style, 'source': source, 'added': dt.date.today().isoformat()})
        have.add((artist.lower(), title.lower())); n += 1
    if artist not in d['artists_done']: d['artists_done'].append(artist)
    if n == 0: d.setdefault('not_found', []).append(artist) if artist not in d.get('not_found', []) else None
    save(d); return n


def next_artists(n=10):
    d = load(); done = {a.lower() for a in d['artists_done']}
    arts = json.load(open(os.path.join(HERE, 'artists.json')))
    return [a['artist'] for a in arts if a['artist'].lower() not in done][:n]


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd', choices=['add', 'next-artists', 'stats', 'mark-done'])
    ap.add_argument('n', nargs='?', type=int, default=10)
    ap.add_argument('--artist'); ap.add_argument('--source', default=''); ap.add_argument('--rows', nargs='*', default=[])
    a = ap.parse_args()
    if a.cmd == 'add': print('added', add(a.artist, a.rows, a.source))
    elif a.cmd == 'mark-done':
        d = load(); d['artists_done'].append(a.artist) if a.artist not in d['artists_done'] else None
        d.setdefault('not_found', []).append(a.artist) if a.artist not in d.get('not_found', []) else None; save(d); print('marked', a.artist)
    elif a.cmd == 'next-artists': print('\n'.join(next_artists(a.n)))
    else:
        import collections
        d = load(); print(len(d['refs']), 'refs from', len(d['artists_done']), 'artists;', dict(collections.Counter(r['style'] for r in d['refs'])))
