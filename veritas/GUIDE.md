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
`id`, `format` (`short`|`video`), `voice`, `speed`, `source_id` (the jobs table id), `job` {employer, logo (slug in
`logos/logos.json`, or "" when there is none), title, short_title (the role in a few words, for the thumbnail), location,
workplace, pay (short form for the screen), pay_full, type, posted, ref, apply_url, apply_site — workplace, type, posted
and ref only when the posting itself states them, otherwise ""}, `details` {about,
duties[], needs[], nice[], benefits, notes[]}, `yt_title`, `hashtags[]`, `tags[]`, `scenes[]` {head, bullets[]
(short screen points), lines[] (spoken), show[] (captions, null where the line reads as written)}.
Shorts: 5 scenes (The role · What you'll do · What you need · Pay · How to apply), one or two lines each.
Videos: 6 scenes (Today's job · About the team/company · What you'll do · What you need · Pay & benefits · How to apply).
The first line of a video welcomes viewers to Veritas Recruitment Agency, and its first scene also says "You'll find the
direct application link in the description." Every upload's last scene has the voice direct viewers to the link:
Shorts "To apply, find the direct application link in the description." then "Follow Veritas for new tech jobs every
day."; videos "To apply, find the direct application link in the description below. It takes you straight to
<Employer>'s careers site." then the subscribe line. The last card's first point is "Application link in the description".
See `jobs/vra001.json` (Short) and `jobs/vra005.json` (video).

## Employer logos and thumbnails
- Every upload shows the employer's **official logo**, taken from the employer's own website or careers site (never a
  logo directory, image search or a redrawn copy). Logos live in `veritas/logos/` with `logos.json` (employer, tile colour,
  source URL). Reuse a logo already there.
- New employer: add `"logos": [{"slug", "employer", "pages": [its homepage, its careers site], "files": [known logo
  URLs, e.g. a Workday careers site's `https://<tenant>.wdN.myworkdayjobs.com/<site>/assets/logo`]}]` to the day's queue
  file; `fetch.py` saves every candidate the pages name (schema.org logo, og:logo/og:image, `<img>`/inline SVG marked
  as the logo, SVG/touch icons) to `veritas/fetched/<day>/logos/<slug>/`. Look at the candidates, pick the employer's
  full logo (wordmark, or mark plus name) at the best resolution, and run
  `python3 veritas/logo.py <slug> "<Employer>" <file> <source URL> [--bg "#RRGGBB"]` (`--bg` when the site publishes
  the logo in white: use the employer's own dark/brand colour). Never recolour, redraw or crop the logo. A site that
  blocks the fetch is not worked around: try the employer's other official pages (careers site, Workday/Lever/Greenhouse
  board), else leave `job.logo` "" and the employer's name is set in type.
- `python3 veritas/thumb.py veritas/jobs/vraNNN.json out/vraNNN_thumb.jpg` makes the thumbnail (video 1280x720, Short
  1080x1920 cover): logo, role (`short_title`), city, pay, "Application link in the description". `make.sh` runs it.

## Build
`./veritas/make.sh veritas/jobs/vraNNN.json` → `out/vraNNN.mp4` (installs the voice model and fonts on first use; a
Short takes about 2.5 minutes, a video about 6). It stops with `SCRIPT TOO LONG` if a Short would reach 59 s — cut words.
Check frames at the start, middle and end with ffmpeg + Read: wordmark, title, employer, place, pay chip, card points
and captions legible, nothing overlapping or cut off, captions matching the voice's written form.

## Hosting and publishing
- Queue and fetched postings live on the `veritas-data` branch (`veritas/queue/YYYY-MM-DD.json` →
  `veritas/fetched/YYYY-MM-DD/*.json` via `.github/workflows/veritas-fetch.yml`); they are working files, not kept.
- Videos and thumbnails are hosted temporarily on the `media` branch (`vraNNN.mp4`, `vraNNN_thumb.jpg`, without touching
  other files) and removed once Metricool has copied them (`static.metricool.com`). The thumbnail goes to Metricool as
  `videoThumbnailUrl` (YouTube shows custom thumbnails only once the channel is verified).
- `ledger.json` records every upload: id, source_id, employer, title, url, format, slot, Metricool uuid, media URL.
