# Video syndication

Daily animated skits (9:16, about 1–2 min) built on what is trending in the US that week, each with its own
original cast and setting, rendered entirely in code and published to YouTube and TikTok through Metricool.

- `engine/cast.py` — parametric characters (people, animals, mascots, talking objects) with lip-sync and gestures
- `engine/scenes.py` — 11 procedural backdrops
- `engine/audio.py` / `engine/video.py` — voices, music moods, SFX, camera cuts, captions, encoding
- `render.py`, `episode_audio.py`, `episode_video.py` — legacy barn renderer (episodes 001–002)
- `make_episode.sh episodes/epNNN.json` — full render → `out/epNNN.mp4`
- `setup.sh` — installs the voice engine and Python deps on a fresh Linux box
- `WRITING_GUIDE.md` — how to write a new episode; `EPISODES.md` — log of past episodes

The latest video is hosted on the `media` branch (replaced each day), giving Metricool a public URL:
`https://raw.githubusercontent.com/ramatladi/videosyndication/media/epNNN.mp4`

## DJ Velvet Grey (`djvelvetgrey/`)
Two original house tracks a week (Tue: melodic chill house, Fri: vocal deep house), 2:59 each, shown over a credited
free-license nature photo. See `djvelvetgrey/GUIDE.md`; build with `./djvelvetgrey/make.sh djvelvetgrey/tracks/dvgNNN.json`.
