# Six skincare channels: production instructions

Channels: skincare.joburg, skincare.durban, dermatologist.joburg, dermatology.joburg, dermatology.durban,
dermatology.capetown. Builder: `skincare-launch/build_launch.py` with `specs.json`.

## Channel identity: Dermalogica product and skincare education (Sello, 7 Nov 2026)
Each channel is named by its locality and has one brand desk. Travel or packing may appear only as an
occasional context, never as a channel's identity.

| Channel | Locality | Brand desk |
|---|---|---|
| skincare.joburg | Rosebank | Moisturizers and textures |
| skincare.durban | Westville | Body care |
| dermatologist.joburg | Midrand | Building a skincare routine |
| dermatology.joburg | Bedfordview | Product labels and ingredients |
| dermatology.durban | uMhlanga | Hydration and layering |
| dermatology.capetown | Cape Town | Daily sun care |

## Language: American English (Sello, 7 Nov 2026; all seven skincare channels incl. Acne Medicine)
Scripts, narration, captions, titles, descriptions, thumbnail text and channel branding use American English
(moisturizer, moisturizing, color, license, center, favorite). Exact official product names stay as the store
lists them, even when they use another spelling. Narration uses American female voices (Kokoro `af_*`).

## Quality rules for every video (launch rebuild and daily production)
- One named Dermalogica product per video, verified against its store listing (name, size, claims, directions).
- The product is named in the title and spoken in the video.
- Thumbnail = the exact real product photo from the store listing (only once usage is authorised); Shorts embed
  a clear, selectable product cover frame.
- Every product, thumbnail photo, script, storyboard and visual sequence is unique: no repeated photographs, stock
  montages or shared templates between channels or between videos.
- QA before staging: listing and image URL checked, thumbnail and render match the product, cross-batch visual
  similarity check, SRT captions from the narration.

### Images: store photos + free photos (Sello, 7 Nov 2026)
- **Sello's confirmation (7 Nov 2026, 01:03 SAST):** Dermalogica images may be used. This covers the Dermalogica
  store product photos in these skincare videos and in their YouTube thumbnails. Each named product is matched to
  its exact store image (packshot SHA-256 in `store/sources.json`, template-matched in QA).
- Store images (dermalogica.co.za listing media, use authorised by Sello) carry the product: packshot on the cover,
  end card and thumbnail; texture, lifestyle and ingredient images in the body. They live in `store/` with
  `store/sources.json` (listing URL, image URL, bytes, SHA-256, date retrieved).
- Free Pexels photos set the locality (skyline, coast, mountain) or a scene; credited in the description.
- How to get store images: the workspace and device shell cannot reach the store, so open the listing in the
  built-in browser, read `/products/<handle>.js` for the media URLs, fetch each image same-origin, download it,
  stage it into the workspace and match its SHA-256 with the in-browser hash. Never use review or customer-quote
  images, or a size chart that duplicates another product's.

### Renderer and QA (`feature.py`, `qa_feature.py`)
- `features.json`: per-channel look (accent, card side, corner radius, chip style, title weight, transition,
  thumbnail layout, music, voice) and per-video scripts. Scene types: cover, photo, stat, bullets, steps, note, end.
- Every frame carries the locality/desk badge and the fine print ("Not dermatologists or doctors · Not medical
  advice" on the four dermatology/dermatologist channels). Progress bar in the channel accent; crossfades only
  between scenes, so a Short's first frame is the clean product cover.
- `python3 qa_feature.py features.json out/feature` must pass before staging: size/codec, Shorts ≤ 59.5 s,
  -14 LUFS (±1.5) and true peak ≤ -0.5 dB, one SRT cue per scene, American English, commission text in the
  description only, product in title and narration, packshot found in the thumbnail and the Short's cover frame,
  no near-identical thumbnails or frames across the batch, no product or free photo used twice.

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

Launch rebuild (7 Nov 2026): 12 product features (one regular video + one Short per channel, 12 different
products) rendered with `feature.py` from `features.json`, staged on the media branch under `skincare-launch/v2/`
with `manifest.json` and `qa.json`. Not published; Codex uploads and schedules. The first launch renders
(`skincare-launch/<date>/...` and the unrendered `shorts.json`) are superseded and must not be published.

Publishing path for v2 (7 Nov 2026): the 12 items are rows in D1 `skincare_launch_v2` (status READY; Shorts due
12:00 SAST and videos 15:00 SAST on 7 Nov 2026). The `acne-youtube-automation` launch page schedules each channel's
pair after Sello picks that channel at Google (code committed in `acnemedicine/cloudflare/worker.mjs`, needs a
deploy). Whoever uploads them (this page or Codex) must set the row to SCHEDULED with its video ID, so nothing is
uploaded twice.
