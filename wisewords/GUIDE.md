# Wise Words with Marco Reyes — writing guide

A recurring vertical video (YouTube Short + TikTok), **exactly 2:55**, 1080×1920.
Marco Reyes — a round, jolly, old-school former trader with a white handlebar moustache,
bow tie and glasses parked on his bald head — tells one short story from his study, and every turn in the story lands on a famous quote.

## Audience and tone
- **Audience: the USA, 18+ target.** The show is published as NOT "made for kids".
- **Keep it very simple** — short sentences and everyday words a 10-year-old could follow — but
  the story, characters and examples are fully adult: jobs, bills, layoffs, family, health,
  friendships, starting over. Nothing that makes the viewer feel like a child (no school
  classrooms, crayons, playgrounds, "the new kid", parents' rules).
- **Never call the audience children.** Greet "everyone"; say "you".
- Warm, wry, a little funny. Marco may make one gentle joke about himself per episode.
- American English: US spelling (pedaling, color, favorite, mom), US references and units (dollars, miles, Fahrenheit, 401(k), the DMV, Thanksgiving). Non-US quote authors are fine — say in a few words who they were.

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
  "youtube_title": "…under 70 chars, ends with #shorts",
  "description": "…2 sentences + 3–5 hashtags incl. #shorts…",
  "tiktok_caption": "…under 150 chars with 3–5 hashtags…",
  "tags": ["quotes", "life advice", …]
}
```
The open and sign-off segments also need `head`, `quote` (a one-line summary card) and `author`.
Write numbers as words in `lines` ("one hundred percent") so the voice reads them right.

Build: `./wisewords/make.sh wisewords/episodes/wwNNN.json` → `out/wwNNN.mp4` (about 2–4 minutes).
