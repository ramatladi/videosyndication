"""Offline test for yt_publish.py: fake Google API + fake media branch (local bare repo). Run:
    python3 skincare-daily/test_yt_publish.py
"""
import datetime as dt, hashlib, http.server, json, os, subprocess, sys, tempfile, threading

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = {'videos': {}, 'uploads': 0, 'thumbs': 0, 'captions': 0, 'existing': {}}
CH = {'ROSEBANK': 'UCrosebank000000000000000', 'MIDRAND': 'UCmidrand0000000000000000'}
MP4 = b'\x00\x00\x00\x18ftypmp42' + b'\x00' * 20000
JPG = b'\xff\xd8' + b'j' * 100
SRT = b'1\n00:00:00,000 --> 00:00:01,000\nhi\n'


class Fake(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, code, obj, headers=None):
        b = json.dumps(obj).encode()
        self.send_response(code)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)

    def _who(self):
        return self.headers.get('Authorization', '').split('tok-')[-1]

    def do_GET(self):
        p, _, q = self.path.partition('?')
        q = dict(x.split('=', 1) for x in q.split('&') if x)
        if p.startswith('/files/'):
            body = {'v.mp4': MP4, 't.jpg': JPG, 'c.srt': SRT}[p[7:]]
            self.send_response(200); self.send_header('Content-Length', str(len(body))); self.end_headers()
            self.wfile.write(body); return
        who = self._who()
        if p == '/youtube/v3/channels':
            return self._json(200, {'items': [{'id': CH[who], 'contentDetails': {'relatedPlaylists': {'uploads': 'UU' + who}}}]})
        if p == '/youtube/v3/playlistItems':
            items = [{'snippet': {'title': t, 'resourceId': {'videoId': v}}} for v, t in STATE['existing'].get(who, {}).items()]
            items += [{'snippet': {'title': x['title'], 'resourceId': {'videoId': v}}} for v, x in STATE['videos'].items() if x['who'] == who]
            return self._json(200, {'items': items})
        if p == '/youtube/v3/videos':
            out = []
            for v in q['id'].split('%2C'):
                x = STATE['videos'].get(v)
                if x:
                    out.append({'id': v, 'snippet': {'channelId': CH[x['who']], 'tags': x['tags']},
                                'status': {'uploadStatus': 'processed', **x['status']}})
            return self._json(200, {'items': out})
        self._json(404, {'error': 'x'})

    def do_POST(self):
        n = int(self.headers.get('Content-Length', 0)); body = self.rfile.read(n)
        p = self.path.split('?')[0]
        if p == '/token':
            rt = dict(x.split('=') for x in body.decode().split('&'))['refresh_token']
            return self._json(200, {'access_token': 'ya29.tok-' + rt})
        if p == '/upload/youtube/v3/videos':
            meta = json.loads(body); sid = 'S%d' % len(STATE['videos'])
            STATE.setdefault('sessions', {})[sid] = (self._who(), meta)
            return self._json(200, {}, {'Location': f'http://127.0.0.1:{PORT}/session/{sid}'})
        if p == '/upload/youtube/v3/thumbnails/set':
            STATE['thumbs'] += 1; return self._json(200, {})
        if p == '/upload/youtube/v3/captions':
            STATE['captions'] += 1; return self._json(200, {})
        self._json(404, {'error': 'x'})

    def do_PUT(self):
        n = int(self.headers.get('Content-Length', 0)); self.rfile.read(n)
        sid = self.path.rsplit('/', 1)[-1]; who, meta = STATE['sessions'][sid]
        vid = 'vid%d' % len(STATE['videos']); STATE['uploads'] += 1
        STATE['videos'][vid] = {'who': who, 'title': meta['snippet']['title'], 'tags': meta['snippet']['tags'],
                                'status': {k: meta['status'][k] for k in ('privacyStatus', 'publishAt') if k in meta['status']}}
        self._json(200, {'id': vid})


def sh(*a, cwd=None):
    subprocess.run(a, cwd=cwd, check=True, capture_output=True)


def main():
    global PORT
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Fake); PORT = srv.server_port
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{PORT}'
    tmp = tempfile.mkdtemp()
    remote, media = os.path.join(tmp, 'remote.git'), os.path.join(tmp, 'media')
    sh('git', 'init', '-q', '--bare', remote)
    sh('git', 'init', '-q', '-b', 'media', media)
    sh('git', 'config', 'user.email', 't@t', cwd=media); sh('git', 'config', 'user.name', 't', cwd=media)
    sh('git', 'remote', 'add', 'origin', remote, cwd=media)
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=2)))
    day = now.strftime('%Y-%m-%d')
    past = (now - dt.timedelta(hours=3)).strftime('%Y-%m-%d %H:%M')
    past2 = (now - dt.timedelta(hours=2)).strftime('%Y-%m-%d %H:%M')
    future = (now + dt.timedelta(hours=5)).strftime('%Y-%m-%d %H:%M')
    sha = lambda b: hashlib.sha256(b).hexdigest()

    def item(handle, slot, slug, title, fmt='short'):
        return {'handle': handle, 'slot_sast': slot, 'format': fmt, 'slug': slug, 'title': title, 'status': 'ready',
                'description': 'desc', 'tags': ['a', 'b'], 'paid_promotion': True, 'made_for_kids': False,
                'altered_or_synthetic_content': False, 'media_url': base + '/files/v.mp4', 'sha256': sha(MP4),
                'thumbnail_url': base + '/files/t.jpg', 'thumbnail_sha256': sha(JPG),
                'captions_url': base + '/files/c.srt', 'captions_sha256': sha(SRT)}
    items = [item('@SkincareJoburgRosebank', past, 'r1', 'Rosebank one #shorts'),
             item('@SkincareJoburgRosebank', past2, 'r2', 'Rosebank two #shorts'),
             item('@SkincareJoburgRosebank', future, 'r3', 'Rosebank three', 'regular'),
             item('@DermatologistJoburgMidrand', past, 'm1', 'Midrand already posted #shorts'),
             item('@DermatologyCapeTown', future, 'c1', 'Cape Town not signed in')]
    d = os.path.join(media, 'skincare-daily', day); os.makedirs(d)
    json.dump({'items': items}, open(os.path.join(d, 'manifest.json'), 'w'))
    json.dump({'items': [{'manifest_slug': i['slug'], 'status': 'staged_awaiting_youtube_receipt', 'youtube_id': None}
                         for i in items]}, open(os.path.join(d, 'receipt-ledger.json'), 'w'))
    sh('git', 'add', '.', cwd=media); sh('git', 'commit', '-q', '-m', 'seed', cwd=media)
    sh('git', 'push', '-q', 'origin', 'media', cwd=media)
    STATE['existing']['MIDRAND'] = {'oldvid': 'Midrand already posted #shorts'}

    env = dict(os.environ, YT_TEST_MODE='1', YT_TOKEN_URL=base + '/token', YT_API_BASE=base,
               YT_SK_CLIENT_ID='cid', YT_SK_CLIENT_SECRET='GOCSPX-secret',
               YT_SK_REFRESH_ROSEBANK='ROSEBANK', YT_SK_CHANNEL_ROSEBANK=CH['ROSEBANK'],
               YT_SK_REFRESH_MIDRAND='MIDRAND', YT_SK_CHANNEL_MIDRAND=CH['MIDRAND'], RUNNER_TEMP=tmp, YT_SK_CAPTIONS='1')
    cmd = [sys.executable, os.path.join(HERE, 'yt_publish.py'), media, '--since', day]
    out = subprocess.run(cmd, env=env, capture_output=True, text=True)
    print(out.stdout, out.stderr)
    assert out.returncode == 0, 'run failed'
    L = {r['manifest_slug']: r for r in json.load(open(os.path.join(d, 'receipt-ledger.json')))['items']}
    assert STATE['uploads'] == 3, STATE['uploads']
    assert L['m1']['youtube_id'] == 'oldvid' and L['m1']['status'] == 'youtube_adopted'
    assert L['c1']['youtube_id'] is None
    v = {x['title']: x['status'] for x in STATE['videos'].values()}
    assert v['Rosebank one #shorts'] == {'privacyStatus': 'public'}, v                       # overdue: now
    assert v['Rosebank two #shorts']['privacyStatus'] == 'private' and v['Rosebank two #shorts']['publishAt']  # +1h
    exp = dt.datetime.strptime(future, '%Y-%m-%d %H:%M').replace(tzinfo=dt.timezone(dt.timedelta(hours=2)))
    assert v['Rosebank three']['publishAt'] == exp.astimezone(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    assert L['r3']['status'] == 'youtube_scheduled' and L['r1']['status'] == 'youtube_published'
    assert STATE['thumbs'] == 3 and STATE['captions'] == 3
    # Origin holds the ledger; no secret leaked into any committed file.
    sh('git', 'fetch', '-q', 'origin', cwd=media)
    blob = subprocess.run(['git', 'log', '-p', 'origin/media'], cwd=media, capture_output=True, text=True).stdout
    assert 'oldvid' in blob and 'GOCSPX' not in blob and 'ya29' not in blob
    # Second run: nothing new.
    out2 = subprocess.run(cmd, env=env, capture_output=True, text=True)
    assert out2.returncode == 0 and STATE['uploads'] == 3, out2.stdout
    print('ALL TESTS PASSED')


if __name__ == '__main__':
    main()
