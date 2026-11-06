# Six skincare channels: production instructions

Channels: skincare.joburg, skincare.durban, dermatologist.joburg, dermatology.joburg, dermatology.durban,
dermatology.capetown. Builder: `skincare-launch/build_launch.py` with `specs.json`.

## Commission disclosure (Sello, 6 Nov 2026; supersedes the six-channel launch brief)
- Same format as Acne Medicine Johannesburg: the affiliate commission disclosure goes **in the YouTube description
  only** ("We earn a commission if you buy through our link…", near the top).
- **Never** in the narration, on-screen text, the bottom strip, banners, thumbnails or cards.
- `build_launch.py` refuses to build a scene whose narration, caption or label mentions a commission or affiliate.
- The uploader's paid-promotion setting stays on (YouTube's own "Includes paid promotion" label).
- If a specific applicable requirement conflicts with this, flag it to Sello before producing or publishing.

## Other standing rules for these channels
- Female voice; free Pexels photos credited in the description; original music only.
- Product facts from the official product pages, in their words; no clinical or credential claims. The four
  dermatology/dermatologist channels say on screen and in the description that they are not run by
  dermatologists or doctors (this is not a commission disclosure).
- Search-first titles, chapters, hashtags and tags as in `acnemedicine/discover.py`.
- No AI-content label on uploads.

## Status
The six launch videos are public (uploaded 6-7 Nov 2026) and are left in place. They were rendered under the
earlier brief, so they still carry the commission strip and spoken lines; any revised render must come from the
current `specs.json`, which no longer includes them.
