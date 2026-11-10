# Wise Words with Marco Reyes — writing guide

A recurring story video, **exactly 2:55**, rendered in two versions from the same script:
`out/wwNNN.mp4` (1080×1920) and `out/wwNNN_yt.mp4` (1920×1080).
Marco Reyes — a round, jolly, old-school storyteller with a white handlebar moustache, red bow tie,
green cardigan and gold glasses parked on his bald head — fills the screen from his wingback chair in a
warm study (night-city window, bookshelf, banker's lamp, vintage microphone). He tells one short story,
and every turn in the story lands on a famous quote; he raises an open hand as he says each quote.
The studio art lives in `wisewords/scene.py`; `render.py` handles the camera (alternating wide and close
shots), captions, headline band and the quote card.

## Where episodes go (from ww030, 23 Oct 2026)
- YouTube channel "Marco Reyes - Mr. Wise Words" (@MrWiseWords, Metricool brand 7614792): six uploads a day, every one a different episode: 4 Shorts (the 1080×1920 file, YouTube type "short") at 08:00, 12:00, 18:00 and 22:00 America/New_York, and 2 regular videos (the 1920×1080 file, YouTube type "video") at 15:00 and 20:00.
- TikTok + Instagram Reels (Metricool brand everythingyouwant_tv, 7321327): only the two video-slot episodes, as their 1080×1920 version, at the same time as the YouTube video.
- Nothing goes to the everythingyouwant_tv YouTube channel any more (episodes up to ww029 stay there).
- Titles and descriptions never carry #shorts.

## Continuity rules (Sello, 10 Nov 2026)

Every run works through these steps in order, before starting new work:

1. **Resume first.** Look for work from the last 36 hours that was made but never posted: an episode JSON in wisewords/episodes/ with a row in wisewords/EPISODES.md. Check Metricool (getScheduledPosts on the brand, from that day to tomorrow) for a post with its title. If there is none, it never aired: render it again if its video file is gone, host it, schedule it in this run's slot (or at now + 30 minutes if this run's slot has passed), and update the ledger. Only then move on to new work, and never make new work for a slot this resumed item filled.
2. **Missed slots.** If a slot from the last 6 hours is empty because an earlier run failed or never ran, fill it with resumed or new work at now + 30 minutes, at most two make-up posts per run and 40 minutes apart. Leave slots older than 6 hours empty: never flood the channel to catch up.
3. **Record as you go.** Commit the episode JSON and EPISODES.md file right after writing it, and add the ledger or log entry right after createScheduledPost returns, so a run that dies part-way leaves enough behind for step 1 of the next run.
4. **Leftover hosted files.** Remove files on the media branch belonging to this series that are older than 24 hours, once Metricool has its copy (the post exists) or the item is logged as posted. Leave anything newer: it may belong to a run in progress.
5. **Refused or held steps.** If hosting, scheduling or any other step is refused or held for approval, do not retry it and do not look for another route around it. Leave the item committed but unposted, so step 1 of the next run picks it up, and send ONE PushNotification naming the step and the exact message.

## Audience and tone
- **Audience: the USA, 18+ target.** The show is published as NOT "made for kids".
- **Keep it very simple** — short sentences and everyday words a 10-year-old could follow — but
  the story, characters and examples are fully adult: jobs, bills, layoffs, family, health,
  friendships, starting over. Nothing that makes the viewer feel like a child (no school
  classrooms, crayons, playgrounds, "the new kid", parents' rules).
- **Never call the audience children.** Greet "everyone"; say "you".
- Warm, wry, a little funny. Marco may make one gentle joke about himself per episode.
- American English: US spelling (pedaling, color, favorite, mom), US references and units (dollars, miles, Fahrenheit, 401(k), the DMV, Thanksgiving). Non-US quote authors are fine — say in a few words who they were.

## Never mention AI
No caption, title, description, tag or spoken line may say or hint that AI or a computer wrote, made or
chose anything. Present every video as our own.

## Quotes
- Six quotes per episode, mixing eras and kinds of people (scientists, athletes, writers,
  leaders, philosophers, ancient sayings). Take them from BrainyQuote and other reputable
  quote sources (Wikiquote, Quote Investigator, the original speech, book or interview).
- **Accuracy rule:** use only quotes whose wording and attribution you can confirm. Check every
  quote on Wikiquote or Quote Investigator; if a quote is listed as "misattributed" or
  "disputed", don't use it (common traps: many "Einstein", "Mark Twain", "Buddha",
  "Maya Angelou", "Dr. Seuss" and "Oscar Wilde" lines).
- Each quote is under 25 words. No song lyrics, no poems or verse, no lines from films or TV.
- No quotes from living politicians, no political, religious or divisive topics, no tragedy.
- Don't reuse any quote already listed in `wisewords/EPISODES.md`.

## Structure: one story told through six quotes
Do NOT read a quote and then explain it. Marco tells ONE continuous story about one ordinary
American (a name, a town, a job, one problem) across six chapters. In each chapter something
happens, the character remembers or hears the quote at that moment, and what they do next
shows the lesson. The quote is the turning point, never a lecture. Never use a market-report,
stock-ticker or finance-jargon framing (indices, "trading at", "closed higher") — just a plain life story.
1. Open — "Good evening, everyone. I'm Marco Reyes, and this is Wise Words." + who the story is
   about + a hook (≈4–5 lines).
2–7. Six chapters (`head`: "CHAPTER N: SHORT TITLE"), 4–5 lines each: what happens, how the
   quote enters (a memory, a note, something a friend says), the quote spoken in full as its
   own line, then the action it leads to.
8. Sign-off — a one-line recap of the six lessons as actions, then "I'm Marco Reyes. Good night."
The on-screen quote card types out exactly when Marco says the quote, so the quote line must
contain the quote's words as written in `quote`.

About **400–430 spoken words** in total. The renderer stops with `SCRIPT TOO LONG` / `SCRIPT TOO
SHORT` and the number of seconds to cut or add.

## Episode JSON (`wisewords/episodes/wwNNN.json`)
```
{
  "title": "Wise Words", "subtitle": "WITH MARCO REYES  ·  STORY NIGHT",
  "voice": "am_onyx", "speed": 0.86,
  "segments": [
    {"head": "CHAPTER 1: THE COUCH",            // red headline band, UPPERCASE, under 30 chars
     "quote": "…exact quote…", "author": "Albert Einstein",
     "lines": ["spoken line", "spoken line", …]}   // one sentence or two short ones per line
  ],
  "youtube_title": "…under 70 chars, a story hook, no #shorts",
  "description": "…2 sentences + 3–5 hashtags (no #shorts)…",
  "tiktok_caption": "…under 150 chars with 3–5 hashtags…",
  "tags": ["quotes", "life advice", …]
}
```
The open and sign-off segments also need `head`, `quote` (a one-line summary card) and `author`.
Write numbers as words in `lines` ("one hundred percent") so the voice reads them right.

Build: `./wisewords/make.sh wisewords/episodes/wwNNN.json` → `out/wwNNN.mp4` + `out/wwNNN_yt.mp4` (about 8 minutes;
run it in the background and poll render.log for the two DONE lines).
