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
cat = [e for e in C.load_catalog() if e.get('status') != 'draft' and C.release_base(e.get('id')) != C.release_base(b.get('release'))]
flags = []
prev = cat[-2:]
if any(e.get('template') == b['arc'] for e in prev): flags.append(f"arc '{b['arc']}' used in the previous 2 tracks")
same_style = [e for e in cat if e.get('style') == b['style']][-3:]
if any(e.get('progression') == b['progression'] for e in same_style): flags.append('progression used in the previous 3 tracks of this style')
if cat and cat[-1].get('lead') == b['lead']: flags.append(f"lead '{b['lead']}' same as the previous track")
if cat and cat[-1].get('bass_a') == b['groove']['bass_a']: flags.append(f"bass_a '{b['groove']['bass_a']}' same as the previous track")
if b['arc'] not in C.TEMPLATES: flags.append(f"unknown arc (choose from {list(C.TEMPLATES)})")
for k in ('bass_a', 'bass_b'):
    if b['groove'].get(k) not in C.GROOVES: flags.append(f"unknown {k} (choose from {list(C.GROOVES)})")
import styles as S
st = S.ALIASES.get(b.get('style'), b.get('style'))
if st not in S.STYLES: flags.append(f"unknown style '{b.get('style')}'")
else:
    P = S.STYLES[st]
    if not (P['bpm'][0] <= b['bpm'] <= P['bpm'][1]): flags.append(f"bpm {b['bpm']} outside {st} range {P['bpm']}")
    if b.get('mode', 'minor') not in P['modes']: flags.append(f"mode {b.get('mode')} not in {P['modes']}")
    fit = C.mode_fit(b['progression'], b.get('mode', 'minor'))
    if fit < 0.85: flags.append(f"mode {b.get('mode', 'minor')} clashes with the progression (fit {fit:.2f}); use {C.best_mode(b['progression'], P['modes'])}")
    if b['arc'] not in P['arcs']: flags.append(f"arc {b['arc']} not in {P['arcs']}")
    if b['groove'].get('bass_a') not in P['bass_a']: flags.append(f"bass_a not in {P['bass_a']}")
    if b['lead'] not in P['leads']: flags.append(f"lead not in {P['leads']}")
    import make_track as MT
    flags += [f'profile: {e}' for e in MT.validate(b, P)]
print(json.dumps({'flags': flags, 'catalog_tracks': len(cat)}, indent=1))
