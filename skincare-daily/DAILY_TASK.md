# Six skincare channels: daily production task

Scheduled run: produce and stage **tomorrow's** batch (4 Shorts + 2 regular videos per channel, 36 items) for the six
skincare channels below, then hand it to Codex through the media-branch manifest and receipt ledger.
**Codex publishes**: this run never uploads to YouTube, never schedules posts, never touches Metricool or YouTube Studio,
and never writes a `youtube_id`. Work unattended; never stop to ask. Sello set these rules on 11 Nov 2026.

| Domain | Handle | Desk | SAST slots |
|---|---|---|---|
| skincare.joburg | @SkincareJoburgRosebank | Rosebank: moisturizers & textures | Shorts 08:00 12:00 16:00 20:00; videos 10:00 18:00 |
| skincare.durban | @SkincareDurbanWestville | Westville: body care | same |
| dermatologist.joburg | @DermatologistJoburgMidrand | Midrand: building a routine | same |
| dermatology.joburg | @DermatologyJoburgBedfordview | Bedfordview: labels & ingredients | same |
| dermatology.durban | @DermatologyDurbanUmhlanga | uMhlanga: hydration & layering | same |
| dermatology.capetown | @DermatologyCapeTown | Cape Town: daily sun care | same |

Standing rules (unchanged): American English (exact official product names keep the store's spelling); American female
Kokoro voices; exact Dermalogica store packshot per SKU (Sello authorised store images and thumbnails, 7 Nov 2026);
facts only from the item's own dermalogica.co.za listing; no before/after, clinical-percentage, review, award or
customer-quote images or claims; commission disclosure in the description only; no AI-content labels
(`altered_or_synthetic_content: false`); unique scripts, titles and visuals, never relabel an earlier video.
Renderer and QA: `skincare-launch/feature.py`, `skincare-launch/qa_feature.py` (see `skincare-launch/PRODUCTION.md`).
Pipeline: `skincare-daily/sk.py` (all commands below).

## Product selection: standing fallback (a thin catalog never blocks a slot)
Rolling **7-day no-repeat window per channel** (a product may return to a channel after 7 days; one product appears
at most once per day across all six channels). For every slot `sk.py plan` takes the first tier that has a product,
applies it automatically and logs the tier and reason in `plan.json` and the manifest (`selection`):

- **(a)** an unused SKU in the channel's desk (product and SKU not used anywhere in the last 7 days);
- **(b)** a different size or kit (new SKU) of a desk product not used on this channel in the last 7 days, with a new
  script and new visuals;
- **(c)** a face product covered from the channel's angle: Westville only when the listing's directions cover the
  neck/chest; Cape Town only when the listing itself talks about UV, daytime, free radicals or environmental stress;
- **(d)** the least recently used desk or angle product outside the channel's 7-day window (new script and visuals).

Kits: components and sizes come only from the kit's own listing ("What's inside" / "Kit includes"); `sk.py write`
checks that every component and size appears in the facts and the narration (`kit_check`), and the planner skips kits
whose listing doesn't name its contents. Never take kit contents from another product's page.

## Steps (time limit 3 hours; retry a failed step once, then carry on and list it in the report)
0. Setup: add_repo ramatladi/videosyndication (push); `git clone --depth 20 https://github.com/ramatladi/videosyndication /home/claude/videosyndication`;
   `bash setup.sh` (Kokoro voices, fonts); media checkout without videos:
   `git clone --filter=blob:none --no-checkout -b media https://github.com/ramatladi/videosyndication /tmp/launch-media && cd /tmp/launch-media && git sparse-checkout set --no-cone '/skincare-daily/*/*.json' '/skincare-daily/*/renders/*/*.jpg' '/skincare-launch/v2.1/*' && git checkout media`.
   DATE = tomorrow (Africa/Johannesburg). If `skincare-daily/DATE/manifest.json` already lists 36 ready items, skip to step 8.
1. **Heal first** (before any new work): `python3 skincare-daily/sk.py heal /tmp/launch-media DATE`. For every earlier
   day it refreshes the receipt ledger from the manifest (rows Codex reads: `staged_awaiting_youtube_receipt`, checksums
   verified; rows with a `youtube_id` are never touched). If a day still lists `missing_render` or a slot with no row,
   produce those items first with steps 2-7 for that day (same tiers, logged), then do DATE.
2. **Catalog**: open https://dermalogica.co.za/collections/all in the built-in browser (load the built-in-browser skill;
   the workspace and the device shell cannot reach the store). Run the catalog snapshot JS from `skincare-daily/README.md`
   (same-origin `/products.json` plus each product page's text) — it downloads one JSON into ~/Downloads. Find it with
   device_bash (`ls -at ~/mnt/Downloads | head`; it is a hidden `.Q6L2SF6YDW.com.anthropic.claudefordesktop.*` file),
   stage it with device_stage_files and save it as `/home/claude/skwork/catalog-DATE.json`.
3. **Plan**: `SK_WORK=/home/claude/skwork python3 skincare-daily/sk.py plan DATE /home/claude/skwork/catalog-DATE.json /tmp/launch-media`.
4. **Images**: `python3 skincare-daily/sk.py fetchjs DATE /tmp/launch-media`, commit and push the queue
   (`skincare-daily/DATE/fetch/`) to media, then run each printed JS in the store tab (one call per chunk; if the call
   times out it keeps running: poll ~/mnt/Downloads until the bundle appears). Stage the bundles and
   `python3 skincare-daily/sk.py ingest DATE <bundle paths>` (SHA-256 checked per image).
5. **Look at the images**: build a labelled contact sheet per 6 products from `skwork/DATE/img` and view it. Add any
   before/after, clinical-claim, percentage, review/quote, award or person-of-note image to `skwork/DATE/skip.json`
   (file names). Packshots (index 00) must show the exact product and size.
6. **Write + render**: `SK_MEDIA=/tmp/launch-media python3 skincare-daily/sk.py write DATE` (prints kit/text/overlap
   problems; a slot with a problem is replanned with the next product). If a replanned product has no images yet
   ("fewer than 2 store images"), run `fetchjs` again (it queues only the missing SKUs), ingest, and `write` again.
   Then `python3 skincare-daily/sk.py render DATE` as a background job of this session (about 1.5 min per item, so
   ~55 min for 36) and keep polling until it finishes: a background process dies when the session's reply ends, so
   never end the turn while it runs. `render` also picks each thumbnail's most distinct layout (14-day + batch dHash). It renders, retries failures once one by one, runs QA and the 14-day
   thumbnail check. Look at one frame of every item on a contact sheet. Fix and re-render anything that fails.
7. **Stage**: `python3 skincare-daily/sk.py stage DATE /tmp/launch-media` — copies renders/images, writes the manifest
   (hashes, selection tier, QA), verifies every hash and writes the receipt ledger rows Codex expects, so no slot is left
   as `missing_render`. Commit and push the media branch (pull --rebase and retry if rejected); confirm a few
   raw.githubusercontent.com URLs return 200.
8. **Clean up the Mac**: delete every hidden bundle this run downloaded:
   `cd ~/mnt/Downloads && for f in .Q6L2SF6YDW.com.anthropic.claudefordesktop.*; do : > "$f"; rm -f -- "$f"; done`.
   If rm is refused, call device_request_delete_permission for the Downloads folder once; if that is declined or
   unanswered, the files are already emptied (0 bytes) — list them in the report. Close the browser tab you opened.
   Delete /home/claude/skwork/DATE/img after staging.
9. **Commit code changes** (main): only sk.py / docs fixes, never media. Commit as user.name "ramatladi",
   user.email "rsmphela@gmail.com", messages ending with the session's attribution lines.
10. **Report** (final reply): per channel the 6 titles with SAST slots and selection tier; anything not staged and why;
   earlier days healed; ledger counts (staged, missing_render, youtube_id recorded). Send ONE PushNotification only if
   fewer than 36 items were staged or a heal failed.
