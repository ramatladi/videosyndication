"""One-time OAuth sign-in for the Acne Medicine Johannesburg uploader. Run this ON YOUR OWN COMPUTER, not in CI.

    python3 acnemedicine/auth_local.py path/to/client_secret_XXXX.json            # Desktop app client
    python3 acnemedicine/auth_local.py path/to/client_secret_XXXX.json --port 8765  # Web application client
    python3 acnemedicine/auth_local.py path/to/client_secret_XXXX.json --port 8765 --redirect-confirmed
        # Web client whose JSON was downloaded before http://localhost:8765/ was added: use only after confirming in
        # Google Cloud (Clients > the client > Authorised redirect URIs) that it is saved. The JSON is not edited.

Needs Python 3 and the GitHub CLI (`gh auth login` done) with access to ramatladi/videosyndication.
Client types:
- "Desktop app" (JSON has "installed"): loopback redirect http://127.0.0.1:<random port>/.
- "Web application" (JSON has "web"): pass --port N; http://localhost:N/ must be a registered redirect URI. It is
  checked against the JSON's redirect_uris; an older JSON that predates the registration needs --redirect-confirmed
  (Google itself still rejects the sign-in with redirect_uri_mismatch if the URI is not really registered).
Each channel gets its own refresh token; this never reads, replaces or revokes another channel's token.

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


def wait_for_code(state, port=0):
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

    srv = http.server.HTTPServer(('127.0.0.1', port), H)
    srv.timeout = 1
    port = srv.server_port

    def serve():
        deadline = time.time() + TIMEOUT
        while not done.is_set() and time.time() < deadline:
            srv.handle_request()                # returns after 1 s idle, so the loop always ends
        srv.server_close()

    t = threading.Thread(target=serve, daemon=True)
    return port, got, done, t


def pick_redirect(raw, port, confirmed=False):
    """Return (client, redirect_host, port) or exit. Web clients need an exact pre-registered localhost redirect."""
    if 'installed' in raw:
        return raw['installed'], '127.0.0.1', 0
    if 'web' in raw:
        if not port:
            sys.exit('This is a "Web application" client: pass --port N, with http://localhost:N/ registered as a '
                     'redirect URI on that client.')
        want = f'http://localhost:{port}/'
        regs = raw['web'].get('redirect_uris', [])
        if want not in regs and want.rstrip('/') not in regs and not confirmed:
            sys.exit(f'{want} is not listed in this JSON\'s redirect URIs. If Google Cloud shows it saved on the client '
                     '(Clients > the client > Authorised redirect URIs), rerun with --redirect-confirmed. '
                     'Otherwise add it there first. Do not edit the JSON file.')
        return raw['web'], 'localhost', port
    sys.exit('Unrecognised client JSON: expected a "Desktop app" or "Web application" OAuth client.')


def main(client_file, port=0, confirmed=False):
    raw = json.load(open(client_file))
    c, host, port = pick_redirect(raw, port, confirmed)
    if not c.get('client_id') or not c.get('client_secret'):
        sys.exit('This client JSON has no client_secret. Nothing was saved.')
    cid, csec = c['client_id'], c['client_secret']
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    state = secrets.token_urlsafe(24)
    port, got, done, t = wait_for_code(state, port)
    redirect = f'http://{host}:{port}/'
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
        sys.exit('Google returned no refresh token. Nothing was saved. Run the script again (it always asks Google '
                 'for fresh consent). Do NOT remove the app from your Google Account permissions: other channels '
                 'and services may share the same app.')

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
    a = sys.argv[1:]
    confirmed = '--redirect-confirmed' in a
    a = [x for x in a if x != '--redirect-confirmed']
    if len(a) == 1 and not confirmed:
        main(a[0])
    elif len(a) == 3 and a[1] == '--port' and a[2].isdigit() and 1024 <= int(a[2]) <= 65535:
        main(a[0], int(a[2]), confirmed)
    else:
        sys.exit(__doc__)
