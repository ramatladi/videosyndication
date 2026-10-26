# Mirage Tropical Records (YouTube)

Instrumental house/disco on the **Mirage Tropical Records** YouTube channel through Metricool (brand "Mirage Tropical
Records", blogId **7593699**, YouTube only, timezone Africa/Johannesburg). Started 22 Oct 2026 (Sello).

## Since 26 Oct 2026: every song is written by hand, one act per sub-genre
Sello heard the procedural engine's tracks as "AI-ish" (random melody, fake-sounding, flat) and paused uploads on 25 Oct.
On 26 Oct he approved hand-written songs ("it is better") and asked: **write all the songs by hand, use a different artist
name per sub-genre (not all DJs), and upload as per the schedule.**

- **Acts:** `artists.json` maps each of the 15 styles to its act (Saltglass Society = deep, Aurelle Vane = melodic,
  DJ Saltwater = house, Sahel Bloom = afro, Coco Meridian = tropical, Prism Kites = future bass, Glossy Boulevard = nu-disco,
  Northline Arc = progressive, DJ Concrete Palm = tech, Seraphine Tide = trance, Honey Static = vocal house (instrumental),
  Ellis Honeywell = soulful, Disco Lantern Club = disco, Les Nuits Pastel = French house, Neon Tamarind = indie dance).
  The act's name is on the video's brand pill, in the title and in the description. Releases before mtr012 are DJ Velvet Purple.
- **Writing a song = writing a spec** `mirage/songs/mtrNNN.json` by hand (format in `loopkit/song.py`'s docstring): 8 bars
  of chord voicings + bass roots, a keys comping rhythm, a bass line (intervals from each root), an 8-bar hook, pad layers
  (+ optional arpeggio) and three drum patterns (main / alt for drop 2 / tops without kick) in 16th-note steps.
  `song_release.py next` gives the release id, the style from the 24-slot rotation and its act.
- **Craft rules (what made the approved songs work):**
  - A real progression with smooth voice leading (hold common tones; move other voices by step), voicings an octave+ above
    the bass, 4-5 notes. Minor keys for deep/melodic/afro/progressive most of the time; major for tropical/disco/nu-disco/
    house/future bass often.
  - The hook is a **singable phrase**: a 1-2 bar motif, repeated, answered, and resolved on bar 8 (call bars 1-4, answer 5-8;
    reuse rhythms). Strong-beat and long notes are chord tones or gentle tensions (9th/11th/13th); never a minor 2nd above a
    chord tone. 4-8 notes a bar, a range of about an octave, the peak note once or twice.
  - Bass locks to the kick and outlines the chord (root/octave/fifth), with a walk-up or walk-down into bar 1 at bar 8.
  - Drums: four-on-the-floor kick (half-time feel for future bass), clap/snare on 2 and 4, offbeat open hats, 16th hats with
    accents, and genre percussion (congas/bongos/shaker for afro/organic/melodic; tambourine/ride for disco/progressive).
  - Instrument palettes (all real recordings): Steinway (`piano_steinway`), `gm_ep`/`gm_ep2` (Rhodes), `gm_organ`, guitars
    (`gm_guitar_clean`, `gm_guitar_muted`, `gm_guitar_nylon`), basses (`upright_bass`, `gm_bass_finger`, `gm_bass_pick`,
    `gm_bass_slap`, `gm_bass_fretless`), `string_section`, `violins`/`violas`/`celli`, `violin_pizz`, `brass_section`, `trumpet`,
    `trumpet_stac`, `horn`, `trombone`, `flute`, `clarinet`, `tenor_sax`, `harp`, `vibraphone`, `marimba`, `kalimba`,
    `glockenspiel`, `xylophone`, `gm_steel_drums`; drums `909`/`808` kits + studio hand percussion. Typical:
    deep = piano/Rhodes + upright or finger bass; melodic = flute/harp/strings/piano; afro = marimba/kalimba + Rhodes +
    heavy percussion; progressive = pizzicato+harp plucks, piano, rolling offbeat bass; tropical = steel drums/marimba/
    nylon guitar, 100-112 BPM; nu-disco/disco = slap/pick bass, muted guitar, strings, brass stabs; soulful = Rhodes/organ +
    sax; trance = strings/pizz arps, 132-140 BPM; future bass = 140-160 BPM, half-time drums, big brass/string chords.
  - Key and tempo: vary from the last releases (`next` lists them). A song may follow the public tempo/key/genre of a song in
    Sello's library (`taste/refs.json`), recorded in the spec's `reference`; melodies, chords and arrangement stay original.
- **Checks (fail-closed):** `song_release.py check` lints the writing (key, clashes, ranges, repetition, bass downbeats,
  drum parts, the act matches the style) and refuses a hook more than 55% the same as any earlier spec, a copy of an earlier
  progression + hook rhythm, or a used title. `build` then renders, exports and runs the blocking QC (`qc.py`); nothing
  is scheduled unless QC passes. Machine ears (`ears.py`) are recorded but informational. Nothing is described as listened to.
- **Sound:** `loopkit/song.py` plays the parts on the CC0 studio pack (VSCO 2 CE + VCSL, repo `samples` branch), FluidR3 GM
  recordings (gm_*) and TR-909/808 recordings (`loopkit/drumkit.py` fetches them from npm: @fluid-music/tr-909, tr-808),
  then `loopkit/arrange.py` arranges 2:59 (intro, build, drop, break, build, drop 2, outro), ducks bass/pad/keys to the kick,
  keeps the low end mono and masters (-10/-11 LUFS).
  The Looperman drum loops Sello supplied were used only for the in-session samples (their licence forbids redistribution, so
  they are not in the repo).

## Looperman loops first, hand-written as the fallback (Sello, 26 Oct 2026)
"Use Looperman where completeness and accuracy are met, use other sources as a fallback." Sello keeps a Looperman loop
library in his Google Drive (folder "looperman", one WAV per loop + CSVs). In a session with the Google Drive connector,
download the WAVs one by one (`download_file_content`; files over ~5.5 MB fail), decode them into
/home/claude/loops/<cat>/, then run `python3 mirage/loopkit/verify.py /home/claude/loops`:
- **completeness:** bar-exact, decodable, not silent; **accuracy:** the key comes from the audio — the uploader's label is
  kept only when the audio agrees (about half of the labels were wrong); unverifiable loops go to `_unverified/`.
- Pick loops whose bar-by-bar chords agree (no semitone clashes between their strongest notes) and name them in the
  spec's `loops` (roles keys, bass, melody, melody2, pad, vocals, drums_main, drums_alt, drums_tops; a Looperman id is
  enough). Roles without a fitting verified loop are written by hand; `song.py check` verifies those hand-written chords
  against what the keys/melody loop actually plays in each bar. A melody loop is not reused within 30 songs and a
  keys+melody pair never.
- Vocals are allowed (Sello, 26 Oct). Wordless vocal loops (ahs, oohs) keep the "Instrumental" title; a vocal with lyrics
  would need the title changed.
- Loops are never committed (Looperman forbids redistribution); the ledger records which loops each release used.
- Scheduled runs have no Google Drive access, so they write the whole song by hand (the fallback). Looperman-led songs are
  made in sessions with Sello and scheduled ahead (mtr018, mtr019 were the first).

## Schedule
- **Four uploads a day (Sello, 26 Oct 2026): 2 videos + 2 Shorts (SAST):** 23:55 **video**, 07:55 Short, 11:55 **video**,
  19:55 Short. (23-26 Oct it was six a day, adding 03:55 and 15:55 Shorts.) Every upload is a different song.
- Two scheduled tasks share the day: 19:37 → 23:55 video + 07:55 Short (next day); 09:37 → 11:55 video + 19:55 Short.
- The old-engine posts mtr009 (26 Oct 23:55) and mtr010 (27 Oct 03:55) were replaced before publishing by mtr014/mtr015.

## Photo (Sello, 23 Oct), in this order of preference
1. **Bikini:** one or more attractive adult women in bikinis/swimsuits, any setting (beach, pool, boat, island, coastline…).
2. **Fashion models** (only when no unused qualifying bikini photo can be found): adult fashion models, any outfit, any setting.
3. **Nature** (only when neither can be found): tropical/nature scenery, no person in focus.
Tasteful throughout: clearly adults, face visible, natural or glamour poses, no nudity or see-through clothing, no close-up
body crops, no rear/thong-focused shots, no logos, text, watermarks or alcohol branding. Free Unsplash License only (never
Unsplash+ / premium_photo), never reused (`ledger.json`). Landscape for the video (pre-crop to 16:9 if the centre crop would
cut the head), portrait for the Short. **The photo credit is in the description only — never on the video.**
For a video, the face must sit between the brand pill (top ~20% of the frame, and the slow zoom grows 12%) and the
equalizer/title (below ~62%): when the subject's head is near the top of a landscape photo with plain sky above, run
`python3 mirage/reframe.py photo.jpg photo_169.jpg --extend-top 130..200` and preview before building.
Unsplash photo pages are read with WebFetch from search-result URLs; images download from images.unsplash.com.

## Text
Title `<Title> - <Act> | <Genre> Instrumental` (Shorts add ` #shorts`); description and tags from `describe.py --artist`:
`🎧 <Act> - <Title> (<Genre> Instrumental)`, a one-line mood/instrument hook, subscribe + like call, track/artist/label/genre/
key/BPM lines, photo credit + page URL, a "<genre> for …" keyword line and hashtags. Nothing mentions AI. YouTube: category
MUSIC, madeForKids false, isAiGeneratedContent false (Sello's standing preference).
Media is hosted temporarily on the repo's `media` branch (`mtrNNN.mp4`) and removed once Metricool has copied it.

## Files
- `song_release.py` — `next` / `check --spec` / `build --spec --format video|short ...` / `record --spec ...`.
- `songs/` — every hand-written song spec (the uniqueness catalogue).
- `loopkit/` — `song.py` (lint + performance), `drumkit.py` (909/808 + hand percussion), `arrange.py` (arrangement, mix,
  master), `parts.py` (shared note renderer); `song_lido.py` / `song_sunbird.py` are the first hand-written drafts.
- `artists.json` — the 15 acts. `video.py` / `video_short.py` (`--artist`), `describe.py` (`--artist`).
- `ledger.json` — every release (format, slot, title, act, style, key, tempo, photo, Metricool uuid, ears).
- Legacy (before 26 Oct): `make_release.py` + djvelvetgrey engine v4 studio mode, `catalog.json`, `taste/` research.
