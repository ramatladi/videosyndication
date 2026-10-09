# Writing a new Marigold, Pip & Gourdon episode

Each episode is one JSON file in `episodes/` (see `episodes/ep001.json` for a full example).
Format of the video: the TikTok "we had an AI write our script" trend — a deadpan, melodramatic
skit played completely straight, in one barn set at night.

## Audience and trends (do this first, every episode)
Target audience: **the United States**. Every episode must ride something trending in the US *this week*:
1. Research before writing (WebSearch/WebFetch): this month's TikTok trends (e.g. newengen.com/insights "<month> TikTok trends"),
   Instagram Reels trends, YouTube Shorts trends, and Google Trends US daily (trends.google.com/trends/trendingsearches/daily?geo=US).
2. Pick ONE trending **format** that suits a multi-character dialogue skit (e.g. "answer in one word", POV, documentary chair-sit,
   absurd-rule skit, bait-and-switch), and optionally ONE light **topic** hook from US trends (sports weekend, a holiday, weather,
   a viral challenge, a big streaming release — referred to generically).
3. Never touch tragedies, crime, politics, health scares, real people's names, team/brand/show names, or copyrighted songs/quotes.
   Keep it US-English (fall, candy, football, Thanksgiving, etc.).
4. Record the trend you used in the episode's `trend` field and in EPISODES.md. Use the trend's hashtag in the captions.

## The cast (never change their personalities)
- **Marigold (`M`)** — a patchwork scarecrow queen. Dignified, dramatic, secretly soft. Takes everything personally.
- **Pip (`P`)** — her small crow, lives on her shoulder. Blunt, literal, a little selfish, deeply loyal. Loves corn.
- **Gourdon (`G`)** — a jack-o'-lantern on the floor. Theatrical, over-emotional narrator who butts in. Says one-word interjections ("Gasp.", "Kiss.") and grand false morals.

## Rules
1. **Brand-new premise every episode.** Read `EPISODES.md` first and do not reuse a premise, conflict, punchline or callback that's listed there. Vary the situation (a mystery, a talent show, a job interview, a haunted object, a family visit, a misunderstanding, a holiday, a competition, a secret, therapy for Gourdon, …).
2. **Length:** 24–36 lines, about 70–120 seconds. Short sentences (TTS reads them better). Every line under about 20 words.
3. **Speakable text only:** no emoji, no stage directions in `text`, numbers as words, no abbreviations, no ALL CAPS. Use `.`, `?` and `,` for rhythm.
4. **Clean, all-ages comedy.** No profanity, violence, romance beyond a joke "Kiss." gag, real people, brands, or copyrighted characters/songs.
5. **Structure:** cold open with the conflict in the first two lines → escalate → absurd twist → button line. End with Gourdon if the candle gag is used.
6. **Season:** Halloween framing up to 31 October; after that, autumn/spooky-cosy or whatever holiday is near — keep the barn.

## Line fields
`{"spk": "M"|"P"|"G"|"MP", "text": "...", "shot": "W"|"MP"|"M"|"P"|"G", "pre": 0.0, "post": 0.5, "during": ..., "after": ...}`
- `spk`: `MP` = Marigold and Pip say it together (use for one or two words only).
- `shot`: `W` wide (all three), `MP` two-shot of Marigold & Pip, `M`/`P`/`G` close-ups. Use the speaker's close-up most of the time, `MP` for back-and-forth, `W` for reactions or physical gags. Gourdon lines usually `G`.
- `pre` / `post`: seconds of silence before/after (default 0 / 0.5). Use `pre` 0.8–1.0 for an awkward pause, `post` 1.3–1.5 before a sting.
- `during` (optional): `"arms"` — Marigold throws her arms out wide during her line (once per episode at most); `"flare"` — Gourdon's candle flares up while he speaks.
- `after` (optional): `"sting"` — a dun-dun-DUN organ sting (max 2 per episode); `"fly"` — Pip flies off-screen and comes back a few seconds later (max once; the next line should acknowledge it); `"candle_out"` — Gourdon's candle blows out and the episode ends in the dark with Marigold's glowing eyes (only on the LAST line).

## Episode file fields
- `id` (number), `slug`, `title`
- `intro`: on-screen hook card, 2–3 short lowercase lines, the last one smaller (e.g. `["we had an AI write our", "halloween script", "we changed nothing"]`). Vary it each time.
- `youtube_title` (≤ 90 chars, include the episode title), `description` (2–4 lines + hashtags incl. #shorts), `tags` (6–10), `tiktok_caption` (≤ 150 chars with hashtags)
- `lines`: the script.

After writing it, add a row to `EPISODES.md`: `| NNN | date | title | one-line premise | key jokes |`.
