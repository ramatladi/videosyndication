# DJ Velvet Grey — weekly house tracks

Two original tracks a week by **DJ Velvet Grey**, each a 2:59 (179.0 s) vertical video of one
beach/nature photo featuring a woman in a bikini with a slow zoom, the track title, a live equalizer and the photo credit,
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
