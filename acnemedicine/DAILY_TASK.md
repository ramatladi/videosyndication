# Acne Medicine Johannesburg — daily task

Scheduled run: build and stage the **next day's** 4 Shorts + 2 full videos for the YouTube channel Acne Medicine
Johannesburg (`UCtwhnWNVzoS6MR0SkvZIDHQ`). Sello's Cloudflare connection does the YouTube upload from the media branch;
**do not** upload, queue `acne-data`, or touch Metricool. Work unattended; never stop to ask. Report at the end.

Repo: `ramatladi/videosyndication` (clone `--depth 20`). Rules: `acnemedicine/GUIDE.md` ("Daily output" and
"Content rules"). Commits: user.name "ramatladi", user.email "rsmphela@gmail.com", message ending with
"Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" and "Claude-Session: <this session URL>".

## Steps
1. `bash setup.sh` (voice model) and `python3 acnemedicine/day.py fetch` (photo pool). Tomorrow = DATE (Africa/Johannesburg). If `acnemedicine/ledger.json` already has DATE,
   or the media branch already has `acnemedicine/DATE/manifest.json`, stop and report "already staged".
2. **Products (6, all different).** Choose from Dermalogica South Africa (dermalogica.co.za). Prefer acne and
   breakout products, then oily/congested skin, then other ranges. Do not reuse a product used in the last 7 days
   (ledger). Get each product's facts with `WebSearch` limited to `dermalogica.co.za` (the workspace can't open the
   site directly; never route around that). Use only what the product page says: description, benefits, key
   ingredients, how to use, FAQ cautions. State it directly — never "Dermalogica says". No customer reviews,
   ratings, before/after or percentage claims, nothing invented. Each video ends: "The link is in the description."
3. **Photos.** Free Pexels photos only (Sello, 6 Nov 2026). Reuse `acnemedicine/photos/pool.json`, and add new ones:
   `WebSearch` with `allowed_domains: ["pexels.com"]` for skincare scenes that match the product (washing, cream,
   serum, mask, mirror, body care); take the photo ID (end of the `/photo/...-<id>/` URL) and the photographer from
   the result. Download `https://images.pexels.com/photos/<id>/pexels-photo-<id>.jpeg?auto=compress&cs=tinysrgb&w=1600`
   to `acnemedicine/photos/pexels/<id>.jpg`, then build a labelled contact sheet and **look at it**. Keep only
   clearly adult people in ordinary skincare scenes; reject anything showing another brand's products, nudity,
   suggestive or shower/bath body shots, children or teens, or text/watermarks. Add accepted photos to `pool.json`
   (`{"id","by","tag"}`, plus `"cx"` 0-1 when the subject of a landscape photo is off-centre, so Shorts crop to the face). After building, look at a frame from every scene that uses a landscape photo in a Short. Store images: Sello authorised Dermalogica store images on 7 Nov 2026, but this scheduled run cannot reach the store and `day.py` does not yet place a packshot, so keep these runs on Pexels photos until that support lands (verified store images for 12 products are in `skincare-launch/store/`).
4. **Plan** `acnemedicine/days/DATE/plan.json` (same shape as `days/2026-11-07/plan.json`): slots Shorts 10:00, 13:00,
   16:00, 19:00 and videos 14:00, 17:00. Shorts: 5-6 scenes, under 60 s (about 100-120 spoken words). Videos:
   12-16 scenes, more photos, about 2-3 min (300-420 words). Vary photos between items; thumbnail photo = a face photo
   that fits the product. Titles under 100 characters; Shorts end with "#shorts".
   **American English** (Sello, 7 Nov 2026) for scripts, captions, titles, descriptions, tags and thumbnail text:
   moisturizer, moisturizing, color, license. Keep exact official product names as the store lists them.
   **Make every post searchable** (Sello, 6 Nov 2026): the title starts with what people type: "How to Use Dermalogica
   <Product> (<key ingredient>)", "Dermalogica <Product>: <what it does, from the product page>" or, for videos,
   "Dermalogica <Product> Review: <key ingredient>, How to Use It"; put the key fact (e.g. "0.5% Salicylic Acid") in
   the title when the product page states it. Add `"lead"`: one sentence starting "Dermalogica <Product>: …" saying
   what it is and who it's for, in the product page's words; it becomes the first line of the description. `tags`:
   3-5 specific phrases (the concern, the product type, the key ingredient); `day.py` adds the product-name,
   how-to-use, review and South Africa tags, the three hashtags, chapters for full videos (from the real scene timings)
   and an English caption file from the narration. Scene captions in videos become chapter names, so keep them short
   and specific ("Salicylic acid 0.5%", not "What's inside").
5. Quality (Sello, 7 Nov 2026, all skincare channels): six different products, each named in its title and spoken; no photo used twice in the day; no commission or affiliate words on screen or in narration (description only); American English. Then `python3 acnemedicine/day.py build acnemedicine/days/DATE/plan.json` (run in the background and poll; ~2-4 min per
   video). Check one frame from each video and each thumbnail by looking at them.
6. `python3 acnemedicine/day.py stage acnemedicine/days/DATE/plan.json`. Confirm each
   `https://raw.githubusercontent.com/ramatladi/videosyndication/media/acnemedicine/DATE/<file>` returns 200 and
   its SHA-256 matches the manifest.
7. Add DATE to `acnemedicine/ledger.json` (`{"date", "items": [{id, product, format, slot}]}`), commit `ledger.json`,
   `photos/pool.json` and the plan to `main` (fetch + rebase first), push. Do not commit photos or videos to `main`.
8. Report to Sello in one short message: the six titles with times and any problem.
