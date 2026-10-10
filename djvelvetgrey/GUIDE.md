# DJ Velvet Grey — weekly house tracks

Two original tracks a week by **DJ Velvet Grey**, each a 2:59 (179.0 s) vertical video of one
beach/nature photo featuring a woman in a bikini with a slow zoom, the track title, a live equalizer and the photo credit,
published to YouTube (Short) and TikTok through Metricool (brand `everythingyouwant_tv`, id 7321327).

| Day | Style (`style`) | Sound |
|---|---|---|
| Tuesday | `chill` — Melodic Chill House | instrumental: bright lead motif with call-and-response, airy pads, four-on-the-floor |
| Friday | `deep` — Deep House | instrumental: warm lead motif with call-and-response, rolling/walking bass, swung shakers/congas |

**Every new track uses engine v2** (`"engine": "v2"`, section below). The original `music.py` is kept only
so the first published track (dvg001) can be rebuilt.

Both styles come from Sello's own library (Oct 2026 study: 58% deep house, 17% melodic house;
top artists Paul Lock, Jerro, Sharapov, Nando Fortunato, NICCKO, Housenick, Papa Tin,
Pete Bellis & Tommy). `music.py` changes key, tempo, chord progression, melodies, patterns and
lead sound with every seed, so each track is new.

## Files
- `music.py` — track generator (`--style chill|deep --seed N --out x.wav`), always exactly 179.0 s
- `video.py` — 1080x1920 video from photo + audio + title + credit
- `make.sh tracks/dvgNNN.json` — builds `out/dvgNNN.mp4` and `out/dvgNNN.mp3` (takes ~6 min; run it in the background and poll)
- `tracks/dvgNNN.json` — one file per published track; `TRACKS.md` — log of every track and photo used

## Track file
```json
{
  "title": "Silver Fern Morning",
  "style": "chill",
  "seed": 482913,
  "image": "djvelvetgrey/photos/dvg001.jpg",
  "photo_page": "https://unsplash.com/photos/...",
  "photo_url": "https://images.unsplash.com/photo-...",
  "photographer": "Jane Doe",
  "photo_site": "Unsplash",
  "credit": "Photo: Jane Doe / Unsplash",
  "youtube_title": "Silver Fern Morning — DJ Velvet Grey | Melodic Chill House",
  "scene": "Road trip — Pacific Coast Highway, Big Sur",
  "description": "Picture yourself ... (scene first, then credit and hashtags)",
  "tiktok_caption": "...",
  "tags": ["deep house", "chill house", "DJ Velvet Grey", "..."]
}
```

## Rules
- **Title**: original, evocative, nature/mood inspired, 2–4 words, Title Case; never used before in
  `TRACKS.md` and not the title of a well-known existing song (check with a quick web search).
- **Photo**: a beautiful natural setting (beach, ocean, lake, island, waterfall, coastline, dunes,
  tropical lagoon…) featuring one or more adult women in bikinis — the "lady in a bikini" beach-lifestyle
  look. Keep it tasteful: clearly adults, natural relaxed or playful poses with the scenery clearly visible,
  no nudity or see-through swimwear, no close-up crops of body parts, no explicit or provocative posing,
  no visible brand logos, no text or watermarks, no buildings or vehicles dominating the frame. Portrait
  or large enough to crop to 9:16 (at least ~1600 px on the short side). Leave the lower-middle of the frame
  for the title (the subject sits best in the upper two-thirds or off-centre).
- **Finding photos**: Unsplash search pages work with WebFetch, e.g.
  `https://unsplash.com/s/photos/woman-bikini-beach?orientation=portrait&license=free`; then confirm on the
  photo page that it says "Free to use under the Unsplash License". Pexels search pages block fetching.
- **Photo sources**: free-license sites only — Unsplash (Unsplash License; never Unsplash+),
  Pexels (Pexels License) or Pixabay (Pixabay Content License). Always credit the photographer and
  site in the video (`credit`) and in the YouTube description and TikTok caption.
- **Captions spark the imagination**: the YouTube description and TikTok caption open with one vivid,
  second-person scene (1–2 sentences) of where this track belongs — a lifestyle moment or activity
  (road trip, beach walk, hiking, running, a leisure drive, a boat at sunset, a rooftop evening,
  a slow morning coffee, cycling, a picnic…) set at a famous tourist attraction somewhere in the world
  (e.g. driving the Pacific Coast Highway, a sunrise hike up Table Mountain, a boat on Lake Como,
  a run along Copacabana, Iceland's Ring Road, the Amalfi Coast, Santorini at sunset, Banff's Moraine Lake).
  Match the track's mood (chill = bright and breezy, deep = warm and after-dark) and the photo's feel;
  never repeat an activity + place pairing from `TRACKS.md`.
- Never reuse a photo or a title listed in `TRACKS.md`.
- Nothing in titles, captions or descriptions mentions AI.
- `madeForKids` is always false; YouTube category MUSIC, type short.
- The video is removed from the `media` branch once Metricool has copied it.

## Engine v2 — distinct, instrumental-first tracks (`djvelvetgrey/v2/`)
Required for all new tracks (Sello, Oct 2026): set `"engine": "v2"` and a `"brief"` in the track file.
Track files without it fall back to the original generator (only dvg001 relies on that).

**Workflow per track:** written brief → 6 motif candidates → catalogue screen → selection → developed
arrangement → mix → automated QC → listening feedback.

1. **Brief** (`"brief"` in the track file): mood, `lead` and `answer` instruments (mallet, pluck, flute,
   rhodes, kalimba, glass), `progression` (scale degree + chord type), `groove` (`bass_a`, `bass_b` from
   offbeat, rolling, syncop, octave, walk, sustain; optional `swing`), `arc` (classic, early, burn, wave),
   `bpm`, `tonic` (MIDI), `loudness_lufs`, `seed`. Vary these deliberately between tracks — a new title,
   key, seed or photo does not make a new composition.
2. **Motif candidates:** `python3 djvelvetgrey/v2/previews.py djvelvetgrey/tracks/dvgNNN.json <outdir>`
   writes six 8-bar hook previews at equal loudness (-14 LUFS) over the same backing, plus
   `candidates.json` with compositional evidence and a shortlist of three. The shortlist is NOT a listening
   judgement; a listener chooses. Record the choice with
   `python3 djvelvetgrey/v2/select_motif.py <track.json> <outdir>/candidates.json [id]` (no id = automatic pick:
   top-scoring shortlisted candidate without catalogue flags, recorded as not a listening judgement).
   Before previews, run `python3 djvelvetgrey/v2/brief_check.py <track.json>` and revise the brief if it
   flags repeated arc/progression/lead/bass choices. After publishing, catalogue the motif with
   `python3 djvelvetgrey/v2/catalog_add.py <track.json> dvgNNN`.
3. **Motif design:** 2-bar rhythm cell + contour, developed into an 8-bar call (lead) and response
   (answer instrument) hook, strong/long notes on chord tones. The motif is teased ~2–10 s in and the full
   hook lands ~15–25 s in (all four arcs). The second drop develops the idea (bass pattern change, lead up
   an octave, guide-tone countermelody, extra percussion).
4. **Catalogue screening** (`djvelvetgrey/catalog.json`): motifs compared by intervals + rhythm + contour,
   including transposed, shifted and rotated versions. Calibration (`python3 djvelvetgrey/v2/compose.py`):
   identical/transposed/shifted 0.0, one changed interval ~0.02–0.06, different motifs 0.26–0.61; distances
   below 0.18 are flagged for revision or review. Identical progression + arc + groove + lead combinations
   are flagged too. This screens our own catalogue only; it is not an all-music originality guarantee.
5. **Sound and mix:** original synthesis (PolyBLEP oscillators, filter envelopes, FM bells, synthesised
   drums with humanised timing/velocity, ghost hats, fills every 8 bars), per-group gain staging and bus
   compression, kick sidechain, separate reverb/delay returns, low end mono below ~120 Hz, loudness set
   by the brief, true-peak limiter at -1.5 dBTP internally. Licensed drum one-shots may be added later only
   with documented terms permitting commercial use, logged with source and licence.
6. **QC** (`djvelvetgrey/v2/qc.py`, run automatically by make.sh for v2): duration, integrated loudness,
   true peak on the encoded file (target ≤ -1.0 dBTP), clipping, click suspects (spikes not repeated 1, 2,
   8 or 16 bars earlier), silence, mono compatibility, low end below 80 Hz mono, tease/hook timing and
   second-drop changes. These are automated technical checks only — hook memorability, groove feel, tone
   and mix balance, the second-drop payoff and overall quality need listening.

Counts above (6 candidates, 4 arcs, fills every 8 bars, range ≤ a tenth) are starting heuristics, not
quality gates. Upgraded tracks are recommended for listener review before release; automated selection is
never described as listening approval.
