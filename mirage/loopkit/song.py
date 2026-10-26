"""Render a hand-written Mirage song spec (mirage/songs/<id>.json) to a mastered 2:59 WAV.

Every Mirage song is written by hand (Sello, 26 Oct 2026): chords and voicings, bass line, hook, pad and drum
patterns are typed note by note into a JSON spec. This script only checks the writing (music-theory lint +
uniqueness against every earlier spec) and performs it on real recordings: CC0 studio pack (Steinway, upright bass,
strings, brass, flute, sax, harp, pizzicato, mallets, hand percussion), FluidR3 GM recordings for electric piano,
guitars, organ and electric bass (gm_* names), and TR-909/808 recordings for the drum machine parts.

    python3 mirage/loopkit/song.py check  mirage/songs/mtr012.json
    python3 mirage/loopkit/song.py render mirage/songs/mtr012.json --out out/mtr012.master.wav

Spec (all beats are quarter notes inside a 4/4 bar; MIDI note numbers; 8 bars that loop):
{
 "id": "mtr012", "title": "...", "artist": "Saltglass Society", "style": "deep", "bpm": 122, "key": "Am",
 "reference": {"artist": "...", "title": "...", "data": "122 BPM, A minor, Deep House", "source": "url"},   (optional)
 "chords": [[57,60,64,67,71], ... 8 voicings], "roots": [33, ... 8 bass roots],
 "keys":  {"inst": "piano_steinway", "comp": [[beat, len, vel], ...], "release": 0.5, "shift": 0},
 "bass":  {"inst": "upright_bass", "pattern": [[beat, len, interval, vel], ...], "last_bar": [[...]] (optional), "release": 0.25},
 "hook":  {"layers": [{"inst": "flute", "shift": 0, "gain": 1.0}, ...], "bars": [[[beat, len, midi, vel], ...] x 8]},
 "pad":   {"layers": [{"inst": "string_section", "shift": 12, "vel": 48, "gain": 1.0}],
           "arp": {"inst": "harp", "order": [0,1,2,3,2,1,3,2], "shift": 12, "gain": 0.55, "vel": 74}},             (arp optional)
 "drums": {"kit": "909", "swing": 0.015,
           "main": {"kick": [0,4,8,12], "clap": [4,12], "hat": [2,6,10,14], "perc": {"shaker": [...]}},
           "alt":  {...  variation for drop 2 ...},
           "tops": {...  no kick: hats/percussion for intro and break ...}}
}
"""
import argparse, glob, json, os, re, sys, tempfile
import numpy as np, soundfile as sf
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(REPO, 'djvelvetgrey', 'v2'))
import parts as P          # noqa: E402
import drumkit as DK       # noqa: E402
import arrange as AR       # noqa: E402
ST = P.ST; SR = P.SR
SONGS = os.path.join(REPO, 'mirage', 'songs')
LOOPLIB = os.environ.get('MIRAGE_LOOPS', '/home/claude/loops')
LOOP_ROLES = ('keys', 'bass', 'melody', 'melody2', 'pad', 'vocals', 'drums_main', 'drums_alt', 'drums_tops')
PART_OF = {'keys': 'keys', 'bass': 'bass', 'melody': 'hook', 'pad': 'pad'}    # loop role -> hand-written field it replaces


def loop_file(sub):
    """a verified Looperman loop in LOOPLIB whose file name contains `sub` (set-aside folders excluded)"""
    hits = [f for f in glob.glob(os.path.join(LOOPLIB, '*', '*.wav')) if sub in os.path.basename(f) and os.sep + '_' not in f[len(LOOPLIB):]]
    return hits[0] if len(hits) == 1 else None


def drums_by_loops(spec):
    L = spec.get('loops', {})
    return all(r in L for r in ('drums_main', 'drums_alt', 'drums_tops'))


def loop_harmony(spec):
    """accuracy check for a song mixing Looperman loops with hand-written parts: every hand-written chord (bass and
    pad follow it) must agree with what the keys loop (or melody loop) actually plays in that bar."""
    import librosa
    L = spec.get('loops', {}); ref = L.get('keys') or L.get('melody')
    if not ref or not any(PART_OF.get(r) in spec for r in ('bass', 'pad', 'keys') if r not in L): return []
    f = loop_file(ref)
    item = [i for c, v in AR.library(LOOPLIB).items() for i in v if i['file'] == f][0]
    k = parse_key(spec['key']); lk = item['key']
    if lk[1] != k[1]:
        rel = (lk[0] + (3 if lk[1] == 'minor' else -3)) % 12; d = ((k[0] - rel + 6) % 12) - 6
    else: d = ((k[0] - lk[0] + 6) % 12) - 6
    x = AR.stretch(item, float(spec['bpm']), d).mean(1)
    y = librosa.resample(x, orig_sr=SR, target_sr=22050)
    c = librosa.feature.chroma_cqt(y=y, sr=22050, hop_length=512); fpb = 22050 / 512 * 240 / spec['bpm']
    nb = max(1, int(round(c.shape[1] / fpb))); bars = [c[:, int(b * fpb):int((b + 1) * fpb)].mean(1) for b in range(nb)]
    err = []; ch8 = (spec['chords'] * 2)[:8]; ro8 = (spec['roots'] * 2)[:8]
    for b in range(8):
        top = set(np.argsort(bars[b % nb])[-4:])
        pcs = {n % 12 for n in ch8[b]}
        if ro8[b] % 12 not in top or len(pcs & top) < 2:
            err.append(f'bar {b+1}: hand-written chord (root {ro8[b] % 12}) disagrees with the {ref} loop (plays pcs {sorted(top)})')
    return err
NOTES = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
GM = {'gm_ep': 4, 'gm_ep2': 5, 'gm_clav': 7, 'gm_organ': 16, 'gm_organ_perc': 17, 'gm_guitar_nylon': 24, 'gm_guitar_steel': 25,
      'gm_guitar_jazz': 26, 'gm_guitar_clean': 27, 'gm_guitar_muted': 28, 'gm_bass_finger': 33, 'gm_bass_pick': 34,
      'gm_bass_fretless': 35, 'gm_bass_slap': 36, 'gm_steel_drums': 114, 'gm_vibes': 11}
STYLES = ['deep', 'melodic', 'house', 'afro', 'tropical', 'futurebass', 'nudisco', 'progressive', 'tech', 'trance', 'vocal',
          'soulful', 'disco', 'french', 'indiedance']
BPM_RANGE = {'tropical': (98, 112), 'trance': (132, 140), 'futurebass': (140, 160), 'nudisco': (110, 124), 'disco': (112, 124)}


def parse_key(k):
    m = re.fullmatch(r'([A-G])([#b]?)(m?)', k.strip())
    if not m: raise ValueError(f'key {k!r}: use e.g. Am, F#m, Eb, C')
    return (NOTES[m.group(1)] + {'#': 1, 'b': -1, '': 0}[m.group(2)]) % 12, 'minor' if m.group(3) else 'major'


def scale(key):
    pc, mode = parse_key(key)
    iv = [0, 2, 3, 5, 7, 8, 10] if mode == 'minor' else [0, 2, 4, 5, 7, 9, 11]
    return {(pc + i) % 12 for i in iv}


def inst_range(inst):
    if inst in GM: return 28, 100
    names = [n for n, lo, hi in ST.ENSEMBLES.get(inst, [])] or [inst]
    ks = [r['key'] for n in names for r in ST.index()['instruments'][n]['regions']]
    return min(ks) - 2, max(ks) + 2          # VSCO/VCSL notes are pitch-shifted at most 2 semitones past the sampled range


def note(inst, key, dur, vel, release):
    if inst in GM:
        import sampler as SM
        return SM.render(0, GM[inst], key, dur, vel, release)
    return ST.render(inst, key, dur, vel, release)


# ---------------------------------------------------------------- lint (the writing must be musically correct)
def check(spec):
    err, warn = [], []
    LP = spec.get('loops', {})
    need = ['id', 'title', 'artist', 'style', 'bpm', 'key', 'chords', 'roots'] + [PART_OF[r] for r in PART_OF if r not in LP]
    if not drums_by_loops(spec): need.append('drums')
    for k in need:
        if k not in spec: err.append(f'missing {k}')
    for r, sub in LP.items():
        if r not in LOOP_ROLES: err.append(f'loops.{r}: unknown role (use {LOOP_ROLES})')
        elif loop_file(sub) is None: err.append(f'loops.{r}: no single verified loop matches {sub!r} in {LOOPLIB} (run loopkit/verify.py)')
    if err: return err, warn
    if spec['style'] not in STYLES: err.append(f"style {spec['style']} not one of {STYLES}")
    lo, hi = BPM_RANGE.get(spec['style'], (116, 128))
    if not lo <= spec['bpm'] <= hi: err.append(f"bpm {spec['bpm']} outside {spec['style']} range {lo}-{hi}")
    sc = scale(spec['key']); ch = spec['chords']; ro = spec['roots']
    if len(ch) not in (4, 8) or len(ro) != len(ch): err.append('chords/roots must have 4 or 8 bars (same count)')
    ch8 = (ch * 2)[:8]; ro8 = (ro * 2)[:8]
    for b, (c, r) in enumerate(zip(ch8, ro8)):
        if not 3 <= len(c) <= 6: err.append(f'bar {b+1}: chord needs 3-6 notes')
        if min(c) - r < 12: err.append(f'bar {b+1}: voicing must sit at least an octave above the bass root (mud)')
        out = [n for n in c if n % 12 not in sc]
        if len(out) > 1: err.append(f'bar {b+1}: chord has {len(out)} notes outside {spec["key"]} (max 1, e.g. a leading tone)')
    pcs = [{n % 12 for n in c} | {r % 12} for c, r in zip(ch8, ro8)]
    # instruments and ranges
    def rng_ok(inst, notes, what):
        try: a, z = inst_range(inst)
        except KeyError: err.append(f'{what}: unknown instrument {inst}'); return
        bad = sorted({n for n in notes if not a <= n <= z})
        if bad: err.append(f'{what}: notes {bad} outside {inst} range {a}-{z}')
    K = spec.get('keys') if 'keys' not in LP else None
    if K: rng_ok(K['inst'], [n + K.get('shift', 0) for c in ch8 for n in c], 'keys')
    B = spec['bass']; bn = [r + p[2] for r in ro8 for p in B['pattern']]; rng_ok(B['inst'], bn, 'bass')
    for b, r in enumerate(ro8):
        for (bt, ln, iv, v) in (B.get('last_bar') if b == 7 and B.get('last_bar') else B['pattern']):
            n = r + iv
            if n % 12 not in sc and n % 12 not in pcs[b]: err.append(f'bar {b+1}: bass note {n} outside key and chord')
            if bt in (0, 0.0) and n % 12 not in pcs[b]: err.append(f'bar {b+1}: bass downbeat {n} is not a chord tone')
    H = spec.get('hook') if 'melody' not in LP else None
    bars = H['bars'] if H else []
    if H:
      if True:
        if len(bars) != 8: err.append('hook needs exactly 8 bars')
        for L in H['layers']: rng_ok(L['inst'], [n[2] + L.get('shift', 0) for bar in bars for n in bar], f"hook layer {L['inst']}")
        rhythms = set()
        for b, bar in enumerate(bars):
            if not 1 <= len(bar) <= 10: err.append(f'hook bar {b+1}: {len(bar)} notes (1-10)')
            rhythms.add(tuple((n[0], n[1]) for n in bar))
            for (bt, ln, k, v) in bar:
                if bt + ln > 4.01 and b < 7 and False: pass
                if k % 12 not in sc and k % 12 not in pcs[b]: err.append(f'hook bar {b+1}: note {k} outside key and chord')
                strong = abs(bt - round(bt)) < 1e-6 or ln >= .9
                if strong and k % 12 not in pcs[b] and any((k - c) % 12 == 1 for c in pcs[b]):
                    err.append(f'hook bar {b+1} beat {bt}: note {k} sits a minor 2nd above a chord tone (clash)')
        if len(rhythms) > 6: err.append('hook has no repetition: reuse a bar rhythm (call and answer) - at most 6 different bar rhythms')
        allh = [n[2] for bar in bars for n in bar]
        if len(set(allh)) < 4: err.append('hook uses fewer than 4 different pitches')
        if max(allh) - min(allh) > 19: warn.append('hook spans more than an octave and a fifth')
    for L in (spec['pad']['layers'] if 'pad' not in LP else []): rng_ok(L['inst'], [n + L.get('shift', 0) for c in ch8 for n in c], f"pad {L['inst']}")
    D = spec.get('drums') if not drums_by_loops(spec) else None
    if D and D.get('kit') not in DK.MAP: err.append('drums.kit must be 909 or 808')
    for part in (('main', 'alt', 'tops') if D else ()):
        if part not in D: err.append(f'drums.{part} missing'); continue
        if part == 'tops' and D[part].get('kick'): err.append('drums.tops must not contain a kick')
        if part != 'tops' and not D[part].get('kick'): err.append(f'drums.{part} needs a kick')
    if not err and LP: err += loop_harmony(spec)
    return err, warn


def hook_sig(spec):
    ev = [(b * 16 + int(round(n[0] * 4)), n[2]) for b, bar in enumerate(spec['hook']['bars']) for n in bar]
    return {(t, k2 - k1) for (t, k1), (_, k2) in zip(ev, ev[1:])}


def degrees(spec):
    pc, _ = parse_key(spec['key'])
    return tuple((r - pc) % 12 for r in (spec['roots'] * 2)[:8])


def unique(spec):
    """refuse a hook that is >55% the same (onset + interval) as any earlier song, or a copy of an earlier song's
    progression + hook rhythm; compares against every spec in mirage/songs/."""
    err = []; hand = 'hook' in spec and 'melody' not in spec.get('loops', {})
    me = hook_sig(spec) if hand else set(); rh = [tuple((n[0], n[1]) for n in bar) for bar in spec['hook']['bars']] if hand else None
    LP = spec.get('loops', {}); files = sorted(glob.glob(os.path.join(SONGS, '*.json')))
    for f in files:
        o = json.load(open(f))
        if o.get('id') == spec['id']: continue
        if o.get('title', '').lower() == spec['title'].lower(): err.append(f"title already used by {o['id']}")
        OL = o.get('loops', {})
        if LP.get('melody') and LP.get('melody') == OL.get('melody') and LP.get('keys') == OL.get('keys'):
            err.append(f"same keys + melody loops as {o['id']}")
        if LP.get('melody') and LP['melody'] in (OL.get('melody'), OL.get('melody2')) and f in files[-30:]:
            err.append(f"melody loop {LP['melody']} was used by {o['id']} within the last 30 songs")
        if not hand or 'hook' not in o or 'melody' in OL: continue
        s = hook_sig(o); j = len(me & s) / max(1, len(me | s))
        if j > .55: err.append(f"hook {j:.0%} the same as {o['id']} '{o.get('title')}'")
        orh = [tuple((n[0], n[1]) for n in bar) for bar in o['hook']['bars']]
        if degrees(o) == degrees(spec) and orh == rh: err.append(f"same progression and hook rhythm as {o['id']}")
    return err


# ---------------------------------------------------------------- performance
def play(bpm, events, inst, release, seed, swing=.015, humanize_ms=6):
    rng = np.random.default_rng(seed)
    beat = 60 / bpm; N = int(round(32 * beat * SR)); out = np.zeros((N + SR * 4, 2), np.float32)
    for (t, dur, key, vel) in events:
        sw = swing * beat if abs((t % 1) - .5) < 1e-6 else 0
        p = max(0, int((t * beat + sw + rng.normal(0, humanize_ms / 1000)) * SR))
        y = note(inst, int(key), dur * beat, int(np.clip(vel + rng.integers(-3, 4), 1, 127)), release)
        out[p:p + len(y)] += y[: len(out) - p]
    tail = out[N:].copy(); out = out[:N]; out[:len(tail)] += tail[:N]
    return out


def nrm(y): return y / max(1e-6, np.abs(y).max())


def render_parts(spec, lib):
    LP = spec.get('loops', {})
    bpm = spec['bpm']; ch = (spec['chords'] * 2)[:8]; ro = (spec['roots'] * 2)[:8]
    tag = f"{int(bpm) if float(bpm).is_integer() else bpm}bpm_{spec['key']}_song"
    def save(cat, name, y):
        os.makedirs(os.path.join(lib, cat), exist_ok=True)
        sf.write(os.path.join(lib, cat, f'{cat}_{tag}_{name}.wav'), nrm(y) * .9, SR, subtype='PCM_24')
    K = spec.get('keys') if 'keys' not in LP else None
    if K:
     ev = [(b * 4 + bt + i * .006, ln, n + K.get('shift', 0), v - 6 * (i == 0)) for b in range(8) for (bt, ln, v) in K['comp'] for i, n in enumerate(ch[b])]
     save('keys', 'keys', play(bpm, ev, K['inst'], K.get('release', .5), 1))
    B = spec.get('bass') if 'bass' not in LP else None
    if B:
     ev = [(b * 4 + bt, ln, ro[b] + iv, v) for b in range(8) for (bt, ln, iv, v) in (B.get('last_bar') if b == 7 and B.get('last_bar') else B['pattern'])]
     save('bass', 'bass', play(bpm, ev, B['inst'], B.get('release', .25), 2, humanize_ms=3))
    H = spec.get('hook') if 'melody' not in LP else None; mix = 0
    for i, L in enumerate(H['layers'] if H else []):
        ev = [(b * 4 + bt, ln, k + L.get('shift', 0), v + L.get('dv', 0)) for b, bar in enumerate(H['bars']) for (bt, ln, k, v) in bar]
        mix = mix + L.get('gain', 1.0) * nrm(play(bpm, ev, L['inst'], L.get('release', .5), 3 + i, humanize_ms=5))
    if H: save('melody', 'hook', mix)
    Pd = spec.get('pad') if 'pad' not in LP else None; mix = 0
    for i, L in enumerate(Pd['layers'] if Pd else []):
        ev = [(b * 4, 4.0, n + L.get('shift', 0), L.get('vel', 50)) for b in range(8) for n in ch[b]]
        mix = mix + L.get('gain', 1.0) * nrm(play(bpm, ev, L['inst'], L.get('release', .8), 10 + i, swing=0, humanize_ms=0))
    if Pd and Pd.get('arp'):
        A = Pd['arp']; order = A.get('order', [0, 1, 2, 3, 2, 1, 3, 2])
        ev = [(b * 4 + s * (4 / len(order)), 4 / len(order) * .9, ch[b][order[s] % len(ch[b])] + A.get('shift', 12), A.get('vel', 74) + 6 * (s % 2 == 0))
              for b in range(8) for s in range(len(order))]
        mix = mix + A.get('gain', .55) * nrm(play(bpm, ev, A['inst'], A.get('release', .6), 20))
    if Pd: save('pad', 'pad', mix)
    if drums_by_loops(spec): return
    D = spec['drums']; DK.ensure_kits(); sw = D.get('swing', .015)
    for part, name in (('main', 'main'), ('alt', 'alt'), ('tops', 'tops')):
        y = DK.render_loop(D[part], D['kit'], bpm, bars=4 if D[part].get('steps', 16) == 16 else 4, swing=sw, seed=30 + len(name))
        save('drums', f'drums{name}', y)


def render(spec, out, lufs=None):
    lufs = lufs if lufs is not None else (-10.0 if spec['style'] in ('progressive', 'tech', 'trance', 'futurebass', 'house') else -11.0)
    with tempfile.TemporaryDirectory() as lib:
        render_parts(spec, lib)
        force = {'main': 'drumsmain', 'alt': 'drumsalt', 'top': 'drumstops'}
        for role, sub in spec.get('loops', {}).items():           # verified Looperman loops, linked in under their role
            f = loop_file(sub); parts = os.path.basename(f).split('_')
            cat = 'drums' if role.startswith('drums') else role
            tag = role.replace('_', '') if role.startswith('drums') else 'loop'
            os.makedirs(os.path.join(lib, cat), exist_ok=True)
            os.symlink(f, os.path.join(lib, cat, '_'.join([cat, parts[1], parts[2], tag] + parts[3:])))
            if not role.startswith('drums'): force[cat] = 'loop'
        L = AR.library(lib)
        form = spec.get('form') or AR.form_for(spec['style'], spec['id'])
        mix, meta = AR.arrange(L, 1, float(spec['bpm']), AR.parse_key(spec['key']), lufs, force, form)
    sf.write(out, mix, SR, subtype='PCM_16')
    meta.update(id=spec['id'], title=spec['title'], artist=spec['artist'], style=spec['style'], key=spec['key'], bpm=spec['bpm'],
                written_by_hand=True, reference=spec.get('reference'))
    meta['looperman'] = {r: os.path.basename(loop_file(sub)) for r, sub in spec.get('loops', {}).items()}
    meta.pop('loops', None)
    return meta


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd', choices=['check', 'render']); ap.add_argument('spec')
    ap.add_argument('--out'); ap.add_argument('--lufs', type=float)
    a = ap.parse_args(); spec = json.load(open(a.spec))
    err, warn = check(spec); err += unique(spec)
    for w in warn: print('warning:', w)
    if err:
        print('REFUSED:'); [print(' -', e) for e in err]; sys.exit(2)
    print('check ok:', spec['id'], spec['title'], '-', spec['artist'])
    if a.cmd == 'render':
        meta = render(spec, a.out, a.lufs)
        json.dump(meta, open(os.path.splitext(a.out)[0] + '.song.json', 'w'), indent=1, default=str)
        print(json.dumps({k: meta[k] for k in ('id', 'bpm', 'key', 'achieved_lufs_master')}))
