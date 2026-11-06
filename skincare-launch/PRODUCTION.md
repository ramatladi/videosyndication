# Six skincare channels: production instructions

Channels: skincare.joburg, skincare.durban, dermatologist.joburg, dermatology.joburg, dermatology.durban,
dermatology.capetown. Builder: `skincare-launch/build_launch.py` with `specs.json`.

## Channel identity: Dermalogica product and skincare education (Sello, 7 Nov 2026)
Each channel is named by its locality and has one brand desk. Travel or packing may appear only as an
occasional context, never as a channel's identity.

| Channel | Locality | Brand desk |
|---|---|---|
| skincare.joburg | Rosebank | Moisturisers and textures |
| skincare.durban | Westville | Body care |
| dermatologist.joburg | Midrand | Building a skincare routine |
| dermatology.joburg | Bedfordview | Product labels and ingredients |
| dermatology.durban | uMhlanga | Hydration and layering |
| dermatology.capetown | Cape Town | Daily sun care |

## Quality rules for every video (launch rebuild and daily production)
- One named Dermalogica product per video, verified against its store listing (name, size, claims, directions).
- The product is named in the title and spoken in the video.
- Thumbnail = the exact real product photo from the store listing (only once usage is authorised); Shorts embed
  a clear, selectable product cover frame.
- Every product, thumbnail photo, script, storyboard and visual sequence is unique: no repeated photographs, stock
  montages or shared templates between channels or between videos.
- QA before staging: listing and image URL checked, thumbnail and render match the product, cross-batch visual
  similarity check, SRT captions from the narration.

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
