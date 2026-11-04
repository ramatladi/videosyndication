"""Upload one queued video to the Acne Medicine Johannesburg YouTube channel through the YouTube Data API.

Runs in GitHub Actions (.github/workflows/acne-upload.yml). Standard library only.

    python3 acnemedicine/upload.py <queue.json> <video.mp4> <results_dir> <persist_cmd>

<persist_cmd> is run as `<persist_cmd> <result_file>` after every state change and must exit 0 only once the result
is durably stored (the workflow's persist.sh commits and pushes it to acne-data). If it fails, the run stops.

Credentials come only from environment variables (GitHub Actions secrets) and never appear in output:
    YT_ACNE_CLIENT_ID, YT_ACNE_CLIENT_SECRET, YT_ACNE_REFRESH_TOKEN

Result states (results/<id>.json):
    UPLOADING          upload about to start (persisted first); a rerun reconciles against the channel's uploads
    UPLOADED           YouTube returned a video ID (persisted at once); not yet verified
    PENDING            video exists but YouTube has not finished processing; rerun re-verifies
    VERIFIED           processed, on the expected channel, with the requested privacy/publishAt
    FAILED_PREUPLOAD   nothing was sent to YouTube; a rerun may try again
    FAILED             a video exists but is rejected/failed/wrong; needs a person
    NEEDS_REVIEW       an upload may have happened but its video cannot be found; needs a person
Exit codes: 0 VERIFIED, 2 PENDING (retry later), 1 anything else.
"""
import json, os, re, subprocess, sys, time, urllib.request, urllib.parse, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
EXPECTED_CHANNEL_ID = open(os.path.join(HERE, 'CHANNEL_ID')).read().strip()
TEST_MODE = os.environ.get('YT_TEST_MODE') == '1'           # only the offline tests set this
TOKEN_URL = os.environ['YT_TOKEN_URL'] if TEST_MODE else 'https://oauth2.googleapis.com/token'
API = os.environ['YT_API_BASE'] if TEST_MODE else 'https://www.googleapis.com'
POLL = float(os.environ.get('YT_POLL_SECONDS', '15')) if TEST_MODE else 15.0
POLL_TRIES = int(os.environ.get('YT_POLL_TRIES', '40')) if TEST_MODE else 40      # ~10 minutes
ALLOWED_PRIVACY = {'public', 'unlisted', 'private'}
ID_RE = re.compile(r'^[a-z0-9][a-z0-9_-]{2,40}$')
SECRET_ENV = ('YT_ACNE_CLIENT_ID', 'YT_ACNE_CLIENT_SECRET', 'YT_ACNE_REFRESH_TOKEN')
TOKEN_PATTERNS = re.compile(r'(ya29\.[\w.-]+|1//[\w.-]+|GOCSPX-[\w-]+|Bearer\s+\S+)')


class Fail(Exception):
    pass


class WrongVideo(Fail):
    """The uploaded video is on the wrong channel, rejected, or has the wrong privacy/schedule."""


class NoSession(Fail):
    """The resumable session was never opened, so YouTube cannot have created a video."""


def sanitize(text):
    """Strip any secret value or token-looking string from text that may be logged or committed."""
    text = str(text)
    for k in SECRET_ENV:
        v = os.environ.get(k)
        if v and len(v) >= 4:
            text = text.replace(v, '[redacted]')
    for v in list(_seen_tokens):
        text = text.replace(v, '[redacted]')
    return TOKEN_PATTERNS.sub('[redacted]', text)[:1500]


_seen_tokens = set()


def _google_error(raw):
    """Only Google's short error code/reason, never the raw body (it can echo request values)."""
    try:
        d = json.loads(raw)
    except Exception:  # noqa: BLE001
        return 'non-JSON error body'
    e = d.get('error')
    if isinstance(e, dict):
        reasons = ','.join(x.get('reason', '') for x in e.get('errors', []) if isinstance(x, dict))
        return f"{e.get('status', '')} {reasons}".strip() or 'error'
    if isinstance(e, str):                 # OAuth token endpoint: {"error": "invalid_grant", ...}
        return e if re.fullmatch(r'[a-z_]{3,40}', e) else 'oauth error'
    return 'error'


def _req(method, url, data=None, headers=None, timeout=120):
    r = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        raise Fail(f'{method} {urllib.parse.urlparse(url).path} -> HTTP {e.code} {_google_error(e.read()[:4000])}') from None


def access_token():
    missing = [k for k in SECRET_ENV if not os.environ.get(k)]
    if missing:
        raise Fail('missing secrets: ' + ', '.join(missing))
    body = urllib.parse.urlencode({
        'client_id': os.environ['YT_ACNE_CLIENT_ID'], 'client_secret': os.environ['YT_ACNE_CLIENT_SECRET'],
        'refresh_token': os.environ['YT_ACNE_REFRESH_TOKEN'], 'grant_type': 'refresh_token'}).encode()
    _, _, raw = _req('POST', TOKEN_URL, body, {'Content-Type': 'application/x-www-form-urlencoded'})
    tok = json.loads(raw).get('access_token')
    if not tok:
        raise Fail('token endpoint returned no access_token')
    _seen_tokens.add(tok)
    return tok


def api_json(method, path, token, params=None):
    url = API + path + ('?' + urllib.parse.urlencode(params) if params else '')
    _, _, raw = _req(method, url, None, {'Authorization': 'Bearer ' + token})
    return json.loads(raw) if raw else {}


def check_channel(token):
    d = api_json('GET', '/youtube/v3/channels', token, {'part': 'id,snippet,contentDetails', 'mine': 'true'})
    ids = [c['id'] for c in d.get('items', [])]
    if ids != [EXPECTED_CHANNEL_ID]:
        raise Fail(f'token is for channel(s) {ids}, expected {EXPECTED_CHANNEL_ID}; refusing')
    c = d['items'][0]
    return c['snippet'].get('title', ''), c.get('contentDetails', {}).get('relatedPlaylists', {}).get('uploads')


def validate(item, video_path):
    if not ID_RE.match(str(item.get('id', ''))):
        raise Fail('id must be 3-41 chars of a-z, 0-9, - or _')
    for k in ('title', 'description'):
        if not str(item.get(k, '')).strip():
            raise Fail(f'queue item missing "{k}"')
    if len(item['title']) > 100 or '<' in item['title'] or '>' in item['title']:
        raise Fail('title must be at most 100 characters with no < or >')
    if len(item['description'].encode()) > 5000:
        raise Fail('description longer than 5000 bytes')
    if item.get('privacy', 'public') not in ALLOWED_PRIVACY:
        raise Fail('privacy must be public, unlisted or private')
    if not isinstance(item.get('contains_synthetic_media'), bool):
        raise Fail('contains_synthetic_media must be set true or false for this video\'s actual content')
    if item.get('publish_at') and not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ', item['publish_at']):
        raise Fail('publish_at must be UTC like 2026-11-06T08:00:00Z')
    tags = item.get('tags', [])
    if not isinstance(tags, list) or sum(len(t) + 2 for t in tags) > 480:
        raise Fail('tags must be a list under 480 characters')
    if not os.path.isfile(video_path):
        raise Fail('video file not found')
    size = os.path.getsize(video_path)
    with open(video_path, 'rb') as f:
        head = f.read(12)
    if size < 10_000 or head[4:8] != b'ftyp' or size > 2 * 1024 ** 3:
        raise Fail(f'video is not a usable MP4 ({size} bytes)')
    return size


def resource(item):
    status = {'privacyStatus': item.get('privacy', 'public'), 'selfDeclaredMadeForKids': False,
              'embeddable': True, 'license': 'youtube',
              'containsSyntheticMedia': item['contains_synthetic_media']}
    if item.get('publish_at'):
        status['privacyStatus'] = 'private'          # YouTube requires private + publishAt for scheduling
        status['publishAt'] = item['publish_at']
    return {'snippet': {'title': item['title'], 'description': item['description'], 'tags': item.get('tags', []),
                        'categoryId': str(item.get('category_id', '26')),
                        'defaultLanguage': item.get('language', 'en'),
                        'defaultAudioLanguage': item.get('language', 'en')},
            'status': status}


def upload(token, path, size, item):
    url = API + '/upload/youtube/v3/videos?' + urllib.parse.urlencode(
        {'uploadType': 'resumable', 'part': 'snippet,status', 'notifySubscribers': 'true'})
    try:
        _, headers, _ = _req('POST', url, json.dumps(resource(item)).encode(), {
            'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json; charset=UTF-8',
            'X-Upload-Content-Type': 'video/mp4', 'X-Upload-Content-Length': str(size)})
    except Fail as e:
        raise NoSession(str(e)) from None
    except (urllib.error.URLError, TimeoutError):
        raise NoSession('could not open upload session (network)') from None
    session = headers.get('Location') or headers.get('location')
    if not session:
        raise NoSession('no resumable upload session returned')
    chunk, start = 8 * 1024 * 1024, 0
    with open(path, 'rb') as f:
        while True:
            f.seek(start); data = f.read(chunk); end = start + len(data) - 1
            req = urllib.request.Request(session, data=data, method='PUT', headers={
                'Content-Length': str(len(data)), 'Content-Range': f'bytes {start}-{end}/{size}'})
            for attempt in range(5):
                try:
                    with urllib.request.urlopen(req, timeout=600) as resp:
                        return json.loads(resp.read())['id']
                except urllib.error.HTTPError as e:
                    if e.code == 308:
                        rng = e.headers.get('Range')
                        start = int(rng.split('-')[1]) + 1 if rng else end + 1
                        break
                    if e.code in (500, 502, 503, 504) and attempt < 4:
                        time.sleep(2 ** attempt * 3); continue
                    raise Fail(f'upload chunk -> HTTP {e.code} {_google_error(e.read()[:4000])}') from None
                except (urllib.error.URLError, TimeoutError):
                    if attempt < 4:
                        time.sleep(2 ** attempt * 3); continue
                    raise Fail('upload chunk: network error after retries') from None
            else:
                raise Fail('upload chunk failed after retries')
            if start >= size:
                raise Fail('upload ended without a video resource')


def find_existing(token, uploads_playlist, title, since):
    """After an interrupted run: look for a video with this title uploaded since the marker was written."""
    if not uploads_playlist:
        return None
    d = api_json('GET', '/youtube/v3/playlistItems', token,
                 {'part': 'snippet,contentDetails', 'playlistId': uploads_playlist, 'maxResults': '50'})
    hits = [i['contentDetails']['videoId'] for i in d.get('items', [])
            if i['snippet'].get('title') == title and i['snippet'].get('publishedAt', '') >= since[:19]]
    return hits[0] if len(hits) == 1 else ('AMBIGUOUS' if hits else None)


def check_video(token, vid, item):
    """One read-back. Returns ('VERIFIED'|'PENDING', state) or raises Fail for a wrong/failed video."""
    d = api_json('GET', '/youtube/v3/videos', token, {'part': 'snippet,status,processingDetails', 'id': vid})
    if not d.get('items'):
        return 'PENDING', {'note': 'not visible yet'}
    v = d['items'][0]; st = v.get('status', {})
    state = {'channelId': v['snippet'].get('channelId'), 'uploadStatus': st.get('uploadStatus'),
             'privacyStatus': st.get('privacyStatus'), 'publishAt': st.get('publishAt'),
             'containsSyntheticMedia': st.get('containsSyntheticMedia'),
             'rejectionReason': st.get('rejectionReason'), 'failureReason': st.get('failureReason')}
    if state['channelId'] != EXPECTED_CHANNEL_ID:
        raise WrongVideo(f'video is on channel {state["channelId"]}, expected {EXPECTED_CHANNEL_ID}')
    if state['uploadStatus'] in ('rejected', 'failed', 'deleted'):
        raise WrongVideo(f'YouTube {state["uploadStatus"]} the video ({state["rejectionReason"] or state["failureReason"]})')
    want = 'private' if item.get('publish_at') else item.get('privacy', 'public')
    if state['privacyStatus'] != want:
        raise WrongVideo(f'privacy is {state["privacyStatus"]}, expected {want}')
    if item.get('publish_at') and (state['publishAt'] or '')[:19] != item['publish_at'][:19]:
        raise WrongVideo(f'publishAt is {state["publishAt"]}, expected {item["publish_at"]}')
    return ('VERIFIED' if state['uploadStatus'] == 'processed' else 'PENDING'), state


def now():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def main(qpath, video_path, res_dir, persist_cmd):
    item = json.load(open(qpath))
    if not ID_RE.match(str(item.get('id', ''))):
        print('queue item has no valid id'); return 1
    os.makedirs(res_dir, exist_ok=True)
    res_path = os.path.join(res_dir, item['id'] + '.json')
    r = json.load(open(res_path)) if os.path.exists(res_path) else {}
    r.update(id=item['id'], title=item.get('title'), channel_id=EXPECTED_CHANNEL_ID)

    def persist(**kw):
        if 'error' in kw and kw['error'] is not None:
            kw['error'] = sanitize(kw['error'])
        before = json.dumps({k: v for k, v in r.items() if k != 'updated'}, sort_keys=True)
        r.update(kw)
        if os.path.exists(res_path) and json.dumps({k: v for k, v in r.items() if k != 'updated'}, sort_keys=True) == before:
            return                                            # nothing changed: no new commit
        r['updated'] = now()
        tmp = res_path + '.tmp'
        json.dump(r, open(tmp, 'w'), indent=2); os.replace(tmp, res_path)
        p = subprocess.run([persist_cmd, res_path], capture_output=True, text=True)
        if p.returncode != 0:
            raise SystemExit(f'{item["id"]}: could not persist result ({r["status"]}); stopping')

    code = 1
    try:
        if r.get('status') in ('FAILED', 'NEEDS_REVIEW'):
            print(f'{item["id"]}: {r["status"]} needs a person; not touching it'); return 1
        token = access_token()
        title, uploads = check_channel(token)
        r['channel_title'] = title
        if r.get('status') == 'UPLOADING' and not r.get('video_id'):
            found = find_existing(token, uploads, item['title'], r.get('upload_started', ''))
            if found in (None, 'AMBIGUOUS'):
                persist(status='NEEDS_REVIEW', error='earlier run may have uploaded; video not found uniquely'
                        if found is None else 'several matching uploads found')
                return 1
            persist(status='UPLOADED', video_id=found, reconciled=True)
        if not r.get('video_id'):
            size = validate(item, video_path)
            persist(status='UPLOADING', upload_started=now(), bytes=size, error=None)
            try:
                vid = upload(token, video_path, size, item)
            except NoSession as e:
                persist(status='FAILED_PREUPLOAD', error=str(e))
                return 1
            except Fail as e:
                # Bytes were sent: a video may exist. Stay UPLOADING so the next run reconciles instead of re-uploading.
                persist(error=str(e))
                return 1
            persist(status='UPLOADED', video_id=vid,
                    url=('https://youtube.com/shorts/' if item.get('short') else 'https://www.youtube.com/watch?v=') + vid)
        status, state = 'PENDING', {}
        for i in range(POLL_TRIES):
            status, state = check_video(token, r['video_id'], item)
            if status == 'VERIFIED':
                break
            time.sleep(POLL)
        persist(status=status, verified=state if status == 'VERIFIED' else None, last_state=state, error=None)
        code = 0 if status == 'VERIFIED' else 2
    except Fail as e:
        if isinstance(e, WrongVideo):
            persist(status='FAILED', error=str(e))            # the video itself is wrong: a person must look
        elif r.get('video_id') or r.get('status') == 'UPLOADING':
            persist(error=str(e))                             # transient (token/network): keep state, retry later
        else:
            persist(status='FAILED_PREUPLOAD', error=str(e))
    except (urllib.error.URLError, TimeoutError) as e:
        persist(error='network error: ' + type(e).__name__)
    except SystemExit as e:
        print(sanitize(e)); return 1
    print(sanitize(json.dumps(r, indent=2)))
    return code


if __name__ == '__main__':
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    sys.exit(main(*sys.argv[1:]))
