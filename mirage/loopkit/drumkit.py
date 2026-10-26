"""Hand-programmed drums for Mirage songs, played on real recordings:
  - Roland TR-909 (Jason Baker / Rob Roy Recordings set: free to use, not to be sold as samples) and TR-808 (Michael
    Fischer set, no restrictions), fetched from the npm packages @fluid-music/tr-909 and @fluid-music/tr-808
  - hand percussion from the CC0 studio pack (shaker, congas, bongos, tambourine, cabasa, claves, cowbell, woodblock)

A song spec writes each drum loop as 16th-note step lists over 1 or 2 bars, e.g.
    "main": {"kick": [0, 4, 8, 12], "clap": [4, 12], "hat": [2, 6, 10, 14], "ohat": [], "perc": {"shaker": [0,1,2,...]}}
Optional per-voice velocity accents: "vel": {"hat": [90, 60]} cycles through the list.

    from drumkit import render_loop, ensure_kits
"""
import os, subprocess, tarfile, io
import numpy as np, soundfile as sf, scipy.signal as ss

SR = 44100
KITS_DIR = os.environ.get('MIRAGE_DRUMS', '/home/claude/npmdrums')
PKGS = {'909': ('@fluid-music/tr-909', '0.0.4', 'tr-909'), '808': ('@fluid-music/tr-808', '0.0.2', 'tr-808')}
# voice -> file (relative to the package dir) per kit; several kick/snare flavours selectable as kick_b, kick_c...
MAP = {
    '909': {'kick': 'TR909all/BT7A0D7.WAV', 'kick_b': 'TR909all/BT3A0DA.WAV', 'kick_c': 'TR909all/BTAA0D3.WAV', 'kick_d': 'TR909all/BT0AAD0.WAV',
            'clap': 'TR909all/HANDCLP1.WAV', 'clap_b': 'TR909all/HANDCLP2.WAV', 'snare': 'TR909all/ST3T3S7.WAV', 'snare_b': 'TR909all/ST7T7SA.WAV',
            'hat': 'TR909all/HHCD2.WAV', 'hat_b': 'TR909all/HHCD6.WAV', 'ohat': 'TR909all/HHOD4.WAV', 'ohat_b': 'TR909all/HHODA.WAV',
            'ride': 'TR909all/RIDED4.WAV', 'crash': 'TR909all/CSHD6.WAV', 'rim': 'TR909all/RIM63.WAV',
            'tom_lo': 'TR909all/LT3D7.WAV', 'tom_mid': 'TR909all/MT3D7.WAV', 'tom_hi': 'TR909all/HT3D7.WAV'},
    '808': {'kick': 'TR808WAV/BD/BD5050.WAV', 'kick_b': 'TR808WAV/BD/BD7575.WAV', 'kick_c': 'TR808WAV/BD/BD2525.WAV', 'kick_d': 'TR808WAV/BD/BD0010.WAV',
            'clap': 'TR808WAV/CP/CP.WAV', 'snare': 'TR808WAV/SD/SD5050.WAV', 'snare_b': 'TR808WAV/SD/SD2575.WAV',
            'hat': 'TR808WAV/CH/CH.WAV', 'ohat': 'TR808WAV/OH/OH25.WAV', 'ohat_b': 'TR808WAV/OH/OH75.WAV', 'cowbell808': 'TR808WAV/CB/CB.WAV',
            'clave808': 'TR808WAV/CL/CL.WAV', 'maracas': 'TR808WAV/MA/MA.WAV', 'rim': 'TR808WAV/RS/RS.WAV',
            'conga808_lo': 'TR808WAV/LC/LC50.WAV', 'conga808_mid': 'TR808WAV/MC/MC50.WAV', 'conga808_hi': 'TR808WAV/HC/HC50.WAV'},
}
STUDIO_PERC = {'shaker', 'conga_hi', 'conga_lo', 'bongo_hi', 'bongo_lo', 'tamb', 'cabasa', 'claves', 'cowbell', 'wood', 'side_stick',
               'bell_hi', 'bell_lo', 'hat_ac', 'hat_open_ac', 'snare_ac', 'clap_ac'}
PAN = {'hat': .12, 'hat_b': .12, 'ohat': -.1, 'ohat_b': -.1, 'ride': .2, 'shaker': .25, 'tamb': -.3, 'conga_hi': .35, 'conga_lo': -.35,
       'bongo_hi': .45, 'bongo_lo': -.25, 'cabasa': .3, 'claves': -.4, 'cowbell': .3, 'wood': -.3, 'rim': -.15, 'maracas': .3,
       'clave808': -.4, 'cowbell808': .3, 'conga808_hi': .35, 'conga808_mid': .1, 'conga808_lo': -.35, 'tom_hi': .3, 'tom_lo': -.3}
GAIN = {'kick': 1.0, 'clap': .55, 'snare': .5, 'hat': .3, 'ohat': .3, 'ride': .22, 'crash': .3, 'rim': .35, 'perc': .45}


def ensure_kits():
    """download the two npm drum packages once (npm registry is reachable from scheduled runs)."""
    import urllib.request
    for kit, (pkg, ver, short) in PKGS.items():
        d = os.path.join(KITS_DIR, f'{short}-{ver}')
        if os.path.exists(os.path.join(d, 'package')): continue
        url = f'https://registry.npmjs.org/{pkg}/-/{short}-{ver}.tgz'
        data = subprocess.run(['curl', '-sfL', url], capture_output=True, check=True).stdout
        os.makedirs(d, exist_ok=True)
        tarfile.open(fileobj=io.BytesIO(data)).extractall(d)


_wav = {}


def sample(kit, voice):
    k = (kit, voice)
    if k not in _wav:
        if voice in STUDIO_PERC:
            import sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'djvelvetgrey', 'v2'))
            import studio as ST
            name = {'hat_ac': 'hat', 'hat_open_ac': 'hat_open', 'snare_ac': 'snare', 'clap_ac': 'clap'}.get(voice, voice)
            _wav[k] = ('studio', name)
        else:
            base = MAP[kit].get(voice) or MAP['909' if kit == '808' else '808'].get(voice)
            if base is None: raise ValueError(f'unknown drum voice {voice!r} for kit {kit}')
            _, ver, short = PKGS[kit if voice in MAP[kit] else ('909' if kit == '808' else '808')]
            kd = kit if voice in MAP[kit] else ('909' if kit == '808' else '808')
            f = os.path.join(KITS_DIR, f'{PKGS[kd][2]}-{PKGS[kd][1]}', 'package', base)
            x, sr = sf.read(f, always_2d=True, dtype='float32')
            x = x.mean(1)
            if sr != SR: x = ss.resample_poly(x, SR, sr).astype('float32')
            _wav[k] = x / (np.abs(x).max() + 1e-9)
    return _wav[k]


def hit(kit, voice, vel):
    s = sample(kit, voice)
    if isinstance(s, tuple):
        import studio as ST
        y = ST.render(s[1], 60, .35, int(np.clip(vel, 1, 127)), .3).mean(1)
        return y / (np.abs(y).max() + 1e-9) * (vel / 127) ** 1.3
    return s * (vel / 127) ** 1.3


def group(voice):
    v = voice.split('_')[0]
    return v if v in GAIN else 'perc'


def render_loop(pat, kit, bpm, bars=4, swing=0.0, seed=0, humanize_ms=3.0):
    """pat: {"kick": [steps], ..., "perc": {voice: [steps]}, "vel": {voice: [..]}, "steps": 16|32}; returns (bars) stereo loop."""
    rng = np.random.default_rng(seed)
    steps = int(pat.get('steps', 16)); step_s = 60 / bpm / 4
    N = int(round(bars * 16 * step_s * SR)); out = np.zeros((N + SR, 2), np.float32)
    voices = {k: v for k, v in pat.items() if k not in ('perc', 'vel', 'steps')}
    voices.update(pat.get('perc', {}))
    vels = pat.get('vel', {})
    for voice, st in voices.items():
        if not st: continue
        g = GAIN[group(voice)]; pan = PAN.get(voice, 0.0)
        pl, pr = np.sqrt(.5 - pan / 2), np.sqrt(.5 + pan / 2)
        vl = vels.get(voice) or ([110] if group(voice) == 'kick' else [100, 78])
        for rep in range(bars * 16 // steps):
            for i, s in enumerate(st):
                n = rep * steps + s
                sw = swing * 60 / bpm if n % 2 == 1 else 0.0
                hz = 0 if group(voice) == 'kick' else rng.normal(0, humanize_ms / 1000)
                p = max(0, int((n * step_s + sw + hz) * SR))
                v = vl[i % len(vl)] + (0 if group(voice) == 'kick' else rng.integers(-4, 5))
                y = hit(kit, voice, v) * g
                if voice.startswith('ohat'): y = y[: int(step_s * 1.8 * SR)] * np.linspace(1, 0, min(len(y), int(step_s * 1.8 * SR))) ** .5
                e = min(len(out), p + len(y))
                out[p:e, 0] += y[: e - p] * pl; out[p:e, 1] += y[: e - p] * pr
    tail = out[N:].copy(); out = out[:N]; out[:len(tail)] += tail[:N]
    return out
