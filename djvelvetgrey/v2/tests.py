"""Engine v3 test suite (no audio rendering except tiny fixtures). Run: python3 djvelvetgrey/v2/tests.py
Exits non-zero if any test fails. Negative tests prove that invalid, missing or QC-failed inputs never
reach the publishing step (release_gate.py exit != 0, and the simulated publisher is never called).
"""
import datetime as dt, hashlib, json, os, shutil, subprocess, sys, tempfile
import numpy as np
from scipy.io import wavfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); REPO = os.path.dirname(ROOT)
sys.path.insert(0, HERE)
import compose as C, styles as S, rotation as R, release_gate as G, manifest as M

results = []
def test(name):
    def deco(fn):
        try: fn(); results.append((name, 'PASS', ''))
        except AssertionError as e: results.append((name, 'FAIL', str(e)))
        except Exception as e: results.append((name, 'ERROR', repr(e)))
        return fn
    return deco


@test('similarity calibration: identical / transposed / shifted = 0, one interval < 0.06, different > 0.25')
def _():
    c = C.calibrate()
    assert c['identical'] == 0 and c['transposed'] == 0 and c['shifted_8th'] == 0, c
    assert c['one_interval_changed'] < 0.06, c
    assert c['different_motif_a'] > 0.25 and c['different_motif_b'] > 0.25, c


@test('similarity threshold boundary: near-copy flagged, clearly different motif not flagged')
def _():
    h = C.Harmony(57, C.PROGRESSIONS[0]); rng = np.random.default_rng(0)
    base = C.motif_repr(C.make_hook(h, 'lilt', 'arch', 69, 64, 80, rng)['call'])
    near = dict(base, intervals=base['intervals'][:-1] + [base['intervals'][-1] + 1])
    far = C.motif_repr(C.make_hook(h, 'sparse', 'zigzag', 72, 64, 80, rng)['call'])
    cat = [{'id': 'dvg900', 'title': 'Prior', 'motif': base}]
    b = {'progression': None, 'arc': None, 'groove': {}, 'lead': None, 'style': None}
    assert C.screen(near, b, cat, release='dvg950')['flags'], 'near-copy not flagged'
    assert not C.screen(far, b, cat, release='dvg950')['flags'], 'different motif flagged'
    assert C.similarity_distance(near, base) < C.FLAG_THRESHOLD <= C.similarity_distance(far, base)


@test('own-identity: a re-render/version of the same release never rejects itself')
def _():
    h = C.Harmony(57, C.PROGRESSIONS[0]); rng = np.random.default_rng(0)
    m = C.motif_repr(C.make_hook(h, 'lilt', 'arch', 69, 64, 80, rng)['call'])
    cat = [{'id': 'dvg001v2', 'title': 'Self', 'motif': m}]
    b = {'groove': {}}
    assert not C.screen(m, b, cat, release='dvg001')['flags']
    assert not C.screen(m, b, cat, release='dvg001v3')['flags']
    assert C.screen(m, b, cat, release='dvg002')['flags']


@test('answer phrase and production features are screened')
def _():
    h = C.Harmony(57, C.PROGRESSIONS[0]); rng = np.random.default_rng(1)
    hk = C.make_hook(h, 'call', 'fall', 70, 64, 80, rng)
    other = C.motif_repr(C.make_hook(h, 'sparse', 'zigzag', 72, 64, 80, rng)['call'])
    ans = C.motif_repr(hk['answer'][:4])
    cat = [{'id': 'dvg900', 'title': 'Prior', 'motif': other, 'answer_motif': ans}]
    assert C.screen(other if False else C.motif_repr(C.make_hook(h, 'anthem', 'rise', 67, 64, 80, rng)['call']),
                    {'groove': {}}, cat, answer=ans, release='dvg950')['flags'], 'answer copy not flagged'
    feats = {'progression': [[0, 'm9']], 'template': 'wave', 'bass_a': 'walk', 'bass_b': 'octave', 'lead': 'rhodes', 'style': 'deep', 'mode': 'minor'}
    cat2 = [dict(feats, id='dvg901', title='Twin', motif=other)]
    b = {'progression': [[0, 'm9']], 'arc': 'wave', 'groove': {'bass_a': 'walk', 'bass_b': 'octave'}, 'lead': 'rhodes', 'style': 'deep', 'mode': 'minor'}
    far = C.motif_repr(C.make_hook(h, 'skip', 'valley', 66, 64, 80, rng)['call'])
    assert any('production' in f for f in C.screen(far, b, cat2, release='dvg950')['flags'])


@test('tempo fit: every style, every allowed arc, low/mid/high tempo covers 179 s and the outro is heard >= 6 bars')
def _():
    for st, P in S.STYLES.items():
        for arc in P['arcs']:
            for bpm in (P['bpm'][0], (P['bpm'][0] + P['bpm'][1]) // 2, P['bpm'][1]):
                f = C.fit_sections(C.TEMPLATES[arc], bpm); bar = 240 / bpm
                tot = sum(n for _, n in f)
                assert tot * bar >= 179, (st, arc, bpm, tot * bar)
                heard = (179 - (tot - f[-1][1]) * bar) / bar
                assert heard >= 6, (st, arc, bpm, round(heard, 1))


@test('style registry: 12 distinct styles with distinct groove/arrangement signatures')
def _():
    assert len(S.ORDER) == 12 and set(S.ORDER) == set(S.STYLES)
    sigs = {(P['kick'], P['hats'], P['perc'], P['comp'], P['focal'], P['bass'], tuple(P['arcs'])) for P in S.STYLES.values()}
    assert len(sigs) == 12, 'two styles share an identical groove/arrangement signature'
    for st, P in S.STYLES.items():
        for prog in P['progressions']:
            assert all(t in C.CHORD_TYPES for _, t in prog), (st, prog)
        for g in P['bass_a'] + P['bass_b']: assert g in C.GROOVES, (st, g)
        for a in P['arcs']: assert a in C.TEMPLATES, (st, a)


@test('rotation maths: 12 x 2, one Tue + one Fri each, gaps 11/13, no adjacent repeat')
def _():
    R.verify()
    assert R.ROTATION[0] == 'deep' and R.ROTATION[1] == 'melodic' and R.ROTATION[22] == 'french' and R.ROTATION[23] == 'disco'


@test('rotation debt: a held slot is repaid in a later slot and reported as displacement; transitional flagged')
def _():
    tmp = tempfile.mkdtemp(); led, st = R.LEDGER, R.STATUS
    try:
        R.LEDGER = os.path.join(tmp, 'ledger.json'); R.STATUS = os.path.join(tmp, 'status.json')
        json.dump({'styles': {s: {'status': 'active-technical'} for s in S.ORDER}}, open(R.STATUS, 'w'))
        c1 = R.choose(dt.date(2026, 10, 13)); assert c1['chosen_style'] == 'deep' and not c1['displaced'], c1
        # deep slot held (nothing published); next slot (Fri) is melodic but deep is owed
        c2 = R.choose(dt.date(2026, 10, 16))
        assert c2['scheduled_style'] == 'melodic'
        assert c2['chosen_style'] in ('melodic', 'deep') and (c2['owed'] or c2['displaced']), c2
        # publish melodic + verify -> next Tuesday repays deep
        lg = R.ledger(); lg['releases'].append({'release_id': 'x1', 'style': 'melodic', 'platforms': {'youtube': {'status': 'PUBLISHED'}, 'tiktok': {'status': 'PUBLISHED'}}}); R.save(lg)
        c3 = R.choose(dt.date(2026, 10, 20))
        assert c3['owed'].get('deep') or c3['chosen_style'] == 'deep', c3
        json.dump({'styles': {'deep': {'status': 'active-technical'}}}, open(R.STATUS, 'w'))
        c4 = R.choose(dt.date(2026, 10, 23)); assert c4['transitional'], c4
    finally:
        R.LEDGER, R.STATUS = led, st; shutil.rmtree(tmp)


@test('rotation: platform counting uses verified posts only; FAILED is repairable, FAILED_FINAL makes the slot owed')
def _():
    lg = {'releases': [{'release_id': 'a', 'style': 'afro', 'platforms': {'youtube': {'status': 'PUBLISHED'}, 'tiktok': {'status': 'FAILED'}}}]}
    per, dlv, pend = R.delivered(lg, 'afro')
    assert per == {'youtube': 1, 'tiktok': 0} and dlv == 0 and pend == 1, (per, dlv, pend)
    lg['releases'][0]['platforms']['tiktok']['status'] = 'FAILED_FINAL'
    per, dlv, pend = R.delivered(lg, 'afro')
    assert dlv == 0 and pend == 0, (per, dlv, pend)


def simulate(slots, holds=(), active=None, activated=None):
    """Run the rotation for N slots on a temp ledger; returns (choices, max deficit seen, ledger)."""
    tmp = tempfile.mkdtemp(); led, st = R.LEDGER, R.STATUS
    try:
        R.LEDGER = os.path.join(tmp, 'ledger.json'); R.STATUS = os.path.join(tmp, 'status.json')
        json.dump({'styles': {s: dict({'status': 'active-technical'}, **({'activated': activated[s]} if activated and s in activated else {}))
                              for s in (active or S.ORDER)}}, open(R.STATUS, 'w'))
        out, worst = [], 0
        for n in range(slots):
            d = R.START + dt.timedelta(days=7 * (n // 2) + (0 if n % 2 == 0 else 3))
            c = R.choose(d); out.append(c)
            worst = max([worst] + [v['deficit'] for v in c['styles'].values()])
            if n in holds or c['chosen_style'] is None: continue
            lg = R.ledger(); lg['releases'].append({'release_id': f'r{n}', 'style': c['chosen_style'], 'slot_date': str(d),
                                                    'platforms': {p: {'status': 'PUBLISHED'} for p in R.PLATFORMS}}); R.save(lg)
        return out, worst, R.ledger()
    finally:
        R.LEDGER, R.STATUS = led, st; shutil.rmtree(tmp)


@test('rotation debt: repaid in spare slots; never bounced pointlessly when every slot is taken; shortfall reported')
def _():
    out, worst, lg = simulate(72)
    assert worst <= 1 and not any(c['displaced'] for c in out), 'clean run must follow the schedule exactly'
    # all 12 active, one hold: zero-sum -> no pointless displacements, deep reported owed, max deficit 2 (own slot)
    out, worst, lg = simulate(72, holds={0})
    assert worst <= 2 and not any(c['displaced'] for c in out), [c['slot_abs'] for c in out if c['displaced']]
    assert out[-1]['styles']['deep']['deficit'] == 1 and out[-1]['owed'].get('deep') == 1, out[-1]['owed']
    # a style held twice outranks a scheduled style owed once (largest deficit first)
    out, worst, lg = simulate(30, holds={0, 13})
    assert any(c['displaced'] and c['chosen_style'] == 'deep' for c in out), 'deficit-2 style never repaid'
    # transitional: debt is genuinely repaid in a spare slot (scheduled style inactive), no active style displaced
    out, worst, lg = simulate(24, holds={0}, active=['deep', 'melodic', 'house'])
    rep = [c for c in out if c['chosen_style'] == 'deep' and c['scheduled_style'] not in c['active_styles']]
    assert rep, 'owed deep never used a spare slot'
    assert all(c['scheduled_style'] not in c['active_styles'] for c in out if c['displaced']), 'an active style was displaced'
    assert out[-1]['styles']['deep']['deficit'] == 0, out[-1]['styles']['deep']


@test('rotation: late-activated styles are counted from their activation date (no inherited debt)')
def _():
    out, worst, lg = simulate(24, active=['deep', 'melodic', 'afro'], activated={'afro': '2026-10-27'})
    afro = out[-1]['styles']['afro']
    assert afro['deficit'] <= 1 and worst <= 1, (afro, worst)
    assert all(c['transitional'] for c in out)
    held = [c for c in out if c['chosen_style'] is None]
    assert held, 'slots of inactive styles must be held when nobody is owed'


def fake_release(d, name, style='deep', qc_status='pass', man_status='pass', dirty=False):
    base = os.path.join(d, name)
    for ext in ('.mp4', '.mp3', '.m4a', '.delivery.wav', '.json', '.jpg'): open(base + ext, 'wb').write(os.urandom(64))
    json.dump({'status': qc_status}, open(base + '.qc.json', 'w'))
    for ext in ('.meta.json', '.export.json'): json.dump({}, open(base + ext, 'w'))
    files = M.hashed_files(base + '.json', base + '.jpg', base)
    json.dump({'status': man_status, 'style': style, 'engine_version': '3.1.0', 'code_sha256': M.code_sha256(), 'repo_dirty': dirty,
               'files': files, 'sha256': {k: M.sha256(p) for k, p in files.items()}}, open(base + '.manifest.json', 'w'))


@test('release gate NEGATIVE: missing/failed/tampered/inactive inputs -> 0 publishing calls; valid control -> 1')
def _():
    tmp = tempfile.mkdtemp(); st = G.STATUS; calls = []
    def publish_if_allowed(d, n):
        ok, reasons, _ = G.check(d, n)
        if ok: calls.append(n)
        return ok, reasons
    try:
        G.STATUS = os.path.join(tmp, 'status.json')
        json.dump({'styles': {'deep': {'status': 'active-technical'}, 'afro': {'status': 'inactive'}, 'melodic': {'status': 'inactive'}}}, open(G.STATUS, 'w'))
        cases = {}
        os.makedirs(os.path.join(tmp, 'a')); cases['no manifest'] = (os.path.join(tmp, 'a'), 'r1')
        d = os.path.join(tmp, 'b'); os.makedirs(d); fake_release(d, 'r2', qc_status='fail'); cases['QC failed'] = (d, 'r2')
        d = os.path.join(tmp, 'c'); os.makedirs(d); fake_release(d, 'r3'); open(os.path.join(d, 'r3.mp4'), 'ab').write(b'x'); cases['mp4 changed after QC'] = (d, 'r3')
        d = os.path.join(tmp, 'e'); os.makedirs(d); fake_release(d, 'r4', style='afro'); cases['inactive style'] = (d, 'r4')
        d = os.path.join(tmp, 'f'); os.makedirs(d); fake_release(d, 'r5', man_status='fail'); cases['manifest not pass'] = (d, 'r5')
        d = os.path.join(tmp, 'g'); os.makedirs(d); fake_release(d, 'r6'); os.remove(os.path.join(d, 'r6.qc.json')); cases['QC report missing'] = (d, 'r6')
        d = os.path.join(tmp, 'h'); os.makedirs(d); fake_release(d, 'r7'); open(os.path.join(d, 'r7.manifest.json'), 'w').write('{broken'); cases['manifest unreadable'] = (d, 'r7')
        d = os.path.join(tmp, 'i'); os.makedirs(d); fake_release(d, 'r8a'); open(os.path.join(d, 'r8a.m4a'), 'ab').write(b'x'); cases['aac changed'] = (d, 'r8a')
        d = os.path.join(tmp, 'j'); os.makedirs(d); fake_release(d, 'r8b'); open(os.path.join(d, 'r8b.jpg'), 'ab').write(b'x'); cases['photo changed'] = (d, 'r8b')
        d = os.path.join(tmp, 'k'); os.makedirs(d); fake_release(d, 'r8c', dirty=True); cases['built from dirty code'] = (d, 'r8c')
        d = os.path.join(tmp, 'l'); os.makedirs(d); fake_release(d, 'r8d')
        mp = os.path.join(d, 'r8d.manifest.json'); m = json.load(open(mp)); m['code_sha256'] = '0' * 64; json.dump(m, open(mp, 'w')); cases['code changed'] = (d, 'r8d')
        d = os.path.join(tmp, 'm'); os.makedirs(d); fake_release(d, 'r8e', style='chill'); cases['alias of inactive style'] = (d, 'r8e')
        for label, (dd, n) in cases.items():
            ok, reasons = publish_if_allowed(dd, n)
            assert not ok and reasons, f'{label}: gate allowed publishing'
        assert calls == [], f'publishing called for negative cases: {calls}'
        d = os.path.join(tmp, 'ok'); os.makedirs(d); fake_release(d, 'r9')
        ok, why = publish_if_allowed(d, 'r9'); assert ok and calls == ['r9'], f'valid control was refused: {why}'
        r = subprocess.run([sys.executable, os.path.join(HERE, 'release_gate.py'), os.path.join(tmp, 'a'), 'r1'], capture_output=True)
        assert r.returncode == 5, 'CLI exit code not 5 for missing manifest'
    finally:
        G.STATUS = st; shutil.rmtree(tmp)


@test('make.sh parses (bash -n) and the success path reaches the music step with a valid track file')
def _():
    r = subprocess.run(['bash', '-n', os.path.join(ROOT, 'make.sh')], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    tj = json.load(open(os.path.join(ROOT, 'tracks', 'dvg001v2.json')))
    for k in ('title', 'image', 'credit'): assert tj.get(k)
    r = subprocess.run(['bash', os.path.join(ROOT, 'make.sh'), os.path.join('djvelvetgrey', 'tracks', 'dvg001v2.json'), '--check'],
                       capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 0 and 'CHECK OK dvg001v2 style=chill' in r.stdout, (r.stdout, r.stderr[-500:])
    tmpd = tempfile.mkdtemp(dir=os.path.join(ROOT, 'tracks'))
    try:
        tj['brief'].pop('motif'); p = os.path.join(tmpd, 'nomotif_check.json'); json.dump(tj, open(p, 'w'))
        r = subprocess.run(['bash', os.path.join(ROOT, 'make.sh'), p, '--check'], capture_output=True, text=True, cwd=REPO)
        assert r.returncode == 0, ('--check must accept a brief before the hook is chosen', r.stderr[-300:])
        tj['brief']['lead'] = 'banjo'; json.dump(tj, open(p, 'w'))
        r = subprocess.run(['bash', os.path.join(ROOT, 'make.sh'), p, '--check'], capture_output=True, text=True, cwd=REPO)
        assert r.returncode != 0, '--check accepted an off-profile brief'
    finally:
        shutil.rmtree(tmpd)


@test('make.sh NEGATIVE: invalid JSON, legacy engine, missing motif, missing photo -> non-zero exit and no manifest')
def _():
    tmp = tempfile.mkdtemp(dir=os.path.join(ROOT, 'tracks'))
    try:
        cases = {'invalid.json': '{not json', 'legacy.json': json.dumps({'title': 'X', 'image': 'x.jpg', 'credit': 'c', 'engine': 'v1', 'brief': {}}),
                 'nomotif.json': json.dumps({'title': 'X', 'image': 'x.jpg', 'credit': 'c', 'engine': 'v2', 'brief': {'style': 'deep'}}),
                 'nophoto.json': json.dumps({'title': 'X', 'image': '/nonexistent.jpg', 'credit': 'c', 'engine': 'v2',
                                             'brief': {'style': 'deep', 'motif': {'cell': 'lilt', 'contour': 'arch', 'start': 69}}})}
        for fn, body in cases.items():
            p = os.path.join(tmp, fn); open(p, 'w').write(body)
            r = subprocess.run(['bash', os.path.join(ROOT, 'make.sh'), p], capture_output=True, text=True, cwd=REPO)
            assert r.returncode != 0, f'{fn}: make.sh exited 0'
            assert not os.path.exists(os.path.join(REPO, 'out', fn[:-5] + '.manifest.json')), f'{fn}: manifest written'
    finally:
        shutil.rmtree(tmp)


@test('qc.py NEGATIVE: a broken 30 s file exits 2 (blocking) and a missing file exits 4')
def _():
    tmp = tempfile.mkdtemp()
    try:
        x = (np.sin(2 * np.pi * 440 * np.arange(30 * 44100) / 44100) * 0.99)
        wavfile.write(os.path.join(tmp, 'b.wav'), 44100, (np.stack([x, x], 1) * 32767).astype(np.int16))
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.join(tmp, 'b.wav'), os.path.join(tmp, 'b.mp3')], check=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=black:s=64x64:d=30', '-i', os.path.join(tmp, 'b.wav'),
                        '-shortest', '-c:a', 'aac', os.path.join(tmp, 'b.mp4')], check=True)
        json.dump({'bpm': 120, 'target_lufs': -10, 'outro_start_s': 20}, open(os.path.join(tmp, 'b.meta.json'), 'w'))
        args = lambda w: [sys.executable, os.path.join(HERE, 'qc.py'), '--wav', w, '--mp3', os.path.join(tmp, 'b.mp3'),
                          '--mp4', os.path.join(tmp, 'b.mp4'), '--meta', os.path.join(tmp, 'b.meta.json')]
        r = subprocess.run(args(os.path.join(tmp, 'b.wav')), capture_output=True, text=True)
        assert r.returncode == 2, f'broken file exit {r.returncode}'
        cats = {f['category'] for f in json.loads(r.stdout)['failures']}
        assert 'structure' in cats and 'master' in cats, cats
        r = subprocess.run(args(os.path.join(tmp, 'missing.wav')), capture_output=True, text=True)
        assert r.returncode == 4, f'missing file exit {r.returncode}'
    finally:
        shutil.rmtree(tmp)


@test('harmony: strong hook notes are chord tones of the chord the engine plays (hr=1 and hr=2 styles)')
def _():
    import engine as E
    for st in S.ORDER:
        P = S.STYLES[st]
        for prog in P['progressions']:
            b = {'style': st, 'tonic': 57, 'progression': prog, 'mode': C.best_mode(prog, P['modes']), 'seed': 5, 'bpm': P['bpm'][0],
                 'arc': P['arcs'][0], 'lead': P['leads'][0], 'groove': {'bass_a': P['bass_a'][0]}}
            for cell in (P['cells'] or list(C.RHYTHM_CELLS))[:3]:
                h, hook = C.hook_from_spec(b, {'cell': cell, 'contour': 'arch', 'start': 69})
                assert h.hr == P['harm_rhythm']
                tr = E.TrackV2(b, {'cell': cell, 'contour': 'arch', 'start': 69}); tr.anchor = 40
                for part in ('lead', 'answer'):
                    for i, (s0, d, m) in enumerate(hook[part]):
                        strong = d >= .75 or abs(s0 % 4) < 1e-6
                        if not strong: continue
                        ci = tr.ci(40 + int(s0 // 4))          # engine chord in a hook starting at section bar 40
                        assert m % 12 in h.pcs[ci], (st, prog, cell, part, s0, m, ci)


def layers(style, template, bpm=None):
    import engine as E
    P = S.STYLES[style]
    b = {'style': style, 'tonic': 57, 'progression': P['progressions'][0], 'mode': C.best_mode(P['progressions'][0], P['modes']),
         'seed': 11, 'bpm': bpm or P['bpm'][0], 'arc': P['arcs'][0], 'lead': P['leads'][0], 'answer': P['answers'][0],
         'groove': {'bass_a': P['bass_a'][0], 'bass_b': P['bass_b'][0]}}
    class T(E.TrackV2):
        def mix(self, L, kick_t, comp_env): return L
    tr = T(b, {'cell': (P['cells'] or ['lilt'])[0], 'contour': 'arch', 'start': 69}, template=template)
    return tr, tr.render()


@test('focal fallback: bass-focal and rhythm-focal styles have no silent bass/comp bars inside hooks and drops')
def _():
    for st, layer in (('nudisco', 'bass'), ('tech', 'bass'), ('house', 'comp'), ('french', 'comp')):
        tr, L = layers(st, [('hook', 8), ('drop1', 8)])
        n = int(tr.bar * C.np.float64(1) * 44100) if False else int(round(tr.bar * 44100))
        rms = [float(np.sqrt((L[layer][i * n:(i + 1) * n] ** 2).mean())) for i in range(16)]
        assert min(rms) > 0.02 * max(rms), (st, layer, [round(r, 4) for r in rms])


@test('no silent bars: every style sounds in every intro and breakdown bar (pad-less styles included)')
def _():
    for st in S.ORDER:
        tr, L = layers(st, [('intro', 4), ('hook', 8), ('break', 4), ('build', 4)])
        tot = sum(v for v in L.values()); n = int(round(tr.bar * 44100))
        rms = [float(np.sqrt((tot[i * n:(i + 1) * n] ** 2).mean())) for i in range(20)]
        assert min(rms) > 1e-3 * max(rms), (st, [round(r, 5) for r in rms])


@test('pads and drop-2 organ never sustain across a chord change (afro hr=2, house organ layer)')
def _():
    import engine as E
    calls = []
    orig = E.I.pad_chord
    def spy(notes, dur, cut, seed=0): calls.append(dur); return orig(notes, dur, cut, seed)
    E.I.pad_chord = spy
    try:
        tr, _ = layers('afro', [('intro', 4), ('hook', 9)])
    finally:
        E.I.pad_chord = orig
    assert calls and max(calls) <= tr.bar * tr.hr + 1e-6, calls
    assert abs(sum(calls) - 13 * tr.bar) < 1e-3, (sum(calls), 13 * tr.bar)     # pads tile the sections exactly


@test('unknown instruments and off-profile briefs are refused (no silent flute substitute)')
def _():
    import instruments as I, make_track as MT
    try: I.note('banjo', 60, .5); raise AssertionError('unknown instrument accepted')
    except ValueError: pass
    P = S.STYLES['deep']
    b = {'lead': 'brass', 'answer': 'flute', 'groove': {'bass_a': 'rolling'}, 'arc': 'classic', 'mode': 'minor', 'progression': P['progressions'][0]}
    assert any('lead' in e for e in MT.validate(b, P))
    b['lead'] = 'rhodes'; assert MT.validate(b, P) == []


@test('near-twin styles differ in drums, comping and bass (melodic/progressive, house/vocal, nudisco/disco)')
def _():
    for a, b in (('melodic', 'progressive'), ('house', 'vocal'), ('nudisco', 'disco')):
        A, B = S.STYLES[a], S.STYLES[b]
        diff = [k for k in ('kick', 'hats', 'perc', 'comp', 'comp_inst', 'pad', 'backbeat', 'focal', 'harm_rhythm') if A[k] != B[k]]
        assert len(diff) >= 4, (a, b, diff)
        assert set(A['bass_a']) != set(B['bass_a']), (a, b)


@test('qc.py detects a real click (single discontinuity) in an otherwise repeating track')
def _():
    tmp = tempfile.mkdtemp()
    try:
        sr, bpm = 44100, 120; t = np.arange(int(179 * sr)) / sr; beat = 60 / bpm
        ph = (t % beat); x = 0.3 * np.sin(2 * np.pi * 55 * t) * np.exp(-ph * 6) + 0.1 * np.sin(2 * np.pi * 330 * t)
        i0 = int(90.3 * sr); x[i0:i0 + 3] += 0.5           # a 3-sample spike = a click at 90.3 s (off the grid)
        i1 = int(120.0 * sr) + 20; x[i1:i1 + 3] -= 0.5     # and one right on a beat onset (120.0 s)
        y = np.stack([x, x * .98], 1)
        wavfile.write(os.path.join(tmp, 'c.wav'), sr, (y * 32767).astype(np.int16))
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.join(tmp, 'c.wav'), '-b:a', '320k', os.path.join(tmp, 'c.mp3')], check=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=black:s=64x64:d=179', '-i', os.path.join(tmp, 'c.wav'),
                        '-shortest', '-c:a', 'aac', os.path.join(tmp, 'c.mp4')], check=True)
        json.dump({'bpm': bpm, 'target_lufs': -14, 'outro_start_s': 150}, open(os.path.join(tmp, 'c.meta.json'), 'w'))
        r = subprocess.run([sys.executable, os.path.join(HERE, 'qc.py'), '--wav', os.path.join(tmp, 'c.wav'), '--mp3', os.path.join(tmp, 'c.mp3'),
                            '--mp4', os.path.join(tmp, 'c.mp4'), '--meta', os.path.join(tmp, 'c.meta.json')], capture_output=True, text=True)
        rep = json.loads(r.stdout)
        assert any(abs(c - 90.3) < .05 for c in rep['click_suspects']), rep['click_suspects']
        assert any(abs(c - 120.0) < .05 for c in rep['click_suspects']), ('on-grid click missed', rep['click_suspects'])
    finally:
        shutil.rmtree(tmp)


if __name__ == '__main__':
    for n, s_, msg in results: print(f'{s_:5s} {n}' + (f'\n      -> {msg}' if msg else ''))
    bad = [r for r in results if r[1] != 'PASS']
    print(f'\n{len(results) - len(bad)}/{len(results)} passed')
    sys.exit(1 if bad else 0)
