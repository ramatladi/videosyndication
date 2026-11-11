"""One-time YouTube sign-in for the six skincare channels. Run this ON YOUR OWN COMPUTER (not in CI).

    python3 skincare-daily/yt_auth.py path/to/client_secret_XXXX.json            # all six, one after another
    python3 skincare-daily/yt_auth.py path/to/client_secret_XXXX.json MIDRAND    # just one channel (key or @handle)
    ... add  --port 8765  for a "Web application" client (http://localhost:8765/ must be a registered redirect URI)

Needs Python 3 and the GitHub CLI signed in (`gh auth login`) with access to ramatladi/videosyndication.
For each channel it opens Google's consent page: choose that channel's account when Google asks, then Allow.
It refuses to save anything unless the signed-in channel's handle matches the one asked for, then stores
YT_SK_CLIENT_ID, YT_SK_CLIENT_SECRET, YT_SK_REFRESH_<KEY> and YT_SK_CHANNEL_<KEY> as GitHub Actions secrets
(values go over stdin; nothing secret is printed or written to disk). Other channels' tokens are never touched.
"""
import base64, hashlib, http.server, json, os, secrets, subprocess, sys, threading, time
import urllib.error, urllib.parse, urllib.request, webbrowser

REPO = 'ramatladi/videosyndication'
SCOPES = ' '.join('https://www.googleapis.com/auth/' + s for s in ('youtube.upload', 'youtube.readonly'))
HERE = os.path.dirname(os.path.abspath(__file__))
CHANNELS = {h: v for h, v in json.load(open(os.path.join(HERE, 'CHANNELS.json'))).items() if not h.startswith('_')}
TIMEOUT = 600


def client(path, port):
    raw = json.load(open(path))
    if 'installed' in raw:
        c, host = raw['installed'], '127.0.0.1'
    elif 'web' in raw:
        if not port:
            sys.exit('This is a "Web application" client: add --port N (http://localhost:N/ must be registered).')
        c, host = raw['web'], 'localhost'
    else:
        sys.exit('Unrecognised client JSON: expected a "Desktop app" or "Web application" OAuth client.')
    if not c.get('client_id') or not c.get('client_secret'):
        sys.exit('This client JSON has no client_secret. Nothing was saved.')
    return c['client_id'], c['client_secret'], host


def sign_in(cid, csec, host, port, handle):
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    state = secrets.token_urlsafe(24)
    got, done = {}, threading.Event()

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query)
            if u.path != '/' or q.get('state', [''])[0] != state or done.is_set():
                self.send_response(400); self.end_headers(); return
            got.update({k: v[0] for k, v in q.items()}); done.set()
            self.send_response(200); self.send_header('Content-Type', 'text/plain'); self.end_headers()
            self.wfile.write(b'Done - close this tab and go back to the terminal.')

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(('127.0.0.1', port or 0), H); srv.timeout = 1
    redirect = f'http://{host}:{srv.server_port}/'
    url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode({
        'client_id': cid, 'redirect_uri': redirect, 'response_type': 'code', 'scope': SCOPES,
        'access_type': 'offline', 'prompt': 'consent select_account', 'state': state,
        'code_challenge': challenge, 'code_challenge_method': 'S256'})
    print(f'\n=== {handle} ===\nOpening Google sign-in. Pick the {handle} channel, then Allow.')
    print('If no browser opens, paste this address into one:\n' + url)
    webbrowser.open(url)
    deadline = time.time() + TIMEOUT
    while not done.is_set() and time.time() < deadline:
        srv.handle_request()
    srv.server_close()
    if 'code' not in got:
        print(f'{handle}: sign-in not completed ({got.get("error", "timed out")}). Nothing saved.'); return None
    body = urllib.parse.urlencode({'code': got['code'], 'client_id': cid, 'client_secret': csec,
                                   'redirect_uri': redirect, 'grant_type': 'authorization_code',
                                   'code_verifier': verifier}).encode()
    try:
        tok = json.loads(urllib.request.urlopen(urllib.request.Request(
            'https://oauth2.googleapis.com/token', data=body,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}), timeout=60).read())
    except urllib.error.HTTPError as e:
        print(f'{handle}: Google refused the code exchange (HTTP {e.code}). Nothing saved.'); return None
    if 'refresh_token' not in tok:
        print(f'{handle}: Google returned no refresh token. Nothing saved; run this channel again.'); return None
    me = json.loads(urllib.request.urlopen(urllib.request.Request(
        'https://www.googleapis.com/youtube/v3/channels?part=id,snippet&mine=true',
        headers={'Authorization': 'Bearer ' + tok['access_token']}), timeout=60).read())
    items = me.get('items', [])
    got_handle = (items[0]['snippet'].get('customUrl', '') if len(items) == 1 else '').lower().lstrip('@')
    if got_handle != handle.lower().lstrip('@'):
        print(f'{handle}: that sign-in is for {[i["snippet"].get("customUrl") or i["snippet"].get("title") for i in items]},'
              f' not {handle}. Nothing saved; run again and pick {handle}.'); return None
    print(f'{handle}: signed in as "{items[0]["snippet"]["title"]}" ({items[0]["id"]})')
    return tok['refresh_token'], items[0]['id']


def gh_secret(name, value):
    subprocess.run(['gh', 'secret', 'set', name, '-R', REPO], input=value.encode(), check=True,
                   stdout=subprocess.DEVNULL)


def main(args):
    port = 0
    if '--port' in args:
        i = args.index('--port'); port = int(args[i + 1]); del args[i:i + 2]
    if not args:
        sys.exit(__doc__)
    cid, csec, host = client(args[0], port)
    want = args[1:] or list(CHANNELS)
    todo = []
    for w in want:
        h = next((h for h, v in CHANNELS.items() if w.lower() in (h.lower(), v['key'].lower())), None)
        if not h:
            sys.exit(f'unknown channel {w}; use one of: ' + ', '.join(v['key'] for v in CHANNELS.values()))
        todo.append(h)
    gh_secret('YT_SK_CLIENT_ID', cid); gh_secret('YT_SK_CLIENT_SECRET', csec)
    ok = []
    for h in todo:
        res = sign_in(cid, csec, host, port, h)
        if res:
            key = CHANNELS[h]['key']
            gh_secret(f'YT_SK_REFRESH_{key}', res[0]); gh_secret(f'YT_SK_CHANNEL_{key}', res[1])
            print(f'{h}: saved'); ok.append(h)
    missed = [h for h in todo if h not in ok]
    print(f'\nSaved {len(ok)} of {len(todo)} channels.' + (' Run again for: ' + ', '.join(
        CHANNELS[h]['key'] for h in missed) if missed else ' Publishing starts on the next hourly run.'))
    print('Delete the downloaded client JSON once you no longer need it.')


if __name__ == '__main__':
    main(sys.argv[1:])
