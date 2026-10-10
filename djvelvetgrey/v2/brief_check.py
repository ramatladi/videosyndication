"""Check a track brief for deliberate variety against the catalogue (published tracks).

    python3 brief_check.py djvelvetgrey/tracks/dvgNNN.json

Flags (heuristics, not bans): same arc as either of the previous 2 tracks, same progression as any of
the previous 3 tracks of the same style, same lead as the previous track, same bass_a as the previous
track. Exit code 0 always; read the flags and revise the brief if any are listed.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compose as C

b = json.load(open(sys.argv[1]))['brief']
cat = [e for e in C.load_catalog() if e.get('status') != 'draft']
flags = []
prev = cat[-2:]
if any(e.get('template') == b['arc'] for e in prev): flags.append(f"arc '{b['arc']}' used in the previous 2 tracks")
same_style = [e for e in cat if e.get('style') == b['style']][-3:]
if any(e.get('progression') == b['progression'] for e in same_style): flags.append('progression used in the previous 3 tracks of this style')
if cat and cat[-1].get('lead') == b['lead']: flags.append(f"lead '{b['lead']}' same as the previous track")
if cat and cat[-1].get('bass_a') == b['groove']['bass_a']: flags.append(f"bass_a '{b['groove']['bass_a']}' same as the previous track")
for k in ('lead', 'answer'):
    if b.get(k) not in C.LEADS: flags.append(f"unknown {k} '{b.get(k)}' (choose from {C.LEADS})")
if b['arc'] not in C.TEMPLATES: flags.append(f"unknown arc (choose from {list(C.TEMPLATES)})")
for k in ('bass_a', 'bass_b'):
    if b['groove'].get(k) not in C.GROOVES: flags.append(f"unknown {k} (choose from {list(C.GROOVES)})")
print(json.dumps({'flags': flags, 'catalog_tracks': len(cat)}, indent=1))
