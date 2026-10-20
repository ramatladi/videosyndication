# Writing a new episode

Every episode is a fresh, original animated skit built on **what is trending in the United States this week**.
Each render makes two files: `out/epNNN.mp4` (9:16, for TikTok and Instagram) and `out/epNNN_yt.mp4` (16:9, posted to YouTube as a regular video, not a Short).
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

## 4. Length and script
- **Length (`target_seconds`):** pick a length that fits the trend: about as long as the original trend content runs,
  never under **175 (2:55)** and never over **1795 (29:55)**. Quick one-clip formats (POV, one-word answers, a dance
  or prank reveal) stay at 175–240. Formats with more story behind them (documentary narration, storytime, a home tour,
  a series, a big event or holiday with many angles) can run 300–600. Go past 600 (10 minutes) only when the trend itself
  is long-form, because TikTok takes 10 minutes at most. Instagram Reels take 3 minutes at most, so anything over 180
  goes to YouTube and TikTok only. Write the reason in `length_reason`.
- **Lines:** about **22 lines per minute** of `target_seconds` (58–70 lines for 2:55, about 110 for 5:00, about 220 for 10:00).
  The engine stretches pauses and the outro to land exactly on the target. If the render step says `SCRIPT TOO LONG`
  or `SCRIPT TOO SHORT`, cut or add lines by the amount it gives.
  Keep sentences short, every line under about 20 words.
- **Structure:** hook in the first 2 lines, then 3 escalating beats (each with its own mini-punchline and a sound effect),
  a twist at about 70% of the running time, and a final button line. For episodes over 5 minutes, add one more beat
  per extra 2–3 minutes, give each beat its own small story turn, and bring back an earlier joke every couple of minutes
  so it stays funny all the way through.
- Speakable text only: no emoji, no stage directions, numbers as words, no abbreviations or ALL CAPS.
- Line: `{"spk": "<id>" | ["id1","id2"] | "all", "text", "shot", "gesture", "jump", "pre", "post", "after"}`
  - `shot`: `CU` close-up on speaker (default), `TWO` speaker + the last other speaker, `W` wide (everyone), or a cast id for a reaction close-up
  - `gesture`: talk (default while speaking), wave, point, shrug, arms_up, cross, hips, facepalm, think
  - `jump`: true = speaker hops (excitement)
  - `pre`/`post`: silence before/after in seconds (defaults 0 / 0.45); `pre` 0.8–1.0 = awkward pause
  - `after`: sound effect after the line — sting, boing, whoosh, applause, rimshot, record_scratch, ding (use 4–7 per 2:55, roughly 2 per extra minute)

## 5. Metadata
`id`, `slug`, `title`, `trend` (what trend and where), `target_seconds`, `length_reason`, `youtube_title` (≤ 90 chars),
`description` (2–3 lines + hashtags incl. the trend's hashtag; no #shorts, because YouTube gets a regular 16:9 video),
`tags` (6–10), `tiktok_caption` (≤ 150 chars with hashtags).

After writing, add a row to the END of `EPISODES.md`: `| NNN | date | title | Trend: … — premise | cast | key jokes |`.
