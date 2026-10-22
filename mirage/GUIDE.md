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
  hook melody distance ≥ 0.35 to every earlier release. A plan that can't meet this stops instead of publishing.
- **Fail-closed:** a release is only scheduled if `qc.py` passed (exit 0) on the final WAV/MP3/AAC. Nothing is described as
  listened to — all checks are automated.
- **Photo:** one free-licence tropical/nature photo per release (Unsplash License, never Unsplash+), no people in focus, no
  logos or text, never reused (see `ledger.json`). Credited on screen and in the description.
- **Text:** title `<Title> - DJ Velvet Purple | <Style> Instrumental` (Shorts add ` #shorts`); description = one line on the
  mood/instruments, key and BPM, photo credit + page URL, "Music: DJ Velvet Purple", "Label: Mirage Tropical Records",
  hashtags. Nothing mentions AI. YouTube: category MUSIC, madeForKids false, isAiGeneratedContent false (Sello's standing
  preference for all his uploads).
- Media is hosted temporarily on the repo's `media` branch (`mtrNNN.mp4`) and removed once Metricool has copied it
  (`static.metricool.com`).

## Files
- `make_release.py` — `plan` / `build --format video|short` / `record`.
- `video.py` (16:9) and `video_short.py` (9:16) — photo, slow zoom, "DJ VELVET PURPLE" + "Mirage Tropical Records",
  title, style label + "Instrumental", live equalizer, photo credit.
- `ledger.json` — every release (format, slot, title, style, key, tempo, instruments, chord loop, photo, Metricool uuid).
- `catalog.json` — hook melodies of every release (melody-distance screening).
- `sets/2026-10-22/` — how the first 10 were made (from the hit-style set, instrumental versions).
