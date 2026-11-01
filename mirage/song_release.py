"""Mirage release from a hand-written song spec (replaces make_release.py plan/build since 26 Oct 2026).

    python3 mirage/song_release.py next                      -> next release id (mtrNNN), the style + artist this slot should use
    python3 mirage/song_release.py check  --spec mirage/songs/mtrNNN.json
    python3 mirage/song_release.py build  --spec mirage/songs/mtrNNN.json --format video|short --photo out/mtrNNN.jpg \
            --photographer "Name" --photo-page URL [--photo-kind bikini|fashion|nature]
    python3 mirage/song_release.py record --spec mirage/songs/mtrNNN.json --date YYYY-MM-DD --slot YYYY-MM-DDTHH:MM \
            --format video|short --uuid UUID --media URL [--photo-kind ...] [--replaces mtrXXX]

build = lint + uniqueness (song.py) -> render on real recordings -> export (codec-safe peaks) -> blocking QC ->
video with the act's name on the brand pill -> machine ears (informational).
"""
import argparse, re, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
V2 = os.path.join(REPO, 'djvelvetgrey', 'v2'); OUT = os.path.join(REPO, 'out'); LEDGER = os.path.join(HERE, 'ledger.json')
sys.path.insert(0, os.path.join(HERE, 'loopkit'))
ROSTER = json.load(open(os.path.join(HERE, 'artists.json')))['roster']   # style -> [acts]; 1000 fictional acts (Sello, 1 Nov 2026)


def pick_act(style, releases):
    """Rotate the style's roster: the act (not retired) with the fewest releases; roster order breaks ties."""
    used = {}
    for r in releases: used[r.get('artist')] = used.get(r.get('artist'), 0) + 1
    acts = [a for a in ROSTER[style] if not a.get('retired')]
    return min(acts, key=lambda a: (used.get(a['name'], 0), ROSTER[style].index(a)))
# 24-slot style rotation (deep/melodic most often: they are most of Sello's library), no style twice in a row
CYCLE = ['deep', 'melodic', 'progressive', 'afro', 'house', 'tropical', 'deep', 'nudisco', 'melodic', 'soulful', 'progressive', 'indiedance',
         'deep', 'french', 'melodic', 'trance', 'afro', 'disco', 'deep', 'futurebass', 'melodic', 'tech', 'house', 'vocal']
KEYNAME = {'C': 'C', 'C#': 'C#', 'Db': 'Db', 'D': 'D', 'D#': 'D#', 'Eb': 'Eb', 'E': 'E', 'F': 'F', 'F#': 'F#', 'Gb': 'Gb', 'G': 'G',
           'G#': 'G#', 'Ab': 'Ab', 'A': 'A', 'A#': 'A#', 'Bb': 'Bb', 'B': 'B'}


def ledger(): return json.load(open(LEDGER))


def key_text(k): return (k[:-1] + ' minor') if k.endswith('m') else (k + ' major')


def slot_source(slot):
    """'mureka' if the slot (YYYY-MM-DDTHH:MM, SAST) is one of the weekly Creative Claw Mureka slots, else 'hand'."""
    import datetime as dt
    if not slot: return None
    cfg = json.load(open(os.path.join(HERE, 'mureka_slots.json')))
    d = dt.datetime.strptime(slot[:16], '%Y-%m-%dT%H:%M')
    for w in cfg['weekly']:
        if d.strftime('%a') == w['weekday'] and d.strftime('%H:%M') == w['time']:
            return {'source': 'mureka', 'model': cfg['model'], 'credits': cfg['credits_per_song'], 'vocals': cfg['vocals'], 'format': w['format']}
    return {'source': 'hand'} if cfg.get('hand_written', True) else {'source': 'none', 'why': 'no upload in this slot (Creative Claw only, one a day)'}


def nxt(slot=None):
    L = ledger()['releases']
    n = max(int(r['release'][3:]) for r in L) + 1
    hand = [r for r in L if r.get('written_by_hand') or r.get('generated')]   # rotation counts hand-written and Creative Claw releases
    style = CYCLE[len(hand) % len(CYCLE)]
    if hand and hand[-1]['style'] == style: style = CYCLE[(len(hand) + 1) % len(CYCLE)]
    act = pick_act(style, L)
    print(json.dumps({'release': f'mtr{n:03d}', 'style': style, 'artist': act['name'], 'artist_line': act['line'],
                      'artist_kind': act['kind'], 'artist_gender': act['gender'], 'artist_heritage': act['heritage'],
                      'slot': slot, 'make': slot_source(slot),
                      'recent': [(r['release'], r['style'], r.get('key'), r.get('bpm'), r['title']) for r in hand[-8:]]}, indent=1))


GEN_FIELDS = ['id', 'title', 'artist', 'style', 'source']


def lint(spec):
    if spec.get('source'):                      # a Creative Claw track (Sello approved Creative Claw, 1 Nov 2026)
        err, warn = [f'missing {k}' for k in GEN_FIELDS if not spec.get(k)], []
        src = spec.get('source') or {}
        for k in ('generator', 'model', 'job_id', 'audio_url', 'prompt'):
            if not src.get(k): err.append(f'source.{k} missing')
        if not str(src.get('audio_url', '')).startswith('https://cdn.creativeclaw.co/'): err.append('source.audio_url must be the completed Creative Claw CDN URL')
        if spec.get('vocals') and not src.get('lyrics'): err.append('a vocal song needs the lyrics it was sung from in source.lyrics')
        if re.search(r'\bA\.?I\.?\b|artificial intelligence', spec['title'] + ' ' + str(src.get('lyrics', '')), re.I): err.append('title/lyrics mention AI')
    else:
        import song as G
        err, warn = G.check(spec); err += G.unique(spec)
    names = {a['name'] for a in ROSTER[spec['style']] if not a.get('retired')}
    if spec['artist'] not in names: err.append(f"artist {spec['artist']!r} is not an active act in the {spec['style']} roster (mirage/artists.json)")
    if any(r['title'].lower() == spec['title'].lower() for r in ledger()['releases'] if r['release'] != spec['id']): err.append('title already in the ledger')
    return err, warn


def build(a):
    spec = json.load(open(a.spec)); rid = spec['id']; os.makedirs(OUT, exist_ok=True); base = os.path.join(OUT, rid)
    err, warn = lint(spec)
    for w in warn: print('warning:', w)
    if err: print('REFUSED:', *err, sep='\n - '); sys.exit(2)
    if spec.get('source'):
        src = base + '.gen.mp3'
        subprocess.run(['curl', '-sSLf', '-o', src, spec['source']['audio_url']], check=True)
        r = subprocess.run([sys.executable, os.path.join(HERE, 'gen_master.py'), src, base + '.master.wav', base + '.meta.json', '--style', spec['style']],
                           capture_output=True, text=True)
        if r.returncode: raise SystemExit((r.stdout + r.stderr).strip()[-400:])
        meta = json.load(open(base + '.meta.json'))
        spec['bpm'], spec['key'] = meta['bpm'], meta['key_measured']        # the description states what the audio measures
        json.dump(spec, open(a.spec, 'w'), indent=1, ensure_ascii=False)
    else:
        import song as G
        meta = G.render(spec, base + '.master.wav')
        meta['sections'] = [{'name': s['section'], 'bars': s['bars']} for s in meta['sections']]
        bar = 240 / spec['bpm']; meta['outro_start_s'] = None; t = 0
        for s in meta['sections']:
            if s['name'] == 'outro': meta['outro_start_s'] = t * bar
            t += s['bars']
        json.dump(meta, open(base + '.meta.json', 'w'), indent=1, default=str)
    def export(src):
        subprocess.run([sys.executable, os.path.join(V2, 'export.py'), src, OUT, rid, '--title', spec['title'], '--artist', spec['artist']], check=True, capture_output=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=black:s=64x64:r=1', '-i', base + '.m4a', '-map', '0:v', '-map', '1:a',
                        '-c:v', 'libx264', '-c:a', 'copy', '-shortest', base + '.qc.mp4'], check=True)
        return subprocess.run([sys.executable, os.path.join(V2, 'qc.py'), '--wav', base + '.delivery.wav', '--mp3', base + '.mp3', '--mp4', base + '.qc.mp4',
                               '--meta', base + '.meta.json', '--out', base + '.qc.json'], capture_output=True).returncode
    rc = export(base + '.master.wav')
    q = json.load(open(base + '.qc.json'))
    if rc != 0: raise SystemExit(f"QC failed: {[f['check'] for f in q.get('failures', [])]}")
    vs = 'video_short.py' if a.format == 'short' else 'video.py'
    subprocess.run([sys.executable, os.path.join(HERE, vs), '--image', a.photo, '--audio', base + '.delivery.wav', '--aac', base + '.m4a',
                    '--title', spec['title'], '--style', spec['style'], '--credit', '-', '--artist', spec['artist'], '--out', base + '.mp4']
                   + (['--vocals'] if spec.get('vocals') else []), check=True)
    p = {'release': rid, 'title': spec['title'], 'artist': spec['artist'], 'style': spec['style'], 'key': spec['key'], 'bpm': spec['bpm'],
         'photographer': a.photographer, 'photo_page': a.photo_page, 'photo_kind': a.photo_kind, 'format': a.format, 'qc': q['status'],
         'lufs': q['files']['wav']['integrated_lufs'], 'reference': spec.get('reference'),
         'source': spec.get('source'), 'vocals': bool(spec.get('vocals'))}
    try:
        sys.path.insert(0, V2); import ears; ears.ensure_deps()
        r = subprocess.run([sys.executable, os.path.join(V2, 'ears.py'), base + '.mp3'], capture_output=True, text=True, timeout=600)
        p['ears'] = json.loads([l for l in r.stdout.splitlines() if l.startswith('{')][-1])
    except Exception as e:
        p['ears'] = {'error': str(e)[:200]}
    json.dump(p, open(base + '.plan.json', 'w'), indent=1)
    print(json.dumps({'release': rid, 'title': spec['title'], 'artist': spec['artist'], 'qc': q['status'], 'lufs': p['lufs'], 'mp4': base + '.mp4',
                      'key_text': key_text(spec['key']), 'bpm': spec['bpm'], 'vocals': bool(spec.get('vocals')),
                      'house': p['ears'].get('house')}))


def record(a):
    spec = json.load(open(a.spec)); rid = spec['id']; p = json.load(open(os.path.join(OUT, rid + '.plan.json'))); L = ledger()
    if any(x['release'] == rid for x in L['releases']): raise SystemExit('already recorded')
    L['releases'].append({'release': rid, 'date': a.date, 'slot': a.slot, 'format': a.format, 'title': spec['title'], 'artist': spec['artist'],
                          'style': spec['style'], 'key': key_text(spec['key']), 'bpm': spec['bpm'], 'written_by_hand': not spec.get('source'),
                          'generated': ({k: spec['source'][k] for k in ('generator', 'model', 'job_id', 'audio_url')} if spec.get('source') else None),
                          'vocals': bool(spec.get('vocals')),
                          'spec': f'mirage/songs/{rid}.json', 'photographer': p['photographer'], 'photo_page': p['photo_page'],
                          'photo_kind': a.photo_kind or p.get('photo_kind') or 'bikini', 'metricool_uuid': a.uuid, 'media_url': a.media,
                          'reference': spec.get('reference'), 'ears': p.get('ears')})
    if a.replaces:
        for r in L['releases']:
            if r['release'] == a.replaces: r['replaced_by'] = rid; r['status'] = 'replaced before publishing (old engine)'
    json.dump(L, open(LEDGER, 'w'), indent=1)
    print('recorded', rid)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd', choices=['next', 'check', 'build', 'record'])
    for k in ('spec', 'photo', 'photographer', 'photo-page', 'date', 'slot', 'uuid', 'media', 'replaces'): ap.add_argument('--' + k)
    ap.add_argument('--format', choices=['video', 'short'], default='video')
    ap.add_argument('--photo-kind', choices=['bikini', 'fashion', 'nature'], default=None)
    a = ap.parse_args()
    if a.cmd == 'next': nxt(a.slot)
    elif a.cmd == 'check':
        e, w = lint(json.load(open(a.spec))); [print('warning:', x) for x in w]
        if e: print('REFUSED:', *e, sep='\n - '); sys.exit(2)
        print('check ok')
    elif a.cmd == 'build': a.photo_kind = a.photo_kind or 'bikini'; build(a)
    else: record(a)
