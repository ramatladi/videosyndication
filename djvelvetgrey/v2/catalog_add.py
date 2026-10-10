"""Add (or update) a track's motif and production choices in djvelvetgrey/catalog.json.

    python3 catalog_add.py djvelvetgrey/tracks/dvgNNN.json <id> [status]

status defaults to "published"; use "draft" for unreleased mixes (drafts are ignored by brief_check).
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compose as C

t = json.load(open(sys.argv[1])); b = t['brief']
h, hook = C.hook_from_spec(b, b['motif'])
C.add_to_catalog({'id': sys.argv[2], 'title': t['title'], 'status': sys.argv[3] if len(sys.argv) > 3 else 'published',
                  'style': b['style'], 'motif': C.motif_repr(hook['call']), 'cell': b['motif']['cell'],
                  'contour': b['motif']['contour'], 'progression': b['progression'], 'template': b['arc'],
                  'bass_a': b['groove']['bass_a'], 'lead': b['lead'], 'answer': b.get('answer'),
                  'key': C.key_name(b['tonic']), 'bpm': b['bpm']})
print('catalogued', sys.argv[2])
