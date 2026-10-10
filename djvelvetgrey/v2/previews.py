"""Six hook previews at equal loudness over the same backing, plus a compositional shortlist.

    python3 previews.py djvelvetgrey/tracks/dvgNNN.json outdir/

Writes outdir/candidates.json and outdir/hook_N.mp3 (8 bars each, -14 LUFS).
The shortlist uses compositional evidence (shape, range, rhythm, catalog distance) — it is
explicitly NOT based on hearing; a listener makes the choice.
"""
import json, os, sys, subprocess, numpy as np
from scipy.io import wavfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compose as C, engine as E


def main(track_json, outdir):
    os.makedirs(outdir, exist_ok=True)
    brief = json.load(open(track_json))['brief']
    cands = C.candidates(brief, 6)
    length = 8 * 4 * 60 / brief['bpm'] + 1.5
    for c in cands:
        t = E.TrackV2(brief, c, template=[('hook', 8)], length=length, lufs=-14.0)
        mix = t.render()
        wav = os.path.join(outdir, f"hook_{c['id']}.wav")
        wavfile.write(wav, E.SR, (np.clip(mix, -1, 1) * 32767).astype(np.int16))
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', wav, '-b:a', '256k', wav[:-4] + '.mp3'], check=True)
        os.remove(wav)
    # pairwise distances and shortlist: best score first, skipping near-duplicates of what is already picked
    for c in cands:
        c['distance_to_others'] = {o['id']: C.similarity_distance(c['motif'], o['motif']) for o in cands if o is not c}
    short = []
    for c in sorted(cands, key=lambda c: -c['score']):
        if all(C.similarity_distance(c['motif'], s['motif']) >= .35 for s in short) and c['evidence']['range_semitones'] >= 4:
            short.append(c)
        if len(short) == 3: break
    out = {'note': 'Shortlist from compositional evidence only — not from listening. A listener chooses.',
           'candidates': cands, 'shortlist': [s['id'] for s in short]}
    json.dump(out, open(os.path.join(outdir, 'candidates.json'), 'w'), indent=1, default=str)
    for c in cands:
        mark = '*' if c['id'] in out['shortlist'] else ' '
        print(f"{mark} hook_{c['id']}: {c['cell']}/{c['contour']} score {c['score']} {c['evidence']} catalog {c['catalog']}")


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
