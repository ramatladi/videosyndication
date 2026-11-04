"""One-time OAuth sign-in for the Acne Medicine Johannesburg uploader. Run this ON YOUR OWN COMPUTER, not in CI.

    python3 acnemedicine/auth_local.py path/to/client_secret_XXXX.json

Needs Python 3 and the GitHub CLI (`gh auth login` done) with access to ramatladi/videosyndication.
The client file must be a "Desktop app" OAuth client (the JSON has an "installed" section).

1. Opens Google's consent page (loopback redirect to 127.0.0.1 on a random port, PKCE, state check).
   When Google asks which account/channel, pick **Acne Medicine Johannesburg**.
2. Exchanges the code for a refresh token and refuses to continue unless it belongs to the expected channel.
3. Stores YT_ACNE_CLIENT_ID, YT_ACNE_CLIENT_SECRET and YT_ACNE_REFRESH_TOKEN as GitHub Actions secrets through
   `gh secret set` (values go over stdin; nothing secret is printed or written to disk).
"""
import base64, hashlib, http.server, json, os, secrets, subprocess, sys, threading, time
import urllib.error, urllib.parse, urllib.request, webbrowser

REPO = 'ramatladi/videosyndication'
SCOPES = 'https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly'
HERE = os.path.dirname(os.path.abspath(__file__))
EXPECTED = open(os.path.join(HERE, 'CHANNEL_ID')).read().strip()
TIMEOUT = 600


def wait_for_code(state):
    """Serve on 127.0.0.1 until a request with the right state arrives or TIMEOUT passes. Ignores stray requests."""
    got, done = {}, threading.Event()

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query)
            if u.path != '/' or q.get('state', [''])[0] != state or done.is_set():
                self.send_response(400); self.end_headers(); self.wfile.write(b'Not this request.'); return
            got.update({k: v[0] for k, v in q.items()}); done.set()
            self.send_response(200); self.send_header('Content-Type', 'text/plain'); self.end_headers()
            self.wfile.write(b'Done - you can close this tab and return to the terminal.')

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(('127.0.0.1', 0), H)
    srv.timeout = 1
    port = srv.server_port

    def serve():
        deadline = time.time() + TIMEOUT
        while not done.is_set() and time.time() < deadline:
            srv.handle_request()                # returns after 1 s idle, so the loop always ends
        srv.server_close()

    t = threading.Thread(target=serve, daemon=True)
    return port, got, done, t


def main(client_file):
    raw = json.load(open(client_file))
    if 'installed' not in raw:
        sys.exit('This must be a "Desktop app" OAuth client JSON (it has no "installed" section).')
    c = raw['installed']
    cid, csec = c['client_id'], c['client_secret']
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    state = secrets.token_urlsafe(24)
    port, got, done, t = wait_for_code(state)
    redirect = f'http://127.0.0.1:{port}/'
    url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode({
        'client_id': cid, 'redirect_uri': redirect, 'response_type': 'code', 'scope': SCOPES,
        'access_type': 'offline', 'prompt': 'consent select_account', 'state': state,
        'code_challenge': challenge, 'code_challenge_method': 'S256'})
    t.start()
    print('Opening Google sign-in. Choose the Acne Medicine Johannesburg channel when asked.')
    print('If the browser does not open, paste this address into it:\n' + url)
    webbrowser.open(url)
    t.join(TIMEOUT + 5)
    if not done.is_set():
        sys.exit('Timed out waiting for Google sign-in. Nothing was saved.')
    if 'code' not in got:
        sys.exit('Sign-in was not completed (' + got.get('error', 'no code') + '). Nothing was saved.')

    body = urllib.parse.urlencode({'code': got['code'], 'client_id': cid, 'client_secret': csec,
                                   'redirect_uri': redirect, 'grant_type': 'authorization_code',
                                   'code_verifier': verifier}).encode()
    try:
        tok = json.loads(urllib.request.urlopen(urllib.request.Request(
            'https://oauth2.googleapis.com/token', data=body,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}), timeout=60).read())
    except urllib.error.HTTPError as e:
        sys.exit(f'Google refused the code exchange (HTTP {e.code}). Nothing was saved.')
    if 'refresh_token' not in tok:
        sys.exit('Google returned no refresh token; remove the app at myaccount.google.com/permissions and retry.')

    me = json.loads(urllib.request.urlopen(urllib.request.Request(
        'https://www.googleapis.com/youtube/v3/channels?part=id,snippet&mine=true',
        headers={'Authorization': 'Bearer ' + tok['access_token']}), timeout=60).read())
    ids = [i['id'] for i in me.get('items', [])]
    if ids != [EXPECTED]:
        sys.exit(f'That sign-in is for channel {ids}, not Acne Medicine Johannesburg ({EXPECTED}). Nothing was saved. '
                 'Run again and pick the right channel.')
    print('Signed in as channel:', me['items'][0]['snippet']['title'], f'({EXPECTED})')

    for name, value in (('YT_ACNE_CLIENT_ID', cid), ('YT_ACNE_CLIENT_SECRET', csec),
                        ('YT_ACNE_REFRESH_TOKEN', tok['refresh_token'])):
        subprocess.run(['gh', 'secret', 'set', name, '-R', REPO], input=value.encode(), check=True,
                       stdout=subprocess.DEVNULL)
        print('saved GitHub secret', name)
    print('All set. Delete the downloaded client JSON once you no longer need it.')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
