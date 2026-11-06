"""Build one day of Acne Medicine Johannesburg posts from a plan and stage them for the Cloudflare uploader.

    python3 acnemedicine/day.py build acnemedicine/days/<YYYY-MM-DD>/plan.json      # renders into out/<date>/
    python3 acnemedicine/day.py stage acnemedicine/days/<YYYY-MM-DD>/plan.json      # pushes to the media branch
    python3 acnemedicine/day.py fetch                                                # downloads the photo pool

Plan: {"date": "2026-11-07", "items": [ {
    "id": "amj-20261107-s1", "slot": "10:00", "format": "short" | "video",
    "product": "breakout clearing booster", "source": "<dermalogica.co.za product URL>",
    "title": "…", "hook": "…", "facts": ["…"], "tags": ["…"],
    "thumb": {"photo": "<pexels id>", "title": "…", "kicker": "…"},
    "scenes": [ {"photo": "<pexels id>", "caption": "…", "say": "…"} ] } ]}
Photos come from acnemedicine/photos/pool.json (free Pexels photos, credited in the description only).
Staged on the media branch under acnemedicine/<date>/: <id>.mp4, <id>.jpg, <id>.json, manifest.json.
"""
import datetime as dt, hashlib, json, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SHOP = 'https://acnemedicine.co.za/'
SAST = dt.timezone(dt.timedelta(hours=2))


def pool():
    return {p['id']: p for p in json.load(open(f'{HERE}/photos/pool.json'))}


def photo_path(pid):
    return f'{HERE}/photos/pexels/{pid}.jpg'


def metadata(plan, it, P):
    ids = [s['photo'] for s in it['scenes']] + [it['thumb']['photo']]
    names = []
    for i in ids:
        if P[i]['by'] not in names:
            names.append(P[i]['by'])
    desc = '\n'.join([
        it['hook'], '',
        'We earn a commission if you buy through our link.', '',
        *[f'• {f}' for f in it['facts']], '',
        f'Shop: {SHOP}', '',
        'General product information, not medical advice.', '',
        'Photos from Pexels (free licence): ' + ', '.join(names), '',
        ' '.join('#' + t.replace(' ', '') for t in it['tags'][:3]),
    ])
    h, m = map(int, it['slot'].split(':'))
    local = dt.datetime.fromisoformat(plan['date']).replace(hour=h, minute=m, tzinfo=SAST)
    title = it['title']
    assert len(title) <= 100 and '<' not in title and '>' not in title, title
    assert len(desc.encode()) <= 5000
    return {'id': it['id'], 'title': title, 'description': desc, 'tags': it['tags'],
            'publish_at': local.astimezone(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'publish_at_sast': local.strftime('%Y-%m-%d %H:%M'), 'short': it['format'] == 'short',
            'privacy': 'public', 'paid_promotion': True, 'contains_synthetic_media': False,
            'made_for_kids': False, 'category_id': '26', 'language': 'en', 'product': it['product'],
            'product_source': it['source'], 'video': f"{it['id']}.mp4", 'thumbnail': f"{it['id']}.jpg"}


def build(plan_path):
    plan = json.load(open(plan_path)); P = pool()
    out = f"{ROOT}/out/{plan['date']}"; os.makedirs(out, exist_ok=True)
    for it in plan['items']:
        for s in it['scenes'] + [it['thumb']]:
            assert s['photo'] in P, f"photo {s['photo']} not in pool"
        spec = {'id': it['id'], 'format': it['format'], 'voice': 'af_heart', 'product': it['product'],
                'thumbnail': {'image': photo_path(it['thumb']['photo']), 'title': it['thumb']['title'],
                              'kicker': it['thumb'].get('kicker', '')},
                'scenes': [{'image': photo_path(s['photo']), 'caption': s['caption'], 'say': s['say'],
                            'fit': s.get('fit', 'auto'), 'cx': P[s['photo']].get('cx', 0.5)} for s in it['scenes']]}
        sp = f"{out}/{it['id']}.spec.json"; json.dump(spec, open(sp, 'w'), indent=1)
        mp4, jpg = f"{out}/{it['id']}.mp4", f"{out}/{it['id']}.jpg"
        if not os.path.exists(mp4):
            subprocess.run([sys.executable, f'{HERE}/build_video.py', sp, mp4, jpg], check=True)
        json.dump(metadata(plan, it, P), open(f"{out}/{it['id']}.json", 'w'), indent=1, ensure_ascii=False)
        dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', mp4],
                                   capture_output=True, text=True).stdout)
        if it['format'] == 'short':
            assert dur < 60, f"{it['id']} is {dur:.1f}s; Shorts must be under 60 s"
        print(f"{it['id']}: {dur:.1f}s")


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def fetch(_=None):
    """Download every pool photo that isn't here yet (photos are not kept in git)."""
    os.makedirs(f'{HERE}/photos/pexels', exist_ok=True)
    for pid in pool():
        f = photo_path(pid)
        if not os.path.exists(f):
            subprocess.run(['curl', '-sS', '-m', '60', '-o', f,
                            f'https://images.pexels.com/photos/{pid}/pexels-photo-{pid}.jpeg?auto=compress&cs=tinysrgb&w=1600'], check=True)
    print('photos ready:', len(pool()))


def stage(plan_path):
    plan = json.load(open(plan_path)); d = plan['date']; out = f"{ROOT}/out/{d}"
    tmp = '/tmp/acne-mediahost'; shutil.rmtree(tmp, ignore_errors=True)
    subprocess.run(['git', 'clone', '-q', '--depth', '1', '-b', 'media', 'https://github.com/ramatladi/videosyndication', tmp], check=True)
    dest = f'{tmp}/acnemedicine/{d}'; os.makedirs(dest, exist_ok=True)
    man = {'date': d, 'channel_id': open(f'{HERE}/CHANNEL_ID').read().strip(), 'items': []}
    for it in plan['items']:
        meta = json.load(open(f"{out}/{it['id']}.json"))
        for f in (meta['video'], meta['thumbnail'], f"{it['id']}.json"):
            shutil.copy(f'{out}/{f}', f'{dest}/{f}')
        man['items'].append({'id': it['id'], 'format': it['format'], 'publish_at': meta['publish_at'],
                             'publish_at_sast': meta['publish_at_sast'], 'title': meta['title'],
                             'video': f"acnemedicine/{d}/{meta['video']}", 'video_sha256': sha(f"{out}/{meta['video']}"),
                             'thumbnail': f"acnemedicine/{d}/{meta['thumbnail']}", 'thumbnail_sha256': sha(f"{out}/{meta['thumbnail']}"),
                             'metadata': f"acnemedicine/{d}/{it['id']}.json"})
    json.dump(man, open(f'{dest}/manifest.json', 'w'), indent=1, ensure_ascii=False)
    g = lambda *a: subprocess.run(['git', '-C', tmp, *a], check=True)
    g('add', f'acnemedicine/{d}')
    g('-c', 'user.name=ramatladi', '-c', 'user.email=rsmphela@gmail.com', 'commit', '-q', '-m',
      f'Acne Medicine Johannesburg: stage {d} ({len(plan["items"])} posts)\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>')
    for i in range(3):
        if subprocess.run(['git', '-C', tmp, 'push', '-q', 'origin', 'HEAD:media']).returncode == 0:
            break
        g('pull', '-q', '--rebase', 'origin', 'media')
    else:
        sys.exit('push to media failed')
    print(json.dumps(man, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    {'build': build, 'stage': stage, 'fetch': fetch}[sys.argv[1]](*sys.argv[2:3])
