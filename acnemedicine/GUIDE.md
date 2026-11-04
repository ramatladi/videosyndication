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
| `auth_local.py` | One-time sign-in on Sello's computer; stores the three Actions secrets with `gh secret set`. |
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
    "short": true, "contains_synthetic_media": false, "publish_at": null}
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
Status (4 Nov 2026): Google Cloud terms accepted (marketing emails off); project created; YouTube Data API v3 enabled; no billing account linked (checked on the Billing page). Auth Platform (consent screen) not yet created: its last step needs agreement to the Google API Services User Data Policy. No OAuth client exists yet.
- Project: `acne-medicine-uploader` (project number 23501395330), No organization, on ecstacyspiritlifestyle@gmail.com, no billing.
- Enabled: YouTube Data API v3 only.
- OAuth consent screen (Google Auth Platform → Branding/Audience): app name "Acne Medicine Uploader"; user support
  email and developer contact ecstacyspiritlifestyle@gmail.com; no logo (a logo triggers brand verification);
  audience **External**; publishing status **In production** (Testing-mode refresh tokens expire after 7 days).
  Not submitted for verification: Google shows an "unverified app" warning on sign-in and caps it at 100 users — fine
  for a single owner.
- Data access (scopes): `https://www.googleapis.com/auth/youtube.upload`, `https://www.googleapis.com/auth/youtube.readonly`.
- Client: type **Desktop app**, name "videosyndication-uploader". Download its JSON once at creation and keep it only on
  Sello's computer for `auth_local.py`.

## Content rules
- Review real products honestly from the maker's own published information (ingredients, skin type, how to use).
  Never invent customer testimonials, ratings or before/after results, and never claim a cosmetic cures or treats acne
  as a medicine would.
- Every description links https://acnemedicine.co.za/. If Sello earns from sales through that link, the description must
  say so, and YouTube's paid-promotion box must be ticked for the video (the uploader does not set it yet; tick it in Studio).
- `selfDeclaredMadeForKids: false`. Category 26 (Howto & Style).
