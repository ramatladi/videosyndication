DJ Velvet Grey - vocal kit (Real Instruments Set, take 2) - 22 Oct 2026

WHAT THIS IS
Scripts and data used to make take 2 of the 12-song Real Instruments Set and to put CC0 vocals on every song.
The finished songs are the audio files of this same artifact (audio/01-...mp3 to audio/12-...mp3).

WHERE THE VOCALS COME FROM
- freesound.org and cdn.freesound.org are blocked from the workspace; cdn.pixabay.com is reachable.
- Pixabay hosts copies of Freesound's CC0 sounds under the user "freesound_community"; each Pixabay sound page says
  "Artist <name> (Freesound)". Find a sound on pixabay.com in Chrome, take the cdn.pixabay.com/download/audio/... mp3
  from its page HTML, download it in the workspace with curl, then confirm CC0 on the original Freesound page in Chrome.
- Only sounds whose Freesound page says CC0 are used. sources.json lists the 47 verified sounds with download URLs.
- Pixabay copies are mostly 24 kHz mp3, so the top end is a little dull; vocalize.py adds a little "air".
- Excluded on purpose: Vocaloid / synth voices (synthetic), a protest crowd chant ("get down in the name of education"),
  anything whose CC0 licence could not be found on Freesound.

PIPELINE (paths as used in the session: engine at /home/claude/vs/djvelvetgrey/v2)
1. plan_take2.py      - draws new briefs for the 12 songs (same titles/tempos/tonics as take 1) so every song gets a
                        different lead instrument; writes briefs.json.
2. render_take2.py N  - renders song N (0-11) in real-instruments mode from briefs.json (~70 s per song).
3. cache_sources.py   - pyin pitch-class histogram, tuning offset and a 16th-grid tempo fit for every vocal source.
4. vocalize.py N      - re-renders song N with the lead 3.5 dB lower (answer 1 dB lower), captures the PRE-MASTER mix by
                        wrapping engine.master, then:
                        * shifts each vocal into the song's key (pitch-class fit) and tempo with Rubber Band
                          (rubberband -3 -F, formants preserved),
                        * "reseq" hooks: slices a source at onsets, trims each slice to its attack, snaps every syllable
                          to the nearest scale note (pyin + small Rubber Band shift) and lays the syllables on a 16th
                          pattern; "loop" hooks: stretches a loop with a known BPM and downbeat offset,
                        * arranges hook / layer / bed / phrase / ad-libs on the song's own section map
                          (intro swell, filtered tease in the hook, hook in groove and drops, stutter in builds,
                          pads and sung phrases in breaks, fade-out in the outro),
                        * HPF, compression, reverb, dotted-8th delay, ducks the band up to 2 dB under the lead vocal,
                        * masters with the engine's own master() at the style's loudness (-2.8 dBTP).
                        The per-song choices live in vocal_plans.json. vocal_osc.py is the hand-built first version
                        for Open Sky Chorus.
5. check_vocals.py NN - loudness/peak, vocal onset distance from the 16th grid and share of sung notes in key per drop.
6. build_page.py + page_template.html - the listening page.

LIMITS LEARNED
- Run renders ONE AT A TIME: two vocalize.py runs in parallel hit the 8 GB memory limit and get killed.
- Grid timing in the drops ended at 6-20 ms median; share of sung notes in key 85-100% (Midnight Driftwood is mostly
  shouts and a glitch voice, so its in-key figure is not meaningful).
- Nobody has listened to any of it yet; all checks are technical.

LEADS FOR VOCALS WITH REAL LYRICS (on Pixabay's mirror; check each one's licence page and what the words say first)
- Plaedo: "What is a Vocal" (4:30 hip-hop acapella; showed up in Freesound's CC0-filtered search),
  "Occupy the acapella", "Insomnia rough draft vocals", "The cosmic dance scratch vocals"
- .Andre_Onate: "this is the moment w fx" (shouted drop; showed up in Freesound's CC0-filtered search)
- SA7RIAmusic: "Cool kids never sleep"
- LoopMaiden: "Female singing - name of love" (not found on Freesound by title; licence unconfirmed - do not use until found)
- Verified CC0 with words already in sources.json: Paranoye "Many Lovers" (#365849), ellenmentor "hey hey hey yeah",
  "ooh-aha", short shouts ("yeah", "oh yeah", "woo hoo", "hey", "go for it", "hell yeah").
Never use lyrics or melodies from commercial songs; new songs can follow the style of the hits in the library only.
