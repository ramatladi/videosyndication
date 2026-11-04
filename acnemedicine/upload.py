"""Upload one queued video to the Acne Medicine Johannesburg YouTube channel through the YouTube Data API.

Runs in GitHub Actions (.github/workflows/acne-upload.yml). Standard library only.

    python3 acnemedicine/upload.py acnemedicine/queue/<id>.json

Credentials come only from environment variables (GitHub Actions secrets) and are never printed:
    YT_ACNE_CLIENT_ID, YT_ACNE_CLIENT_SECRET, YT_ACNE_REFRESH_TOKEN

Safety rules (fail closed):
- The token must belong to EXPECTED_CHANNEL_ID, or nothing is uploaded.
- A queue item with a result file already present is never uploaded twice.
- After upload the video is read back and its channel, upload status and privacy are checked.

Writes acnemedicine/results/<id>.json (no secrets) and exits non-zero on any failure.
"""
import json, os, sys, time, urllib.request, urllib.parse, urllib.error, tempfile, hashlib

EXPECTED_CHANNEL_ID = (os.environ.get('YT_ACNE_CHANNEL_ID')
                       or open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'CHANNEL_ID')).read().strip())
TOKEN_URL = os.environ.get('YT_TOKEN_URL', 'https://oauth2.googleapis.com/token')
API = os.environ.get('YT_API_BASE', 'https://www.googleapis.com')
ALLOWED_PRIVACY = {'public', 'unlisted', 'private'}
ALLOWED_HOSTS = ('raw.githubusercontent.com', 'github.com', 'objects.githubusercontent.com', '127.0.0.1', 'localhost')
MAX_BYTES = 2 * 1024 ** 3


class Fail(Exception):
    pass


def _req(method, url, data=None, headers=None, timeout=120):
    r = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        body = e.read()[:2000].decode('utf-8', 'replace')
        raise Fail(f'{method} {url.split("?")[0]} -> HTTP {e.code}: {body}') from None


def access_token():
    need = ['YT_ACNE_CLIENT_ID', 'YT_ACNE_CLIENT_SECRET', 'YT_ACNE_REFRESH_TOKEN']
    missing = [k for k in need if not os.environ.get(k)]
    if missing:
        raise Fail('missing secrets: ' + ', '.join(missing))
    body = urllib.parse.urlencode({
        'client_id': os.environ['YT_ACNE_CLIENT_ID'],
        'client_secret': os.environ['YT_ACNE_CLIENT_SECRET'],
        'refresh_token': os.environ['YT_ACNE_REFRESH_TOKEN'],
        'grant_type': 'refresh_token'}).encode()
    _, _, raw = _req('POST', TOKEN_URL, body, {'Content-Type': 'application/x-www-form-urlencoded'})
    tok = json.loads(raw).get('access_token')
    if not tok:
        raise Fail('token endpoint returned no access_token')
    return tok


def api_json(method, path, token, payload=None, params=None):
    url = API + path + ('?' + urllib.parse.urlencode(params) if params else '')
    h = {'Authorization': 'Bearer ' + token}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        h['Content-Type'] = 'application/json; charset=UTF-8'
    _, headers, raw = _req(method, url, data, h)
    return headers, (json.loads(raw) if raw else {})


def check_channel(token):
    _, d = api_json('GET', '/youtube/v3/channels', token, params={'part': 'id,snippet', 'mine': 'true'})
    ids = [c['id'] for c in d.get('items', [])]
    if ids != [EXPECTED_CHANNEL_ID]:
        raise Fail(f'token is for channel(s) {ids}, expected {EXPECTED_CHANNEL_ID}; refusing to upload')
    return d['items'][0]['snippet'].get('title', '')


def validate(item):
    for k in ('id', 'title', 'description', 'media_url'):
        if not str(item.get(k, '')).strip():
            raise Fail(f'queue item missing "{k}"')
    if not all(c.isalnum() or c in '-_' for c in item['id']):
        raise Fail('id may only contain letters, digits, - and _')
    if len(item['title']) > 100:
        raise Fail('title longer than 100 characters')
    if '<' in item['title'] or '>' in item['title']:
        raise Fail('title may not contain < or >')
    if len(item['description'].encode()) > 5000:
        raise Fail('description longer than 5000 bytes')
    if item.get('privacy', 'public') not in ALLOWED_PRIVACY:
        raise Fail('privacy must be public, unlisted or private')
    host = urllib.parse.urlparse(item['media_url']).hostname or ''
    if host not in ALLOWED_HOSTS:
        raise Fail(f'media_url host {host!r} not allowed (GitHub only)')
    tags = item.get('tags', [])
    if sum(len(t) + 2 for t in tags) > 480:
        raise Fail('tags too long')


def download(url, dest):
    r = urllib.request.Request(url, headers={'User-Agent': 'videosyndication-uploader'})
    h = hashlib.sha256(); n = 0
    with urllib.request.urlopen(r, timeout=300) as resp, open(dest, 'wb') as f:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            n += len(chunk)
            if n > MAX_BYTES:
                raise Fail('video larger than 2 GB')
            h.update(chunk); f.write(chunk)
    with open(dest, 'rb') as f:
        head = f.read(12)
    if n < 10_000 or head[4:8] != b'ftyp':
        raise Fail(f'downloaded file is not an MP4 ({n} bytes)')
    return n, h.hexdigest()


def resource(item):
    status = {
        'privacyStatus': item.get('privacy', 'public'),
        'selfDeclaredMadeForKids': False,
        'embeddable': True,
        'license': 'youtube',
        # Sello's standing choice: no altered/synthetic label on his uploads.
        'containsSyntheticMedia': bool(item.get('contains_synthetic_media', False)),
    }
    if item.get('publish_at'):
        status['privacyStatus'] = 'private'          # YouTube requires private + publishAt for scheduling
        status['publishAt'] = item['publish_at']
    return {
        'snippet': {
            'title': item['title'],
            'description': item['description'],
            'tags': item.get('tags', []),
            'categoryId': str(item.get('category_id', '26')),   # 26 = Howto & Style
            'defaultLanguage': item.get('language', 'en'),
            'defaultAudioLanguage': item.get('language', 'en'),
        },
        'status': status,
    }


def upload(token, path, size, item):
    meta = json.dumps(resource(item)).encode()
    url = API + '/upload/youtube/v3/videos?' + urllib.parse.urlencode(
        {'uploadType': 'resumable', 'part': 'snippet,status', 'notifySubscribers': 'true'})
    _, headers, _ = _req('POST', url, meta, {
        'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json; charset=UTF-8',
        'X-Upload-Content-Type': 'video/mp4', 'X-Upload-Content-Length': str(size)})
    session = headers.get('Location') or headers.get('location')
    if not session:
        raise Fail('no resumable upload session returned')
    chunk = 8 * 1024 * 1024
    with open(path, 'rb') as f:
        start = 0
        while start < size:
            f.seek(start)
            data = f.read(chunk)
            end = start + len(data) - 1
            req = urllib.request.Request(session, data=data, method='PUT', headers={
                'Content-Length': str(len(data)), 'Content-Range': f'bytes {start}-{end}/{size}'})
            for attempt in range(5):
                try:
                    with urllib.request.urlopen(req, timeout=600) as resp:
                        return json.loads(resp.read())                     # 200/201: done
                except urllib.error.HTTPError as e:
                    if e.code == 308:                                    # chunk accepted, continue
                        rng = e.headers.get('Range')
                        start = int(rng.split('-')[1]) + 1 if rng else end + 1
                        break
                    if e.code in (500, 502, 503, 504) and attempt < 4:
                        time.sleep(2 ** attempt * 3); continue
                    raise Fail(f'upload chunk -> HTTP {e.code}: {e.read()[:1000].decode("utf-8", "replace")}')
                except (urllib.error.URLError, TimeoutError):
                    if attempt < 4:
                        time.sleep(2 ** attempt * 3); continue
                    raise
            else:
                raise Fail('upload chunk failed after retries')
    raise Fail('upload ended without a video resource')


def verify(token, vid, item, tries=6):
    last = None
    for i in range(tries):
        _, d = api_json('GET', '/youtube/v3/videos', token, params={'part': 'snippet,status', 'id': vid})
        items = d.get('items', [])
        if items:
            v = items[0]
            last = {'channelId': v['snippet'].get('channelId'), 'uploadStatus': v['status'].get('uploadStatus'),
                    'privacyStatus': v['status'].get('privacyStatus'), 'publishAt': v['status'].get('publishAt'),
                    'rejectionReason': v['status'].get('rejectionReason'),
                    'failureReason': v['status'].get('failureReason')}
            if last['channelId'] != EXPECTED_CHANNEL_ID:
                raise Fail(f'video landed on channel {last["channelId"]}, expected {EXPECTED_CHANNEL_ID}')
            if last['uploadStatus'] in ('rejected', 'failed', 'deleted'):
                raise Fail(f'YouTube {last["uploadStatus"]} the video: {last}')
            want = 'private' if item.get('publish_at') else item.get('privacy', 'public')
            if last['privacyStatus'] != want:
                raise Fail(f'privacy is {last["privacyStatus"]}, expected {want} (locked by YouTube?)')
            if last['uploadStatus'] in ('processed', 'uploaded'):
                return last
        time.sleep(min(30, 5 * (i + 1)))
    if last:
        return last
    raise Fail('uploaded video not found when reading it back')


def main(qpath):
    item = json.load(open(qpath))
    if not all(c.isalnum() or c in '-_' for c in str(item.get('id', ''))) or not item.get('id'):
        raise SystemExit('queue item has no valid id')
    root = os.path.dirname(os.path.dirname(os.path.abspath(qpath)))
    res_dir = os.path.join(root, 'results'); os.makedirs(res_dir, exist_ok=True)
    res_path = os.path.join(res_dir, item['id'] + '.json')
    if os.path.exists(res_path) and json.load(open(res_path)).get('video_id'):
        print(f'{item["id"]}: already uploaded, skipping'); return 0
    result = {'id': item['id'], 'title': item['title'], 'channel_id': EXPECTED_CHANNEL_ID,
              'started': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    try:
        validate(item)
        token = access_token()
        result['channel_title'] = check_channel(token)
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, 'v.mp4')
            size, sha = download(item['media_url'], path)
            result.update(bytes=size, sha256=sha)
            v = upload(token, path, size, item)
        result['video_id'] = v['id']
        result['url'] = ('https://youtube.com/shorts/' if item.get('short') else 'https://www.youtube.com/watch?v=') + v['id']
        result['verified'] = verify(token, v['id'], item)
        result['status'] = 'UPLOADED'
        code = 0
    except Exception as e:  # noqa: BLE001 - record any failure, never a secret (none are in messages)
        result['status'] = 'FAILED'
        result['error'] = str(e)[:1500]
        code = 1
    result['finished'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    json.dump(result, open(res_path, 'w'), indent=2)
    print(json.dumps(result, indent=2))
    return code


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
