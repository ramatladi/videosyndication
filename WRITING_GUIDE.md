# Writing a new episode

Every episode is a fresh, original animated skit built on **what is trending in the United States this week**.
Each episode gets its **own cast and setting**, designed for that trend. Don't reuse the same characters day after day
(a character may return only if the trend calls for a recurring bit, and never two days in a row).

Episodes use the **cast engine**: one JSON file in `episodes/` with `"engine": "cast"`.
Full working example: `episodes/examples/cast_example.json`.
(The original barn episodes 001–002 used the legacy Marigold/Pip/Gourdon renderer — don't use that for new episodes.)

## 1. Find the trend (every episode)
Research before writing (WebSearch/WebFetch), US-focused, this week:
- TikTok trends this month (e.g. newengen.com/insights "<month> <year> TikTok trends"; also "TikTok trending sounds this week")
- Instagram Reels trends, YouTube Shorts trends
- Google Trends US daily: https://trends.google.com/trends/trendingsearches/daily?geo=US

Pick the **most trending format or topic that works as a dialogue skit** (POV, "answer in one word", documentary narration,
"tell me without telling me", absurd-rule skit, bait-and-switch, reaction, interview, a viral challenge acted out by characters,
a big sports weekend, a holiday, the weather, a hyped release referred to generically…). Prefer a different format from the last 3 episodes in `EPISODES.md`.

**Never:** tragedies, crime, violence, politics, health scares, real people or their names, brand / team / show / product names,
logos, copyrighted characters, lyrics or quotes. Refer to things generically ("the big game", "that new show everyone is watching").
All-ages, US-English.

## 2. Design the cast for the trend (2–4 characters)
Each cast member: `{"id", "name", "kind", "color", ... , "voice": {...}}`
- `kind`: `human` | `animal` | `mascot` (a talking object or creature)
- `color`: skin (human), fur (animal) or body colour (mascot) — hex
- `scale`: optional 0.85–1.15 (kids smaller, big personalities bigger)
- **human**: `hair` `{"style": short|long|curly|afro|bun|ponytail|spiky|mohawk|bald, "color"}`
- **animal**: `ears`: cat|fox|bear|mouse|bunny|dog; optional `snout` (default true), `belly`, `inner` colours
- **mascot**: `shape`: gumdrop|box|cup|phone|ghost|pumpkin|egg|ball|football|toast; optional `case` (phone), `sleeve`/`lid` (cup), `crust` (toast)
- clothes (human/animal): `top` `{"color", "pattern": plain|stripes|dots|jersey|hoodie|suit|apron, "pattern_color", "number"}`, `bottom`, `shoes`
- `accessories` (list, optional `:#hex` colour): glasses, sunglasses, cap, beanie, crown, headphones, mic_headset, bow, tophat, witchhat,
  party_hat, chef_hat, tie, scarf, whistle, halo, horns — e.g. `"cap:#c0392b"` (`bow` is a hair bow worn on the head, not a bow tie; use `tie` for men)
- face: `eye`: round|big|sleepy|happy; `brows`: neutral|angry|worried|raised; `mouth` when silent: smile|flat|frown; `blush`: true/false
- `label_color`: optional caption name colour
- **voice** `{"id", "pitch", "tempo"}` — natural HUMAN voices only, never cartoon voices. `id` is one of:
  US female `af_heart` `af_bella` `af_nicole` (soft/whispery) `af_sarah` `af_jessica` `af_river` `af_nova` `af_kore` `af_aoede`;
  US male `am_michael` `am_adam` `am_eric` `am_liam` `am_onyx` (deep) `am_echo` `am_puck` (playful) `am_fenrir` (gruff);
  British female `bf_emma` `bf_isabella` `bf_alice` `bf_lily`; British male `bm_george` `bm_lewis` `bm_daniel` `bm_fable`.
  `pitch` −2…+2 semitones only (subtle), `tempo` 0.85–1.15. Animals and talking objects still speak with a normal human
  voice (that contrast is part of the joke). Give every character a different `id`.

Make the look tell the joke instantly: a referee with a whistle and stripes, a dramatic cat in a suit, a phone that's "too online",
a sleepy coffee cup, a ghost at a party, etc.

## Never mention AI
No caption, title, description, hook card, tag or line of dialogue may say or hint that AI, a chatbot or a computer
wrote, made or chose anything ("we asked AI…", "an AI wrote this…", "ChatGPT…"). Present every video as our own.

## 3. Scene, music, hook
- `scene`: studio | kitchen | living_room | classroom | office | street_night | park_day | stadium | bedroom | halloween_porch | barn
- `desk`: true puts a desk in front (podcast, news, interview, talk show — best with `studio` or `office`)
- `music`: upbeat | lofi | dramatic (documentary/serious) | spooky
- `intro`: on-screen hook card, 2–3 short lowercase lines, the last one smaller — usually the trend's own phrasing (e.g. "pov:", "answer in one word", "tell me you're X without telling me")

## 4. Script
- **Every video is exactly 2:55 (175 s).** Write about **58–70 lines** (roughly 145–170 s of natural speech); the engine stretches pauses
  and the outro to land on 2:55 exactly. If the render step says `SCRIPT TOO LONG` or `SCRIPT TOO SHORT`, cut or add lines by the amount it gives.
  Short sentences; every line under ~20 words. Structure for the length: hook in the first 2 lines, then 3 escalating beats (each with its own
  mini-punchline and a sound effect), a twist around the two-minute mark, and a final button line.
- Speakable text only: no emoji, no stage directions, numbers as words, no abbreviations or ALL CAPS.
- Line: `{"spk": "<id>" | ["id1","id2"] | "all", "text", "shot", "gesture", "jump", "pre", "post", "after"}`
  - `shot`: `CU` close-up on speaker (default), `TWO` speaker + the last other speaker, `W` wide (everyone), or a cast id for a reaction close-up
  - `gesture`: talk (default while speaking), wave, point, shrug, arms_up, cross, hips, facepalm, think
  - `jump`: true = speaker hops (excitement)
  - `pre`/`post`: silence before/after in seconds (defaults 0 / 0.45); `pre` 0.8–1.0 = awkward pause
  - `after`: sound effect after the line — sting, boing, whoosh, applause, rimshot, record_scratch, ding (use 4–7 per episode)

## 5. Metadata
`id`, `slug`, `title`, `trend` (what trend and where), `youtube_title` (≤ 90 chars), `description` (2–3 lines + hashtags incl. the trend's hashtag and #shorts),
`tags` (6–10), `tiktok_caption` (≤ 150 chars with hashtags).

After writing, add a row to the END of `EPISODES.md`: `| NNN | date | title | Trend: … — premise | cast | key jokes |`.
