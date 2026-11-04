"""Offline tests for acnemedicine/upload.py against a fake Google API (no network, no real credentials).

    python3 acnemedicine/test_upload.py
"""
import http.server, json, os, shutil, subprocess, sys, tempfile, threading, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
CH = open(os.path.join(HERE, 'CHANNEL_ID')).read().strip()
STATE = {}


class Fake(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj=None, headers=None, raw=None):
        body = raw if raw is not None else (json.dumps(obj).encode() if obj is not None else b'')
        self.send_response(code)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query)
        auth = self.headers.get('Authorization', '')
        if u.path == '/media/v.mp4':
            return self._send(200, raw=STATE['mp4'])
        if auth != 'Bearer AT':
            return self._send(401, {'error': 'bad token'})
        if u.path == '/youtube/v3/channels':
            return self._send(200, {'items': [{'id': STATE['channel'], 'snippet': {'title': 'Acne Medicine Johannesburg'}}]})
        if u.path == '/youtube/v3/videos':
            v = STATE.get('video')
            items = [v] if v and q.get('id', [''])[0] == v['id'] else []
            return self._send(200, {'items': items})
        self._send(404, {})

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        n = int(self.headers.get('Content-Length', 0)); body = self.rfile.read(n)
        if u.path == '/token':
            f = urllib.parse.parse_qs(body.decode())
            ok = f.get('refresh_token') == ['RT'] and f.get('client_secret') == ['CS']
            return self._send(200 if ok else 400, {'access_token': 'AT'} if ok else {'error': 'invalid_grant'})
        if u.path == '/upload/youtube/v3/videos':
            STATE['meta'] = json.loads(body); STATE['size'] = int(self.headers['X-Upload-Content-Length'])
            STATE['got'] = b''
            return self._send(200, headers={'Location': f'http://127.0.0.1:{STATE["port"]}/session/1'})
        self._send(404, {})

    def do_PUT(self):
        n = int(self.headers.get('Content-Length', 0)); STATE['got'] += self.rfile.read(n)
        if len(STATE['got']) < STATE['size']:
            return self._send(308, headers={'Range': f'bytes=0-{len(STATE["got"]) - 1}'})
        st = dict(STATE['meta']['status'])
        priv = STATE.get('force_privacy') or st['privacyStatus']
        STATE['video'] = {'id': 'VID123', 'snippet': {'channelId': STATE['channel']},
                          'status': {'uploadStatus': 'processed', 'privacyStatus': priv, 'publishAt': st.get('publishAt')}}
        self._send(200, {'id': 'VID123'})


def run(env_extra, item, mp4=None, channel=CH, force_privacy=None, pre_result=None):
    STATE.clear(); STATE.update(channel=channel, force_privacy=force_privacy, port=PORT,
                                mp4=mp4 if mp4 is not None else MP4)
    d = tempfile.mkdtemp(); os.makedirs(f'{d}/queue'); os.makedirs(f'{d}/results')
    item = {'id': 'amj001', 'title': 'Test review', 'description': 'desc',
            'media_url': f'http://127.0.0.1:{PORT}/media/v.mp4', **item}
    json.dump(item, open(f'{d}/queue/amj001.json', 'w'))
    if pre_result:
        json.dump(pre_result, open(f'{d}/results/amj001.json', 'w'))
    env = {**os.environ, 'YT_TOKEN_URL': f'http://127.0.0.1:{PORT}/token', 'YT_API_BASE': f'http://127.0.0.1:{PORT}',
           'YT_ACNE_CLIENT_ID': 'CID', 'YT_ACNE_CLIENT_SECRET': 'CS', 'YT_ACNE_REFRESH_TOKEN': 'RT', **env_extra}
    env = {k: v for k, v in env.items() if v is not None}
    p = subprocess.run([sys.executable, os.path.join(HERE, 'upload.py'), f'{d}/queue/amj001.json'],
                       capture_output=True, text=True, env=env, timeout=120)
    res = json.load(open(f'{d}/results/amj001.json'))
    shutil.rmtree(d)
    return p, res


def main():
    global PORT, MP4
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Fake); PORT = srv.server_port
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    td = tempfile.mkdtemp()
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-f', 'lavfi', '-i', 'testsrc=size=320x240:rate=25', '-t', '20',
                    '-pix_fmt', 'yuv420p', f'{td}/t.mp4'], check=True)
    MP4 = open(f'{td}/t.mp4', 'rb').read()
    # make the file span several 8 MB chunks to exercise resumable 308 handling
    MP4 = MP4 + b'\0' * (17 * 1024 * 1024)
    fails = 0

    def check(name, cond, p=None, res=None):
        nonlocal fails
        print(('PASS ' if cond else 'FAIL ') + name)
        if not cond:
            fails += 1; print(p.stdout[-800:] if p else '', p.stderr[-800:] if p else '', res)

    p, r = run({}, {'privacy': 'public', 'tags': ['skincare'], 'short': True})
    check('happy path uploads, verifies channel and privacy', p.returncode == 0 and r['status'] == 'UPLOADED'
          and r['video_id'] == 'VID123' and r['verified']['privacyStatus'] == 'public'
          and r['url'].endswith('/shorts/VID123') and STATE['got'] == MP4, p, r)
    check('metadata: no synthetic label, not for kids, Howto & Style',
          STATE['meta']['status']['containsSyntheticMedia'] is False
          and STATE['meta']['status']['selfDeclaredMadeForKids'] is False and STATE['meta']['snippet']['categoryId'] == '26')
    check('no secret appears in output or result', all(s not in p.stdout + p.stderr + json.dumps(r) for s in ('CS', 'RT', 'Bearer AT')))

    p, r = run({}, {}, channel='UCsomeOtherChannel000000')
    check('wrong channel is refused before any upload', p.returncode == 1 and 'refusing' in r['error'] and 'meta' not in STATE, p, r)

    p, r = run({'YT_ACNE_REFRESH_TOKEN': None}, {})
    check('missing secret fails closed', p.returncode == 1 and 'missing secrets' in r['error'], p, r)

    p, r = run({'YT_ACNE_REFRESH_TOKEN': 'WRONG'}, {})
    check('bad refresh token fails', p.returncode == 1 and 'HTTP 400' in r['error'], p, r)

    p, r = run({}, {}, mp4=b'<html>not a video</html>' * 1000)
    check('non-MP4 download refused', p.returncode == 1 and 'not an MP4' in r['error'] and 'meta' not in STATE, p, r)

    p, r = run({}, {'privacy': 'public'}, force_privacy='private')
    check('privacy lock detected and reported', p.returncode == 1 and 'locked' in r['error'], p, r)

    p, r = run({}, {'publish_at': '2026-11-06T08:00:00Z'})
    check('scheduled upload is private with publishAt', p.returncode == 0 and STATE['meta']['status']['privacyStatus'] == 'private'
          and STATE['meta']['status']['publishAt'] == '2026-11-06T08:00:00Z', p, r)

    p, r = run({}, {}, pre_result={'id': 'amj001', 'video_id': 'OLD'})
    check('already-uploaded item is not uploaded twice', p.returncode == 0 and 'meta' not in STATE and r['video_id'] == 'OLD', p, r)

    p, r = run({}, {'media_url': 'https://evil.example.com/v.mp4'})
    check('non-GitHub media host refused', p.returncode == 1 and 'not allowed' in r['error'], p, r)

    srv.shutdown(); shutil.rmtree(td)
    print(f'\n{"ALL PASSED" if not fails else f"{fails} FAILED"}')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
