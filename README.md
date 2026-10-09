# Video syndication — Marigold, Pip & Gourdon

Daily animated skits (9:16, ~1.5 min) featuring three original characters, rendered entirely in code
and published to YouTube and TikTok through Metricool.

- `render.py` — scene, characters (Marigold, Pip) and drawing helpers
- `episode_audio.py` — voices (Festival TTS), timeline, lip-sync, music and SFX
- `episode_video.py` — animation, camera cuts, captions, encoding
- `make_episode.sh episodes/epNNN.json` — full render → `out/epNNN.mp4`
- `setup.sh` — installs the voice engine and Python deps on a fresh Linux box
- `WRITING_GUIDE.md` — how to write a new episode; `EPISODES.md` — log of past episodes

Each finished video is attached to a GitHub release tagged `epNNN`, which gives Metricool a public URL:
`https://github.com/ramatladi/videosyndication/releases/download/epNNN/epNNN.mp4`
