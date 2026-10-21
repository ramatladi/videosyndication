#!/usr/bin/env bash
# Usage: ./wisewords/make.sh wisewords/episodes/wwNNN.json
# Builds out/wwNNN.mp4 (1080x1920, TikTok/Instagram) and out/wwNNN_yt.mp4 (1920x1080, regular YouTube video), 2:55 each.
set -e
EP="$1"; [ -f "$EP" ] || { echo "usage: $0 wisewords/episodes/wwNNN.json"; exit 1; }
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
NAME="$(basename "$EP" .json)"
export WORK="/tmp/wisewords_$NAME"; rm -rf "$WORK"; mkdir -p "$WORK" "$ROOT/out"

# one-time setup: python libs, voice model (GitHub release), fonts (GitHub)
command -v ffmpeg >/dev/null || apt-get install -y -q ffmpeg >/dev/null
python3 -c "import kokoro_onnx, cairosvg, soundfile, PIL, cv2" 2>/dev/null || \
  pip install -q --break-system-packages kokoro-onnx cairosvg soundfile pillow opencv-python-headless
M=~/.cache/kokoro; mkdir -p $M
[ -s $M/kokoro.onnx ] || curl -sSL -o $M/kokoro.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
[ -s $M/voices.bin ] || curl -sSL -o $M/voices.bin https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
F="$HERE/fonts"; mkdir -p "$F"
[ -s "$F/SourceSerif4-Bold.ttf" ] || curl -sSL -o "$F/SourceSerif4-Bold.ttf" https://raw.githubusercontent.com/adobe-fonts/source-serif/release/TTF/SourceSerif4-Bold.ttf
for w in Bold SemiBold; do
  [ -s "$F/IBMPlexSans-$w.ttf" ] || curl -sSL -o "$F/IBMPlexSans-$w.ttf" https://raw.githubusercontent.com/IBM/plex/master/packages/plex-sans/fonts/complete/ttf/IBMPlexSans-$w.ttf
done
mkdir -p ~/.fonts && cp "$F"/*.ttf ~/.fonts/ && fc-cache -f >/dev/null 2>&1 || true

echo "== voice"; python3 "$HERE/tts.py" "$EP"
echo "== render (tall for TikTok/Instagram, wide for YouTube) in parallel"
python3 "$HERE/render.py" "$EP" "$ROOT/out/$NAME.mp4" tall > "$WORK/tall.log" 2>&1 & P1=$!
python3 "$HERE/render.py" "$EP" "$ROOT/out/${NAME}_yt.mp4" wide > "$WORK/wide.log" 2>&1 & P2=$!
wait $P1; R1=$?; wait $P2; R2=$?
cat "$WORK/tall.log" "$WORK/wide.log" | grep -v " frame " | sort -u
if [ $R1 -ne 0 ] || [ $R2 -ne 0 ]; then exit 1; fi
for f in "$ROOT/out/$NAME.mp4" "$ROOT/out/${NAME}_yt.mp4"; do
  D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")
  WH=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "$f")
  S=$(du -m "$f" | cut -f1)
  echo "DONE ${f#$ROOT/} ${WH} duration=${D}s size=${S}MB"
done
