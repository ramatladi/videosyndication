# DJ Velvet Purple — Mirage Tropical Records (YouTube)

Instrumental house/disco by **DJ Velvet Purple**, released on the **Mirage Tropical Records** YouTube channel through Metricool
(brand "Mirage Tropical Records", blogId **7593699**, YouTube only, timezone Africa/Johannesburg). Started 22 Oct 2026 (Sello).

## Schedule
- **Six uploads a day (Sello, 23 Oct 2026): 2 videos + 4 Shorts, every 4 hours (SAST):** 23:55 **video**, 03:55 Short,
  07:55 Short, 11:55 **video**, 15:55 Short, 19:55 Short. Every upload is a different song. (Until 23 Oct: one video at 23:55
  and one Short at 05:55; the already-scheduled Shorts of 24-27 Oct were moved to 03:55.)
- Three scheduled tasks share the day, each building and scheduling two slots with `make_release.py`:
  19:37 → 23:55 video + 03:55 Short (next day); 03:37 → 07:55 Short + 11:55 video; 11:37 → 15:55 Short + 19:55 Short.

## Rules
- **Styles (15):** Deep, Melodic, House, Afro, Tropical, **Future Bass**, Nu-Disco, Progressive House, Tech House, **Trance**,
  Vocal House (instrumental), Soulful, **Indie Dance**, Disco, French House. The three in bold were added 23 Oct (Sello) as
  Mirage-only styles (`EXTRA_STYLES` in djvelvetgrey/v2/styles.py; DJ Velvet Grey's 12-style rotation is unchanged). Each was
  test-built end to end in real-instruments mode and passed QC before going live.
- **Instrumental only — no vocals.** Every sound is a recorded instrument: djvelvetgrey engine v4 in real-instruments mode
  (`"instruments": "real"`; synth voices are disabled during the render).
- **Every release different** (enforced by `make_release.py plan` against `ledger.json` + `catalog.json`): style rotation over
  the 15 styles (never the same style twice in a row), key+mode not used in the last 10 releases, tempo not within 1 BPM of the
  previous one, chord loop at most 0.85 alike to each release of the last day (1.0 = same loop), production never identical to an earlier release in 5 of its 6 choices, lead/answer instrument families of the last 2 releases avoided,
  hook melody searched over every rhythm cell x contour x start note of the style (plus generated rhythms when needed), realised exactly as rendered, the furthest from every earlier release and at least 0.25 away (near-copies score below 0.18). A plan that can't meet this stops instead of publishing.
- **Fail-closed:** a release is only scheduled if `qc.py` passed (exit 0) on the final WAV/MP3/AAC. Nothing is described as
  listened to — all checks are automated.
- **Photo (Sello, 23 Oct 2026), in this order of preference:**
  1. **Bikini:** one or more attractive adult women in bikinis, any setting (beach, pool, boat, island, coastline…).
  2. **Fashion models** (only when no unused qualifying bikini photo can be found): one or more adult fashion models wearing
     anything (swimwear, summer dresses, streetwear, evening wear), any setting.
  3. **Nature** (only when neither of the above can be found): tropical/nature scenery, no person in focus.
  Tasteful throughout: clearly adults, face visible, natural or glamour poses, no nudity or see-through clothing, no close-up
  body crops, no rear/thong-focused shots, no logos, text, watermarks or alcohol branding. Free Unsplash License only (never
  Unsplash+), never reused (see `ledger.json`, which records `photo_kind`). Landscape for the video (pre-crop to 16:9 if the
  centre crop would cut the head), portrait for the Short. **The photo credit is in the description only — never drawn on the
  video.**
- **Text:** title `<Title> - DJ Velvet Purple | <Style> Instrumental` (Shorts add ` #shorts`). Description from `describe.py`,
  laid out like the most-viewed uploads on big house/disco channels: `🎧 DJ Velvet Purple - <Title> (<Genre> Instrumental)`, a
  one-line mood/instrument hook, subscribe + like call, track/artist/label/genre/key/BPM lines, photo credit + page URL, a
  "<genre> for …" keyword line and hashtags. Nothing mentions AI. YouTube: category MUSIC, madeForKids false,
  isAiGeneratedContent false (Sello's standing preference for all his uploads).
- Media is hosted temporarily on the repo's `media` branch (`mtrNNN.mp4`) and removed once Metricool has copied it
  (`static.metricool.com`).

## Files
- `make_release.py` — `plan` / `build --format video|short` / `record`.
- `video.py` (16:9) and `video_short.py` (9:16) — photo, slow zoom, "DJ VELVET PURPLE" + "Mirage Tropical Records",
  title, style label + "Instrumental", live equalizer (no photo credit on screen). The brand sits on a dark frosted pill with a purple rule so it stays
  legible on bright skies and sand.
- `describe.py` — YouTube title, description and tags.
- `ledger.json` — every release (format, slot, title, style, key, tempo, instruments, chord loop, photo, Metricool uuid).
- `catalog.json` — hook melodies of every release (melody-distance screening).
- `sets/2026-10-22/` — how the first 10 were made (from the hit-style set, instrumental versions).
