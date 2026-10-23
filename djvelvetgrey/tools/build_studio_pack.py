"""Build the "studio pack": a compact, curated set of CC0 multi-sampled recordings for engine v4's studio mode.

Sources (both CC0 1.0 — public domain, no attribution required):
  VSCO 2 Community Edition  https://github.com/sgossner/VSCO-2-CE  (SFZ branch: orchestral strings, brass, woodwinds, harp)
  Versilian Community Sample Library (VCSL)  https://github.com/sgossner/VCSL  (Steinway B grand, tenor sax, mallets,
      kalimba, hand percussion, hi-hats, claps, snare, toms, cymbals)

    python3 djvelvetgrey/tools/build_studio_pack.py <vsco_dir> <vcsl_dir> <out_dir>

Selection per instrument: up to 3 dynamic layers (soft/mid/loud) and 2 round-robins per sampled note; samples are
resampled to 44.1 kHz, leading silence trimmed, tails cut at a per-instrument maximum with a smooth fade, written as
FLAC, and indexed in index.json as SFZ-style regions (lokey/hikey/keycenter/lovel/hivel/rr).
"""
import glob, json, os, re, sys
import numpy as np, soundfile as sf
from scipy.signal import resample_poly

SR = 44100
NOTE = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
DYN = {'ppp': 0, 'pp': 1, 'p': 2, 'soft': 2, 'mp': 3, 'med': 4, 'medium': 4, 'mf': 5, 'normal': 5, 'f': 6, 'loud': 7,
       'ff': 8, 'fff': 9}


def midi(name):                       # C4 = 60 (VCSL convention)
    m = re.fullmatch(r'([A-G])(#|b)?(-?\d)', name)
    return 12 * (int(m.group(3)) + 1) + NOTE[m.group(1)] + (1 if m.group(2) == '#' else -1 if m.group(2) == 'b' else 0)


def load(path, max_s):
    x, sr = sf.read(path, always_2d=True, dtype='float32')
    if x.shape[1] == 1: x = np.repeat(x, 2, 1)
    x = x[:, :2]
    if sr != SR:
        from math import gcd
        g = gcd(SR, sr); x = resample_poly(x, SR // g, sr // g, axis=0).astype('float32')
    a = np.abs(x).max(1); pk = a.max() + 1e-9
    on = int(np.argmax(a > pk * 10 ** (-50 / 20)))
    x = x[max(0, on - int(.002 * SR)):]
    n = min(len(x), int(max_s * SR))
    x = x[:n].copy()
    f = min(int(.08 * SR), n // 4)
    if f > 0: x[-f:] *= np.linspace(1, 0, f)[:, None] ** 2
    return x


# ---------------------------------------------------------------- pitched instruments from VCSL (filename parsing)
VCSL_PITCHED = {
    'piano_steinway': ('Chordophones/Zithers/Grand Piano, Steinway B/NoSus/*.wav', r'_([A-G]#?\d)_vl(\d)_rr(\d)', 6.0),
    'tenor_sax':      ('Aerophones/Reed Aerophones/Tenor Saxophone/Vibrato/*.wav', r'_([A-G]#?\d)_var(\d)', 4.0),
    'vibraphone':     ('Idiophones/Struck Idiophones/Vibraphone/Hard Mallets/*.wav', r'_([A-G]#?\d)_v(\d)_rr(\d)', 4.0),
    'marimba':        ('Idiophones/Struck Idiophones/Marimba/*.wav', r'_([A-G]#?\d)_(med|loud|soft)_(\d+)', 3.0),
    'xylophone':      ('Idiophones/Struck Idiophones/Xylophone/Hard Mallets/*.wav', r'_([A-G]#?\d)_(pp|p|mp|mf|f|ff)_(\d+)', 2.5),
    'glockenspiel':   ('Idiophones/Struck Idiophones/Glockenspiel/*.wav', r'_(soft|medium|loud)_([A-G]#?\d)_(\d+)', 3.0),
    'kalimba':        ('Idiophones/Plucked Idiophones/Kalimba, Kenya/*.wav', r'_([A-G]#?\d)_k\d+_vl(\d)_rr(\d)', 3.0),
}
# ---------------------------------------------------------------- one-shot percussion from VCSL: name -> (globs, max_s)
VCSL_PERC = {
    'clap':      (['Idiophones/Struck Idiophones/Claps/Clap_rr*.wav'], 1.2),
    'hat':       (['Idiophones/Struck Idiophones/Hi-Hat Cymbal/HiHat_HitC_v*_Mid.wav'], .8),
    'hat_open':  (['Idiophones/Struck Idiophones/Hi-Hat Cymbal/HiHat_HitO_*_Mid.wav'], 1.5),
    'shaker':    (['Idiophones/Struck Idiophones/Shaker, Small/Mid_Shaker_Slap_*.wav', 'Idiophones/Struck Idiophones/Shaker, Small/Mid_ShakerDouble_*.wav'], .6),
    'tamb':      (['Idiophones/Struck Idiophones/Tambourine 1/Tamb1_Hit_*.wav'], 1.0),
    'cowbell':   (['Idiophones/Struck Idiophones/Cowbells/Cowbell1_Hit_*.wav'], 1.0),
    'claves':    (['Idiophones/Struck Idiophones/Claves/Claves1_Hit_*.wav'], .8),
    'wood':      (['Idiophones/Struck Idiophones/Woodblock/wood_click_*.wav'], .6),
    'bell_hi':   (['Idiophones/Struck Idiophones/Agogo Bells/Agogo_High_*.wav'], 1.0),
    'bell_lo':   (['Idiophones/Struck Idiophones/Agogo Bells/Agogo_Low_*.wav'], 1.0),
    'cabasa':    (['Idiophones/Struck Idiophones/Cabasa/Cabasa1_Hit_*.wav'], .6),
    'conga_hi':  (['Membranophones/Struck Membranophones/Conga/Conga_HitN_*.wav', 'Membranophones/Struck Membranophones/Conga/Quinto_HitN_*.wav'], 1.2),
    'conga_lo':  (['Membranophones/Struck Membranophones/Conga/Tumba_HitN_*.wav', 'Membranophones/Struck Membranophones/Conga/Tumba_HitFM_*.wav'], 1.2),
    'bongo_hi':  (['Membranophones/Struck Membranophones/Bongos/BongoH_Hit1_*.wav', 'Membranophones/Struck Membranophones/Bongos/BongoH_Hit*_*.wav'], 1.0),
    'bongo_lo':  (['Membranophones/Struck Membranophones/Bongos/BongoL_Hit1_*.wav'], 1.0),
    'snare':     (['Membranophones/Struck Membranophones/Snare Drum, Modern 1/Snare2_HitNS_*.wav'], 1.2),
    'side_stick': (['Membranophones/Struck Membranophones/Snare Drum, Modern 1/Snare2_stick_*.wav'], .6),
    'tom_mid':   (['Membranophones/Struck Membranophones/Tom 1/Stick/*.wav'], 1.5),
    'crash':     (['Idiophones/Struck Idiophones/Suspended Cymbal 1/susCymb1_hit_f*.wav', 'Idiophones/Struck Idiophones/Suspended Cymbal 1/susCymb1_hit_m*.wav'], 4.0),
    'cymbal_swell': (['Idiophones/Struck Idiophones/Suspended Cymbal 1/susCymb1_cresc_*.wav'], 6.0),
}
# ---------------------------------------------------------------- VSCO instruments via their SFZ files: name -> (sfz, max_s)
VSCO_SFZ = {
    'violins':     ('ViolinEnsSusVib.sfz', 6.0),
    'violas':      ('ViolaEnsSusVib.sfz', 6.0),
    'celli':       ('CelloEnsSusVib.sfz', 6.0),
    'violin_pizz': ('ViolinEnsPizz.sfz', 1.5),
    'upright_bass': ('ContrabassPizz.sfz', 2.5),
    'harp':        ('Harp.sfz', 4.0),
    'trumpet':     ('TrumpetSus.sfz', 4.0),
    'trumpet_stac': ('TrumpetStac.sfz', 1.2),
    'horn':        ('FHornSus.sfz', 4.0),
    'trombone':    ('TromboneSus.sfz', 4.0),
    'flute':       ('FluteSusVib.sfz', 4.0),
    'clarinet':    ('ClarinetSus.sfz', 4.0),
}


def dyn_rank(tok):
    return int(tok) if str(tok).isdigit() else DYN[str(tok).lower()]


def ranges(keys):
    keys = sorted(keys); out = {}
    for i, k in enumerate(keys):
        lo = keys[i - 1] + 1 + (k - keys[i - 1] - 1) // 2 if i else max(0, k - 12)
        hi = k + (keys[i + 1] - k) // 2 if i + 1 < len(keys) else min(127, k + 12)
        out[k] = (lo, hi)
    return out


def vel_split(n):
    edges = np.linspace(0, 128, n + 1).astype(int)
    return [(int(edges[i]), int(edges[i + 1] - 1)) for i in range(n)]


def pick_layers(ranks, n=3):
    r = sorted(set(ranks))
    if len(r) <= n: return r
    return [r[0], r[len(r) // 2], r[-1]]


def build_vcsl_pitched(vcsl, out, name, pat, rx, max_s, index):
    files = {}
    for f in glob.glob(os.path.join(vcsl, pat)):
        m = re.search(rx, os.path.basename(f))
        if not m: continue
        g = m.groups()
        if name == 'glockenspiel': dyn, note, rr = g
        elif name == 'tenor_sax': note, rr = g; dyn = 5
        else: note, dyn, rr = g
        # VCSL names the mallet instruments and kalimba an octave below their sounding pitch (measured: every sample's
        # spectrum sits exactly 2x the named note), the piano and sax at sounding pitch.
        off = 12 if name in ('vibraphone', 'marimba', 'kalimba', 'glockenspiel', 'xylophone') else 0
        files.setdefault(midi(note) + off, []).append((dyn_rank(dyn), int(rr), f))
    rg = ranges(files); regions = []
    for k, lst in sorted(files.items()):
        layers = pick_layers([d for d, _, _ in lst])
        for li, (lv, hv) in zip(layers, vel_split(len(layers))):
            cands = sorted([x for x in lst if x[0] == li], key=lambda x: x[1])[:2]
            for ri, (_, _, f) in enumerate(cands):
                rel = f'{name}/{k}_{li}_{ri}.flac'; os.makedirs(os.path.join(out, name), exist_ok=True)
                sf.write(os.path.join(out, rel), load(f, max_s), SR, format='FLAC', subtype='PCM_16')
                regions.append(dict(file=rel, key=k, lokey=rg[k][0], hikey=rg[k][1], lovel=lv, hivel=hv, rr=ri,
                                    src='VCSL/' + os.path.relpath(f, vcsl)))
    index[name] = dict(kind='pitched', source='VCSL (CC0)', regions=regions)


def build_vcsl_perc(vcsl, out, name, globs, max_s, index):
    fs = []
    for g in globs: fs += sorted(glob.glob(os.path.join(vcsl, g)))
    fs = list(dict.fromkeys(fs))
    def rank(f):
        b = os.path.basename(f)
        m = re.search(r'_v(\d)_', b) or re.search(r'_(ppp|pp|p|mp|mf|f|ff|fff)(?:_|\d|\.)', b)
        return dyn_rank(m.group(1)) if m else 5
    ranked = sorted(fs, key=rank)
    layers = pick_layers([rank(f) for f in ranked]); regions = []
    for li, (lv, hv) in zip(layers, vel_split(len(layers))):
        cands = [f for f in ranked if rank(f) == li][:3]
        for ri, f in enumerate(cands):
            rel = f'{name}/{li}_{ri}.flac'; os.makedirs(os.path.join(out, name), exist_ok=True)
            sf.write(os.path.join(out, rel), load(f, max_s), SR, format='FLAC', subtype='PCM_16')
            regions.append(dict(file=rel, key=60, lokey=0, hikey=127, lovel=lv, hivel=hv, rr=ri, src='VCSL/' + os.path.relpath(f, vcsl)))
    index[name] = dict(kind='oneshot', source='VCSL (CC0)', regions=regions)


def parse_sfz(path):
    txt = open(path, encoding='latin-1').read()
    dp = re.search(r'default_path=([^\n\r]+)', txt)
    base = dp.group(1).strip().replace('\\', '/') if dp else ''
    regs = []
    for chunk in txt.split('<region>')[1:]:
        chunk = chunk.split('<group>')[0]
        kv = {}
        for line in chunk.splitlines():
            line = line.split('//')[0].strip()
            if '=' in line:
                k, v = line.split('=', 1); kv[k.strip()] = v.strip()
        if 'sample' not in kv: continue
        regs.append(kv)
    return base, regs


def build_vsco(vsco, out, name, sfz, max_s, index):
    base, regs = parse_sfz(os.path.join(vsco, sfz))
    by_vel = {}
    for r in regs:
        by_vel.setdefault((int(r.get('lovel', 0)), int(r.get('hivel', 127))), []).append(r)
    vlayers = sorted(by_vel)
    if len(vlayers) > 3: vlayers = [vlayers[0], vlayers[len(vlayers) // 2], vlayers[-1]]
    regions = []
    for (lv0, hv0), (lv, hv) in zip(vlayers, vel_split(len(vlayers))):
        seen = {}
        for r in by_vel[(lv0, hv0)]:
            kc = int(r.get('pitch_keycenter', r.get('key', 60)))
            rr = seen.get(kc, 0)
            if rr >= 2: continue
            seen[kc] = rr + 1
            f = os.path.join(vsco, base, r['sample'].replace('\\', '/'))
            if not os.path.exists(f): continue
            rel = f'{name}/{kc}_{lv}_{rr}.flac'; os.makedirs(os.path.join(out, name), exist_ok=True)
            sf.write(os.path.join(out, rel), load(f, max_s), SR, format='FLAC', subtype='PCM_16')
            regions.append(dict(file=rel, key=kc, lokey=int(r.get('lokey', kc)), hikey=int(r.get('hikey', kc)), lovel=lv, hivel=hv,
                                rr=rr, src='VSCO-2-CE/' + os.path.relpath(f, vsco)))
    index[name] = dict(kind='pitched', source='VSCO 2 CE (CC0)', regions=regions)


if __name__ == '__main__':
    vsco, vcsl, out = sys.argv[1:4]
    os.makedirs(out, exist_ok=True); index = {}
    for n, (sfz, mx) in VSCO_SFZ.items():
        build_vsco(vsco, out, n, sfz, mx, index); print(n, len(index[n]['regions']), flush=True)
    for n, (pat, rx, mx) in VCSL_PITCHED.items():
        build_vcsl_pitched(vcsl, out, n, pat, rx, mx, index); print(n, len(index[n]['regions']), flush=True)
    for n, (gl, mx) in VCSL_PERC.items():
        build_vcsl_perc(vcsl, out, n, gl, mx, index); print(n, len(index[n]['regions']), flush=True)
    json.dump({'version': 1, 'licence': 'CC0 1.0 (VSCO 2 Community Edition; Versilian Community Sample Library)',
               'instruments': index}, open(os.path.join(out, 'index.json'), 'w'), indent=1)
    print('done', sum(len(v['regions']) for v in index.values()), 'regions')
