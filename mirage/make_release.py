"""DJ Velvet Purple / Mirage Tropical Records - build one instrumental release (16:9 video or 9:16 Short), fail-closed.

    python3 mirage/make_release.py plan  --date YYYY-MM-DD            -> prints the next release plan (JSON), writes out/mtrNNN.plan.json
    python3 mirage/make_release.py build --release mtrNNN --format video|short --photo PATH --photographer NAME --photo-page URL --title "Title"
    python3 mirage/make_release.py record --release mtrNNN --date YYYY-MM-DD --slot "YYYY-MM-DDTHH:MM" --uuid UUID --media URL

Music: djvelvetgrey engine v4 in real-instruments mode (every sound a recorded instrument, no vocals).
"Different every day" is enforced against the ledger (ledger.json), not assumed:
  - style rotation over the 15 Mirage styles (DJ Velvet Grey's 12 + trance + future bass + indie dance), never the same style twice in a row;
  - key+mode not used in the last 10 releases, tempo not within 1 BPM of the previous release;
  - chord loop at most 0.85 alike (any key, any rotation; 1.0 = same loop) to each release of the last day (6); the last 30 weigh in;
  - production (progression, arc, basslines, lead, mode) never identical in 5 of those 6 choices to an earlier release of the style;
  - lead and answer instrument families avoided if used as lead/answer in the last 2 releases (weighted);
  - hook melody: every rhythm cell x contour x start note of the style is realised exactly as rendered; the one furthest
    from every earlier release is used, and it must be at least 0.25 away (near-copies are < 0.18).
build renders, exports (codec headroom), runs the blocking QC (qc.py, exit 0 required) and makes the 16:9 video.
Automated technical checks only - not a listening judgement.
"""
import argparse, collections, json, os, subprocess, sys, datetime as dt
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
V2 = os.path.join(ROOT, 'djvelvetgrey', 'v2'); sys.path.insert(0, V2)
os.environ.setdefault('DVG_CATALOG', os.path.join(HERE, 'catalog.json'))
import styles as S, compose as C, engine as E, sampler as SM, make_track as MT  # noqa: E402
S.STYLES.update(getattr(S, 'EXTRA_STYLES', {}))   # Mirage-only styles (trance)
MIRAGE_ORDER = ['deep', 'melodic', 'house', 'afro', 'tropical', 'futurebass', 'nudisco', 'progressive', 'tech', 'trance', 'vocal', 'soulful',
                'indiedance', 'disco', 'french']   # DJ Velvet Grey's 12 + trance + future bass + indie dance (Sello, 23 Oct)
assert set(MIRAGE_ORDER) == set(S.STYLES), set(S.STYLES) ^ set(MIRAGE_ORDER)
OUT = os.path.join(ROOT, 'out'); os.makedirs(OUT, exist_ok=True)
LEDGER = os.path.join(HERE, 'ledger.json')
MODES = {'major': [0, 2, 4, 5, 7, 9, 11], 'minor': [0, 2, 3, 5, 7, 8, 10], 'dorian': [0, 2, 3, 5, 7, 9, 10], 'mixolydian': [0, 2, 4, 5, 7, 9, 10]}
FAMILY = {'Yamaha Grand Piano': 'piano', 'Bright Yamaha Grand': 'piano', 'Electric Piano': 'piano', 'Strings': 'strings', 'Slow Strings': 'strings',
          'Synth Strings 1': 'strings', 'Orchestral Pad': 'strings', 'Brass Section': 'brass', 'Brass 2': 'brass', 'Rhodes EP': 'ep',
          'Legend EP 2': 'ep', 'Detuned EP 1': 'ep', 'Percussive Organ': 'organ', 'DrawbarOrgan': 'organ', 'Rock Organ': 'organ',
          'Alto Sax': 'sax', 'Tenor Sax': 'sax'}
FAM = lambda n: FAMILY.get(n, n)
CHORD_STRICT = 6   # chord loop at most CHORD_MAX alike to each of the last 6 releases (one day); the last 30 weigh in above 0.75
CHORD_MAX = 0.85  # 1.0 = same loop in any key/rotation; common diatonic loops sit at 0.5-0.8
HOOK_TRIES = 12   # briefs tried for a far-enough hook before refusing
CELLS_OVERRIDE = None
GEN_CELLS = 40    # extra procedurally generated rhythm cells searched when the style's own cells can't reach HOOK_MIN


def gen_cell(k):
    """Deterministic 2-bar hook rhythm 'gen<k>': 5-8 notes, mostly on 8ths with some 16ths, at least two notes per bar,
    last note held. Registered into compose.RHYTHM_CELLS so hook_from_spec renders it exactly like a built-in cell."""
    g = np.random.default_rng(1_000_003 + int(k))
    grid = np.arange(0, 6.75, .25); w = np.array([3.0 if (x * 2) % 1 == 0 else 1.0 for x in grid])
    while True:
        n = int(g.integers(5, 9))
        on = sorted(g.choice(grid, size=n, replace=False, p=w / w.sum()).tolist())
        if on[0] <= 1 and sum(1 for o in on if o < 4) >= 2 and sum(1 for o in on if o >= 4) >= 2: break
    cell = [(float(o), float(min(2.0, b - o))) for o, b in zip(on, on[1:])] + [(float(on[-1]), float(min(2.5, 8 - on[-1])))]
    return cell


def ensure_cell(name):
    if isinstance(name, str) and name.startswith('gen') and name not in C.RHYTHM_CELLS:
        C.RHYTHM_CELLS[name] = gen_cell(int(name[3:]))
    return name
HOOK_MIN = 0.25    # melody distance to every earlier release (near-copies score < 0.18; unrelated tunes ~0.4+)


def ledger():
    return json.load(open(LEDGER)) if os.path.exists(LEDGER) else {'releases': []}


def chord_pcs(style, tonic, mode, prog):
    H = C.Harmony(tonic, prog, mode, S.STYLES[style].get('harm_rhythm', 1))
    return [frozenset(n % 12 for n in c[:4]) for c in H.chords]


def chord_sim(a, b):
    best = 0.0
    for sh in range(12):
        for rot in range(4):
            bb = [frozenset((p + sh) % 12 for p in x) for x in b[rot:] + b[:rot]]
            best = max(best, sum(len(x & y) / len(x | y) for x, y in zip(a, bb)) / 4)
    return best


def plan(date):
    L = ledger()['releases']; n = len(L) + 1; rid = f'mtr{n:03d}'
    r = np.random.default_rng(int(dt.date.fromisoformat(date).strftime('%Y%m%d')) * 31 + n)
    recent_styles = [x['style'] for x in L[-(len(MIRAGE_ORDER) - 1):]]
    yesterday = L[-1]['style'] if L else None
    unused = [s for s in MIRAGE_ORDER if s not in recent_styles]          # least recently used style first, never yesterday's
    style = unused[0] if unused else min((s for s in MIRAGE_ORDER if s != yesterday),
                                         key=lambda s: max(i for i, x in enumerate(recent_styles) if x == s))
    P = S.STYLES[style]
    used_keys = {(x['tonic'] % 12, x['mode']) for x in L[-10:]}
    last_bpm = L[-1]['bpm'] if L else None
    recent_pcs = [[frozenset(p) for p in x['chord_pcs']] for x in L[-30:]]
    strict_pcs = recent_pcs[-CHORD_STRICT:]; soft_pcs = recent_pcs[:-CHORD_STRICT] if len(recent_pcs) > CHORD_STRICT else []
    recent_fams = {f for x in L[-2:] for f in (x['lead_family'], x['answer_family'])}
    cat = C.load_catalog()
    def prod_overlap(b):   # compose.screen flags every hook of a brief that shares >= 5 production features with a release
        g = b['groove']; feats = {'progression': b['progression'], 'template': b['arc'], 'bass_a': g['bass_a'], 'bass_b': g['bass_b'],
                                  'lead': b['lead'], 'style': b['style'], 'mode': b['mode']}
        return max([sum(1 for k, v in feats.items() if e.get(k) == v) for e in cat] or [0])
    pool = []
    for it in range(3000):
        if it >= 300 and sum(1 for x in pool if x[0] == 0) >= HOOK_TRIES: break
        prog = P['progressions'][int(r.integers(len(P['progressions'])))]; mode = C.best_mode(prog, P['modes'])
        tonic = int(r.integers(55, 63)); bpm = int(r.integers(P['bpm'][0], P['bpm'][1] + 1))
        lead = P['leads'][int(r.integers(len(P['leads'])))]; ans = [a for a in P['answers'] if a != lead]; answer = ans[int(r.integers(len(ans)))]
        seed = int(r.integers(100000, 999999)); d = SM.Palette(seed, style, real=True).describe()
        li, ai = d.get(lead, lead), d.get(answer, answer)
        pcs = chord_pcs(style, tonic, mode, prog)
        c = dict(prog=prog, mode=mode, tonic=tonic, bpm=bpm, lead=lead, answer=answer, seed=seed, li=li, ai=ai, pcs=pcs,
                 ba=P['bass_a'][int(r.integers(len(P['bass_a'])))], bb=P['bass_b'][int(r.integers(len(P['bass_b'])))],
                 arc=P['arcs'][int(r.integers(len(P['arcs'])))], swing=round(float(r.uniform(*P['swing'])), 3))
        b = {'engine': 'v2', 'style': style, 'release': rid, 'bpm': bpm, 'tonic': tonic, 'progression': [list(x) for x in prog],
             'mode': mode, 'lead': lead, 'answer': answer, 'groove': {'bass_a': c['ba'], 'bass_b': c['bb'], 'swing': c['swing']},
             'arc': c['arc'], 'loudness_lufs': P['lufs'], 'seed': seed, 'instruments': 'real'}
        ov = prod_overlap(b)
        pen = (1000 if FAM(li) == FAM(ai) else 0) + (300 if (tonic % 12, mode) in used_keys else 0) \
            + (300 if last_bpm is not None and abs(bpm - last_bpm) <= 1 else 0) \
            + sum(400 for q in strict_pcs if chord_sim(pcs, q) > CHORD_MAX) + min(120, sum(20 for q in soft_pcs if chord_sim(pcs, q) > .75)) \
            + (1000 if ov >= 6 else 150 if ov == 5 else 10 * ov) \
            + (100 if FAM(li) in recent_fams else 0) + (50 if FAM(ai) in recent_fams else 0)
        if pen < 300: pool.append((pen, len(pool), c, b))
    if not pool: raise SystemExit('could not find a release different enough from the ledger')
    pool.sort(key=lambda x: (x[0], x[1]))
    motifs = [e['motif'] for e in cat]
    def hook_search(b):
        """Every (rhythm cell, contour, start note) of the style, realised exactly as the render will (hook_from_spec),
        scored by its distance to the nearest catalogue hook; returns the furthest."""
        h = C.harmony_for(b); lo, hi = b['tonic'] + 9, b['tonic'] + 24
        best = (-1.0, None)
        style_cells = CELLS_OVERRIDE or P.get('cells') or [c for c in C.RHYTHM_CELLS if not c.startswith('gen')]
        gen = [ensure_cell(f'gen{int(r.integers(1, 10**6))}') for _ in range(GEN_CELLS)]
        for cell in style_cells + ['|'] + gen:
            if cell == '|':
                if best[0] >= HOOK_MIN: break      # the style's own rhythms are far enough: keep the idiomatic one
                continue
            for con in C.CONTOURS:
                for start in h.chord_tones_in(0, lo + 2, hi - 5):
                    spec = {'cell': cell, 'contour': con, 'start': int(start)}
                    rep = C.motif_repr(C.hook_from_spec(b, spec)[1]['call'])
                    d = 1.0
                    for m in motifs:
                        d = min(d, C.similarity_distance(rep, m))
                        if d <= best[0]: break
                    if d > best[0]: best = (d, spec)
        return best
    chosen = None
    for pen, _, c, b in pool[:HOOK_TRIES]:   # next-best brief when no hook of this one is far enough from the catalogue
        if MT.validate(b, P): continue
        d, spec = hook_search(b)
        if spec and d >= HOOK_MIN: chosen = (pen, c, b, dict(spec, distance=round(d, 3))); break
    if not chosen: raise SystemExit(f'no hook candidate is far enough (>= {HOOK_MIN}) from every earlier release ({HOOK_TRIES} briefs tried)')
    pen, c, b, pick = chosen
    b['motif'] = {'cell': pick['cell'], 'contour': pick['contour'], 'start': pick['start'], 'candidate': 'search', 'distance': pick['distance'],
                  'selected_by': 'automatic, screened against every earlier release - not a listening judgement'}
    p = {'release': rid, 'date': date, 'style': style, 'label': P['label'], 'key': C.key_name(c['tonic'], c['mode']), 'bpm': c['bpm'],
         'lead': c['li'], 'answer': c['ai'], 'mood': P['mood'], 'photo_brief': P['photo'], 'penalty': pen, 'brief': b,
         'chord_pcs': [sorted(x) for x in c['pcs']]}
    json.dump(p, open(os.path.join(OUT, rid + '.plan.json'), 'w'), indent=1)
    print(json.dumps({k: v for k, v in p.items() if k not in ('brief', 'chord_pcs')}, indent=1))


def build(a):
    p = json.load(open(os.path.join(OUT, a.release + '.plan.json'))); b = p['brief']; base = os.path.join(OUT, a.release)
    from scipy.io import wavfile
    ensure_cell(b['motif']['cell'])
    t = E.TrackV2(b, b['motif']); mix = t.render()
    wavfile.write(base + '.master.wav', E.SR, (np.clip(mix, -1, 1) * 32767).astype(np.int16))
    meta = dict(t.meta, title=a.title, bpm=b['bpm'], key=p['key'], brief=b)
    json.dump(meta, open(base + '.meta.json', 'w'), indent=1, default=str)
    def export(src):
        subprocess.run([sys.executable, os.path.join(V2, 'export.py'), src, OUT, a.release, '--title', a.title], check=True, capture_output=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=black:s=64x64:r=1', '-i', base + '.m4a', '-map', '0:v', '-map', '1:a',
                        '-c:v', 'libx264', '-c:a', 'copy', '-shortest', base + '.qc.mp4'], check=True)
        return subprocess.run([sys.executable, os.path.join(V2, 'qc.py'), '--wav', base + '.delivery.wav', '--mp3', base + '.mp3', '--mp4', base + '.qc.mp4',
                               '--meta', base + '.meta.json', '--out', base + '.qc.json'], capture_output=True).returncode
    rc = export(base + '.master.wav')
    if rc == 2:   # codec overshoot made the export trim too deep: re-master with more headroom once, then re-check
        import soundfile as sf, scipy.signal as ss
        x, sr = sf.read(base + '.master.wav'); x = ss.sosfiltfilt(ss.butter(4, 15500, 'low', fs=sr, output='sos'), x, axis=0)
        y, _ = E.master(x, b['loudness_lufs'] - .5, ceiling_db=-4.5)
        sf.write(base + '.master2.wav', (np.clip(y, -1, 1) * 32767).astype(np.int16), sr, subtype='PCM_16'); rc = export(base + '.master2.wav')
    q = json.load(open(base + '.qc.json'))
    if rc != 0: raise SystemExit(f"QC failed: {[f['check'] for f in q.get('failures', [])]}")
    # photo credit goes in the description only (describe.py), never on the video
    vs = 'video_short.py' if a.format == 'short' else 'video.py'
    subprocess.run([sys.executable, os.path.join(HERE, vs), '--image', a.photo, '--audio', base + '.delivery.wav', '--aac', base + '.m4a',
                    '--title', a.title, '--style', b['style'], '--credit', '-', '--out', base + '.mp4'], check=True)
    p.update(title=a.title, photographer=a.photographer, photo_page=a.photo_page, qc=q['status'], lufs=q['files']['wav']['integrated_lufs'], format=a.format)
    json.dump(p, open(os.path.join(OUT, a.release + '.plan.json'), 'w'), indent=1)
    print(json.dumps({'release': a.release, 'title': a.title, 'qc': q['status'], 'lufs': p['lufs'], 'mp4': base + '.mp4'}))


def record(a):
    p = json.load(open(os.path.join(OUT, a.release + '.plan.json'))); b = p['brief']; L = ledger()
    if any(x['release'] == a.release for x in L['releases']): raise SystemExit('already recorded')
    ensure_cell(b['motif']['cell'])
    hook = C.hook_from_spec(b, b['motif'])[1]
    lead_fam, ans_fam = FAM(p['lead']), FAM(p['answer'])
    L['releases'].append({'release': a.release, 'date': a.date, 'slot': a.slot, 'format': p.get('format', a.format), 'title': p['title'], 'style': p['style'], 'tonic': b['tonic'], 'mode': b['mode'],
                          'key': p['key'], 'bpm': b['bpm'], 'lead': p['lead'], 'answer': p['answer'], 'lead_family': lead_fam, 'answer_family': ans_fam,
                          'chord_pcs': p['chord_pcs'], 'photographer': p['photographer'], 'photo_page': p['photo_page'], 'photo_kind': a.photo_kind or 'bikini',
                          'metricool_uuid': a.uuid, 'media_url': a.media})
    json.dump(L, open(LEDGER, 'w'), indent=1)
    C.add_to_catalog({'id': a.release, 'title': p['title'], 'status': 'published', 'style': p['style'], 'mode': b['mode'],
                      'motif': C.motif_repr(hook['call']), 'progression': b['progression'], 'template': b['arc'], 'lead': b['lead'],
                      'answer': b['answer'], 'bass_a': b['groove']['bass_a'], 'bass_b': b['groove']['bass_b'], 'key': p['key'], 'bpm': b['bpm']})
    print('recorded', a.release)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd', choices=['plan', 'build', 'record'])
    for k in ('date', 'release', 'photo', 'photographer', 'photo-page', 'title', 'uuid', 'media', 'slot'): ap.add_argument('--' + k)
    ap.add_argument('--photo-kind', choices=['bikini', 'fashion', 'nature'], default='bikini')
    ap.add_argument('--format', choices=['video', 'short'], default='video')
    a = ap.parse_args()
    {'plan': lambda: plan(a.date), 'build': lambda: build(a), 'record': lambda: record(a)}[a.cmd]()
