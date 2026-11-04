# Beautiful Ladies Only — daily publishing task

Channel: YouTube **Beautiful Ladies Only** (@BeautifulLadiesOnly, channel ID `UCog0c7ed2gre4xO1nzibhoA`).
In Metricool it sits under the brand **"everythingyouwant_tv"** (blogId `7321327`, timezone Africa/Johannesburg).
Post to **YouTube only**. Never add that brand's Facebook, Instagram or TikTok accounts.

Each run builds and schedules the **next day's** batch: **4 Shorts and 2 videos**.

## Content rules (Sello's choices, 4 Nov 2026)
- Photos come from free sites only: Unsplash (free licence, not Unsplash+). Bikini and swimwear photos come first; any photo of a beautiful lady is fine.
- Present it as swimwear, beach fashion, travel and lifestyle. Titles, captions and thumbnails must not be suggestive.
- Only adults who are clearly adults. If age is in any doubt, skip the photo. Skip any photo whose alt text says "girl" or "teen".
- Use full-figure or lifestyle shots only. No body-part close-ups, no rear-focused shots, no bedroom or lingerie shots, no wet-shirt or similar shots, and no photos marked `flagged`. Look at every photo on a contact sheet before using it.
- Credit every photo twice: on screen (build.py does this) and in the description, with the photographer's name and Unsplash link.
- Music: existing Mirage Tropical Records tracks from Creative Claw (`search_assets` type audio, from cdn.creativeclaw.co). Rotate the tracks. **Never generate new music for this channel**, because those credits are budgeted for Mirage.
- YouTube: `madeForKids: false`, `isAiGeneratedContent: false`, category `TRAVEL_EVENTS`, privacy public. Shorts use `type: "short"` with "#shorts" in the title.

## Formats
- Short: 1080x1920, 5 photos × 6 s = 30 s; music starts 40–60 s into the track.
- Video: 1920x1080, 12 photos × 15 s = 3:00; music starts at 0. A video may reuse photos from that day's Shorts.

## Daily slots (SAST, best YouTube hours from Metricool)
Shorts at 10:00, 13:00, 16:00 and 19:00. Videos at 14:00 and 17:00.

## Steps
1. `cd beautifulladies`. Read `ledger.json`. Never reuse a slug from `photos` used in the last 60 days, and never use a slug listed in `rejected`.
2. Find fresh photos. WebFetch Unsplash search pages, `https://unsplash.com/s/photos/<query>?license=free`, and ask for the image URL, the photo page URL (its slug is the last part), the photographer and the alt text. Rotate queries such as bikini-beach, swimwear-fashion, woman-beach, summer-dress-beach, woman-pool, woman-travel, resort-fashion, tropical-woman and beach-hat. You need at least 20 new usable photos plus 4 spare. The shell can reach images.unsplash.com but not unsplash.com.
3. Download candidates with `https://images.unsplash.com/<photo-id>?w=1440&q=85&fm=jpg`, build a labelled contact sheet with Pillow, look at it, and apply the content rules. Add every rejected slug to `rejected`, and add each accepted slug to `photos` as `{image, photographer, date}`.
4. Write `days_YYYY-MM-DD.json` in the same shape as `days_2026-11-04.json`. Give each photo a short, non-suggestive mood caption, such as "Golden hour glow" or "Island time". Don't invent locations.
5. Run `python3 build.py days_YYYY-MM-DD.json`. Shorts take about 1.5 min each and videos about 4 min. Run long builds in the background and poll. Check one frame from each output.
6. Host the files: `git clone --depth 1 -b media https://github.com/ramatladi/videosyndication /tmp/mediahost`, copy them in as `blo-YYYYMMDD-short1..4.mp4` and `blo-YYYYMMDD-video1..2.mp4`, then commit and push. If the push is rejected, run `pull --rebase` and retry. Confirm that each `https://raw.githubusercontent.com/ramatladi/videosyndication/media/<file>` returns 200.
7. Schedule each file with Metricool `createScheduledPost`. The description is a one-line hook, then "Photos from Unsplash (Unsplash License), credited to:" with a bullet per photo (name – link), then "Music: <style> from Mirage Tropical Records.", then 3–4 hashtags. If a call times out, check `getScheduledPosts` before retrying, and retry once at most.
8. Add the day to `ledger.posts` with its files and Metricool IDs. Commit `ledger.json` and the day file to `main` (fetch and rebase first), then push.
