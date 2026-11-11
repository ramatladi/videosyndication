"""Publish the six skincare channels' staged videos to YouTube with the YouTube Data API.

Runs in GitHub Actions (.github/workflows/skincare-upload.yml), hourly. Standard library only.

    python3 skincare-daily/yt_publish.py MEDIA_CHECKOUT [--since YYYY-MM-DD] [--max-uploads N] [--dry-run]

MEDIA_CHECKOUT is a checkout of the media branch holding skincare-daily/<DATE>/manifest.json and receipt-ledger.json
(sparse is fine: videos, thumbnails and captions are downloaded from their raw.githubusercontent.com URLs and checked
against the manifest's SHA-256).

For every `ready` manifest item whose ledger row has no youtube_id:
  1. If the channel already has an upload with exactly the same title (e.g. posted earlier by hand or by Codex), that
     video is adopted: its ID is recorded and nothing is uploaded again.
  2. Otherwise it is uploaded. A slot still in the future is scheduled for its own SAST slot time (private + publishAt).
     An overdue slot is posted now; further overdue items on the same channel are spaced an hour apart so a backlog
     never lands as a burst.
  3. The thumbnail is set (and English captions when YT_SK_CAPTIONS=1: 400 quota units each, and the token must
     include the youtube.force-ssl scope). A failure there is logged and never blocks the video.
  4. The video ID goes into the ledger row (youtube_id, youtube_status, publish_at) and a result file
     skincare-daily/<DATE>/yt/<slug>.json, committed and pushed to media after every state change.

Secrets (env): YT_SK_CLIENT_ID, YT_SK_CLIENT_SECRET (the Google app) and, per channel key in CHANNELS.json,
YT_SK_REFRESH_<KEY> and YT_SK_CHANNEL_<KEY>. A channel without its secrets is skipped (not signed in yet).

Result states: UPLOADING (marker tag saved before any bytes) -> UPLOADED -> PENDING -> VERIFIED; ADOPTED (existing
video found by title); FAILED_PREUPLOAD (nothing sent; retried next run); FAILED / NEEDS_REVIEW (a person must look).
Exit code 0 when nothing needs a person, 1 otherwise.
"""
import datetime as dt, hashlib, json, os, re, secrets, subprocess, sys, time, urllib.error, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CHANNELS = {h: v for h, v in json.load(open(os.path.join(HERE, 'CHANNELS.json'))).items() if not h.startswith('_')}
TEST = os.environ.get('YT_TEST_MODE') == '1'
TOKEN_URL = os.environ['YT_TOKEN_URL'] if TEST else 'https://oauth2.googleapis.com/token'
API = os.environ['YT_API_BASE'] if TEST else 'https://www.googleapis.com'
POLL, POLL_TRIES = (0.01, 3) if TEST else (15.0, 8)
SAST = dt.timezone(dt.timedelta(hours=2))
TOKEN_RE = re.compile(r'(ya29\.[\w.-]+|1//[\w.-]+|GOCSPX-[\w-]+|Bearer\s+\S+)')
_secrets_seen = set()


class Fail(Exception):
    pass


class Quota(Fail):
    """Daily API quota used up: stop uploading this run; the next hourly run continues."""


class NoSession(Fail):
    """No resumable session was opened, so no video can exist."""


class WrongVideo(Fail):
    pass


def sanitize(text):
    text = str(text)
    for k, v in os.environ.items():
        if k.startswith('YT_SK_') and v and len(v) >= 4:
            text = text.replace(v, '[redacted]')
    for v in _secrets_seen:
        text = text.replace(v, '[redacted]')
    return TOKEN_RE.sub('[redacted]', text)[:1500]


def _gerr(raw):
    try:
        e = json.loads(raw).get('error')
    except Exception:  # noqa: BLE001
        return '', 'non-JSON error body'
    if isinstance(e, dict):
        reasons = ','.join(x.get('reason', '') for x in e.get('errors', []) if isinstance(x, dict))
        return reasons, f"{e.get('status', '')} {reasons}".strip()
    if isinstance(e, str):
        return e, e if re.fullmatch(r'[a-z_]{3,40}', e) else 'oauth error'
    return '', 'error'


def req(method, url, data=None, headers=None, timeout=120):
    r = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        reasons, msg = _gerr(e.read()[:4000])
        text = f'{method} {urllib.parse.urlparse(url).path} -> HTTP {e.code} {msg}'
        if 'quotaExceeded' in reasons or 'uploadLimitExceeded' in reasons or 'dailyLimitExceeded' in reasons:
            raise Quota(text) from None
        raise Fail(text) from None


class Channel:
    def __init__(self, handle, key):
        self.handle, self.key = handle, key
        self.channel_id = os.environ.get(f'YT_SK_CHANNEL_{key}', '').strip()
        self.refresh = os.environ.get(f'YT_SK_REFRESH_{key}', '').strip()
        self._token, self._uploads, self._titles = None, None, None

    def ready(self):
        return bool(self.channel_id and self.refresh and os.environ.get('YT_SK_CLIENT_ID')
                    and os.environ.get('YT_SK_CLIENT_SECRET'))

    def token(self):
        if self._token:
            return self._token
        body = urllib.parse.urlencode({'client_id': os.environ['YT_SK_CLIENT_ID'],
                                       'client_secret': os.environ['YT_SK_CLIENT_SECRET'],
                                       'refresh_token': self.refresh, 'grant_type': 'refresh_token'}).encode()
        _, _, raw = req('POST', TOKEN_URL, body, {'Content-Type': 'application/x-www-form-urlencoded'})
        tok = json.loads(raw).get('access_token')
        if not tok:
            raise Fail('token endpoint returned no access_token')
        _secrets_seen.add(tok)
        self._token = tok
        d = self.get('/youtube/v3/channels', {'part': 'id,contentDetails', 'mine': 'true'})
        ids = [c['id'] for c in d.get('items', [])]
        if ids != [self.channel_id]:
            self._token = None
            raise Fail(f'{self.handle}: token is for channel(s) {ids}, expected {self.channel_id}; refusing')
        self._uploads = d['items'][0].get('contentDetails', {}).get('relatedPlaylists', {}).get('uploads')
        return tok

    def get(self, path, params):
        _, _, raw = req('GET', API + path + '?' + urllib.parse.urlencode(params), None,
                        {'Authorization': 'Bearer ' + self.token()})
        return json.loads(raw) if raw else {}

    def recent_uploads(self, pages=4):
        """{video_id: snippet} for the channel's latest uploads (50 per page, 1 quota unit per page)."""
        if self._titles is not None:
            return self._titles
        self.token()
        out, page = {}, None
        for _ in range(pages):
            p = {'part': 'snippet', 'playlistId': self._uploads, 'maxResults': '50'}
            if page:
                p['pageToken'] = page
            try:
                d = self.get('/youtube/v3/playlistItems', p)
            except Fail as e:
                if 'playlistNotFound' in str(e):        # brand-new channel with no uploads yet
                    break
                raise
            for it in d.get('items', []):
                sn = it.get('snippet', {})
                vid = (sn.get('resourceId') or {}).get('videoId')
                if vid:
                    out[vid] = sn
            page = d.get('nextPageToken')
            if not page:
                break
        self._titles = out
        return out

    def tags_of(self, ids):
        if not ids:
            return {}
        d = self.get('/youtube/v3/videos', {'part': 'snippet', 'id': ','.join(ids[:50])})
        return {x['id']: x.get('snippet', {}).get('tags') or [] for x in d.get('items', [])}


def fetch(url, sha, dest):
    with urllib.request.urlopen(urllib.request.Request(url), timeout=600) as r, open(dest, 'wb') as f:
        h = hashlib.sha256()
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            h.update(b); f.write(b)
    if sha and h.hexdigest() != sha:
        raise NoSession(f'checksum mismatch for {os.path.basename(dest)}')
    return dest


def resource(item, marker, publish_at):
    status = {'privacyStatus': 'public', 'selfDeclaredMadeForKids': bool(item.get('made_for_kids', False)),
              'embeddable': True, 'license': 'youtube',
              'containsSyntheticMedia': bool(item.get('altered_or_synthetic_content', False))}
    if publish_at:
        status['privacyStatus'] = 'private'
        status['publishAt'] = publish_at
    tags, total = [], len(marker) + 2
    for t in item.get('tags', []):
        if total + len(t) + 2 > 480:
            break
        tags.append(t); total += len(t) + 2
    return {'paidProductPlacementDetails': {'hasPaidProductPlacement': bool(item.get('paid_promotion', True))},
            'snippet': {'title': item['title'], 'description': item['description'], 'tags': tags + [marker],
                        'categoryId': '26', 'defaultLanguage': item.get('default_language', 'en'),
                        'defaultAudioLanguage': item.get('audio_language', 'en')},
            'status': status}


def upload_video(ch, path, item, marker, publish_at):
    size = os.path.getsize(path)
    with open(path, 'rb') as f:
        head = f.read(12)
    if size < 10_000 or head[4:8] != b'ftyp':
        raise NoSession(f'not a usable MP4 ({size} bytes)')
    url = API + '/upload/youtube/v3/videos?' + urllib.parse.urlencode(
        {'uploadType': 'resumable', 'part': 'snippet,status,paidProductPlacementDetails', 'notifySubscribers': 'true'})
    try:
        _, headers, _ = req('POST', url, json.dumps(resource(item, marker, publish_at)).encode(), {
            'Authorization': 'Bearer ' + ch.token(), 'Content-Type': 'application/json; charset=UTF-8',
            'X-Upload-Content-Type': 'video/mp4', 'X-Upload-Content-Length': str(size)})
    except Quota:
        raise
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
            r = urllib.request.Request(session, data=data, method='PUT', headers={
                'Content-Length': str(len(data)), 'Content-Range': f'bytes {start}-{end}/{size}'})
            for attempt in range(5):
                try:
                    with urllib.request.urlopen(r, timeout=600) as resp:
                        return json.loads(resp.read())['id']
                except urllib.error.HTTPError as e:
                    if e.code == 308:
                        rng = e.headers.get('Range')
                        start = int(rng.split('-')[1]) + 1 if rng else end + 1
                        break
                    if e.code in (500, 502, 503, 504) and attempt < 4:
                        time.sleep(2 ** attempt * 3); continue
                    raise Fail(f'upload chunk -> HTTP {e.code} {_gerr(e.read()[:4000])[1]}') from None
                except (urllib.error.URLError, TimeoutError):
                    if attempt < 4:
                        time.sleep(2 ** attempt * 3); continue
                    raise Fail('upload chunk: network error after retries') from None
            if start >= size:
                raise Fail('upload ended without a video resource')


def set_thumbnail(ch, vid, path):
    url = API + '/upload/youtube/v3/thumbnails/set?' + urllib.parse.urlencode({'videoId': vid, 'uploadType': 'media'})
    req('POST', url, open(path, 'rb').read(), {'Authorization': 'Bearer ' + ch.token(), 'Content-Type': 'image/jpeg'})


def add_captions(ch, vid, path, lang):
    boundary = 'skcap' + secrets.token_hex(8)
    meta = json.dumps({'snippet': {'videoId': vid, 'language': lang, 'name': 'English', 'isDraft': False}})
    body = (f'--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{meta}\r\n'
            f'--{boundary}\r\nContent-Type: application/octet-stream\r\n\r\n').encode() + open(path, 'rb').read() + \
        f'\r\n--{boundary}--\r\n'.encode()
    url = API + '/upload/youtube/v3/captions?' + urllib.parse.urlencode({'part': 'snippet', 'uploadType': 'multipart'})
    req('POST', url, body, {'Authorization': 'Bearer ' + ch.token(),
                             'Content-Type': f'multipart/related; boundary={boundary}'})


def check_video(ch, vid, want_publish_at):
    d = ch.get('/youtube/v3/videos', {'part': 'snippet,status', 'id': vid})
    if not d.get('items'):
        return 'PENDING', {'note': 'not visible yet'}
    v = d['items'][0]; st = v.get('status', {})
    s = {'channelId': v['snippet'].get('channelId'), 'uploadStatus': st.get('uploadStatus'),
         'privacyStatus': st.get('privacyStatus'), 'publishAt': st.get('publishAt'),
         'rejectionReason': st.get('rejectionReason'), 'failureReason': st.get('failureReason')}
    if s['channelId'] != ch.channel_id:
        raise WrongVideo(f'video is on channel {s["channelId"]}, expected {ch.channel_id}')
    if s['uploadStatus'] in ('rejected', 'failed', 'deleted'):
        raise WrongVideo(f'YouTube {s["uploadStatus"]} the video ({s["rejectionReason"] or s["failureReason"]})')
    if want_publish_at:
        if s['privacyStatus'] == 'public':
            pass                                   # already went live at its time
        elif s['privacyStatus'] != 'private' or (s['publishAt'] or '')[:16] != want_publish_at[:16]:
            raise WrongVideo(f'schedule is {s["privacyStatus"]} {s["publishAt"]}, expected private until {want_publish_at}')
    elif s['privacyStatus'] != 'public':
        raise WrongVideo(f'privacy is {s["privacyStatus"]}, expected public (an unverified Google app locks API '
                         'uploads to private until Google audits it)')
    return ('VERIFIED' if s['uploadStatus'] == 'processed' else 'PENDING'), s


def iso(t):
    return t.astimezone(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def slot_utc(slot_sast):
    return dt.datetime.strptime(slot_sast, '%Y-%m-%d %H:%M').replace(tzinfo=SAST).astimezone(dt.timezone.utc)


class Media:
    """The media-branch checkout: result files + ledger rows, pushed after every change."""

    def __init__(self, root, dry):
        self.root, self.dry = root, dry

    def push(self, paths, msg):
        if self.dry:
            return
        g = ['git', '-C', self.root]
        subprocess.run(g + ['add', '--sparse', '--'] + paths, check=True)
        if subprocess.run(g + ['diff', '--cached', '--quiet']).returncode == 0:
            return
        subprocess.run(g + ['commit', '-q', '-m', msg], check=True)
        for i in range(6):
            if subprocess.run(g + ['push', '-q', 'origin', 'HEAD:media'], capture_output=True).returncode == 0:
                return
            if subprocess.run(g + ['pull', '-q', '--rebase', 'origin', 'media'], capture_output=True).returncode != 0:
                subprocess.run(g + ['rebase', '--abort'], capture_output=True)
            time.sleep(2 * (i + 1))
        raise SystemExit('could not push to media; stopping so no state is lost')


def main(argv):
    if not argv or argv[0].startswith('-'):
        sys.exit(__doc__)
    root, since, max_up, dry = argv[0], '2026-11-08', 12, False
    a = argv[1:]
    while a:
        k = a.pop(0)
        if k == '--since':
            since = a.pop(0)
        elif k == '--max-uploads':
            max_up = int(a.pop(0))
        elif k == '--dry-run':
            dry = True
        else:
            sys.exit(f'unknown option {k}')
    media = Media(root, dry)
    chans = {h: Channel(h, v['key']) for h, v in CHANNELS.items()}
    not_ready = [h for h, c in chans.items() if not c.ready()]
    if not_ready:
        print('not signed in yet (skipped):', ', '.join(not_ready))
    base = os.path.join(root, 'skincare-daily')
    days = sorted(d for d in os.listdir(base) if re.fullmatch(r'\d{4}-\d\d-\d\d', d) and d >= since
                  and os.path.exists(os.path.join(base, d, 'manifest.json')))
    now = dt.datetime.now(dt.timezone.utc)

    # Work list, in slot order.
    work = []
    for day in days:
        m = json.load(open(os.path.join(base, day, 'manifest.json')))
        for it in m.get('items', []):
            if it.get('status') == 'ready' and it.get('handle') in chans:
                work.append((slot_utc(it['slot_sast']), day, it))
    work.sort(key=lambda w: (w[0], w[2]['handle']))

    # Overdue items are spaced an hour apart per channel; continue after anything already assigned.
    next_overdue = {}
    for _, day, it in work:
        rf = os.path.join(base, day, 'yt', it['slug'] + '.json')
        if os.path.exists(rf):
            r = json.load(open(rf))
            if r.get('overdue') and r.get('publish_at'):
                t = dt.datetime.strptime(r['publish_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=dt.timezone.utc)
                next_overdue[it['handle']] = max(next_overdue.get(it['handle'], now), t + dt.timedelta(hours=1))

    uploads, needs_person, quota_hit, summary = 0, [], False, []
    for slot, day, it in work:
        ch = chans[it['handle']]
        ledger_path = os.path.join(base, day, 'receipt-ledger.json')
        L = json.load(open(ledger_path))
        row = next((r for r in L['items'] if r.get('manifest_slug') == it['slug']), None)
        if row is None or row.get('youtube_id'):
            continue
        if not ch.ready():
            continue
        rdir = os.path.join(base, day, 'yt'); os.makedirs(rdir, exist_ok=True)
        rpath = os.path.join(rdir, it['slug'] + '.json')
        r = json.load(open(rpath)) if os.path.exists(rpath) else {}
        r.update(slug=it['slug'], handle=it['handle'], title=it['title'], slot_sast=it['slot_sast'])
        rel = [os.path.relpath(rpath, root), os.path.relpath(ledger_path, root)]

        def persist(**kw):
            if kw.get('error'):
                kw['error'] = sanitize(kw['error'])
            r.update(kw); r['updated'] = iso(dt.datetime.now(dt.timezone.utc))
            json.dump(r, open(rpath + '.tmp', 'w'), indent=2); os.replace(rpath + '.tmp', rpath)
            if r.get('video_id') and r.get('status') in ('UPLOADED', 'PENDING', 'VERIFIED', 'ADOPTED'):
                LL = json.load(open(ledger_path))
                for x in LL['items']:
                    if x.get('manifest_slug') == it['slug']:
                        x['youtube_id'] = r['video_id']
                        x['status'] = 'youtube_adopted' if r['status'] == 'ADOPTED' else (
                            'youtube_scheduled' if r.get('publish_at') else 'youtube_published')
                        x['publish_at'] = r.get('publish_at') or r.get('published_now')
                LL['youtube_ids_recorded'] = sum(1 for x in LL['items'] if x.get('youtube_id'))
                json.dump(LL, open(ledger_path + '.tmp', 'w'), indent=2); os.replace(ledger_path + '.tmp', ledger_path)
            media.push(rel, f'skincare yt: {day} {it["handle"]} {it["slug"]} {r["status"]}')

        if r.get('status') in ('FAILED', 'NEEDS_REVIEW'):
            needs_person.append(f'{day} {it["handle"]} {it["slug"]}: {r["status"]} {r.get("error", "")}')
            continue
        try:
            # Already on the channel? (exact title; or our marker from an interrupted attempt)
            if not r.get('video_id'):
                ups = ch.recent_uploads()
                same = [v for v, sn in ups.items() if sn.get('title') == it['title']]
                if r.get('status') == 'UPLOADING' and r.get('upload_marker'):
                    tagged = [v for v, tags in ch.tags_of(list(ups)).items() if r['upload_marker'] in tags]
                    if len(tagged) == 1:
                        persist(status='UPLOADED', video_id=tagged[0], reconciled=True)
                    elif not same:
                        persist(status='NEEDS_REVIEW', error='earlier upload attempt cannot be found by its marker')
                        needs_person.append(f'{day} {it["handle"]} {it["slug"]}: NEEDS_REVIEW'); continue
                if not r.get('video_id') and same:
                    persist(status='ADOPTED', video_id=same[0], error=None,
                            note='already on the channel with this exact title; not uploaded again')
                    summary.append(f'{it["handle"]} {it["slot_sast"]} adopted existing {same[0]}')
                    continue
            if not r.get('video_id'):
                if quota_hit or uploads >= max_up:
                    continue
                if dry:
                    summary.append(f'{it["handle"]} {it["slot_sast"]} would upload'); uploads += 1; continue
                if slot > now + dt.timedelta(minutes=10):
                    publish_at, overdue = iso(slot), False
                else:
                    t = next_overdue.get(ch.handle)
                    publish_at, overdue = (iso(t) if t and t > now + dt.timedelta(minutes=10) else None), True
                    next_overdue[ch.handle] = max(t or now, now) + dt.timedelta(hours=1)
                tmp = os.path.join(os.environ.get('RUNNER_TEMP', '/tmp'), it['slug'] + '.mp4')
                try:
                    fetch(it['media_url'], it.get('sha256'), tmp)
                except (urllib.error.URLError, TimeoutError) as e:
                    raise NoSession(f'video download failed: {type(e).__name__}') from None
                marker = 'skref' + secrets.token_hex(6)
                persist(status='UPLOADING', upload_marker=marker, publish_at=publish_at, overdue=overdue,
                        upload_started=iso(dt.datetime.now(dt.timezone.utc)), error=None)
                try:
                    vid = upload_video(ch, tmp, it, marker, publish_at)
                except NoSession as e:
                    persist(status='FAILED_PREUPLOAD', error=str(e)); continue
                except Quota as e:
                    persist(status='FAILED_PREUPLOAD', error=str(e)); quota_hit = True; continue
                except Fail as e:
                    persist(error=str(e)); continue           # bytes may be on YouTube: reconcile next run
                finally:
                    if os.path.exists(tmp):
                        os.remove(tmp)
                uploads += 1
                persist(status='UPLOADED', video_id=vid, published_now=None if publish_at else r['upload_started'],
                        url=('https://youtube.com/shorts/' if it.get('format') == 'short'
                             else 'https://www.youtube.com/watch?v=') + vid)
                summary.append(f'{it["handle"]} {it["slot_sast"]} uploaded {vid} '
                               f'({"scheduled " + publish_at if publish_at else "public now"})')
            # Extras (once each; never blocking)
            if r['status'] != 'ADOPTED':
                for kind, url_k, sha_k, ext, fn in (
                        ('thumbnail', 'thumbnail_url', 'thumbnail_sha256', '.jpg',
                         lambda p: set_thumbnail(ch, r['video_id'], p)),
                        ('captions', 'captions_url', 'captions_sha256', '.srt',
                         lambda p: add_captions(ch, r['video_id'], p, it.get('default_language', 'en')))):
                    if r.get(kind) == 'done' or not it.get(url_k) or quota_hit:
                        continue
                    if kind == 'captions' and os.environ.get('YT_SK_CAPTIONS') != '1':   # 400 quota units each
                        continue
                    p = os.path.join(os.environ.get('RUNNER_TEMP', '/tmp'), it['slug'] + ext)
                    try:
                        fn(fetch(it[url_k], it.get(sha_k), p)); persist(**{kind: 'done'})
                    except Quota as e:
                        quota_hit = True; persist(**{kind: 'quota: retry next run'})
                    except (Fail, urllib.error.URLError, TimeoutError) as e:
                        persist(**{kind: 'failed: ' + sanitize(e)})
                    finally:
                        if os.path.exists(p):
                            os.remove(p)
                status, state = 'PENDING', {}
                for _ in range(POLL_TRIES):
                    status, state = check_video(ch, r['video_id'], r.get('publish_at'))
                    if status == 'VERIFIED':
                        break
                    time.sleep(POLL)
                persist(status=status, last_state=state, error=None)
        except WrongVideo as e:
            persist(status='FAILED', error=str(e))
            needs_person.append(f'{day} {it["handle"]} {it["slug"]}: FAILED {sanitize(e)}')
        except Quota as e:
            quota_hit = True
            print('quota:', sanitize(e))
        except Fail as e:
            if r.get('video_id') or r.get('status') == 'UPLOADING':
                persist(error=str(e))
            else:
                print(f'{it["handle"]} {it["slug"]}: {sanitize(e)}')
        except (urllib.error.URLError, TimeoutError) as e:
            print(f'{it["handle"]} {it["slug"]}: network {type(e).__name__}')

    print('\n'.join(summary) or 'nothing new this run')
    if quota_hit:
        print('YouTube API quota reached; remaining items continue on the next hourly run.')
    if needs_person:
        print('NEEDS A PERSON:\n' + '\n'.join(needs_person))
    return 1 if needs_person else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
