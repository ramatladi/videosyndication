#!/usr/bin/env bash
# Render one episode:  ./make_episode.sh episodes/ep002.json
# Output: out/ep002.mp4 (upload-sized, < 30 MB) and out/ep002_cover.png
set -e
EP_JSON="$1"; NAME=$(basename "$EP_JSON" .json)
WD="work/$NAME"; mkdir -p "$WD" out
python3 episode_audio.py "$EP_JSON" "$WD"
python3 episode_video.py "$WD" video "$WD/master.mp4" | tail -1
ffmpeg -v error -y -i "$WD/master.mp4" -c:v libx264 -preset slow -b:v 2000k -maxrate 2600k -bufsize 5200k \
  -pix_fmt yuv420p -c:a aac -b:a 160k -movflags +faststart "out/$NAME.mp4"
ffmpeg -v error -y -ss 5.3 -i "out/$NAME.mp4" -frames:v 1 "out/${NAME}_cover.png"
ls -la "out/$NAME.mp4"
