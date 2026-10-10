"""Render a full v2 track from a track file whose "brief" includes the chosen motif.

    python3 make_track.py djvelvetgrey/tracks/dvgNNN.json out.wav out_meta.json

The brief's "motif" holds the selected candidate spec ({cell, contour, start}).
"""
import json, os, sys, numpy as np
from scipy.io import wavfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compose as C, engine as E


def validate(brief, P):
    """Every brief field must come from the style's own lists (fail closed, no silent substitutes)."""
    import instruments as I
    e, g = [], brief.get('groove', {})
    if brief.get('lead') not in P['leads']: e.append(f"lead {brief.get('lead')!r} not in {P['leads']}")
    if brief.get('answer') is not None and brief['answer'] not in P['answers']: e.append(f"answer {brief['answer']!r} not in {P['answers']}")
    if g.get('bass_a') not in P['bass_a']: e.append(f"bass_a {g.get('bass_a')!r} not in {P['bass_a']}")
    if g.get('bass_b') is not None and g['bass_b'] not in P['bass_b']: e.append(f"bass_b {g['bass_b']!r} not in {P['bass_b']}")
    if brief.get('arc') not in P['arcs']: e.append(f"arc {brief.get('arc')!r} not in {P['arcs']}")
    if brief.get('mode', 'minor') not in P['modes']: e.append(f"mode {brief.get('mode', 'minor')!r} not in {P['modes']}")
    if tuple(tuple(x) for x in brief['progression']) not in [tuple(map(tuple, p)) for p in P['progressions']]:
        e.append('progression is not one of the style progressions')
    for k in (brief.get('lead'), brief.get('answer')):
        if k is not None and k not in I.KNOWN: e.append(f'unknown instrument {k!r}')
    for k in ('bass_a', 'bass_b'):
        if g.get(k) is not None and g[k] not in C.GROOVES: e.append(f'unknown bass pattern {g[k]!r}')
    return e

if __name__ == '__main__':
    tj, out_wav, out_meta = sys.argv[1:4]
    brief = json.load(open(tj))['brief']
    if 'motif' not in brief:
        raise SystemExit('brief has no selected motif: run previews.py and select_motif.py first')
    import styles as S
    st = S.ALIASES.get(brief.get('style'), brief.get('style'))
    if st not in S.STYLES: raise SystemExit(f"unknown style '{brief.get('style')}' (known: {S.ORDER})")
    lo, hi = S.STYLES[st]['bpm']
    if not (lo <= brief['bpm'] <= hi): raise SystemExit(f"bpm {brief['bpm']} outside the supported {st} range {lo}-{hi}")
    for k in ('tonic', 'progression', 'lead', 'groove', 'arc', 'seed'):
        if k not in brief: raise SystemExit(f'brief missing {k}')
    errs = validate(brief, S.STYLES[st])
    if errs: raise SystemExit('brief does not fit the style profile: ' + '; '.join(errs))
    import manifest as M
    code_at_render = M.code_sha256()          # the manifest refuses if the code changed during the build
    t = E.TrackV2(brief, brief['motif'])
    mix = t.render()
    wavfile.write(out_wav, E.SR, (np.clip(mix, -1, 1) * 32767).astype(np.int16))
    h, hook = C.hook_from_spec(brief, brief['motif'])
    meta = dict(t.meta, bpm=brief['bpm'], key=C.key_name(brief['tonic'], brief.get('mode', 'minor')), arc=brief['arc'],
                motif=C.motif_repr(hook['call']), lead=brief['lead'], answer=brief.get('answer'),
                duration=round(len(mix) / E.SR, 3), code_sha256_at_render=code_at_render)
    json.dump(meta, open(out_meta, 'w'), indent=1)
    print(json.dumps({k: meta.get(k) for k in ('style', 'bpm', 'key', 'arc', 'lead', 'focal', 'tease_s', 'full_hook_s', 'achieved_lufs_master', 'duration')}))
