"""One-time OAuth sign-in for the Acne Medicine Johannesburg uploader. Run this ON YOUR OWN COMPUTER, not in CI.

    python3 acnemedicine/auth_local.py path/to/client_secret_XXXX.json

Needs: Python 3, the GitHub CLI (`gh auth login` done) with access to ramatladi/videosyndication.

What it does:
1. Opens Google's consent page in your browser (loopback redirect to 127.0.0.1, with PKCE).
   When Google asks which account/channel, pick **Acne Medicine Johannesburg**.
2. Exchanges the code for a refresh token and checks that the token belongs to the expected channel.
3. Stores YT_ACNE_CLIENT_ID, YT_ACNE_CLIENT_SECRET and YT_ACNE_REFRESH_TOKEN as GitHub Actions secrets via
   `gh secret set` (values go through stdin; nothing secret is printed or written to disk).
"""
import base64, hashlib, http.server, json, os, secrets, subprocess, sys, threading, urllib.parse, urllib.request, webbrowser

REPO = 'ramatladi/videosyndication'
SCOPES = 'https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly'
EXPECTED = os.environ.get('YT_ACNE_CHANNEL_ID') or open(os.path.join(os.path.dirname(__file__), 'CHANNEL_ID')).read().strip()


def main(client_file):
    c = json.load(open(client_file))
    c = c.get('installed') or c.get('web') or c
    cid, csec = c['client_id'], c['client_secret']
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    state = secrets.token_urlsafe(16)
    got = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if q.get('state', [''])[0] == state:
                got.update({k: v[0] for k, v in q.items()})
            self.send_response(200); self.send_header('Content-Type', 'text/plain'); self.end_headers()
            self.wfile.write(b'Done - you can close this tab and return to the terminal.')

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(('127.0.0.1', 0), H)
    redirect = f'http://127.0.0.1:{srv.server_port}'
    url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode({
        'client_id': cid, 'redirect_uri': redirect, 'response_type': 'code', 'scope': SCOPES,
        'access_type': 'offline', 'prompt': 'consent select_account', 'state': state,
        'code_challenge': challenge, 'code_challenge_method': 'S256'})
    print('Opening Google sign-in. Choose the Acne Medicine Johannesburg channel when asked.')
    print('If the browser does not open, paste this into it:\n' + url)
    webbrowser.open(url)
    t = threading.Thread(target=srv.handle_request); t.start(); t.join(timeout=600)
    srv.server_close()
    if 'code' not in got:
        sys.exit('No authorisation code received: ' + got.get('error', 'timed out'))

    body = urllib.parse.urlencode({'code': got['code'], 'client_id': cid, 'client_secret': csec,
                                   'redirect_uri': redirect, 'grant_type': 'authorization_code',
                                   'code_verifier': verifier}).encode()
    tok = json.loads(urllib.request.urlopen(urllib.request.Request(
        'https://oauth2.googleapis.com/token', data=body,
        headers={'Content-Type': 'application/x-www-form-urlencoded'})).read())
    if 'refresh_token' not in tok:
        sys.exit('Google returned no refresh token; revoke the app at myaccount.google.com/permissions and retry.')

    me = json.loads(urllib.request.urlopen(urllib.request.Request(
        'https://www.googleapis.com/youtube/v3/channels?part=id,snippet&mine=true',
        headers={'Authorization': 'Bearer ' + tok['access_token']})).read())
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
    print('All set. Delete the downloaded client_secret JSON if you no longer need it.')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
