#!/usr/bin/env bash
# Render one episode:  ./make_episode.sh episodes/epNNN.json
# Output (cast engine):
#   out/epNNN.mp4     9:16 vertical  (TikTok / Instagram)
#   out/epNNN_yt.mp4  16:9 landscape (long-form YouTube video)
#   out/epNNN_cover.png
# Length comes from the episode's "target_seconds" (175 = 2:55 minimum, 1795 = 29:55 maximum).
# File size: 27 MB for a 2:55 episode, scaling with length, never more than 90 MB per file (GitHub raw hosting limit is 100 MB).
set -e
EP_JSON="$1"; NAME=$(basename "$EP_JSON" .json)
WD="work/$NAME"; mkdir -p "$WD" out
ENGINE=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('engine','barn'))" "$EP_JSON")

encode () {  # encode MASTER OUT MAXKBPS
  local DUR VBR
  DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$1")
  VBR=$(python3 -c "d=float('$DUR'); mb=min(90, max(27, 27*d/175)); print(max(250, min($3, int((mb*8*1024*1024/d - 128000)/1000))))")
  ffmpeg -v error -y -i "$1" -c:v libx264 -preset slow -b:v ${VBR}k -maxrate $((VBR*13/10))k -bufsize $((VBR*2))k \
    -pix_fmt yuv420p -c:a aac -b:a 128k -movflags +faststart "$2"
  echo "$2: duration ${DUR}s, video ${VBR}k"
}

if [ "$ENGINE" = "cast" ]; then
  python3 engine/audio.py "$EP_JSON" "$WD"
  python3 engine/video.py "$EP_JSON" "$WD" video "$WD/master.mp4" | tail -1
  encode "$WD/master.mp4" "out/$NAME.mp4" 2000
  ffmpeg -v error -y -ss 5.3 -i "out/$NAME.mp4" -frames:v 1 "out/${NAME}_cover.png"
  echo "vertical done; rendering landscape"
  ASPECT=landscape python3 engine/video.py "$EP_JSON" "$WD" video "$WD/master_yt.mp4" | tail -1
  encode "$WD/master_yt.mp4" "out/${NAME}_yt.mp4" 2500
  ls -la "out/$NAME.mp4" "out/${NAME}_yt.mp4"
else
  python3 episode_audio.py "$EP_JSON" "$WD"
  python3 episode_video.py "$WD" video "$WD/master.mp4" | tail -1
  encode "$WD/master.mp4" "out/$NAME.mp4" 2000
  ffmpeg -v error -y -ss 5.3 -i "out/$NAME.mp4" -frames:v 1 "out/${NAME}_cover.png"
  ls -la "out/$NAME.mp4"
fi
