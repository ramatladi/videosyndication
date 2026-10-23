"""Level-match every studio-pack instrument to the FluidR3 recording it replaces, so the engine's existing mix
balance (group levels, per-voice gains) still holds in studio mode. Writes "gain" into the pack's index.json.

    python3 djvelvetgrey/tools/calibrate_studio_pack.py <pack_dir>
"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'v2'))
os.environ['DVG_STUDIO_PACK'] = sys.argv[1]
import sampler as SM, studio as ST  # noqa: E402

REF = {   # instrument -> (bank, preset, key) of the FluidR3 sound it replaces; drums: (128, 0, GM drum note)
    'violins': (0, 48, 72), 'violas': (0, 48, 60), 'celli': (0, 48, 48), 'trumpet': (0, 56, 72), 'trumpet_stac': (0, 56, 72),
    'horn': (0, 60, 62), 'trombone': (0, 57, 52), 'flute': (0, 73, 76), 'clarinet': (0, 71, 64), 'tenor_sax': (0, 66, 58),
    'harp': (0, 46, 67), 'violin_pizz': (0, 45, 69), 'upright_bass': (0, 32, 40), 'piano_steinway': (0, 0, 64),
    'vibraphone': (0, 11, 69), 'marimba': (0, 12, 67), 'xylophone': (0, 13, 79), 'glockenspiel': (0, 9, 84), 'kalimba': (0, 108, 67),
    'clap': (128, 0, 39), 'hat': (128, 0, 42), 'hat_open': (128, 0, 46), 'shaker': (128, 0, 70), 'tamb': (128, 0, 54),
    'cowbell': (128, 0, 56), 'claves': (128, 0, 75), 'wood': (128, 0, 76), 'bell_hi': (128, 0, 67), 'bell_lo': (128, 0, 68),
    'cabasa': (128, 0, 69), 'conga_hi': (128, 0, 63), 'conga_lo': (128, 0, 64), 'bongo_hi': (128, 0, 60), 'bongo_lo': (128, 0, 61),
    'snare': (128, 0, 38), 'side_stick': (128, 0, 37), 'tom_mid': (128, 0, 47), 'crash': (128, 0, 49), 'cymbal_swell': (0, 119, 72),
}


def rms(x, n):
    x = x[:n].mean(1)
    return float(np.sqrt(np.mean(x ** 2)) + 1e-9)


if __name__ == '__main__':
    pack = sys.argv[1]; ix = json.load(open(os.path.join(pack, 'index.json')))
    for name, (bank, prog, key) in REF.items():
        if name not in ix['instruments']: continue
        ix['instruments'][name]['gain'] = 1.0
        ST._index = ix; ST._root = pack; ST.clear_cache()
        drum = bank == 128
        ref = SM.render(bank, prog, key, .3 if drum else 1.0, 100, .35 if drum else .5, chan=9 if drum else 0)
        lib = ST.render(name, key, .3 if drum else 1.0, 100, .35 if drum else .5)
        n = int((.25 if drum else 1.0) * SM.SR)
        g = float(np.clip(rms(ref, n) / rms(lib, n), .05, 20))
        ix['instruments'][name]['gain'] = round(g, 4)
        print(f'{name:15s} gain {g:6.3f}')
    json.dump(ix, open(os.path.join(pack, 'index.json'), 'w'), indent=1)
