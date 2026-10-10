# DJ Velvet Grey — weekly house tracks

Two original tracks a week by **DJ Velvet Grey**, each a 2:59 (179.0 s) vertical video of one
beautiful nature photo with a slow zoom, the track title, a live equalizer and the photo credit,
published to YouTube (Short) and TikTok through Metricool (brand `everythingyouwant_tv`, id 7321327).

| Day | Style (`style`) | Sound |
|---|---|---|
| Tuesday | `chill` — Melodic Chill House | supersaw pads, plucky arp, four-on-the-floor, airy female vocal |
| Friday | `deep` — Vocal Deep House | Rhodes stabs, rolling bass, swung shakers/congas, flute or kalimba hook, female vocal |

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
  "description": "...",
  "tiktok_caption": "...",
  "tags": ["deep house", "chill house", "DJ Velvet Grey", "..."]
}
```

## Rules
- **Title**: original, evocative, nature/mood inspired, 2–4 words, Title Case; never used before in
  `TRACKS.md` and not the title of a well-known existing song (check with a quick web search).
- **Photo**: only beautiful nature — landscapes, mountains, forests, lakes, oceans, waterfalls,
  skies, flowers, deserts, auroras. No people, no buildings, roads, boats, vehicles or other
  man-made objects, no text, logos or watermarks, nothing dark or disturbing. Portrait or large
  enough to crop to 9:16 (at least ~1600 px on the short side).
- **Photo sources**: free-license sites only — Unsplash (Unsplash License; never Unsplash+),
  Pexels (Pexels License) or Pixabay (Pixabay Content License). Always credit the photographer and
  site in the video (`credit`) and in the YouTube description and TikTok caption.
- Never reuse a photo or a title listed in `TRACKS.md`.
- Nothing in titles, captions or descriptions mentions AI.
- `madeForKids` is always false; YouTube category MUSIC, type short.
- The video is removed from the `media` branch once Metricool has copied it.
