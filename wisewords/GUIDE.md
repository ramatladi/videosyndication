# Wise Words with Marco Reyes — writing guide

A recurring vertical video (YouTube Short + TikTok), **exactly 2:55**, 1080×1920.
Marco Reyes — a round, jolly, old-school former trader with a white handlebar moustache,
bow tie and glasses parked on his bald head — presents famous quotes in a news-bulletin
format from his wood-panelled study, and explains each one.

## Audience and tone
- **Audience: adults, 18+.** Topics are adult life: work, money, ambition, failure,
  relationships, friendship, family, health habits, patience, courage, change, ageing, purpose.
- **Language: simple enough that a 10-year-old could follow it.** Short sentences, everyday
  words, one concrete example per quote (a job interview, a bad week, a phone call to your mum,
  a gym you never go to). No jargon, no market talk.
- Never address children (no "young listeners", "your teacher", "crayons"). The show must not
  be "made for kids".
- Warm, wry, a little funny. Marco may make one gentle joke about himself per episode.
- Global English. Don't assume the viewer's country.

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

## Structure (segments in the episode JSON)
1. Open — "Good evening, everyone. I'm Marco Reyes, and this is Wise Words…" (≈4–5 lines)
2–7. One segment per quote: who said it (one short phrase about who they were), the quote read
   in full, then 2–4 lines explaining it with an everyday example, ending on a punchy takeaway.
8. Sign-off — a one-line recap of all six ideas, then "I'm Marco Reyes. Good night."

About **400–430 spoken words** in total. The renderer stops with `SCRIPT TOO LONG` / `SCRIPT TOO
SHORT` and the number of seconds to cut or add.

## Episode JSON (`wisewords/episodes/wwNNN.json`)
```
{
  "title": "Wise Words", "subtitle": "WITH MARCO REYES  ·  WISE WORDS",
  "voice": "am_onyx", "speed": 0.86,
  "segments": [
    {"head": "STORY 1: KEEP PEDALLING",            // red headline band, UPPERCASE, under 30 chars
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
