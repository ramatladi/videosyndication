"""Equal 12-style rotation + release ledger (agreed Oct 2026: Sello / Codex / Claude).

Cycle: 12 weeks = 24 slots at the existing Tue/Fri 18:00 America/New_York slots, starting Tue 2026-10-13.
Every style appears twice per cycle (once on a Tuesday, once on a Friday), no adjacent repeats incl. wrap.

    python3 rotation.py next --date YYYY-MM-DD        which style this slot should publish (JSON)
    python3 rotation.py record --release dvgNNN --date YYYY-MM-DD --style S --scheduled S2 [--media URL] [--uuid U]
    python3 rotation.py status --release dvgNNN --platform youtube|tiktok --status PUBLISHED|FAILED|FAILED_FINAL|PENDING|SCHEDULED [--url U] [--uuid REPAIR_UUID]
    python3 rotation.py open                                                releases not yet verified on every platform (JSON)
    python3 rotation.py hold --date YYYY-MM-DD --style S --reason "..."     (slot held: nothing published)
    python3 rotation.py report                                              counts per style and platform
    python3 rotation.py verify                                              self-test of the cycle maths

Counting rule: only VERIFIED successful posts count, per style AND per platform (a style's delivered count
is the minimum across platforms). Pending or repairable posts (PENDING / SCHEDULED / FAILED on one platform)
are provisional so a slot is not double-assigned; FAILED_FINAL on any platform makes that slot owed again.
Expected slots are counted from each style's activation date ('activated' in styles_status.json).
Debt (a held or lost slot): a slot that cannot be filled makes that style owed. Debt is repaid only inside
existing slots: first in slots that would otherwise be empty (a slot whose scheduled style is not active),
and by displacing a scheduled style only when the owed style's deficit is larger than the scheduled style's
(e.g. 2 vs 1). With all 12 styles active there are no spare slots, so moving a single owed slot onto another
style would only shift the shortfall; in that case the owed slot is NOT bounced around - it stays visible in
the report as owed (the honest state) until a spare slot exists. Order: largest deficit, then the scheduled
style, then the oldest debt. Back-to-back repeats are avoided except on a style's own scheduled slot.
Every non-scheduled pick is reported as a displacement. The rotation is reported as transitional until all
12 styles are active.
"""
import argparse, datetime as dt, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LEDGER = os.path.join(ROOT, 'ledger.json')
STATUS = os.path.join(ROOT, 'styles_status.json')
START = dt.date(2026, 10, 13)          # week 1, Tuesday
WEEKS = [('deep', 'melodic'), ('house', 'afro'), ('tropical', 'nudisco'), ('progressive', 'tech'), ('vocal', 'soulful'),
         ('disco', 'french'), ('melodic', 'deep'), ('afro', 'house'), ('nudisco', 'tropical'), ('tech', 'progressive'),
         ('soulful', 'vocal'), ('french', 'disco')]
ROTATION = [s for w in WEEKS for s in w]          # 24 slots: index 2w = Tuesday, 2w+1 = Friday
PLATFORMS = ('youtube', 'tiktok')


def slot_abs(date):
    if date.weekday() not in (1, 4): raise SystemExit(f'{date} is not a Tuesday or Friday slot')
    week = (date - START).days // 7
    if week < 0: raise SystemExit(f'{date} is before the rotation start {START}')
    return week * 2 + (0 if date.weekday() == 1 else 1)


def load(path, default):
    try: return json.load(open(path))
    except Exception: return default


def ledger(): return load(LEDGER, {'cycle_start': str(START), 'releases': [], 'holds': []})


def save(lg): json.dump(lg, open(LEDGER, 'w'), indent=1)


def active_styles():
    st = load(STATUS, {}).get('styles', {})
    return [s for s in ROTATION[:12] if st.get(s, {}).get('status') in ('active-technical', 'active-auditioned')]


DONE = 'PUBLISHED'; FINAL_FAIL = 'FAILED_FINAL'


def activation_slot(style):
    """First slot index at which the style counts (its 'activated' date in styles_status.json)."""
    d = load(STATUS, {}).get('styles', {}).get(style, {}).get('activated')
    if not d: return 0
    d = dt.date.fromisoformat(d)
    if d <= START: return 0
    days = (d - START).days; week, wd = divmod(days, 7)
    return week * 2 + (0 if wd <= 1 else (1 if wd <= 4 else 2))


def delivered(lg, style):
    """Per-platform verified count; delivered = minimum across platforms.
    pending = releases not yet verified everywhere that can still be repaired (PENDING/SCHEDULED/FAILED);
    a platform marked FAILED_FINAL (given up) leaves that release undelivered, so the slot becomes owed."""
    rel = [r for r in lg['releases'] if r['style'] == style and not r.get('pre_cycle')]
    per = {p: sum(1 for r in rel if r['platforms'].get(p, {}).get('status') == DONE) for p in PLATFORMS}
    pending = 0
    for r in rel:
        sts = [r['platforms'].get(p, {}).get('status') for p in PLATFORMS]
        if all(x == DONE for x in sts) or any(x == FINAL_FAIL for x in sts): continue
        pending += 1
    return per, min(per.values()), pending


def expected_slots(style, n):
    a = activation_slot(style)
    return [k for k in range(a, n + 1) if ROTATION[k % 24] == style]


def choose(date):
    lg = ledger(); n = slot_abs(date); idx = n % 24
    scheduled = ROTATION[idx]
    act = active_styles()
    info = {}
    for s in ROTATION[:12]:
        exp = expected_slots(s, n) if s in act else []
        per, dlv, pend = delivered(lg, s)
        covered = dlv + pend
        oldest = exp[covered] if covered < len(exp) else None          # oldest slot not yet covered
        info[s] = {'expected_so_far': len(exp), 'delivered_per_platform': per, 'pending_or_repairable': pend,
                   'deficit': len(exp) - covered, 'owed_since_slot': oldest,
                   'owed_age_slots': (n - oldest) if oldest is not None else 0, 'active': s in act}
    prev = next((r['style'] for r in reversed(lg['releases']) if not r.get('pre_cycle')), None)
    cands = [s for s in act if info[s]['deficit'] > 0]
    pick, reason = None, ''
    if cands:
        key = lambda s: (info[s]['deficit'], s == scheduled, info[s]['owed_age_slots'], -ROTATION.index(s))
        order = sorted(cands, key=key, reverse=True)
        pick = order[0]
        if pick == prev and pick != scheduled:          # avoid back-to-back repeats, but never block a style's own slot
            pick = next((s for s in order if s != prev), pick)
        if pick == scheduled: reason = 'scheduled style'
        elif scheduled not in act: reason = f"scheduled style '{scheduled}' is not active; slot used for owed {pick} (deficit {info[pick]['deficit']})"
        else: reason = f"repays owed slot for {pick} (deficit {info[pick]['deficit']}, owed {info[pick]['owed_age_slots']} slots); {scheduled} is now owed"
    else:
        reason = 'no active style is owed a slot — hold this slot and report'
    return {'date': str(date), 'slot_abs': n, 'cycle': n // 24 + 1, 'slot_in_cycle': idx + 1,
            'weekday': 'Tue' if date.weekday() == 1 else 'Fri', 'scheduled_style': scheduled, 'chosen_style': pick,
            'displaced': (pick is not None and pick != scheduled), 'reason': reason,
            'transitional': len(act) < 12, 'active_styles': act,
            'note': ('Transitional rotation: only the activated styles are published; this is not yet all-style parity.'
                     if len(act) < 12 else 'All 12 styles active.'),
            'owed': {s: v['deficit'] - (1 if s == pick else 0) for s, v in info.items() if v['deficit'] - (1 if s == pick else 0) > 0},
            'styles': info}


def verify():
    assert len(ROTATION) == 24
    for s in set(ROTATION):
        idx = [i for i, x in enumerate(ROTATION) if x == s]
        assert len(idx) == 2, s
        assert {i % 2 for i in idx} == {0, 1}, f'{s} not once per weekday'
        gaps = sorted([idx[1] - idx[0], 24 - (idx[1] - idx[0])])
        assert gaps == [11, 13], (s, gaps)
    for i in range(24): assert ROTATION[i] != ROTATION[(i + 1) % 24], f'adjacent repeat at {i}'
    assert len(set(ROTATION)) == 12
    return 'ok: 12 styles x 2, one Tue + one Fri each, gaps 11/13, no adjacent repeats incl. wrap'


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd')
    for k in ('date', 'release', 'style', 'scheduled', 'media', 'uuid', 'platform', 'status', 'url', 'reason', 'title'): ap.add_argument('--' + k)
    a = ap.parse_args()
    if a.cmd == 'verify': print(verify())
    elif a.cmd == 'next': print(json.dumps(choose(dt.date.fromisoformat(a.date)), indent=1))
    elif a.cmd == 'record':
        lg = ledger()
        if any(r['release_id'] == a.release for r in lg['releases']): sys.exit(f'{a.release} already recorded')
        if a.style not in ROTATION: sys.exit(f'unknown style {a.style}')
        lg['releases'].append({'release_id': a.release, 'title': a.title, 'slot_date': a.date, 'style': a.style,
                               'scheduled_style': a.scheduled or a.style, 'metricool_uuid': a.uuid, 'media_url': a.media,
                               'platforms': {p: {'status': 'PENDING'} for p in PLATFORMS}})
        save(lg); print('recorded', a.release)
    elif a.cmd == 'status':
        lg = ledger(); r = next((r for r in lg['releases'] if r['release_id'] == a.release), None)
        if not r: sys.exit(f'unknown release {a.release}')
        if a.platform not in PLATFORMS or a.status not in ('PUBLISHED', 'PENDING', 'SCHEDULED', 'FAILED', 'FAILED_FINAL'):
            sys.exit('platform must be youtube|tiktok; status PUBLISHED|PENDING|SCHEDULED|FAILED|FAILED_FINAL')
        p = r['platforms'].setdefault(a.platform, {})
        p.update({'status': a.status, 'checked_utc': dt.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ')})
        if a.url: p['url'] = a.url
        if a.uuid: p['repair_uuid'] = a.uuid          # a single-platform repair post was created for this platform
        save(lg); print(a.release, a.platform, a.status)
    elif a.cmd == 'open':
        lg = ledger()
        print(json.dumps([r for r in lg['releases'] if not r.get('pre_cycle') and
                          any(r['platforms'].get(p, {}).get('status') not in (DONE, FINAL_FAIL) for p in PLATFORMS)], indent=1))
    elif a.cmd == 'hold':
        lg = ledger(); lg['holds'].append({'date': a.date, 'style': a.style, 'reason': a.reason}); save(lg); print('held', a.date)
    elif a.cmd == 'report':
        lg = ledger()
        print(json.dumps({s: dict(zip(('per_platform', 'delivered', 'pending'), delivered(lg, s))) for s in ROTATION[:12]}, indent=1))
    else: sys.exit('unknown command')
