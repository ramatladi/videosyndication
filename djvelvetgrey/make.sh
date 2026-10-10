#!/usr/bin/env bash
# Usage: ./djvelvetgrey/make.sh djvelvetgrey/tracks/dvgNNN.json
# Builds out/dvgNNN.mp4 (2:59, 1080x1920) and out/dvgNNN.mp3 from a track file
# ("engine": "v2" uses the v2 brief/motif engine and also writes out/dvgNNN.qc.json):
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

get() { python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(d.get(sys.argv[2], d.get('brief',{}).get(sys.argv[2],'')))" "$TJ" "$1"; }
STYLE=$(get style); SEED=$(get seed); TITLE=$(get title); IMG=$(get image); CREDIT=$(get credit)
[ -f "$IMG" ] || { echo "image not found: $IMG"; exit 1; }
WAV="/tmp/$NAME.wav"
ENGINE=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('engine','v1'))" "$TJ")
if [ "$ENGINE" = "v2" ]; then
  python3 -c "import pyloudnorm" 2>/dev/null || pip install -q --break-system-packages pyloudnorm
  echo "== music v2 (brief + selected motif)"; python3 "$HERE/v2/make_track.py" "$TJ" "$WAV" "$ROOT/out/$NAME.meta.json"
else
  echo "== music ($STYLE, seed $SEED)"; python3 "$HERE/music.py" --style "$STYLE" --seed "$SEED" --out "$WAV"
fi
echo "== video"; python3 "$HERE/video.py" --image "$IMG" --audio "$WAV" --title "$TITLE" --style "$STYLE" \
  --credit "$CREDIT" --out "$ROOT/out/$NAME.mp4"
ffmpeg -v error -y -i "$WAV" -b:a 320k -metadata title="$TITLE" -metadata artist="DJ Velvet Grey" "$ROOT/out/$NAME.mp3"
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$ROOT/out/$NAME.mp4")
S=$(du -m "$ROOT/out/$NAME.mp4" | cut -f1)
if [ "$ENGINE" = "v2" ]; then
  python3 "$HERE/v2/qc.py" "$WAV" "$ROOT/out/$NAME.mp3" "$ROOT/out/$NAME.meta.json" > "$ROOT/out/$NAME.qc.json" && echo "== QC: out/$NAME.qc.json (automated technical checks, not a listening assessment)"
fi
echo "DONE out/$NAME.mp4 duration=${D}s size=${S}MB"
