# Veritas Recruitment Agency — daily US tech jobs (YouTube)

Real, open US tech jobs read aloud by a natural voice, published on the **Veritas Recruitment Agency** YouTube channel
through Metricool (brand "Veritas Recruitment Agency", YouTube only). Started 23 Oct 2026 (Sello).

## Every day: 4 Shorts + 2 videos, for a US audience
Six different jobs a day, one per upload. Slots (US Eastern, `America/New_York`):

| Slot | Format | Time (ET) |
|---|---|---|
| S1 | Short | 08:15 |
| V1 | video | 11:45 |
| S2 | Short | 13:30 |
| S3 | Short | 16:45 |
| V2 | video | 19:15 |
| S4 | Short | 21:30 |

Short = 1080×1920, under 60 s (about 130–150 spoken words). Video = 1920×1080, about 2–3 minutes (300–380 words),
the fuller read: about the team, what you'll do, what you need, pay and benefits, how to apply.

## Rules
- **Jobs come only from Sello's own jobs collection, gathered from employers' own careers sites** (the daily task
  says where to read it). Never a job board or aggregator. Never name, link or hint at where the collection lives —
  not in a video, title, description, tag, file name or commit message.
- **US tech roles**: software, data, ML/AI, security, cloud/DevOps, networking, IT engineering. Posted in the last 4 days,
  seen by the collector in the last day, not closing within 3 days, pay published (preferred; required for videos).
  At most two jobs per employer per day, never a job already in `ledger.json`; mix seniority (new-grad/entry roles when
  there are any), cities and employers. Videos go to the roles with the richest postings.
- **Full details from the employer's own posting.** `fetch.py` (GitHub Actions) reads each posting from the employer's
  careers site; everything said and written comes from that text. Never invent pay, requirements or benefits; if the
  posting doesn't say it, leave it out. A job whose posting can't be fetched or has closed is replaced by a spare.
- **Own words.** The spoken script and the description summarise the posting in our own words (requirements and pay are
  facts and stay exact). No long verbatim copying of the employer's text.
- **Direct application link**: the job's official URL from the posting, first in the description. Every description
  also says Veritas is not the employer and not affiliated with it, and never charges candidates.
- **Voice**: Kokoro (`af_heart` and `am_michael`, alternating), natural speed (Short 1.05, video 1.0). Write what the voice
  should say in `lines` (numbers as words, acronyms spelled "A W S", "C plus plus", "four-oh-one-k") and the written
  form for captions in `show` wherever they differ (numbers as digits, $ amounts).
- **Never mention AI** as making, writing or choosing anything (jobs that involve AI are of course described as they are).
  YouTube: category SCIENCE_TECHNOLOGY, madeForKids false, isAiGeneratedContent false (Sello's standing preference).
- Text: title from `yt_title` (Shorts get " #shorts" from `describe.py`), under 100 characters, in the pattern
  "<Employer> Is Hiring: <Role> | <City, ST> | $<low>K–$<high>K"; description from `describe.py`; about 10 tags.

## Job file (`veritas/jobs/vraNNN.json`)
`id`, `format` (`short`|`video`), `voice`, `speed`, `source_id` (the jobs table id), `job` {employer, title, location,
workplace, pay (short form for the screen), pay_full, type, posted, ref, apply_url, apply_site — workplace, type, posted
and ref only when the posting itself states them, otherwise ""}, `details` {about,
duties[], needs[], nice[], benefits, notes[]}, `yt_title`, `hashtags[]`, `tags[]`, `scenes[]` {head, bullets[]
(short screen points), lines[] (spoken), show[] (captions, null where the line reads as written)}.
Shorts: 5 scenes (The role · What you'll do · What you need · Pay · How to apply), one or two lines each.
Videos: 6 scenes (Today's job · About the team/company · What you'll do · What you need · Pay & benefits · How to apply).
The first line of a video welcomes viewers to Veritas Recruitment Agency; every upload ends by pointing to the link in
the description and asking viewers to follow/subscribe for new US tech jobs every day.
See `jobs/vra001.json` (Short) and `jobs/vra005.json` (video).

## Build
`./veritas/make.sh veritas/jobs/vraNNN.json` → `out/vraNNN.mp4` (installs the voice model and fonts on first use; a
Short takes about 2.5 minutes, a video about 6). It stops with `SCRIPT TOO LONG` if a Short would reach 59 s — cut words.
Check frames at the start, middle and end with ffmpeg + Read: wordmark, title, employer, place, pay chip, card points
and captions legible, nothing overlapping or cut off, captions matching the voice's written form.

## Hosting and publishing
- Queue and fetched postings live on the `veritas-data` branch (`veritas/queue/YYYY-MM-DD.json` →
  `veritas/fetched/YYYY-MM-DD/*.json` via `.github/workflows/veritas-fetch.yml`); they are working files, not kept.
- Videos are hosted temporarily on the `media` branch (`vraNNN.mp4`, without touching other files) and removed once
  Metricool has copied them (`static.metricool.com`).
- `ledger.json` records every upload: id, source_id, employer, title, url, format, slot, Metricool uuid, media URL.
