#!/usr/bin/env bash
# Usage: ./djvelvetgrey/make.sh djvelvetgrey/tracks/dvgNNN.json
# Builds out/dvgNNN.mp4 (2:59, 1080x1920) and out/dvgNNN.mp3 from a track file:
#   {"title", "style": "chill"|"deep", "seed", "image": "<local photo path>",
#    "credit": "Photo: <Name> / <Site>", ...}
set -e
TJ="$1"; [ -f "$TJ" ] || { echo "usage: $0 djvelvetgrey/tracks/dvgNNN.json"; exit 1; }
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$(cd "$HERE/.." && pwd)"
NAME="$(basename "$TJ" .json)"; mkdir -p "$ROOT/out"
command -v ffmpeg >/dev/null || apt-get install -y -q ffmpeg >/dev/null
python3 -c "import numpy, scipy, PIL" 2>/dev/null || pip install -q --break-system-packages numpy scipy pillow
F="$HERE/fonts"; mkdir -p "$F"
[ -s "$F/SourceSerif4-Bold.ttf" ] || curl -sSL -o "$F/SourceSerif4-Bold.ttf" https://raw.githubusercontent.com/adobe-fonts/source-serif/release/TTF/SourceSerif4-Bold.ttf
[ -s "$F/IBMPlexSans-SemiBold.ttf" ] || curl -sSL -o "$F/IBMPlexSans-SemiBold.ttf" https://raw.githubusercontent.com/IBM/plex/master/packages/plex-sans/fonts/complete/ttf/IBMPlexSans-SemiBold.ttf

get() { python3 -c "import json,sys;print(json.load(open(sys.argv[1]))[sys.argv[2]])" "$TJ" "$1"; }
STYLE=$(get style); SEED=$(get seed); TITLE=$(get title); IMG=$(get image); CREDIT=$(get credit)
[ -f "$IMG" ] || { echo "image not found: $IMG"; exit 1; }
WAV="/tmp/$NAME.wav"
echo "== music ($STYLE, seed $SEED)"; python3 "$HERE/music.py" --style "$STYLE" --seed "$SEED" --out "$WAV"
echo "== video"; python3 "$HERE/video.py" --image "$IMG" --audio "$WAV" --title "$TITLE" --style "$STYLE" \
  --credit "$CREDIT" --out "$ROOT/out/$NAME.mp4"
ffmpeg -v error -y -i "$WAV" -b:a 320k -metadata title="$TITLE" -metadata artist="DJ Velvet Grey" "$ROOT/out/$NAME.mp3"
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$ROOT/out/$NAME.mp4")
S=$(du -m "$ROOT/out/$NAME.mp4" | cut -f1)
echo "DONE out/$NAME.mp4 duration=${D}s size=${S}MB"
