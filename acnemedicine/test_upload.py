"""Offline tests for the Acne Medicine Johannesburg uploader (no network, no real credentials).

    python3 acnemedicine/test_upload.py

Covers upload.py against a fake Google API, run_queue.sh + persist.sh against a local bare Git "origin", and the
auth_local.py loopback listener.
"""
import http.server, json, os, shutil, subprocess, sys, tempfile, threading, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CH = open(os.path.join(HERE, 'CHANNEL_ID')).read().strip()
SECRETS = {'YT_ACNE_CLIENT_ID': 'CID-test-1234', 'YT_ACNE_CLIENT_SECRET': 'GOCSPX-testsecret',
           'YT_ACNE_REFRESH_TOKEN': '1//test-refresh-token'}
S = {}


def reset(**kw):
    S.clear()
    S.update(dict(channel=CH, processing_polls=0, force_privacy=None, echo_secret=False, fail_last_chunk=False,
                  session_fail=False, uploads=[], polls=0, puts=0, inserts=0, videos={}), **kw)


class Fake(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *a):
        pass

    def _send(self, code, obj=None, headers=None):
        body = json.dumps(obj).encode() if obj is not None else b''
        self.send_response(code)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query)
        if self.headers.get('Authorization') != 'Bearer ya29.fake-access':
            return self._send(401, {'error': {'status': 'UNAUTHENTICATED'}})
        if u.path == '/youtube/v3/channels':
            return self._send(200, {'items': [{'id': S['channel'], 'snippet': {'title': 'Acne Medicine Johannesburg'},
                                               'contentDetails': {'relatedPlaylists': {'uploads': 'UU1'}}}]})
        if u.path == '/youtube/v3/playlistItems':
            return self._send(200, {'items': [{'contentDetails': {'videoId': v}} for v in S['uploads']]})
        if u.path == '/youtube/v3/videos':
            ids = q.get('id', [''])[0].split(',')
            if len(ids) > 1 or q.get('part') == ['snippet']:     # reconciliation lookup
                return self._send(200, {'items': [S['videos'][i] for i in ids if i in S['videos']]})
            v = S['videos'].get(ids[0])
            if v:
                S['polls'] += 1
                v['status']['uploadStatus'] = 'processed' if S['polls'] > S['processing_polls'] else 'uploaded'
            return self._send(200, {'items': [v] if v else []})
        self._send(404, {})

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
        if u.path == '/token':
            S['token_hits'] = S.get('token_hits', 0) + 1
            f = urllib.parse.parse_qs(body.decode())
            if S['echo_secret']:   # hostile/buggy error body that reflects the request values
                return self._send(400, {'error': 'invalid_grant', 'error_description': f'bad {f}'})
            ok = f.get('refresh_token') == [SECRETS['YT_ACNE_REFRESH_TOKEN']]
            return self._send(200 if ok else 400, {'access_token': 'ya29.fake-access'} if ok else {'error': 'invalid_grant'})
        if u.path == '/upload/youtube/v3/videos':
            if S['session_fail']:
                return self._send(403, {'error': {'status': 'PERMISSION_DENIED', 'errors': [{'reason': 'forbidden'}],
                                                  'message': 'echo ' + SECRETS['YT_ACNE_CLIENT_SECRET']}})
            S['meta'] = json.loads(body); S['size'] = int(self.headers['X-Upload-Content-Length']); S['got'] = b''
            return self._send(200, headers={'Location': f'http://127.0.0.1:{S["port"]}/session/1'})
        self._send(404, {})

    def do_PUT(self):
        S['got'] += self.rfile.read(int(self.headers.get('Content-Length', 0))); S['puts'] += 1
        if len(S['got']) < S['size']:
            return self._send(308, headers={'Range': f'bytes=0-{len(S["got"]) - 1}'})
        st = S['meta']['status']; S['inserts'] += 1
        vid = f'VID{S["inserts"]}'
        S['videos'][vid] = {'id': vid, 'snippet': {'channelId': S['channel'], 'title': S['meta']['snippet']['title'],
                                                   'tags': S['meta']['snippet']['tags']},
                            'status': {'uploadStatus': 'uploaded', 'privacyStatus': S['force_privacy'] or st['privacyStatus'],
                                       'publishAt': st.get('publishAt'), 'containsSyntheticMedia': st['containsSyntheticMedia']}}
        S['uploads'].append(vid)
        if S['fail_last_chunk']:          # YouTube created the video but the response is lost
            self.close_connection = True; self.connection.shutdown(2); return
        self._send(200, {'id': vid})


def env(**over):
    e = {**os.environ, **SECRETS, 'YT_TEST_MODE': '1', 'YT_TOKEN_URL': f'http://127.0.0.1:{PORT}/token',
         'YT_API_BASE': f'http://127.0.0.1:{PORT}', 'YT_POLL_SECONDS': '0', 'YT_POLL_TRIES': '3', **over}
    return {k: v for k, v in e.items() if v is not None}


def base_item(**kw):
    return {'id': 'amj001', 'title': 'Test review', 'description': 'desc', 'privacy': 'unlisted',
            'contains_synthetic_media': False, **kw}


def run_upload(item, pre=None, persist_ok=True, **envover):
    d = tempfile.mkdtemp(); os.makedirs(f'{d}/results')
    q = f'{d}/q.json'; json.dump(item, open(q, 'w'))
    if pre:
        json.dump(pre, open(f'{d}/results/{item["id"]}.json', 'w'))
    log = f'{d}/persist.log'
    pc = f'{d}/persist.sh'
    open(pc, 'w').write(f'#!/bin/sh\npython3 -c "import json,sys;print(json.load(open(sys.argv[1]))[\'status\'])" "$1" >> {log}\n'
                        + ('exit 0\n' if persist_ok else 'exit 1\n'))
    os.chmod(pc, 0o755)
    p = subprocess.run([sys.executable, f'{HERE}/upload.py', q, VIDEO, f'{d}/results', pc],
                       capture_output=True, text=True, env=env(**envover), timeout=120)
    rp = f'{d}/results/{item["id"]}.json'
    res = json.load(open(rp)) if os.path.exists(rp) else {}
    states = open(log).read().split() if os.path.exists(log) else []
    shutil.rmtree(d)
    return p, res, states


def no_secret(*texts):
    blob = ''.join(texts)
    return all(v not in blob for v in list(SECRETS.values()) + ['ya29.fake-access'])


FAILS = []


def check(name, cond, *debug):
    print(('PASS ' if cond else 'FAIL ') + name)
    if not cond:
        FAILS.append(name)
        for x in debug:
            print('   ', str(x)[-1200:])


def upload_tests():
    reset(port=PORT)
    p, r, st = run_upload(base_item(short=True))
    check('happy path: persisted UPLOADING then UPLOADED (with id) before VERIFIED',
          p.returncode == 0 and st == ['UPLOADING', 'UPLOADED', 'VERIFIED'] and r['video_id'] == 'VID1'
          and r['verified']['uploadStatus'] == 'processed' and S['got'] == open(VIDEO, 'rb').read(), p.stdout, p.stderr, st)
    check('resumable upload used several chunks', S['puts'] >= 3, S['puts'])
    check('disclosure follows the queue item, not a blanket default', S['meta']['status']['containsSyntheticMedia'] is False)
    check('no secret or token in output/result', no_secret(p.stdout, p.stderr, json.dumps(r)))

    reset(port=PORT)
    p, r, st = run_upload({k: v for k, v in base_item().items() if k != 'contains_synthetic_media'})
    check('missing AI-disclosure choice refuses before upload', p.returncode == 1 and 'contains_synthetic_media' in r['error']
          and 'meta' not in S, r)

    reset(port=PORT, processing_polls=99)
    p, r, st = run_upload(base_item())
    check('still processing -> PENDING (exit 2), never VERIFIED', p.returncode == 2 and r['status'] == 'PENDING', r)
    S['processing_polls'] = 0
    p, r2, st = run_upload(base_item(), pre=r)
    check('rerun of PENDING re-verifies the same video without uploading again',
          p.returncode == 0 and r2['status'] == 'VERIFIED' and r2['video_id'] == r['video_id'] and S['inserts'] == 1, r2)

    reset(port=PORT)
    p, r, st = run_upload(base_item(), pre={'id': 'amj001', 'status': 'VERIFIED', 'video_id': 'VID9'})
    check('existing VERIFIED id is re-verified, not trusted blindly (missing video -> PENDING)',
          p.returncode == 2 and r['status'] == 'PENDING' and S['inserts'] == 0, r)

    for pre_status in ('FAILED', 'NEEDS_REVIEW'):
        reset(port=PORT)
        p, r, st = run_upload(base_item(), pre={'id': 'amj001', 'status': pre_status, 'video_id': 'VID9'})
        check(f'{pre_status} result is left for a person (no upload, exit 1)', p.returncode == 1 and S['inserts'] == 0
              and r['status'] == pre_status, r)

    reset(port=PORT, fail_last_chunk=True)
    p, r, st = run_upload(base_item())
    check('response lost after YouTube created the video -> stays UPLOADING, no FAILED_PREUPLOAD',
          p.returncode == 1 and r['status'] == 'UPLOADING' and not r.get('video_id') and S['inserts'] == 1, r, st)
    S['fail_last_chunk'] = False
    p, r2, st = run_upload(base_item(), pre=r)
    check('rerun reconciles to the existing video instead of uploading a duplicate',
          p.returncode == 0 and r2['video_id'] == 'VID1' and r2.get('reconciled') and S['inserts'] == 1, r2)

    check('marker tag saved before upload and sent on the video', r.get('upload_marker', '').startswith('amjref')
          and r['upload_marker'] in S['videos']['VID1']['snippet']['tags'], r)

    def same_title_decoy():
        S['inserts'] += 1; vid = f'VID{S["inserts"]}'
        S['videos'][vid] = {'id': vid, 'snippet': {'channelId': CH, 'title': 'Test review', 'tags': ['other']},
                            'status': {'uploadStatus': 'processed', 'privacyStatus': 'unlisted'}}
        S['uploads'].append(vid)

    reset(port=PORT); same_title_decoy()
    p, r, st = run_upload(base_item(), pre={'id': 'amj001', 'status': 'UPLOADING', 'upload_marker': 'amjref0123456789ab'})
    check('unrelated same-title upload is NOT adopted -> NEEDS_REVIEW', p.returncode == 1 and r['status'] == 'NEEDS_REVIEW'
          and not r.get('video_id') and S['inserts'] == 1, r)

    reset(port=PORT); same_title_decoy()
    p, r, st = run_upload(base_item(), pre={'id': 'amj001', 'status': 'UPLOADING', 'upload_started': '2026-01-01T00:00:00Z'})
    check('UPLOADING without a marker -> NEEDS_REVIEW, no upload', p.returncode == 1 and r['status'] == 'NEEDS_REVIEW'
          and 'no marker' in r['error'] and S['inserts'] == 1, r)

    reset(port=PORT)
    for n in (1, 2):
        S['inserts'] += 1; vid = f'VID{S["inserts"]}'
        S['videos'][vid] = {'id': vid, 'snippet': {'channelId': CH, 'title': 'x', 'tags': ['amjrefdupdupdupdu']},
                            'status': {'uploadStatus': 'processed', 'privacyStatus': 'unlisted'}}
        S['uploads'].append(vid)
    p, r, st = run_upload(base_item(), pre={'id': 'amj001', 'status': 'UPLOADING', 'upload_marker': 'amjrefdupdupdupdu'})
    check('two uploads with the same marker -> NEEDS_REVIEW', p.returncode == 1 and r['status'] == 'NEEDS_REVIEW', r)

    reset(port=PORT)
    p, r, st = run_upload(base_item(), persist_ok=False)
    check('if the UPLOADING marker cannot be persisted, nothing is uploaded', p.returncode == 1 and 'meta' not in S
          and S['inserts'] == 0, p.stdout, st)

    reset(port=PORT, channel='UCsomeOtherChannel000000')
    p, r, st = run_upload(base_item())
    check('wrong channel refused before upload', p.returncode == 1 and 'refusing' in r['error'] and 'meta' not in S, r)

    reset(port=PORT)
    p, r, st = run_upload(base_item(), YT_ACNE_REFRESH_TOKEN=None)
    check('missing secret fails closed', p.returncode == 1 and 'missing secrets' in r['error'], r)

    reset(port=PORT, echo_secret=True)
    p, r, st = run_upload(base_item())
    check('token error body that echoes secrets is sanitised', p.returncode == 1 and r['status'] == 'FAILED_PREUPLOAD'
          and no_secret(p.stdout, p.stderr, json.dumps(r)), r)

    reset(port=PORT, session_fail=True)
    p, r, st = run_upload(base_item())
    check('upload-session refusal -> FAILED_PREUPLOAD, sanitised, retryable', p.returncode == 1
          and r['status'] == 'FAILED_PREUPLOAD' and 'PERMISSION_DENIED' in r['error']
          and no_secret(p.stdout, p.stderr, json.dumps(r)), r)

    reset(port=PORT, force_privacy='private')
    p, r, st = run_upload(base_item(privacy='public'))
    check('privacy lock -> FAILED for a person', p.returncode == 1 and r['status'] == 'FAILED' and 'privacy' in r['error'], r)

    reset(port=PORT)
    p, r, st = run_upload(base_item(publish_at='2026-11-06T08:00:00Z'))
    check('scheduled: sent private + publishAt and publishAt verified', p.returncode == 0
          and S['meta']['status']['privacyStatus'] == 'private' and r['verified']['publishAt'] == '2026-11-06T08:00:00Z', r)

    reset(port=PORT)
    p, r, st = run_upload(base_item(), YT_TEST_MODE=None)
    check('fake endpoints are ignored outside explicit test mode (real Google host used, fake never hit)',
          S.get('token_hits', 0) == 0 and 'meta' not in S and p.returncode == 1, r)
    src = open(f'{HERE}/upload.py').read()
    check('production endpoints are hard-coded HTTPS Google hosts',
          "'https://oauth2.googleapis.com/token'" in src and "'https://www.googleapis.com'" in src)


def git(*a, cwd=None, check_=True):
    return subprocess.run(['git', *a], cwd=cwd, capture_output=True, text=True, check=check_)


def queue_tests():
    """run_queue.sh + persist.sh against a local bare 'origin' with acne-data and acne-media/<id> branches."""
    t = tempfile.mkdtemp(); origin = f'{t}/origin.git'; seed = f'{t}/seed'
    git('init', '-q', '--bare', origin)
    git('init', '-q', '-b', 'acne-data', seed)
    for k, v in (('user.name', 't'), ('user.email', 't@t')):
        git('config', k, v, cwd=seed)
    shutil.copytree(HERE, f'{seed}/acnemedicine', ignore=shutil.ignore_patterns('__pycache__', 'results', 'queue'))
    os.makedirs(f'{seed}/acnemedicine/queue')
    json.dump(base_item(), open(f'{seed}/acnemedicine/queue/amj001.json', 'w'))
    json.dump(base_item(id='amj002', title='Second'), open(f'{seed}/acnemedicine/queue/amj002.json', 'w'))
    json.dump(base_item(id='../evil'), open(f'{seed}/acnemedicine/queue/evil.json', 'w'))
    git('add', '-A', cwd=seed); git('commit', '-qm', 'q1', cwd=seed)
    git('remote', 'add', 'origin', origin, cwd=seed); git('push', '-q', 'origin', 'acne-data', cwd=seed)
    for vid in ('amj001', 'amj002'):        # temporary per-video media branches
        m = f'{t}/m-{vid}'; git('init', '-q', '-b', f'acne-media/{vid}', m)
        for k, v in (('user.name', 't'), ('user.email', 't@t')):
            git('config', k, v, cwd=m)
        os.makedirs(f'{m}/acnemedicine'); shutil.copy(VIDEO, f'{m}/acnemedicine/{vid}.mp4')
        git('add', '-A', cwd=m); git('commit', '-qm', 'media', cwd=m)
        git('push', '-q', origin, f'acne-media/{vid}', cwd=m)
    work = f'{t}/work'; git('clone', '-q', '-b', 'acne-data', origin, work)
    for k, v in (('user.name', 't'), ('user.email', 't@t')):
        git('config', k, v, cwd=work)

    def heads():
        return git('ls-remote', '--heads', origin).stdout

    reset(port=PORT)
    p = subprocess.run(['bash', f'{work}/acnemedicine/run_queue.sh'], capture_output=True, text=True, env=env(), timeout=300)
    o = f'{t}/check'; git('clone', '-q', '-b', 'acne-data', origin, o)
    r1 = json.load(open(f'{o}/acnemedicine/results/amj001.json')); r2 = json.load(open(f'{o}/acnemedicine/results/amj002.json'))
    check('queue: every item processed (not just the last commit), results on origin',
          r1['status'] == 'VERIFIED' and r2['status'] == 'VERIFIED' and S['inserts'] == 2, p.stdout, p.stderr)
    check('queue: invalid id/file name skipped and reported', 'evil.json: invalid id' in p.stdout and p.returncode == 1, p.stdout)
    check('queue: media branches deleted only after verified results are on origin',
          'acne-media/amj001' not in heads() and 'acne-media/amj002' not in heads(), heads())

    p = subprocess.run(['bash', f'{work}/acnemedicine/run_queue.sh'], capture_output=True, text=True, env=env(), timeout=300)
    check('queue: rerun uploads nothing new', S['inserts'] == 2, p.stdout)

    # Persistence failure: origin refuses pushes -> no upload starts and media is kept.
    json.dump(base_item(id='amj003', title='Third'), open(f'{work}/acnemedicine/queue/amj003.json', 'w'))
    git('add', '-A', cwd=work); git('commit', '-qm', 'q3', cwd=work); git('push', '-q', 'origin', 'acne-data', cwd=work)
    m = f'{t}/m-amj003'; git('init', '-q', '-b', 'acne-media/amj003', m)
    for k, v in (('user.name', 't'), ('user.email', 't@t')):
        git('config', k, v, cwd=m)
    os.makedirs(f'{m}/acnemedicine'); shutil.copy(VIDEO, f'{m}/acnemedicine/amj003.mp4')
    git('add', '-A', cwd=m); git('commit', '-qm', 'media', cwd=m); git('push', '-q', origin, 'acne-media/amj003', cwd=m)
    hook = f'{origin}/hooks/pre-receive'
    open(hook, 'w').write('#!/bin/sh\nexit 1\n'); os.chmod(hook, 0o755)
    before = S['inserts']
    p = subprocess.run(['bash', f'{work}/acnemedicine/run_queue.sh'], capture_output=True, text=True, env=env(), timeout=300)
    check('queue: result push failing -> run fails, no upload, media kept',
          p.returncode == 1 and S['inserts'] == before and 'acne-media/amj003' in heads(), p.stdout, p.stderr)
    shutil.rmtree(t)


def auth_tests():
    sys.path.insert(0, HERE)
    import auth_local
    auth_local.TIMEOUT = 3
    port, got, done, th = auth_local.wait_for_code('GOODSTATE'); th.start()
    codes = []
    for path in ('/favicon.ico', '/?state=WRONG&code=x', '/?state=GOODSTATE&code=abc'):
        try:
            codes.append(urllib.request.urlopen(f'http://127.0.0.1:{port}{path}', timeout=5).status)
        except urllib.error.HTTPError as e:
            codes.append(e.code)
    th.join(5)
    check('auth: stray and wrong-state requests rejected, right state accepted, listener stops',
          codes == [400, 400, 200] and got.get('code') == 'abc' and not th.is_alive(), codes, got)
    port, got, done, th = auth_local.wait_for_code('X'); th.start(); th.join(6)
    check('auth: listener times out and stops on its own', not th.is_alive() and not done.is_set())
    d = tempfile.mkdtemp(); f = f'{d}/c.json'; json.dump({'web': {'client_id': 'a', 'client_secret': 'b'}}, open(f, 'w'))
    p = subprocess.run([sys.executable, f'{HERE}/auth_local.py', f], capture_output=True, text=True)
    check('auth: non-Desktop (web) client refused', p.returncode != 0 and 'Desktop app' in p.stderr, p.stderr)
    shutil.rmtree(d)


def main():
    global PORT, VIDEO
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Fake); PORT = srv.server_port
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    td = tempfile.mkdtemp(); VIDEO = f'{td}/t.mp4'
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-f', 'lavfi', '-i', 'testsrc=size=320x240:rate=25', '-t', '5',
                    '-pix_fmt', 'yuv420p', f'{td}/a.mp4'], check=True)
    with open(VIDEO, 'wb') as f:      # pad past 2 chunks to exercise resumable 308 handling
        f.write(open(f'{td}/a.mp4', 'rb').read() + b'\0' * (17 * 1024 * 1024))
    upload_tests(); queue_tests(); auth_tests()
    srv.shutdown(); shutil.rmtree(td)
    print('\nALL PASSED' if not FAILS else f'\n{len(FAILS)} FAILED: {FAILS}')
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
