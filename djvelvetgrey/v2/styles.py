"""DJ Velvet Grey — the 12 style profiles (agreed Oct 2026 with Sello; Codex/Claude decision).

Each profile changes composition, groove, articulation, arrangement and mix — not just tempo or
presets. Fields:
  bpm            supported tempo range (qualified across low/mid/high)
  modes          scale modes the harmony may use
  progressions   4-chord loops as (degree, chord type); harm_rhythm = bars per chord
  kick           kick pattern family; backbeat: clap | snare | snap | rim_clap
  hats           hat pattern family; perc: percussion layer set; fill: fill family
  bass           bass instrument; bass_a / bass_b: allowed bass patterns (first drop / second drop)
  comp           chord comping pattern + instrument; pad: sustained layer (or None)
  focal          musical focal point: melody | bass | rhythm (hook carried by lead, bass or comp)
  leads/answers  instruments for the hook and its answer; cells: allowed motif rhythm cells
  hook_every     bars between hook statements in a drop (8 = every phrase, 16 = sparser)
  arcs           arrangement templates; drop2: how the second drop develops the idea
  swing          16th swing range (beats); lufs: documented loudness target (no universal score)
  mix            per-group level offsets (dB) vs the shared defaults; sidechain depth; reverb size
  label          on-screen / title label; photo / caption mood for the weekly brief
Vocal material is optional: every style here is an instrumental interpretation (no vocals implied).
"""

STYLES = {
    'deep': dict(
        label='Deep House', bpm=(120, 124), modes=['minor', 'dorian'],
        progressions=[[(0, 'm9'), (5, 'm9'), (10, 'add9'), (3, 'maj7')], [(0, 'm7'), (8, 'maj7'), (3, 'maj9'), (10, 'add9')],
                      [(0, 'm11'), (5, 'm9'), (10, 'sus2'), (3, 'maj9')], [(0, 'm9'), (8, 'maj9'), (5, 'm7'), (7, 'm7')]],
        harm_rhythm=1, kick='four_soft', backbeat='clap', hats='offbeat_ghost', perc='deep', fill='clap_conga',
        bass='sub', bass_a=['rolling', 'walk', 'syncop', 'sustain'], bass_b=['octave', 'syncop', 'rolling', 'walk'],
        comp='dub_stab', comp_inst='rhodes', pad='warm', focal='melody',
        leads=['rhodes', 'kalimba', 'flute', 'mallet'], answers=['flute', 'glass', 'rhodes'],
        cells=None, hook_every=8, arcs=['classic', 'early', 'burn', 'wave'],
        drop2=['bass_b', 'lead_oct', 'counter', 'extra_perc'], swing=(.02, .04), lufs=-10.0,
        mix={}, sc=.5, verb=2.6, photo='warm golden-hour or after-dark beach', mood='warm, golden-hour or after-dark'),
    'melodic': dict(
        label='Melodic House', bpm=(118, 124), modes=['minor'],
        progressions=[[(0, 'm9'), (8, 'maj9'), (3, 'maj7'), (10, 'add9')], [(8, 'maj7'), (10, 'add9'), (0, 'm9'), (0, 'm7')],
                      [(0, 'add9'), (10, 'add9'), (8, 'maj7'), (5, 'm9')], [(0, 'm9'), (3, 'maj7'), (10, 'add9'), (5, 'm7')]],
        harm_rhythm=1, kick='four', backbeat='clap', hats='offbeat', perc='light', fill='snare_roll',
        bass='sub', bass_a=['offbeat', 'rolling', 'syncop'], bass_b=['octave', 'rolling'],
        comp='arp16', comp_inst='pluck', pad='warm', focal='melody',
        leads=['mallet', 'glass', 'pluck', 'kalimba'], answers=['flute', 'pluck', 'glass'],
        cells=None, hook_every=8, arcs=['classic', 'wave', 'prog'],
        drop2=['bass_b', 'lead_oct', 'counter', 'arp_double'], swing=(0, 0), lufs=-10.5,
        mix={'pad': 1.5, 'comp': -1}, sc=.6, verb=3.2, photo='bright turquoise shallows or lagoon', mood='bright, breezy daytime'),
    'house': dict(
        label='House', bpm=(122, 126), modes=['dorian', 'minor'],
        progressions=[[(0, 'm7'), (5, '7'), (0, 'm7'), (5, '7')], [(0, 'm9'), (3, 'maj7'), (5, '9'), (3, 'maj7')],
                      [(0, 'm7'), (10, '7'), (8, 'maj7'), (7, 'm7')], [(0, 'm9'), (5, '9'), (10, '6'), (8, 'maj7')]],
        harm_rhythm=1, kick='four', backbeat='clap', hats='house16', perc='house', fill='clap_roll',
        bass='sub', bass_a=['offbeat', 'octave', 'syncop'], bass_b=['octave', 'rolling'],
        comp='house_piano', comp_inst='piano', pad=None, focal='rhythm',
        leads=['piano', 'organ', 'rhodes'], answers=['organ', 'flute', 'glass'],
        cells=['call', 'offbeat', 'syncop', 'skip', 'anthem'], hook_every=8, arcs=['classic', 'early'],
        drop2=['bass_b', 'organ_layer', 'extra_perc'], swing=(.01, .03), lufs=-9.5,
        mix={'comp': 2, 'lead': -1}, sc=.45, verb=1.8, photo='sunny beach party energy', mood='upbeat, sunny'),
    'afro': dict(
        label='Afro House', bpm=(118, 122), modes=['minor', 'dorian'],
        progressions=[[(0, 'm7'), (0, 'm7'), (10, 'sus2'), (8, 'maj7')], [(0, 'm9'), (10, 'add9'), (8, 'maj7'), (10, 'add9')],
                      [(0, 'm7'), (5, 'm7'), (0, 'm7'), (3, 'maj7')], [(0, 'm11'), (8, 'maj9'), (10, 'sus2'), (0, 'm9')]],
        harm_rhythm=2, kick='afro', backbeat='rim_clap', hats='afro', perc='afro', fill='tom_run',
        bass='sub', bass_a=['afro_sub', 'sustain', 'syncop'], bass_b=['afro_roll', 'walk'],
        comp='afro_stab', comp_inst='rhodes', pad='warm', focal='melody',
        leads=['kalimba', 'flute', 'mallet', 'marimba'], answers=['flute', 'kalimba', 'glass'],
        cells=['threes', 'syncop', 'offbeat', 'call', 'skip'], hook_every=8, arcs=['burn', 'classic', 'wave'],
        drop2=['bass_b', 'extra_perc', 'triplet_perc', 'counter'], swing=(.03, .05), lufs=-10.0,
        mix={'perc': 2.5, 'hats': 1}, sc=.4, verb=2.4, photo='sunset beach with dunes or palms', mood='earthy, hypnotic, sunset'),
    'tropical': dict(
        label='Tropical House', bpm=(100, 112), modes=['major'],
        progressions=[[(0, 'maj7'), (7, 'add9'), (9, 'm7'), (5, 'maj7')], [(5, 'maj7'), (7, 'add9'), (4, 'm7'), (9, 'm7')],
                      [(0, 'add9'), (9, 'm7'), (5, 'maj9'), (7, 'add9')], [(9, 'm7'), (5, 'maj7'), (0, 'add9'), (7, 'add9')]],
        harm_rhythm=1, kick='four_soft', backbeat='snap', hats='light', perc='tropical', fill='marimba_run',
        bass='sub', bass_a=['offbeat', 'sustain', 'tropical'], bass_b=['tropical', 'octave'],
        comp='tropical_pluck', comp_inst='pluck', pad='warm', focal='melody',
        leads=['marimba', 'steel', 'flute', 'kalimba'], answers=['flute', 'pluck', 'kalimba'],
        cells=['lilt', 'call', 'dotted', 'skip', 'question'], hook_every=8, arcs=['early', 'classic', 'wave'],
        drop2=['bass_b', 'lead_oct', 'counter', 'extra_perc'], swing=(0, .02), lufs=-11.0,
        mix={'kick': -2, 'clap': -2, 'lead': 1}, sc=.45, verb=2.2, photo='palm-lined tropical beach in bright sun', mood='bright, carefree, island'),
    'nudisco': dict(
        label='Nu-Disco', bpm=(112, 122), modes=['dorian', 'minor'],
        progressions=[[(0, 'm9'), (5, '9'), (0, 'm9'), (5, '9')], [(0, 'm7'), (3, 'maj7'), (5, '7'), (10, '6')],
                      [(0, 'm9'), (10, '6'), (8, 'maj7'), (7, '7')], [(5, 'maj7'), (7, '9'), (0, 'm9'), (0, 'm7')]],
        harm_rhythm=1, kick='four', backbeat='clap', hats='offbeat_ghost', perc='nudisco', fill='snare_roll',
        bass='funk', bass_a=['funk', 'syncop'], bass_b=['funk', 'octave'],
        comp='poly_stab', comp_inst='polysynth', pad='warm', focal='bass',
        leads=['polysynth', 'rhodes', 'glass'], answers=['strings', 'rhodes', 'polysynth'],
        cells=['syncop', 'skip', 'offbeat', 'call', 'lilt'], hook_every=8, arcs=['classic', 'early'],
        drop2=['bass_b', 'lead_layer', 'extra_perc', 'counter'], swing=(.01, .03), lufs=-10.0,
        mix={'bass': 1.5, 'comp': 1}, sc=.4, verb=2.0, photo='summer coastline in vivid colour', mood='funky, sun-drenched, retro'),
    'progressive': dict(
        label='Progressive House', bpm=(122, 128), modes=['minor'],
        progressions=[[(0, 'm9'), (0, 'm9'), (8, 'maj9'), (10, 'add9')], [(0, 'add9'), (8, 'maj7'), (3, 'maj7'), (10, 'sus2')],
                      [(8, 'maj9'), (10, 'add9'), (0, 'm9'), (7, 'm7')], [(0, 'm11'), (3, 'maj9'), (10, 'add9'), (8, 'maj7')]],
        harm_rhythm=2, kick='four', backbeat='clap', hats='rolling16', perc='prog', fill='snare_roll',
        bass='sub', bass_a=['prog_roll', 'rolling'], bass_b=['prog_roll', 'octave'],
        comp='gated8', comp_inst='polysynth', pad='supersaw', focal='melody',
        leads=['glass', 'pluck', 'mallet'], answers=['glass', 'flute', 'pluck'],
        cells=['sparse', 'dotted', 'anthem', 'lilt', 'question'], hook_every=8, arcs=['prog'],
        drop2=['bass_b', 'lead_oct', 'arp_double', 'counter'], swing=(0, 0), lufs=-10.0,
        mix={'pad': 2, 'comp': 0.5}, sc=.6, verb=3.6, photo='wide open coastline or cliffs at golden hour', mood='expansive, euphoric, journeying'),
    'tech': dict(
        label='Tech House', bpm=(124, 128), modes=['minor'],
        progressions=[[(0, 'm7'), (0, 'm7'), (0, 'm7'), (10, '7')], [(0, 'min'), (0, 'min'), (8, 'maj'), (10, 'maj')],
                      [(0, 'm7'), (0, 'm7'), (5, 'm7'), (0, 'm7')], [(0, 'm9'), (0, 'm9'), (3, 'maj7'), (0, 'm9')]],
        harm_rhythm=2, kick='four_hard', backbeat='clap', hats='shuffle', perc='tech', fill='perc_drop',
        bass='acid', bass_a=['tech_roll', 'acid16'], bass_b=['acid16', 'tech_roll'],
        comp='tech_stab', comp_inst='stab', pad=None, focal='bass',
        leads=['stab', 'pluck', 'rim_synth'], answers=['stab', 'glass'],
        cells=['offbeat', 'syncop', 'skip', 'call'], hook_every=16, arcs=['loop', 'classic'],
        drop2=['bass_b', 'filter_open', 'extra_perc'], swing=(.04, .06), lufs=-9.0,
        mix={'kick': 1, 'bass': 1, 'lead': -3, 'pad': -6}, sc=.55, verb=1.4, photo='sunset beach club vibe, sea and sky', mood='driving, late-afternoon, groove-led'),
    'vocal': dict(
        label='Vocal House (Instrumental)', bpm=(120, 124), modes=['major', 'dorian'],
        progressions=[[(0, 'maj7'), (9, 'm7'), (2, 'm7'), (7, '9')], [(5, 'maj7'), (4, 'm7'), (2, 'm7'), (7, '9')],
                      [(0, 'add9'), (7, 'add9'), (9, 'm7'), (5, 'maj9')], [(2, 'm9'), (7, '9'), (0, 'maj9'), (9, 'm7')]],
        harm_rhythm=1, kick='four_soft', backbeat='clap', hats='offbeat', perc='vocal', fill='clap_roll',
        bass='sub', bass_a=['offbeat', 'walk', 'octave'], bass_b=['octave', 'walk'],
        comp='organ_hold', comp_inst='organ', pad='strings', focal='melody',
        leads=['topline', 'flute', 'glass'], answers=['rhodes', 'strings', 'glass'],
        cells=['sparse', 'dotted', 'anthem', 'question', 'lilt'], hook_every=8, arcs=['classic', 'early', 'wave'],
        drop2=['bass_b', 'lead_oct', 'counter', 'strings_stab'], swing=(.01, .02), lufs=-10.0,
        mix={'lead': 1.5}, sc=.45, verb=2.4, photo='joyful sunny beach', mood='uplifting, sing-along, sunny'),
    'soulful': dict(
        label='Soulful House', bpm=(120, 124), modes=['dorian', 'major'],
        progressions=[[(0, 'm9'), (5, '9'), (10, 'maj9'), (3, '69')], [(2, 'm9'), (7, '9'), (0, 'maj9'), (9, 'm9')],
                      [(0, 'maj9'), (4, 'm7'), (9, 'm9'), (2, 'm9')], [(0, 'm9'), (10, '69'), (8, 'maj9'), (7, '9')]],
        harm_rhythm=1, kick='four_soft', backbeat='clap', hats='shuffle_soft', perc='soulful', fill='conga_run',
        bass='funk', bass_a=['walk', 'syncop', 'sustain'], bass_b=['walk', 'funk'],
        comp='soul_comp', comp_inst='piano', pad='strings', focal='melody',
        leads=['rhodes', 'flute', 'topline'], answers=['strings', 'glass', 'flute'],
        cells=['lilt', 'question', 'dotted', 'sparse', 'call'], hook_every=8, arcs=['classic', 'wave', 'early'],
        drop2=['bass_b', 'counter', 'strings_stab', 'extra_perc'], swing=(.02, .04), lufs=-10.5,
        mix={'comp': 1.5, 'pad': 1}, sc=.35, verb=2.6, photo='warm sunset beach, relaxed', mood='warm, soulful, golden hour'),
    'disco': dict(
        label='Disco', bpm=(116, 124), modes=['major', 'mixolydian'],
        progressions=[[(0, 'maj7'), (2, 'm7'), (4, 'm7'), (5, 'maj7')], [(0, '7'), (5, '7'), (0, '7'), (7, '7')],
                      [(9, 'm7'), (2, 'm7'), (7, '9'), (0, 'maj7')], [(0, 'maj9'), (5, '9'), (2, 'm9'), (7, '9')]],
        harm_rhythm=1, kick='four', backbeat='snare', hats='disco16', perc='disco', fill='tom_run',
        bass='funk', bass_a=['disco_oct', 'funk'], bass_b=['disco_oct', 'walk'],
        comp='guitar16', comp_inst='guitar', pad='strings', focal='melody',
        leads=['strings', 'brass', 'polysynth'], answers=['brass', 'strings', 'glass'],
        cells=['anthem', 'call', 'syncop', 'lilt', 'skip'], hook_every=8, arcs=['classic', 'early'],
        drop2=['bass_b', 'strings_stab', 'lead_layer', 'extra_perc'], swing=(0, .01), lufs=-10.0,
        mix={'pad': 1.5, 'comp': 0.5, 'lead': 0.5}, sc=.25, verb=2.0, photo='bright retro summer beach', mood='glittering, joyful, retro'),
    'french': dict(
        label='French House', bpm=(120, 126), modes=['dorian', 'mixolydian', 'minor'],
        progressions=[[(0, 'm7'), (5, '9'), (0, 'm7'), (5, '9')], [(0, 'maj7'), (10, '6'), (5, 'maj7'), (7, '7')],
                      [(0, 'm9'), (3, 'maj7'), (5, '9'), (10, '6')], [(0, '7'), (10, 'maj7'), (5, '9'), (7, '7')]],
        harm_rhythm=1, kick='four_hard', backbeat='clap', hats='disco16', perc='disco', fill='filter_drop',
        bass='funk', bass_a=['disco_oct', 'funk'], bass_b=['funk', 'disco_oct'],
        comp='filter_loop', comp_inst='guitar', pad=None, focal='rhythm',
        leads=['polysynth', 'brass', 'stab'], answers=['polysynth', 'strings'],
        cells=['syncop', 'skip', 'call', 'offbeat'], hook_every=16, arcs=['loop', 'classic'],
        drop2=['bass_b', 'filter_open', 'lead_layer'], swing=(.01, .02), lufs=-9.5,
        mix={'comp': 2.5, 'kick': 1}, sc=.75, verb=1.6, photo='stylish Riviera-style coastline', mood='filtered, pumping, chic'),
}

ORDER = ['deep', 'melodic', 'house', 'afro', 'tropical', 'nudisco', 'progressive', 'tech', 'vocal', 'soulful', 'disco', 'french']
# legacy style name used by dvg001 / dvg001v2
ALIASES = {'chill': 'melodic'}


def get(style):
    return STYLES[ALIASES.get(style, style)]
