"""Plan take-2 briefs for the whole set so instruments vary across it: python3 plan_take2.py > briefs.json
Penalises: lead and answer on the same instrument, the same lead instrument as take 1, a lead or answer
instrument already used elsewhere in the set, too many choir pads, the same bass three times."""
import sys, json, collections, numpy as np
V2 = '/home/claude/vs/djvelvetgrey/v2'; sys.path.insert(0, V2); sys.path.insert(0, '/home/claude/dvg-scripts')
import engine as E, compose as C, styles as S, sampler as SM

SET = [('tropical', 108, 60, 'Coral Lanterns'), ('nudisco', 116, 57, 'Saffron Boulevard'), ('disco', 118, 62, 'Glitter Tidewater'),
       ('afro', 120, 57, 'Baobab Sundown'), ('deep', 121, 55, 'Velvet Harbour Lights'), ('soulful', 122, 58, 'Honeyed Promenade'),
       ('vocal', 122, 60, 'Open Sky Chorus'), ('melodic', 123, 62, 'Lagoon Reverie'), ('house', 124, 55, 'Pier Side Piano'),
       ('french', 124, 57, 'Riviera Shutters'), ('progressive', 126, 59, 'Cliffline Ascent'), ('tech', 126, 57, 'Midnight Driftwood')]
take1_pal = json.load(open('/home/claude/vs/djvelvetgrey/sets/2026-10-21-real/palettes.json'))


def take1(i, P):
    r = np.random.default_rng(4040 + i)
    prog = P['progressions'][int(r.integers(len(P['progressions'])))]
    lead = P['leads'][int(r.integers(len(P['leads'])))]
    ans = [a for a in P['answers'] if a != lead]; answer = ans[int(r.integers(len(ans)))]
    ba = P['bass_a'][int(r.integers(len(P['bass_a'])))]; bb = P['bass_b'][int(r.integers(len(P['bass_b'])))]
    r.uniform(*P['swing']); arc = P['arcs'][int(r.integers(len(P['arcs'])))]
    return dict(prog=prog, lead=lead, answer=answer, bass_a=ba, bass_b=bb, arc=arc, seed=int(r.integers(100000, 999999)))


def other(r, opts, prev):
    pool = [o for o in opts if o != prev] or list(opts)
    return pool[int(r.integers(len(pool)))]


leads, answers, pads, basses = collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter()
plan = []
for i, (st, bpm, tonic, title) in enumerate(SET):
    P = S.STYLES[st]; old = take1(i, P); old_lead_inst = take1_pal[i]['palette'].get(old['lead'], old['lead'])
    r = np.random.default_rng(91000 + i); best = None
    for _ in range(250):
        prog = other(r, P['progressions'], old['prog']); lead = P['leads'][int(r.integers(len(P['leads'])))]
        answer = other(r, [a for a in P['answers'] if a != lead], old['answer']); seed = int(r.integers(100000, 999999))
        pal = SM.Palette(seed, st, real=True).describe(); pad = 'choir' if E.track_variation(seed, st)['pad_src'] == 'blend' else 'strings'
        li, ai, bi = pal.get(lead, lead), pal.get(answer, answer), pal['bass_real']
        pen = (100 if li == ai else 0) + (50 if li == old_lead_inst else 0) + 12 * leads[li] + 6 * answers[ai] + 3 * answers[li] \
            + 3 * leads[ai] + (4 if pads[pad] >= 6 else 0) + (3 * (basses[bi] - 1) if basses[bi] >= 2 else 0)
        if best is None or pen < best[0]:
            best = (pen, dict(prog=prog, lead=lead, answer=answer, seed=seed, li=li, ai=ai, bi=bi, pad=pad,
                              ba=other(r, P['bass_a'], old['bass_a']), bb=other(r, P['bass_b'], old['bass_b']),
                              swing=round(float(r.uniform(*P['swing'])), 3), arc=other(r, P['arcs'], old['arc'])))
        if pen == 0: break
    pen, c = best; leads[c['li']] += 1; answers[c['ai']] += 1; pads[c['pad']] += 1; basses[c['bi']] += 1
    b = {'engine': 'v2', 'style': st, 'release': f'set-real-take2-{i + 1:02d}', 'bpm': bpm, 'tonic': tonic,
         'progression': [list(x) for x in c['prog']], 'mode': C.best_mode(c['prog'], P['modes']), 'lead': c['lead'], 'answer': c['answer'],
         'groove': {'bass_a': c['ba'], 'bass_b': c['bb'], 'swing': c['swing']}, 'arc': c['arc'], 'loudness_lufs': P['lufs'],
         'seed': c['seed'], 'instruments': 'real'}
    plan.append({'i': i, 'title': title, 'brief': b, 'take1': old, 'penalty': pen, 'lead_inst': c['li'], 'answer_inst': c['ai'],
                 'bass_inst': c['bi'], 'pad': c['pad'], 'take1_lead_inst': old_lead_inst})
    print(f"{title:22} pen {pen:3}  {c['li']:20} -> {c['ai']:20} bass {c['bi']:15} pad {c['pad']:8} (take1 {old_lead_inst})", file=sys.stderr)
json.dump(plan, sys.stdout, indent=1)
