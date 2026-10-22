"""Write mtr001-010 into mirage/ledger.json + catalog.json (call with: release uuid media) after each is scheduled."""
import json, sys, os
os.environ['DVG_CATALOG'] = '/home/claude/videosyndication/mirage/catalog.json'
sys.path.insert(0, '/home/claude/videosyndication/djvelvetgrey/v2'); sys.path.insert(0, '/home/claude/videosyndication/mirage')
import compose as C, make_release as MR
rel, uuid, media = sys.argv[1:4]
posts = {p['release']: p for p in json.load(open('/tmp/mirage/posts.json'))}; p = posts[rel]; i = p['n'] - 1
h = json.load(open('/tmp/vox2/hits2.json'))[i]; b = h['brief']
L = MR.ledger()
if any(x['release'] == rel for x in L['releases']): sys.exit('already')
pcs = MR.chord_pcs(b['style'], b['tonic'], b['mode'], b['progression'])
L['releases'].append({'release': rel, 'date': p['slot'][:10], 'slot': p['slot'], 'format': p['format'], 'title': p['title'], 'style': b['style'],
                      'tonic': b['tonic'], 'mode': b['mode'], 'key': p['key'], 'bpm': b['bpm'], 'lead': h['instruments']['lead'],
                      'answer': h['instruments']['answer'], 'lead_family': MR.FAM(h['instruments']['lead']), 'answer_family': MR.FAM(h['instruments']['answer']),
                      'chord_pcs': [sorted(x) for x in pcs], 'photographer': p['photographer'], 'photo_page': p['photo_page'],
                      'metricool_uuid': uuid, 'media_url': media, 'style_reference': h['reference'], 'brief': b})
json.dump(L, open(MR.LEDGER, 'w'), indent=1)
hook = C.hook_from_spec(b, b['motif'])[1]
C.add_to_catalog({'id': rel, 'title': p['title'], 'status': 'published', 'style': b['style'], 'mode': b['mode'], 'motif': C.motif_repr(hook['call']),
                  'progression': b['progression'], 'template': b['arc'], 'lead': b['lead'], 'answer': b['answer'],
                  'bass_a': b['groove']['bass_a'], 'bass_b': b['groove']['bass_b'], 'key': p['key'], 'bpm': b['bpm']})
print('ledger', rel)
