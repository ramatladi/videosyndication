"""Discoverability updates for videos already on YouTube (they can't be changed through the current upload-only
connection): new title/description/tags plus an English caption file from the exact narration.

    python3 acnemedicine/uploaded_updates.py <outdir>   -> <outdir>/updates.json + <outdir>/captions/<video_id>.en.srt
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import discover as D, day
import importlib.util as u

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
ACNE = 'UCtwhnWNVzoS6MR0SkvZIDHQ'

LAUNCH = {   # domain: (video_id, extra tags, topic hashtag)
    'skincare.joburg': ('au8JAjGHi1s', ['moisturizer', 'skin smoothing cream', 'calm water gel', 'skin soothing hydrating lotion',
                                        'best moisturizer south africa', 'minimalist skincare', 'rosebank', 'johannesburg'], 'Moisturizer'),
    'skincare.durban': ('5A9z0B9Q6hw', ['body wash', 'body cream', 'conditioning body wash', 'body hydrating cream',
                                        'body care routine', 'body care for beginners', 'westville', 'durban'], 'BodyCare'),
    'dermatologist.joburg': ('f8_sTs85ahg', ['travel size skincare', 'skincare travel kit', 'intensive moisture balance',
                                             'active clearing kit', 'carry on liquids', 'packing skincare', 'midrand', 'johannesburg'], 'TravelSkincare'),
    'dermatology.joburg': ('zjRvNGxTsFA', ['how to read skincare labels', 'serum ingredients', 'age bright clearing serum',
                                           'salicylic acid serum', 'niacinamide', 'bedfordview', 'johannesburg'], 'SkincareLabels'),
    'dermatology.durban': ('NgYncofIlQo', ['face mist', 'toner', 'micro-pore mist', 'hyaluronic ceramide mist',
                                           'beach packing list', 'umhlanga', 'durban'], 'FaceMist'),
    'dermatology.capetown': ('19db5U7uT6k', ['sunscreen', 'how to read a sunscreen label', 'spf 30', 'broad spectrum sunscreen',
                                             'clearing defense spf30', 'hiking sun protection', 'cape town'], 'Sunscreen'),
}


def launch_items():
    spec = u.spec_from_file_location('b', f'{ROOT}/skincare-launch/build_launch.py'); b = u.module_from_spec(spec)
    spec.loader.exec_module(b)
    for v in b.SPEC['videos']:
        vid, extra, topic = LAUNCH[v['domain']]
        timing = D.read_timing(f"{ROOT}/skincare-launch/out/{v['slug']}.timing.json")
        labels = []
        for s in v['scenes']:
            k = s['kicker'] if s['kicker'] != v['domain'] else 'Where to find it'
            k = k[:1].upper() + k[1:].lower().replace('spf', 'SPF')
            pre = s['caption'].split(':')[0]
            labels.append(f'{k}: {pre}' if ':' in s['caption'] and len(pre) <= 32 and pre.lower() not in k.lower() else k)
        chap = D.chapters(labels, timing)
        desc, _ = b.description(v)
        head, rest = desc.split('\n', 1)
        city = {'joburg': 'Joburg', 'durban': 'Durban', 'capetown': 'CapeTown'}[v['domain'].split('.')[1]]
        desc = (head + '\n' + rest.replace('\n\nShop:', f'\n\nChapters:\n{chap}\n\nShop:', 1)
                + f'\n\n#{topic} #Skincare{city} #SkincareSouthAfrica')
        tg = D.tags('', extra, base=['dermalogica', 'dermalogica south africa', 'skincare south africa', 'skincare tips',
                                     v['domain']])
        tg = [t for t in tg if t not in ('dermalogica', 'how to use', 'review')]
        yield {'channel': v['domain'], 'video_id': vid, 'title': v['title'], 'description': desc, 'tags': tg,
               'default_language': 'en', 'default_audio_language': 'en',
               'captions': D.srt([s['say'] for s in v['scenes']], timing)}


def acne_items():
    plan = json.load(open(f'{HERE}/days/2026-11-07/plan.json')); P = day.pool()
    ids = {'amj-20261107-s1': 'dDt8nlD_r8Q', 'amj-20261107-v1': 'ih7wNORa3bE'}
    for it in plan['items']:
        if it['id'] in ids:
            tm = D.read_timing(f"{ROOT}/out/2026-11-07/{it['id']}.timing.json"); m = day.metadata(plan, it, P, tm)
            yield {'channel': ACNE, 'video_id': ids[it['id']], 'title': m['title'], 'description': m['description'],
                   'tags': m['tags'], 'default_language': 'en', 'default_audio_language': 'en',
                   'captions': D.srt([s['say'] for s in it['scenes']], tm)}
    r = json.load(open(f'{HERE}/reviews/amj001.json')); post = json.load(open(f'{HERE}/reviews/amj001.post.json'))
    tm = D.read_timing(f'{ROOT}/out/amj001.timing.json')
    desc = post['description'].replace(post['description'].split('\n', 1)[0],
                                       "Dermalogica Breakout Clearing Foaming Wash: what's in it (0.5% salicylic acid) and how to use it, in under a minute.", 1)
    desc = desc.replace('#skincare #dermalogica #salicylicacid',
                        '#Dermalogica #BreakoutClearingFoamingWash #SkincareSouthAfrica #SalicylicAcid')
    yield {'channel': ACNE, 'video_id': 'TvLLRDS-X5I',
           'title': 'How to Use Dermalogica Breakout Clearing Foaming Wash (0.5% Salicylic Acid) #shorts',
           'description': desc, 'tags': D.tags('breakout clearing foaming wash', ['salicylic acid', 'face wash', 'acne cleanser']),
           'default_language': 'en', 'default_audio_language': 'en',
           'captions': D.srt([s['say'] for s in r['scenes']], tm) if tm else None}


if __name__ == '__main__':
    out = sys.argv[1]; os.makedirs(f'{out}/captions', exist_ok=True); items = []
    for it in [*acne_items(), *launch_items()]:
        assert len(it['title']) <= 100 and len(it['description'].encode()) <= 5000 and 'earn a commission' in it['description']
        assert len(','.join(it['tags'])) <= 500, it['video_id']
        if it['captions']:
            open(f"{out}/captions/{it['video_id']}.en.srt", 'w').write(it['captions'])
            it['captions'] = f"captions/{it['video_id']}.en.srt"
        items.append(it)
    json.dump({'why': 'Apply with videos.update (snippet: title, description, tags, defaultLanguage, defaultAudioLanguage) '
                      'and captions.insert (language en, name English). Needs the youtube.force-ssl scope, which the '
                      'current upload-only connections do not have. Or paste into YouTube Studio by hand.',
               'items': items}, open(f'{out}/updates.json', 'w'), indent=1, ensure_ascii=False)
    for it in items:
        print(it['video_id'], it['channel'], len(it['title']), len(it['tags']), bool(it['captions']))
