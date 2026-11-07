"""Stage the 12 launch product features into a media-branch checkout under skincare-launch/v2/.

    python3 skincare-launch/stage_v2.py <media checkout>

Per channel folder: <slug>.mp4, .jpg (thumbnail), .en.srt, .json (title/description/tags/meta).
Also: v2/manifest.json, v2/qa.json, v2/images/ (store images used + sources.json) and v2/photos/ (Pexels photos used).
Nothing is published; Codex uploads and schedules. The first launch renders are marked superseded.
"""
import json, os, shutil, sys, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
HANDLES = {'skincare.joburg': '@SkincareJoburgRosebank', 'skincare.durban': '@SkincareDurbanWestville',
           'dermatologist.joburg': '@DermatologistJoburgMidrand', 'dermatology.joburg': '@DermatologyJoburgBedfordview',
           'dermatology.durban': '@DermatologyDurbanUmhlanga', 'dermatology.capetown': '@DermatologyCapeTown'}
OLD = {'dermatologist.joburg': 'f8_sTs85ahg', 'dermatology.capetown': '19db5U7uT6k', 'dermatology.durban': 'NgYncofIlQo',
       'dermatology.joburg': 'zjRvNGxTsFA', 'skincare.durban': '5A9z0B9Q6hw', 'skincare.joburg': 'au8JAjGHi1s'}
RAW = 'https://raw.githubusercontent.com/ramatladi/videosyndication/media/'


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def main():
    media = sys.argv[1]; base = sys.argv[2] if len(sys.argv) > 2 else 'skincare-launch/v2'; dst = f'{media}/{base}'
    spec = json.load(open(f'{HERE}/features.json')); out = f'{HERE}/out/feature'
    qa = json.load(open(f'{out}/qa.json')); assert qa['summary']['passed'] == qa['summary']['renders'] == 12 and not qa['summary']['similarity_fails']
    qrow = {r['slug']: r for r in qa['renders']}
    srcdoc = json.load(open(f'{HERE}/store/sources.json')); sources = {s['file']: s for s in srcdoc['images']}
    os.makedirs(f'{dst}/images', exist_ok=True); os.makedirs(f'{dst}/photos', exist_ok=True)
    items, used_store, used_free = [], {}, {}
    for v in spec['videos']:
        ch = spec['channels'][v['domain']]; d = f'{dst}/{v["domain"]}'; os.makedirs(d, exist_ok=True)
        meta = json.load(open(f'{out}/{v["slug"]}.json')); q = qrow[v['slug']]
        assert sha(f'{out}/{v["slug"]}.mp4') == q['mp4_sha256'], 'render changed after QA'
        files = {}
        for ext, name in (('.mp4', '.mp4'), ('.jpg', '.jpg'), ('.srt', '.en.srt')):
            shutil.copy2(f'{out}/{v["slug"]}{ext}', f'{d}/{v["slug"]}{name}'); files[name] = f'{base}/{v["domain"]}/{v["slug"]}{name}'
        imgs = [v['packshot']] + [s['image'] for s in v['scenes'] if s.get('image')] + ([v['thumb']['photo']] if v['thumb'].get('photo') else [])
        store = sorted({i for i in imgs if i in sources}); free = sorted({i for i in imgs if i not in sources})
        for i in store:
            shutil.copy2(f'{HERE}/store/{i}', f'{dst}/images/{i}'); used_store[i] = sources[i]
        for i in free:
            shutil.copy2(f'{HERE}/photos/{i}', f'{dst}/photos/{i}'); used_free[i] = v['slug']
        item = {
            'domain': v['domain'], 'handle': HANDLES[v['domain']], 'locality': ch['locality'], 'desk': ch['desk'],
            'format': v['format'], 'slug': v['slug'],
            'product': {'name': v['product_name'], 'listing_url': v['product_url'], 'checked': spec['checked'],
                        'packshot': f'{base}/images/{v["packshot"]}', 'packshot_source': sources[v['packshot']]['source']},
            'title': meta['title'], 'description': meta['description'], 'tags': meta['tags'],
            'category': 'Howto & Style', 'default_language': 'en', 'audio_language': 'en', 'made_for_kids': False,
            'paid_promotion': True, 'altered_or_synthetic_content': False,
            'duration_seconds': q['duration'], 'resolution': f"{q['w']}x{q['h']}",
            'media_path': files['.mp4'], 'media_url': RAW + files['.mp4'], 'sha256': q['mp4_sha256'],
            'thumbnail_path': files['.jpg'], 'thumbnail_url': RAW + files['.jpg'], 'thumbnail_sha256': q['jpg_sha256'],
            'captions_path': files['.en.srt'], 'captions_url': RAW + files['.en.srt'], 'captions_sha256': sha(f'{d}/{v["slug"]}.en.srt'),
            'store_images': [f'{base}/images/{i}' for i in store],
            'free_photos': [{'pexels_id': p['id'], 'photographer': p['by'], 'url': f'https://www.pexels.com/photo/{p["id"]}/',
                             'license': 'Pexels License', 'path': f'{base}/photos/{p["id"]}.jpg'} for p in v.get('free_photos', [])],
            'music': 'original, made for this video', 'narration': f"Kokoro text-to-speech, voice {ch['voice']} (American English)",
            'qa': {k: q[k] for k in ('lufs', 'true_peak', 'packshot_match', 'srt_cues', 'pass') if k in q} | (
                {'cover_packshot_match': q['cover_packshot_match']} if 'cover_packshot_match' in q else {}),
            'status': 'staged_not_published',
            'replaces_launch_video_id': OLD[v['domain']] if v['format'] == 'video' else None,
        }
        json.dump(item, open(f'{d}/{v["slug"]}.json', 'w'), indent=1, ensure_ascii=False)
        items.append(item)
    json.dump({'retrieved': srcdoc['retrieved'], 'method': srcdoc['method'], 'images': sorted(used_store.values(), key=lambda x: x['file'])}, open(f'{dst}/images/sources.json', 'w'), indent=1)
    shutil.copy2(f'{out}/qa.json', f'{dst}/qa.json')
    man = {
        'purpose': 'Launch rebuild for the six Dermalogica skincare channels: one regular video and one Short per channel, '
                   '12 different named products. Codex uploads and schedules; nothing here is published.',
        'generated': spec['checked'], 'image_policy': 'Product images from the Dermalogica South Africa store listings '
        '(use confirmed by Sello, 7 Nov 2026 01:03 SAST, for these videos and their YouTube thumbnails); locality photos from Pexels (free license).',
        'commission_disclosure': 'description only', 'language': 'American English',
        'superseded': {'note': 'Do not publish the first launch renders (skincare-launch/<domain>/*-launch.mp4 and the '
                               'unrendered shorts plan). The six first launch videos already public stay in place.',
                       'old_public_video_ids': OLD, 'old_manifest': 'skincare-launch/manifest.json'},
        'qa_summary': qa['summary'], 'items': items,
    }
    json.dump(man, open(f'{dst}/manifest.json', 'w'), indent=1, ensure_ascii=False)
    print(len(items), 'items;', len(used_store), 'store images;', len(used_free), 'free photos')


if __name__ == '__main__':
    main()
