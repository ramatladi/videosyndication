# Beautiful Ladies Only — daily publishing task

Channel: YouTube **Beautiful Ladies Only** (@BeautifulLadiesOnly, channel ID `UCog0c7ed2gre4xO1nzibhoA`).
In Metricool it sits under the brand **"everythingyouwant_tv"** (blogId `7321327`, timezone Africa/Johannesburg).
Post to **YouTube only**. Never add that brand's Facebook, Instagram or TikTok accounts.

Each run builds and schedules the **next day's** batch: **4 Shorts and 2 videos**.

## Continuity rules (Sello, 10 Nov 2026)

Every run works through these steps in order, before starting new work:

1. **Resume first.** Look for work from the last 36 hours that was made but never posted: a day plan (beautifulladies/days_<date>.json) or ledger entry for today or tomorrow whose posts are not all in Metricool. If today's posts are missing because yesterday's batch failed, fill today's remaining slots before building tomorrow's batch. Check Metricool (getScheduledPosts on the brand, from that day to tomorrow) for a post with its title. If there is none, it never aired: render it again if its video file is gone, host it, schedule it in this run's slot (or at now + 30 minutes if this run's slot has passed), and update the ledger. Only then move on to new work, and never make new work for a slot this resumed item filled.
2. **Missed slots.** If a slot from the last 6 hours is empty because an earlier run failed or never ran, fill it with resumed or new work at now + 30 minutes, at most two make-up posts per run and 40 minutes apart. Leave slots older than 6 hours empty: never flood the channel to catch up.
3. **Record as you go.** Commit the day plan file right after writing it, and add the ledger or log entry right after createScheduledPost returns, so a run that dies part-way leaves enough behind for step 1 of the next run.
4. **Leftover hosted files.** Remove files on the media branch belonging to this series that are older than 24 hours, once Metricool has its copy (the post exists) or the item is logged as posted. Leave anything newer: it may belong to a run in progress.
5. **Refused or held steps.** If hosting, scheduling or any other step is refused or held for approval, do not retry it and do not look for another route around it. Leave the item committed but unposted, so step 1 of the next run picks it up, and send ONE PushNotification naming the step and the exact message.

## Content rules (Sello's choices, 4 Nov 2026)
- Photos come from free sites only: Unsplash (free licence, not Unsplash+). Bikini and swimwear photos come first; any photo of a beautiful lady is fine.
- Present it as swimwear, beach fashion, travel and lifestyle. Titles, captions and thumbnails must not be suggestive.
- Only adults who are clearly adults. If age is in any doubt, skip the photo. Skip any photo whose alt text says "girl" or "teen".
- Use full-figure or lifestyle shots only. No body-part close-ups, no rear-focused shots, no bedroom or lingerie shots, no wet-shirt or similar shots, and no photos marked `flagged`. Look at every photo on a contact sheet before using it.
- Credit every photo twice: on screen (build.py does this) and in the description, with the photographer's name and Unsplash link.
- Music: existing Mirage Tropical Records tracks from Creative Claw (cdn.creativeclaw.co), kept in `tracks.json`. Every run adds newly released Mirage tracks and rotates the whole pool, least recently used first (see step 4). **Never generate new music for this channel**, because those credits are budgeted for Mirage.
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
4. Music: run `python3 tracks.py sync` (adds any new release in `../mirage/ledger.json` that has a Creative Claw `audio_url` and is at least 3:05 long), then `python3 tracks.py pick YYYY-MM-DD`. Use its `track_url` and `start` for each slot. Mention any newly added track in the report to Sello.
5. Write `days_YYYY-MM-DD.json` in the same shape as `days_2026-11-04.json`. Give each photo a short, non-suggestive mood caption, such as "Golden hour glow" or "Island time". Don't invent locations.
6. Run `python3 build.py days_YYYY-MM-DD.json`. Shorts take about 1.5 min each and videos about 4 min. Run long builds in the background and poll. Check one frame from each output.
7. Host the files: `git clone --depth 1 -b media https://github.com/ramatladi/videosyndication /tmp/mediahost`, copy them in as `blo-YYYYMMDD-short1..4.mp4` and `blo-YYYYMMDD-video1..2.mp4`, then commit and push. If the push is rejected, run `pull --rebase` and retry. Confirm that each `https://raw.githubusercontent.com/ramatladi/videosyndication/media/<file>` returns 200.
8. Schedule each file with Metricool `createScheduledPost`. The description is a one-line hook, then "Photos from Unsplash (Unsplash License), credited to:" with a bullet per photo (name – link), then "Music: “<title>” by <artist> (<style>) from Mirage Tropical Records." (or "Music: <style> from Mirage Tropical Records." when the track has no title), then 3–4 hashtags. If a call times out, check `getScheduledPosts` before retrying, and retry once at most.
9. Add the day to `ledger.posts` with its files and Metricool IDs. Commit `ledger.json`, `tracks.json` and the day file to `main` (fetch and rebase first), then push.
