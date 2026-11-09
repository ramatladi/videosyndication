"""QA for the product-feature renders: python3 skincare-launch/qa_feature.py <features.json> <outdir>  -> <outdir>/qa.json

Checks per render: container/codec/size, Short <= 60 s, integrated loudness, SRT present and cue count = scenes,
banned words in title/description/SRT, product named in title + narration, commission line only in the description,
thumbnail contains the store packshot (template match), first frame of each Short is the clean cover,
and cross-batch similarity (perceptual hashes of thumbnails and sampled frames; no pair may be near-identical).
"""
import json, os, re, subprocess, sys, hashlib
import numpy as np
from PIL import Image, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
BANNED = re.compile(r'moisturis|colour|licence|millilitre', re.I)
COMM = re.compile(r'commission|affiliate', re.I)


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def probe(p):
    j = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', p], capture_output=True, text=True).stdout)
    v = next(s for s in j['streams'] if s['codec_type'] == 'video'); a = next(s for s in j['streams'] if s['codec_type'] == 'audio')
    return {'w': v['width'], 'h': v['height'], 'vcodec': v['codec_name'], 'acodec': a['codec_name'], 'fps': v['r_frame_rate'],
            'duration': round(float(j['format']['duration']), 2)}


def loudness(p):
    r = subprocess.run(['ffmpeg', '-i', p, '-af', 'loudnorm=I=-14:print_format=json', '-f', 'null', '-'], capture_output=True, text=True).stderr
    j = json.loads(r[r.rindex('{'):r.rindex('}') + 1]); return float(j['input_i']), float(j['input_tp'])


def frame(p, t, size=(256, 256)):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', p, '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True).stdout
    import io
    return Image.open(io.BytesIO(raw)).convert('RGB')


def dhash(im, n=16):
    g = np.asarray(im.convert('L').resize((n + 1, n), Image.LANCZOS), dtype=np.int16)
    return (g[:, 1:] > g[:, :-1]).flatten()


def ham(a, b):
    return int((a != b).sum())


def packshot_in(thumb, pack):
    """Normalized cross-correlation of the trimmed packshot against the thumbnail at a few scales; returns best score."""
    sys.path.insert(0, HERE); import feature as Fe
    t = np.asarray(thumb.convert('L'), dtype=np.float32); p0 = Fe.trim(pack)
    best = 0.0
    import cv2
    for h in range(180, 620, 20):
        p = p0.copy(); p.thumbnail((10000, h)); q = np.asarray(p.convert('L'), dtype=np.float32)
        if q.shape[0] >= t.shape[0] or q.shape[1] >= t.shape[1]:
            continue
        best = max(best, float(cv2.matchTemplate(t, q, cv2.TM_CCOEFF_NORMED).max()))
    return round(best, 3)


def main():
    spec = json.load(open(sys.argv[1])); out = sys.argv[2]; rows, fails = [], []
    hashes = {}
    for v in spec['videos']:
        o = f"{out}/{v['slug']}"; r = {'slug': v['slug'], 'domain': v['domain'], 'format': v['format'], 'product': v['product_name']}
        meta = json.load(open(o + '.json')); pr = probe(o + '.mp4'); r.update(pr)
        short = v['format'] == 'short'
        r['size_ok'] = (pr['w'], pr['h']) == ((1080, 1920) if short else (1920, 1080)) and pr['vcodec'] == 'h264' and pr['acodec'] == 'aac'
        r['duration_ok'] = pr['duration'] <= 59.5 if short else 45 <= pr['duration'] <= 600
        r['lufs'], r['true_peak'] = loudness(o + '.mp4'); r['loudness_ok'] = -15.0 <= r['lufs'] <= -13.0 and r['true_peak'] <= -0.5
        srt = open(o + '.srt').read(); cues = len(re.findall(r'^\d+\s*$', srt, re.M)); r['srt_cues'] = cues
        ends = re.findall(r'--> (\d+):(\d+):(\d+),(\d+)', srt); last = int(ends[-1][0]) * 3600 + int(ends[-1][1]) * 60 + int(ends[-1][2]) + int(ends[-1][3]) / 1000
        r['srt_ok'] = cues >= len(v['scenes']) and last <= pr['duration'] + 0.05
        say = ' '.join(s['say'] for s in v['scenes'])
        r['product_in_title'] = v['product_name'].lower() in meta['title'].lower()
        r['product_spoken'] = v.get('spoken_name', v['product_name']).lower() in say.lower()
        blob = meta['title'] + meta['description'] + srt + ' '.join(meta['tags'])
        blob = re.sub(r'https?://\S+', '', re.sub(r'\s+', ' ', blob))  # store URLs keep the store's spelling
        names = [v['product_name'], v.get('spoken_name', '')]
        names += [re.sub(r'\s*spf.*$', '', n, flags=re.I) for n in names]  # caption cues can split a name before "SPF"
        for nm in names:  # official product names keep their own spelling
            if nm: blob = re.sub(re.escape(nm), '', blob, flags=re.I)
        r['american_english_ok'] = not BANNED.search(blob)
        onscreen = ' '.join(' '.join(str(s.get(k, '')) for k in ('headline', 'sub', 'kicker', 'label', 'stat')) + ' '.join(s.get('items', [])) for s in v['scenes'])
        r['commission_description_only'] = bool(COMM.search(meta['description'])) and not COMM.search(say + onscreen + srt + meta['title'])
        r['title_len'] = len(meta['title']); r['desc_bytes'] = len(meta['description'].encode())
        r['meta_ok'] = r['title_len'] <= 100 and r['desc_bytes'] <= 5000 and len(','.join(meta['tags'])) <= 500
        th = Image.open(o + '.jpg'); r['thumb_size'] = th.size
        r['packshot_match'] = packshot_in(th, Image.open(f"{HERE}/store/{v['packshot']}").convert('RGB'))
        r['packshot_ok'] = r['packshot_match'] >= 0.6 and th.size == (1280, 720)
        if short:
            f0 = frame(o + '.mp4', 0.05); f1 = frame(o + '.mp4', 0.9)
            r['cover_frame_stable'] = ham(dhash(f0), dhash(f1)) <= 30  # Ken Burns drift only, no transition at start
            r['cover_packshot_match'] = packshot_in(f0.resize((540, 960)), Image.open(f"{HERE}/store/{v['packshot']}").convert('RGB'))
            r['cover_ok'] = r['cover_frame_stable'] and r['cover_packshot_match'] >= 0.55
        r['mp4_sha256'] = sha(o + '.mp4'); r['jpg_sha256'] = sha(o + '.jpg'); r['srt_sha256'] = sha(o + '.srt')
        d = pr['duration']; hashes[v['slug']] = {'thumb': dhash(th), 'frames': [dhash(frame(o + '.mp4', d * q)) for q in (0.3, 0.5, 0.7)]}
        oks = [k for k in r if k.endswith('_ok') or k in ('product_in_title', 'product_spoken', 'commission_description_only')]
        r['pass'] = all(r[k] for k in oks)
        if not r['pass']:
            fails.append((v['slug'], [k for k in oks if not r[k]]))
        rows.append(r)
    # cross-batch similarity: min Hamming distance (of 256 bits) between any two renders
    slugs = list(hashes); pairs = []
    for i in range(len(slugs)):
        for j in range(i + 1, len(slugs)):
            a, b = hashes[slugs[i]], hashes[slugs[j]]
            tdist = ham(a['thumb'], b['thumb']); fdist = min(ham(x, y) for x in a['frames'] for y in b['frames'])
            pairs.append({'a': slugs[i], 'b': slugs[j], 'thumb_dist': tdist, 'frame_dist': fdist})
    sim_fail = [p for p in pairs if p['thumb_dist'] < 40 or p['frame_dist'] < 30]
    products = [v['product_name'] for v in spec['videos']]; photos = []
    for v in spec['videos']:
        photos += [s['image'] for s in v['scenes'] if s.get('image') and not s['image'].startswith(tuple('0123456789')) is False]
    free = [s['image'] for v in spec['videos'] for s in v['scenes'] if s.get('image', '')[:1].isdigit()]
    store_by_video = {v['slug']: {s['image'] for s in v['scenes'] if s.get('image') and not s['image'][:1].isdigit()} | {v['packshot']} for v in spec['videos']}
    shared_store = [(a, b, sorted(store_by_video[a] & store_by_video[b])) for a in store_by_video for b in store_by_video if a < b and store_by_video[a] & store_by_video[b]]
    summary = {'renders': len(rows), 'passed': sum(r['pass'] for r in rows), 'fails': fails,
               'unique_products': len(set(products)) == len(products),
               'free_photos_unique': len(set(free)) == len(free), 'store_images_shared_between_videos': shared_store,
               'min_thumb_dist': min(p['thumb_dist'] for p in pairs), 'min_frame_dist': min(p['frame_dist'] for p in pairs),
               'similarity_fails': sim_fail}
    json.dump({'summary': summary, 'renders': rows, 'pairs': pairs}, open(f'{out}/qa.json', 'w'), indent=1, default=str)
    print(json.dumps(summary, indent=1, default=str))


if __name__ == '__main__':
    main()
