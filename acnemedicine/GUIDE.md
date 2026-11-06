# Acne Medicine Johannesburg — direct YouTube uploads

Channel: **Acne Medicine Johannesburg** (@AcneMedicineJohannesburg), channel ID `UCtwhnWNVzoS6MR0SkvZIDHQ`, owned by
the Google account ecstacyspiritlifestyle@gmail.com. Reviews skin-care products and sends viewers to
https://acnemedicine.co.za/. Started 4 Nov 2026 (Sello).

**Not in Metricool.** Uploads go straight to YouTube from GitHub Actions through a Google Cloud OAuth app on that Google
account (YouTube Data API; default quota 100 `videos.insert` calls a day). Other channels and Metricool brands are untouched.

## Files
| File | What it does |
|---|---|
| `upload.py` | Uploads / reconciles / re-verifies one queue item. Refuses any token not for `CHANNEL_ID`. |
| `run_queue.sh` | Processes **every** queue item on `acne-data` (workflow entry point). |
| `persist.sh` | Commits + pushes one result to `acne-data` and confirms origin holds it; non-zero otherwise. |
| `auth_local.py` | One-time sign-in on Sello's computer; stores the three Actions secrets with `gh secret set`. Never remove the app from Google Account permissions to retry: the GlobalNewsFlix client is shared. |
| `test_upload.py` | Offline tests: fake Google API, local bare Git origin, auth listener. `python3 acnemedicine/test_upload.py` |
| `integration/` | Harmless unlisted test card (`make_test_asset.sh`) and its queue item, used once to prove live uploads. |

The workflow (`.github/workflows/acne-upload.yml`) runs on pushes of `acnemedicine/queue/*.json` to `acne-data`, hourly
(to re-check videos still processing) and on manual dispatch. **It executes the code on `acne-data`**, so every change
here must be pushed to both `main` and `acne-data`.

## Secrets (GitHub Actions, repo ramatladi/videosyndication)
`YT_ACNE_CLIENT_ID`, `YT_ACNE_CLIENT_SECRET`, `YT_ACNE_REFRESH_TOKEN`. Never in files, commits, messages or logs.
The repo is public and so are its Actions logs: errors record only Google's short status/reason, and every recorded
message is scrubbed of secret values and token-shaped strings. `.gitignore` blocks client-secret/token/.env files.

## Result states (`acnemedicine/results/<id>.json` on `acne-data`)
`UPLOADING` (persisted before any bytes go out) → `UPLOADED` (video ID persisted the moment YouTube returns it) →
`PENDING` (still processing; re-checked hourly) → `VERIFIED` (processed, right channel, requested privacy/publishAt).
`FAILED_PREUPLOAD` = nothing reached YouTube, retried next run. `FAILED` (video wrong/rejected/locked) and
`NEEDS_REVIEW` (an interrupted upload: each attempt saves a random marker tag, e.g. `amjref3f9c…`, before any bytes and puts it on the video; a rerun adopts only the single recent upload carrying that exact marker, never a title match. This prevents wrong adoption; it is not an exactly-once guarantee) are never retried automatically: a person
checks YouTube Studio, then deletes or edits the result file.

## Publishing one video
1. Put the MP4 alone on a new branch `acne-media/<id>` as `acnemedicine/<id>.mp4` (`git checkout --orphan`). The
   workflow reads it with `git fetch`, so there are no URLs or redirects to validate, and the path is derived from the
   validated id. Never put videos on `main`, `acne-data` or the shared `media` branch.
2. Commit `acnemedicine/queue/<id>.json` to `acne-data` and push:
   ```json
   {"id": "amj001", "title": "…", "description": "…", "tags": ["skincare"], "privacy": "public",
    "short": true, "contains_synthetic_media": false, "paid_promotion": true, "publish_at": null}
   ```
   `id`: 3-41 chars of a-z 0-9 - _, equal to the file name. `publish_at` (UTC, `2026-11-06T08:00:00Z`) schedules it
   (YouTube keeps it private until then). `contains_synthetic_media` is required and must describe that video's
   actual content (YouTube's altered/synthetic disclosure): true when it shows realistic AI-generated or altered
   people, places or events; false for e.g. real product photos with on-screen text.
3. When the result is VERIFIED **on origin**, the workflow deletes `acne-media/<id>`. Deleting the branch makes the
   video unreachable from the repo, but it is not an instant purge: GitHub may keep the objects until its own garbage
   collection, and because the repo is public anyone could have fetched them while the branch existed. Treat anything
   pushed there as public.

## Google Cloud app
- Used for uploads (chosen 4 Nov 2026): a **Desktop app** OAuth client "Acne Medicine channel uploader" inside the
  existing production project `globalnewsflix-video` (account ramatladi.mphela@gmail.com; consent app "GlobalNewsFlix",
  External, In production; YouTube Data API v3 enabled). The project's daily upload allowance is shared with GlobalNewsFlix.
- Never touch that project's Web client "GitHub video uploader" or its two secrets: GlobalNewsFlix depends on them. Its
  `globalnewsflix.com/yt/callback` must not be used for this channel: it overwrites the site's single stored token.
- Sign-in (on Sello's Mac): `python3 acnemedicine/auth_local.py <Desktop client JSON>` (no flags), then pick the
  Acne Medicine Johannesburg channel. To retry, just run it again; never remove the app from Google Account permissions.
- Unused: the separate project `acne-medicine-uploader` (no billing, Testing mode) and its Desktop client.

## Daily output (Sello, 6 Nov 2026)
- **4 Shorts + 2 full videos a day.** Short: 1080x1920, under 60 s. Full video: 1920x1080, about 3 min, with more product
  and face images. Slots (SAST): Shorts 10:00, 13:00, 16:00, 19:00; videos 14:00, 17:00.
- Built with `build_video.py` (photos with slow zoom, captions, female voice `af_heart`; female voices only) and a
  1280x720 thumbnail made from the product photo.
- **Images: free Pexels photos only** (Sello, 6 Nov 2026: "just use free photos"). No Dermalogica images. The pool is
  `photos/pool.json` (`day.py fetch` downloads it; photos are not kept in git). Credit photographers in the description
  only. Adults only, ordinary skincare scenes, no other brands' products, nothing suggestive; check every new photo on a
  contact sheet. Thumbnails: product name + a matching face photo (a free photo can't show the real product).
- **Publishing path:** Cloudflare worker `acne-manifest-sync` (code in `cloudflare/acne-manifest-sync/`, every 10 min)
  reads today's and tomorrow's SAST `manifest.json` from the media branch, checks each video's SHA-256, copies it to R2
  `acne-youtube-media` and queues it in D1 `acne-youtube-automation` (`jobs`, due = publish_at, 2 new per run). The
  existing uploader worker `acne-youtube-automation` then publishes due jobs (one per 5-minute run) and verifies them.
  To post something early, stage it under today's date with the same id: the later date's entry is then skipped.
  Tests: `node cloudflare/acne-manifest-sync/test.mjs <media-branch checkout>`.
- **Daily run:** scheduled task "Acne Medicine daily videos", 11:33 SAST, follows `DAILY_TASK.md` for the next day.
- **Words:** state what the product description says, directly (no "Dermalogica says…"). Add nothing beyond it: no
  invented results, testimonials or ratings.
- **Commission disclosure in the description only** ("We earn a commission if you buy through our link." near the top);
  `paid_promotion: true` on every post. Nothing about commission in the video.
- **Staging for the Cloudflare uploader** (Sello's connection does the YouTube upload; the GitHub uploader stays paused):
  media branch, `acnemedicine/<YYYY-MM-DD>/` with `<id>.mp4`, `<id>.jpg` (thumbnail), `<id>.json` (title, description,
  tags, publish_at UTC, short, paid_promotion, contains_synthetic_media, category_id) and `manifest.json`
  (ids, files, sha256, publish_at).

## Content rules
- Review real products honestly from the maker's own published information (ingredients, skin type, how to use).
  Never invent customer testimonials, ratings or before/after results, and never claim a cosmetic cures or treats acne
  as a medicine would.
- Every description links https://acnemedicine.co.za/. Sello earns a commission on sales through that link (confirmed
  4 Nov 2026), so every post: says "We earn a commission if you buy through our link." near the top of the description
  (not in the video, from 6 Nov 2026); sets `"paid_promotion": true` (YouTube's paid product placement flag,
  sent on upload and checked on read-back: a mismatch is FAILED for a person to fix in Studio). Do not describe this as a
  sponsorship or a Dermalogica partnership: no such relationship is established.
- `selfDeclaredMadeForKids: false`. Category 26 (Howto & Style).
