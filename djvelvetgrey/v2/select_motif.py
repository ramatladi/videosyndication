"""Copy a motif candidate into a track file's brief.

    python3 select_motif.py djvelvetgrey/tracks/dvgNNN.json <previews_dir>/candidates.json [candidate_id]

With an id: records it as chosen by the listener. Without: takes the first shortlisted candidate with no
catalogue flags and records it as "automatic: compositional evidence, not a listening judgement".
"""
import json, sys

tj, cj = sys.argv[1], sys.argv[2]
c = json.load(open(cj)); t = json.load(open(tj))
by_id = {x['id']: x for x in c['candidates']}
if len(sys.argv) > 3:
    pick = by_id[int(sys.argv[3])]; how = 'listener choice'
else:
    order = c['shortlist'] + [x['id'] for x in sorted(c['candidates'], key=lambda x: -x['score']) if x['id'] not in c['shortlist']]
    pick = next((by_id[i] for i in order if not by_id[i]['catalog']['flags']), by_id[order[0]])
    how = 'automatic: top compositional score without catalogue flags (not a listening judgement)'
t['brief']['motif'] = {'cell': pick['cell'], 'contour': pick['contour'], 'start': pick['start'],
                       'candidate': pick['id'], 'selected_by': how}
json.dump(t, open(tj, 'w'), ensure_ascii=False, indent=2)
print(json.dumps({'selected': pick['id'], 'cell': pick['cell'], 'contour': pick['contour'], 'selected_by': how,
                  'shortlist': c['shortlist']}))
