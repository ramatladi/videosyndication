# DJ Velvet Purple — Mirage Tropical Records (YouTube)

Instrumental house/disco by **DJ Velvet Purple**, released on the **Mirage Tropical Records** YouTube channel through Metricool
(brand "Mirage Tropical Records", blogId **7593699**, YouTube only, timezone Africa/Johannesburg). Started 22 Oct 2026 (Sello).

## Schedule
- **Two uploads a day, six hours apart:** a 16:9 **video** at **23:55 SAST** (17:55 US Eastern) and a 9:16 **Short** at
  **05:55 SAST** the next morning (23:55 US Eastern). Every upload is a different song.
- mtr001–mtr010 were built and scheduled on 22 Oct 2026 (videos 22–26 Oct, Shorts 23–27 Oct). From then on the daily
  scheduled task builds the next video + Short with `make_release.py` and schedules them.

## Rules
- **Instrumental only — no vocals.** Every sound is a recorded instrument: djvelvetgrey engine v4 in real-instruments mode
  (`"instruments": "real"`; synth voices are disabled during the render).
- **Every release different** (enforced by `make_release.py plan` against `ledger.json` + `catalog.json`): style rotation over
  the 12 styles (never the same style twice in a row), key+mode not used in the last 10 releases, tempo not within 1 BPM of the
  previous one, chord loop at most 0.75 alike to any of the last 30, lead/answer instrument families not used in the last 3,
  hook melody the furthest of 48 candidates from every earlier release and at least 0.25 away (near-copies score below 0.18). A plan that can't meet this stops instead of publishing.
- **Fail-closed:** a release is only scheduled if `qc.py` passed (exit 0) on the final WAV/MP3/AAC. Nothing is described as
  listened to — all checks are automated.
- **Photo (Sello, 23 Oct 2026):** every upload shows one or more attractive adult women in bikinis, any setting (beach, pool,
  boat, island, coastline…). Tasteful: clearly adults, face visible, natural or glamour poses, no nudity or see-through swimwear,
  no close-up body crops, no rear/thong-focused shots, no logos, text, watermarks or alcohol branding. Free Unsplash License only
  (never Unsplash+), never reused (see `ledger.json`). Landscape for the video (pre-crop to 16:9 if the centre crop would cut the
  head), portrait for the Short. **The photo credit is in the description only — never drawn on the video.**
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
  title, style label + "Instrumental", live equalizer (no photo credit on screen).
- `describe.py` — YouTube title, description and tags.
- `ledger.json` — every release (format, slot, title, style, key, tempo, instruments, chord loop, photo, Metricool uuid).
- `catalog.json` — hook melodies of every release (melody-distance screening).
- `sets/2026-10-22/` — how the first 10 were made (from the hit-style set, instrumental versions).
