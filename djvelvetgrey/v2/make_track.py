"""Render a full v2 track from a track file whose "brief" includes the chosen motif.

    python3 make_track.py djvelvetgrey/tracks/dvgNNN.json out.wav out_meta.json

The brief's "motif" holds the selected candidate spec ({cell, contour, start}).
"""
import json, os, sys, numpy as np
from scipy.io import wavfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compose as C, engine as E

if __name__ == '__main__':
    tj, out_wav, out_meta = sys.argv[1:4]
    brief = json.load(open(tj))['brief']
    if 'motif' not in brief:
        raise SystemExit('brief has no selected motif: run previews.py and copy a candidate into brief.motif')
    t = E.TrackV2(brief, brief['motif'])
    mix = t.render()
    wavfile.write(out_wav, E.SR, (np.clip(mix, -1, 1) * 32767).astype(np.int16))
    h, hook = C.hook_from_spec(brief, brief['motif'])
    meta = dict(t.meta, bpm=brief['bpm'], key=C.key_name(brief['tonic']), arc=brief['arc'],
                motif=C.motif_repr(hook['call']), lead=brief['lead'], answer=brief.get('answer'),
                duration=round(len(mix) / E.SR, 3))
    json.dump(meta, open(out_meta, 'w'), indent=1)
    print(json.dumps({k: meta[k] for k in ('bpm', 'key', 'arc', 'lead', 'tease_s', 'full_hook_s', 'duration')}))
