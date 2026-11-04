# Acne Medicine Johannesburg — direct YouTube uploads

Channel: **Acne Medicine Johannesburg** (@AcneMedicineJohannesburg), channel ID `UCtwhnWNVzoS6MR0SkvZIDHQ`, owned by
the Google account ecstacyspiritlifestyle@gmail.com. Reviews skin-care products and sends viewers to
https://acnemedicine.co.za/. Started 4 Nov 2026 (Sello).

**Not in Metricool.** Uploads go straight to YouTube through a Google Cloud OAuth app on that Google account and the
YouTube Data API (default quota: 100 `videos.insert` calls a day). Other channels and Metricool brands are untouched.

## Files
- `upload.py` — uploads one queue item. Runs only in GitHub Actions (`.github/workflows/acne-upload.yml`).
  Refuses to upload unless the token's channel is `CHANNEL_ID`, reads the video back after upload and checks its channel,
  processing status and privacy. Writes `results/<id>.json` (no secrets).
- `auth_local.py` — one-time sign-in, run on Sello's computer. Stores the three Actions secrets with `gh secret set`.
- `test_upload.py` — offline tests against a fake Google API (`python3 acnemedicine/test_upload.py`).

## Secrets (GitHub Actions, repo ramatladi/videosyndication)
`YT_ACNE_CLIENT_ID`, `YT_ACNE_CLIENT_SECRET`, `YT_ACNE_REFRESH_TOKEN`. Never put them in files, commits, messages or logs.
The repo is public: Actions logs are public too, so the uploader never prints request headers or tokens.

## Publishing one video
1. Put the MP4 on the `media` branch at `acnemedicine/<id>.mp4` (temporary hosting; never commit videos to `main`
   or `acne-data`). Check that `https://raw.githubusercontent.com/ramatladi/videosyndication/media/acnemedicine/<id>.mp4` returns 200.
2. Commit `acnemedicine/queue/<id>.json` to the `acne-data` branch and push. That triggers the workflow:
   ```json
   {"id": "amj001", "title": "…", "description": "…", "tags": ["skincare", "acne"],
    "media_url": "https://raw.githubusercontent.com/ramatladi/videosyndication/media/acnemedicine/amj001.mp4",
    "media_path": "acnemedicine/amj001.mp4", "short": true, "privacy": "public",
    "publish_at": null}
   ```
   `publish_at` (RFC 3339, UTC) schedules it: YouTube keeps it private until then.
3. The workflow commits `acnemedicine/results/<id>.json` back to `acne-data` and, once the upload is verified, deletes the
   MP4 from the `media` branch. A result with a `video_id` is never uploaded again.

## Content rules
- Review real products honestly from the maker's own published information (ingredients, skin type, how to use).
  Never invent customer testimonials, ratings or before/after results, and never claim a cosmetic cures or treats acne
  as a medicine would.
- Every description links https://acnemedicine.co.za/. If Sello earns from sales through that link, the description must
  say so, and YouTube's paid-promotion box must be ticked for the video (the uploader does not set it yet; tick it in Studio).
- No AI-content labels (`containsSyntheticMedia: false`), per Sello's standing choice. `selfDeclaredMadeForKids: false`.
  Category 26 (Howto & Style).
