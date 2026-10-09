#!/usr/bin/env bash
# Render one episode:  ./make_episode.sh episodes/epNNN.json
# Output: out/epNNN.mp4 (sized to stay under 30 MB) and out/epNNN_cover.png
set -e
EP_JSON="$1"; NAME=$(basename "$EP_JSON" .json)
WD="work/$NAME"; mkdir -p "$WD" out
ENGINE=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('engine','barn'))" "$EP_JSON")
if [ "$ENGINE" = "cast" ]; then
  python3 engine/audio.py "$EP_JSON" "$WD"
  python3 engine/video.py "$EP_JSON" "$WD" video "$WD/master.mp4" | tail -1
else
  python3 episode_audio.py "$EP_JSON" "$WD"
  python3 episode_video.py "$WD" video "$WD/master.mp4" | tail -1
fi
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$WD/master.mp4")
# aim for ~27 MB total: video bitrate = budget - 128k audio, capped at 2000k
VBR=$(python3 -c "d=float('$DUR'); print(max(600, min(2000, int((27*8*1024*1024/d - 128000)/1000))))")
ffmpeg -v error -y -i "$WD/master.mp4" -c:v libx264 -preset slow -b:v ${VBR}k -maxrate $((VBR*13/10))k -bufsize $((VBR*2))k \
  -pix_fmt yuv420p -c:a aac -b:a 128k -movflags +faststart "out/$NAME.mp4"
ffmpeg -v error -y -ss 5.3 -i "out/$NAME.mp4" -frames:v 1 "out/${NAME}_cover.png"
echo "duration ${DUR}s, video ${VBR}k"
ls -la "out/$NAME.mp4"
