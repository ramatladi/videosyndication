# DJ Velvet Grey — weekly house & disco tracks (engine v3.1, 12 styles)

Two original instrumental tracks a week by **DJ Velvet Grey** (Tue + Fri, 18:00 America/New_York), each a
2:59 (179.0 s) vertical video of one credited beach/nature photo featuring a woman in a bikini, with a slow
zoom, the track title, a live equalizer and the photo credit, published to YouTube (Short) and TikTok through
Metricool (brand `everythingyouwant_tv`, id 7321327).

## The agreed decision (Oct 2026 — Sello, Codex, Claude)
- **12 styles**, equally represented, from the 1,816 retained house/disco tracks in Sello's library:
  Deep, Melodic, House (house + generic house, raw tags kept), Afro, Tropical, Nu-Disco, Progressive, Tech,
  Vocal (instrumental interpretation), Soulful, Disco, French. The 360 unsure and 976 dropped tracks are out of
  scope unless Sello asks for reclassification. Labels that defaulted to "deep house" are to be re-audited
  before being used as style references.
- **One shared foundation** (synthesis, mix, master, export, QC) with distinct per-style profiles for
  harmony, groove, articulation, comping, focal point and arrangement (`v2/styles.py`). Distinctness is
  checked in code (tests); how different the styles actually *sound* has not been verified by listening. The focal point may be melody, bass or
  rhythm. No compulsory genre instruments. Vocals optional and licensed if ever used; vocal-free versions are
  labelled as instrumental interpretations.
- **Equal rotation** — 12 weeks / 24 slots (`v2/rotation.py`, starts Tue 2026-10-13):
  W1 Deep/Melodic, W2 House/Afro, W3 Tropical/Nu-Disco, W4 Progressive/Tech, W5 Vocal/Soulful, W6 Disco/French,
  W7 Melodic/Deep, W8 Afro/House, W9 Nu-Disco/Tropical, W10 Tech/Progressive, W11 Soulful/Vocal, W12 French/Disco.
  If a build fails, the run tries one backup brief of the **same style**; if that fails too, the slot is
  **held** (`rotation.py hold`) and the style is reported as owed. Debt is repaid only inside existing slots:
  first in slots whose scheduled style is not active yet, and by displacing a scheduled style only when the
  owed style's deficit is larger (largest deficit first; every non-scheduled pick is reported as a
  displacement). With all 12 styles active there is no spare slot, so a single lost slot stays reported as
  owed rather than being bounced between styles. Never filled silently with another style. Only **verified**
  posts count, per style **and** platform; FAILED on one platform is repaired (retry that platform only),
  FAILED_FINAL makes the slot owed. Styles count from their activation date.
  While not all 12 styles are activated, the rotation is called **transitional**, never all-style parity.
- **Fail-closed release**: nothing new is published unless `v2/release_gate.py` exits 0. The one exception is
  repairing a single failed platform of an already-gated release: allowed once, only if its committed
  `manifests/<id>.json` has status pass and the ledger holds the Metricool-hosted copy of that exact video.
- **Assessment wording**: automated selection and QC are technical checks only. Never describe a track as
  listened to / approved unless Sello auditioned it (`auditioned_by` in the manifest / styles_status.json).
  Perceptual quality ("equal or better than deep house") is unverified until listened to. No hit is guaranteed.

## Files
- `v2/styles.py` — the 12 style profiles (tempo range, modes, progressions, kick/backbeat/hats/perc/fills,
  bass instrument + patterns, comping, pad, focal point, leads, motif rhythm cells, arcs, second-drop
  development, swing, documented loudness, mix offsets, photo / caption mood).
- `v2/compose.py` — harmony (modes, chord types, `best_mode`), motif writing, hooks, `fit_sections`
  (arrangement fitted to 179 s at any supported tempo, outro always heard), catalogue screening.
- `v2/instruments.py` — all original synthesis (no samples). `v2/engine.py` — style-driven arrangement,
  mix and master (`ENGINE_VERSION`).
- `v2/previews.py` — six 8-bar hook previews at -14 LUFS + `candidates.json` (shortlist = compositional evidence).
- `v2/select_motif.py` — records the chosen hook: listener choice (id), automatic (no id), or automatic retry
  (`<id> --auto`) — an unattended run never records a listener choice.
- `v2/brief_check.py` — style-range / mode-fit / variety checks; revise the brief if it lists flags.
- `v2/export.py` — codec headroom: final MP3 (320k) and AAC (256k, fast coder) decoded and kept <= -1.3 dBTP.
  The master is limited at -2.8 dBTP so the export trim stays small; the achieved loudness after the trim is
  recorded in QC (it can sit 1–2 dB under the style's target — the target is documented, not guaranteed).
- `v2/qc.py` — blocking QC on the FINAL WAV + MP3 + MP4 audio. Exit 0 pass / 2 blocking failure / 4 could
  not run. Failure categories: master, structure, signal, decode, stereo.
- `v2/manifest.py` — per-track manifest: sha256 of the track file, photo, delivery WAV, MP3, AAC, MP4 and the
  QC / meta / export reports; a hash of the build code (taken at render time and re-checked), repo commit and
  dirty flag, engine + tool versions, brief, motif selection. Written only after QC passes.
- `v2/release_gate.py <out_dir> <name>` — exit 0 only if manifest + QC pass, every bound file still matches its
  hash, the build code is unchanged and was committed, and the style (aliases resolved) is active.
  Do not edit the track file between the build and publishing (its hash is bound).
- `v2/rotation.py` — slot → style, ledger (`ledger.json`) of releases and per-platform verified status, holds.
- `v2/catalog_add.py` — adds the published motif, answer phrase and production features to `catalog.json`.
- `v2/qualify.py` — style qualification renders (full music + export + QC; for speed the MP4 there wraps the
  exact final AAC in a minimal video track — the full visual MP4 path is exercised by make.sh).
  `v2/tests.py` — test suite incl. negative publishing tests.
- `make.sh tracks/dvgNNN.json [--check]` — fail-closed build: music → export → video (copies the exact AAC) →
  QC → manifest. ~10–15 min; run in the background and poll. `--check` validates the track file only.
- `styles_status.json` — per-style activation: `inactive`, `active-technical` (passed the rollout gate, NOT
  listened to) or `active-auditioned` (also heard and approved by Sello).
- `manifests/dvgNNN.json` — copy of the manifest of every published release, committed by the weekly run
  (`out/` is not committed). `ledger.json` — rotation ledger. `TRACKS.md` — human log.

## Rollout gate (before a style may publish)
1. Shared foundation fixed (export headroom, fail-closed QC, tempo fit, musical bug fixes, labels).
2. Real style module in `styles.py`.
3. Three full qualification renders from distinct briefs across the style's tempo range (low/mid/high), all
   passing blocking QC on the final WAV/MP3/AAC, plus the deep and melodic qualification renders as the
   regression check, the test suite (incl. negative publishing tests) and one full make.sh build.
4. Independent reviewer agent reviews code and evidence (it cannot hear either).
5. Recommended (not mandatory): Sello listens once per style; until then the style is `active-technical`.

## Track file
```json
{
  "title": "Silver Fern Morning", "engine": "v2",
  "image": "djvelvetgrey/photos/dvg002.jpg", "photo_page": "https://unsplash.com/photos/...",
  "photo_url": "https://images.unsplash.com/photo-...", "photographer": "Jane Doe", "photo_site": "Unsplash",
  "credit": "Photo: Jane Doe / Unsplash", "scene": "Sunset boat ride — Zanzibar",
  "youtube_title": "Silver Fern Morning — DJ Velvet Grey | Afro House",
  "description": "Picture yourself ... (scene first, then mood line, credit, 'Music: DJ Velvet Grey', hashtags)",
  "tiktok_caption": "...", "tags": ["afro house", "DJ Velvet Grey", "..."],
  "brief": {"engine": "v2", "style": "afro", "release": "dvg002", "mood": "earthy sunset groove",
            "bpm": 120, "tonic": 57, "mode": "minor", "progression": [[0, "m7"], [0, "m7"], [10, "sus2"], [8, "maj7"]],
            "lead": "kalimba", "answer": "flute", "groove": {"bass_a": "afro_sub", "bass_b": "afro_roll", "swing": 0.04},
            "arc": "burn", "loudness_lufs": -10.0, "seed": 482913}
}
```
Choose every brief field from the style's lists in `styles.py` (make.sh refuses anything else); use
`compose.best_mode(progression, modes)` for the mode; vary choices from earlier tracks (a new title, key, seed or photo alone is not a new composition).

## Rules
- **Title**: original, evocative, 2–4 words, Title Case; never used before in `TRACKS.md` and not the title of
  a well-known existing song (quick web search).
- **Photo**: a beautiful natural setting (beach, ocean, lake, island, waterfall, coastline, dunes, lagoon…)
  featuring one or more adult women in bikinis. Tasteful: clearly adults, natural relaxed or playful poses,
  scenery clearly visible, no nudity or see-through swimwear, no close-up crops of body parts, no explicit or
  provocative posing, no brand logos, text or watermarks, no buildings or vehicles dominating. Portrait or
  >= ~1600 px short side; subject in the upper two-thirds or off-centre. Match the style's `photo` mood.
- **Finding photos**: Unsplash search pages work with WebFetch, e.g.
  `https://unsplash.com/s/photos/woman-bikini-beach?orientation=portrait&license=free`; confirm the photo page
  says "Free to use under the Unsplash License". Pexels search pages block fetching.
- **Photo sources**: free licences only — Unsplash (never Unsplash+), Pexels, Pixabay. Credit the photographer
  and site in the video, the YouTube description and the TikTok caption.
- **Captions spark the imagination**: description and TikTok caption open with one vivid second-person scene
  (1–2 sentences) — a lifestyle moment (road trip, beach walk, hiking, running, leisure drive, boat ride,
  rooftop evening, slow morning coffee, cycling, picnic…) at a famous tourist attraction somewhere in the world,
  matching the style's `mood`; never repeat an activity + place pairing from `TRACKS.md`.
- Never reuse a photo or a title. Nothing in titles, captions or descriptions mentions AI.
- `madeForKids` always false; YouTube category MUSIC, type short. TikTok `isAigc` false and YouTube
  `isAiGeneratedContent` false (Sello's decision, 10 Oct 2026).
- The video is removed from the `media` branch once Metricool has copied it.
- `music.py` (v1) is kept only so dvg001 can be rebuilt; it may not be used for releases.
