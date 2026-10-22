import os, json, sys, collections, itertools, numpy as np
os.environ['DVG_CATALOG'] = '/tmp/vox2/set_catalog.json'
json.dump([], open('/tmp/vox2/set_catalog.json', 'w'))
sys.path.insert(0, '/home/claude/videosyndication/djvelvetgrey/v2')
import styles as S, compose as C, engine as E, sampler as SM, make_track as MT
V = lambda s: s  # file names in /tmp/vox/src
SONGS = [  # title, reference, style, bpm, tonic, mode, prog options, vocal plan
 ('Sequin Harbour', 'Stay a While (feat. Sister Sledge) - The Revenge', 'disco', 118, 56, 'major', [0, 2, 3],
  {'hook': {'type': 'phrase', 'src': '365849_many-lovers.mp3', 'region': [0.7, 9.0], 'shift': 0},
   'phrase': {'src': '365849_many-lovers.mp3', 'region': [9.0, 22.6], 'shift': 0}, 'bed': {'src': '211629_uuuhh.mp3'},
   'adlibs': {'drop1': '341488_woo-hoo.mp3'},
   'names': {'hook': '"Many Lovers" sung line (Paranoye)', 'phrase': '"Many Lovers" second line', 'bed': '"Uuuhh" pad', 'adlib_drop1': '"Woo hoo"'}}),
 ('Neon Tide Pull', 'Hypnotized - Purple Disco Machine & Sophie and the Giants', 'nudisco', 116, 55, 'minor', [2],
  {'hook': {'type': 'phrase', 'src': '437584_female-vocal-chops.mp3', 'region': [0.07, 12.75], 'shift': 0},
   'bed': {'src': '577833_vocal-padd.mp3'}, 'adlibs': {'drop2': '387947_oh-yeah.mp3'},
   'names': {'hook': 'Female sung vocal line (chenny0607)', 'bed': 'Vocal pad', 'adlib_drop2': '"Oh yeah"'}}),
 ('Kalahari Footsteps', 'Move - Adam Port, Stryv & Malachiii', 'afro', 121, 60, 'minor', [0, 1, 2, 3],
  {'hook': {'type': 'phrase', 'src': '427418_get-down.mp3', 'region': [5.2, 11.3], 'shift': 0},
   'phrase': {'src': '427418_get-down.mp3', 'region': [0.5, 4.2], 'shift': 0},
   'layer': {'type': 'reseq', 'src': '319254_high-chant.mp3', 'pattern': [0, 6, 10, 16, 22, 26], 'hold': 2.5, 'bars': 2, 'slice_max': .35},
   'bed': {'src': '319253_low-chant.mp3'}, 'adlibs': {'drop1': '57204_men-shouting-hey.mp3'},
   'names': {'hook': '"Get Down" vocal line (thef1like)', 'phrase': '"Get Down" calls', 'layer': 'High chant', 'bed': 'Low chant', 'adlib_drop1': '"Hey!"'}}),
 ('Quiet Signal', 'You & Me (feat. Eliza Doolittle) [Rivo Remix] - Disclosure', 'deep', 122, 62, 'minor', [0, 1, 2, 3],
  {'hook': {'type': 'phrase', 'src': '537090_love-vocal.mp3', 'region': [0.05, 3.25], 'shift': 0},
   'layer': {'type': 'reseq', 'src': '333264_vocal-cut-ups-collage.mp3', 'pattern': [2, 7, 10, 15, 18, 23, 26, 31], 'hold': 2, 'bars': 2, 'slice_max': .3},
   'bed': {'src': '131094_vocal-harmony.mp3'},
   'names': {'hook': '"Love" vocal line (oceaans)', 'layer': 'Breathy female chops', 'bed': 'Vocal harmony pad'}}),
 ('Glass Coastline', 'Diamonds (feat. Solomon Grey) - Lane 8', 'melodic', 120, 57, 'minor', [0, 1, 3],
  {'hook': {'type': 'phrase', 'src': '523227_morning-country-female-vocal-loop.mp3', 'region': [0.0, 9.3], 'shift': 0},
   'phrase': {'src': '523227_morning-country-female-vocal-loop.mp3', 'region': [9.3, 18.65], 'shift': 0},
   'bed': {'src': '577828_dream-vocal-pad.mp3'},
   'names': {'hook': 'Sung female line (szegvari)', 'phrase': 'Sung female answer line', 'bed': 'Dream vocal pad'}}),
 ('Mango Skies', 'Freeze - Kygo', 'tropical', 106, 61, 'major', [0, 1, 2, 3],
  {'hook': {'type': 'phrase', 'src': '508456_female-voice-doodling.mp3', 'region': [1.1, 6.4], 'shift': 1},
   'bed': {'src': '352573_angelic-voice.mp3'}, 'adlibs': {'drop2': '320739_yeah.mp3'},
   'names': {'hook': 'Female improvised sung line (owstu)', 'bed': 'Angelic voice', 'adlib_drop2': '"Yeah!"'}}),
 ('Rooftop Telegram', 'I Got U (feat. Jax Jones) - Duke Dumont', 'house', 124, 59, 'dorian', [0, 1, 3],
  {'hook': {'type': 'phrase', 'src': '469018_vocal3.mp3', 'region': [0.0, 3.69], 'shift': 0},
   'layer': {'type': 'loop', 'src': '467908_vocal2.mp3', 'bpm': 124.8, 'trim': .045, 'bars': 1},
   'adlibs': {'drop1': '384981_hell-yeah.mp3'},
   'names': {'hook': '2-step female sung phrase (arnasarnas)', 'layer': '2-step female chop', 'adlib_drop1': '"Hell yeah!"'}}),
 ('Golden Chorus Line', "Sweet Lovin' - Sigala & Bryn Christopher", 'vocal', 123, 58, 'major', [0, 1, 2, 3],
  {'hook': {'type': 'phrase', 'src': '448705_hey-hey-hey-yeah.mp3', 'region': [0.6, 5.35], 'shift': 0},
   'layer': {'type': 'reseq', 'src': '419161_ooh-aha.mp3', 'pattern': [4, 12, 20, 28], 'hold': 3.5, 'bars': 2, 'slice_max': .5},
   'bed': {'src': '331130_sisters-voices.mp3'}, 'adlibs': {'drop1': '416843_shouting-yeah.mp3'},
   'names': {'hook': '"Hey hey hey yeah" sung line (ellenmentor)', 'layer': '"Ooh-aha" backing', 'bed': "Sisters' voices", 'adlib_drop1': '"Yeah!"'}}),
 ('Concrete Sunrise', 'Favour - FISHER & Tones And I', 'tech', 125, 58, 'minor', [0, 1, 2, 3],
  {'hook': {'type': 'phrase', 'src': '362340_short-vocals-100bpm.mp3', 'region': [1.8, 7.85], 'shift': 0},
   'layer': {'type': 'reseq', 'src': '554623_male-vocal-glitch.mp3', 'pattern': [0, 3, 8, 11, 16, 19, 24, 27], 'hold': 2, 'bars': 2, 'slice_max': .25, 'shift': 'none'},
   'bed': {'src': '395431_male-vocal-drone.mp3'}, 'adlibs': {'build': '63982_go-for-it.mp3'}, 'adlib_shift': {'build': 'none'},
   'names': {'hook': 'Short vocal phrase (DivingInSpace)', 'layer': 'Male vocal glitch', 'bed': 'Male vocal drone', 'adlib_build': '"Go for it"'}}),
 ('Endless July', 'Summer - Calvin Harris', 'progressive', 127, 59, 'minor', [0, 2, 3],
  {'hook': {'type': 'phrase', 'src': '529476_hip-vocal-dance-loop-100bpm.mp3', 'region': [0.0, 7.3], 'shift': 0},
   'layer': {'type': 'loop', 'src': '161507_chopped-vocal-loop.mp3', 'bpm': 126.0, 'bars': 1},
   'bed': {'src': '556980_tension-vocals.mp3'},
   'names': {'hook': 'Dance vocal phrase (szegvari)', 'layer': 'Chopped female loop', 'bed': 'Tension vocals'}}),
]
# 1. every voice used in exactly one song
used = collections.defaultdict(set)
for t, *_, vp in SONGS:
    for k, v in vp.items():
        if k == 'adlibs': [used[f].add(t) for f in v.values()]
        elif isinstance(v, dict) and 'src' in v: used[v['src']].add(t)
shared = {f: s for f, s in used.items() if len(s) > 1}
assert not shared, shared
# 2. instruments / progression / groove: global search so no instrument repeats anywhere in the set (lead or answer)
def draw(i, r):
    title, ref, st, bpm, tonic, mode, popts, vp = SONGS[i]; P = S.STYLES[st]
    while True:
        pi = popts[int(r.integers(len(popts)))]; prog = P['progressions'][pi]
        if C.best_mode(prog, P['modes']) == mode: break
    lead = P['leads'][int(r.integers(len(P['leads'])))]; ans = [a for a in P['answers'] if a != lead]; answer = ans[int(r.integers(len(ans)))]
    seed = int(r.integers(100000, 999999)); d = SM.Palette(seed, st, real=True).describe()
    return dict(pi=pi, prog=prog, lead=lead, answer=answer, seed=seed, li=d.get(lead, lead), ai=d.get(answer, answer), bi=d['bass_real'],
                ki=d['drum_kit'], pad=E.track_variation(seed, st)['pad_src'],
                ba=P['bass_a'][int(r.integers(len(P['bass_a'])))], bb=P['bass_b'][int(r.integers(len(P['bass_b'])))],
                arc=P['arcs'][int(r.integers(len(P['arcs'])))])
def chord_pcs(i, prog):
    t = SONGS[i]; st = t[2]; H = C.Harmony(t[4], prog, t[5], S.STYLES[st].get('harm_rhythm', 1))
    return [frozenset(n % 12 for n in c[:4]) for c in H.chords]
def chord_sim(a, b):
    """0..1: how alike two 4-chord loops are in any key and any rotation (Jaccard of chord pitch-class sets)"""
    best = 0.0
    for sh in range(12):
        for rot in range(4):
            bb = [frozenset((p + sh) % 12 for p in x) for x in b[rot:] + b[:rot]]
            best = max(best, sum(len(x & y) / len(x | y) for x, y in zip(a, bb)) / 4)
    return best
FAMILY = {'Yamaha Grand Piano': 'piano', 'Bright Yamaha Grand': 'piano', 'Electric Piano': 'piano', 'Strings': 'strings', 'Slow Strings': 'strings',
          'Synth Strings 1': 'strings', 'Orchestral Pad': 'strings', 'Brass Section': 'brass', 'Brass 2': 'brass', 'Rhodes EP': 'ep',
          'Legend EP 2': 'ep', 'Detuned EP 1': 'ep', 'Percussive Organ': 'organ', 'DrawbarOrgan': 'organ', 'Rock Organ': 'organ',
          'Alto Sax': 'sax', 'Tenor Sax': 'sax'}
FAM = lambda n: FAMILY.get(n, n)
def cost(ch):
    inst = collections.Counter([FAM(c['li']) for c in ch] + [FAM(c['ai']) for c in ch])
    same = sum(1000 for c in ch if FAM(c['li']) == FAM(c['ai']))
    rep = sum(100 * (n - 1) for n in inst.values() if n > 1)
    bass = sum(5 * (n - 2) for n in collections.Counter(c['bi'] for c in ch).values() if n > 2)
    kit = sum(5 * (n - 1) for n in collections.Counter(c['ki'] for c in ch).values() if n > 1)
    pad = sum(3 * (n - 4) for n in collections.Counter(c['pad'] for c in ch).values() if n > 4)
    prg = sum(200 * (n - 1) for n in collections.Counter(tuple(map(tuple, c['prog'])) for c in ch).values() if n > 1)
    pcs = [chord_pcs(i, c['prog']) for i, c in enumerate(ch)]
    harm = sum(int(400 * (chord_sim(pcs[i], pcs[j]) - .7)) for i in range(len(ch)) for j in range(i + 1, len(ch)) if chord_sim(pcs[i], pcs[j]) > .7)
    return same + rep + bass + kit + pad + prg + harm
R = np.random.default_rng(77000)
CANDS = [[draw(i, R) for _ in range(400)] for i in range(len(SONGS))]
for i, cl in enumerate(CANDS):
    for c in cl: c['pcs'] = chord_pcs(i, c['prog'])
SIM = {}
def csim(a, b):
    k = (tuple(a), tuple(b))
    if k not in SIM: SIM[k] = chord_sim(a, b)
    return SIM[k]
def cost2(idx):
    ch = [CANDS[i][j] for i, j in enumerate(idx)]
    inst = collections.Counter([FAM(c['li']) for c in ch] + [FAM(c['ai']) for c in ch])
    v = sum(1000 for c in ch if FAM(c['li']) == FAM(c['ai'])) + sum(100 * (n - 1) for n in inst.values() if n > 1)
    v += sum(5 * (n - 2) for n in collections.Counter(c['bi'] for c in ch).values() if n > 2)
    v += sum(5 * (n - 1) for n in collections.Counter(c['ki'] for c in ch).values() if n > 1)
    v += sum(200 * (n - 1) for n in collections.Counter(tuple(map(tuple, c['prog'])) for c in ch).values() if n > 1)
    for x in range(len(ch)):
        for y in range(x + 1, len(ch)):
            s_ = csim(ch[x]['pcs'], ch[y]['pcs'])
            if s_ > .7: v += int(400 * (s_ - .7))
    return v
best_idx, best_v = None, 1e9
for restart in range(8):
    idx = [int(R.integers(400)) for _ in SONGS]; v = cost2(idx); T = 200.0
    for it in range(25000):
        i = int(R.integers(len(SONGS))); j = int(R.integers(400)); old = idx[i]; idx[i] = j; v2 = cost2(idx)
        if v2 <= v or R.random() < np.exp((v - v2) / T): v = v2
        else: idx[i] = old
        T = max(.5, T * .9997)
    if v < best_v: best_v, best_idx = v, list(idx)
    print('restart', restart, 'cost', v, 'best', best_v, file=sys.stderr)
    if best_v == 0: break
ch = [CANDS[i][j] for i, j in enumerate(best_idx)]
def cost(_): return best_v
out = []
for i, (title, ref, st, bpm, tonic, mode, popts, vp) in enumerate(SONGS):
    P = S.STYLES[st]; c = ch[i]; pen = cost(ch)
    b = {'engine': 'v2', 'style': st, 'release': 'hitstyle2-' + title.lower().replace(' ', '-'), 'bpm': bpm, 'tonic': tonic,
         'progression': [list(x) for x in c['prog']], 'mode': mode, 'lead': c['lead'], 'answer': c['answer'],
         'groove': {'bass_a': c['ba'], 'bass_b': c['bb'], 'swing': round(sum(P['swing']) / 2, 3)}, 'arc': c['arc'],
         'loudness_lufs': P['lufs'], 'seed': c['seed'], 'instruments': 'real'}
    assert not MT.validate(b, P) and P['bpm'][0] <= bpm <= P['bpm'][1], (title, MT.validate(b, P))
    # 3. hook melody: screened against every earlier song of this set (temporary catalogue), min distance 0.35
    cands = C.candidates(b, 24); prev = json.load(open(os.environ['DVG_CATALOG']))
    ok = [x for x in cands if not x['catalog']['flags'] and all(C.similarity_distance(x['motif'], e['motif']) >= .35 for e in prev)]
    pick = (ok or sorted(cands, key=lambda x: -min([C.similarity_distance(x['motif'], e['motif']) for e in prev] or [1])))[0]
    b['motif'] = {'cell': pick['cell'], 'contour': pick['contour'], 'start': pick['start'], 'candidate': pick['id'],
                  'selected_by': 'automatic, screened against the other 9 songs - not a listening judgement'}
    h, hook = C.hook_from_spec(b, b['motif'])
    C.add_to_catalog({'id': b['release'], 'title': title, 'status': 'published', 'style': st, 'mode': mode, 'motif': C.motif_repr(hook['call']),
                      'progression': b['progression'], 'template': b['arc'], 'bass_a': b['groove']['bass_a'], 'bass_b': b['groove']['bass_b'],
                      'lead': b['lead'], 'answer': b['answer'], 'cell': pick['cell'], 'contour': pick['contour']})
    md = min([C.similarity_distance(C.motif_repr(hook['call']), e['motif']) for e in prev] or [1.0])
    out.append({'title': title, 'reference': ref, 'brief': b, 'vocals': vp, 'instruments': {'lead': c['li'], 'answer': c['ai'], 'bass': c['bi'], 'kit': c['ki'], 'pad': c['pad']},
                'hook_min_distance_to_others': round(md, 3), 'plan_penalty': pen})
    cs = max(chord_sim(chord_pcs(i, c['prog']), chord_pcs(j, ch[j]['prog'])) for j in range(len(SONGS)) if j != i)
    out[-1]['max_chord_similarity'] = round(cs, 2)
    print(f"chordsim {cs:.2f} {title:20} {st:11} {bpm} {C.key_name(tonic, mode):10} lead {c['li']:18} ans {c['ai']:18} bass {c['bi']:14} kit {c['ki']:10} pad {c['pad']:7} arc {c['arc']:7} hookdist {md:.2f} pen {pen}")
json.dump(out, open('/tmp/vox2/hits2.json', 'w'), indent=1)
