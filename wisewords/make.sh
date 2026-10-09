#!/usr/bin/env bash
# Usage: ./wisewords/make.sh wisewords/episodes/wwNNN.json
# Builds out/wwNNN.mp4: Marco Reyes reads and explains famous quotes, 2:55, 1080x1920.
set -e
EP="$1"; [ -f "$EP" ] || { echo "usage: $0 wisewords/episodes/wwNNN.json"; exit 1; }
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
NAME="$(basename "$EP" .json)"
export WORK="/tmp/wisewords_$NAME"; rm -rf "$WORK"; mkdir -p "$WORK" "$ROOT/out"

# one-time setup: python libs, voice model (GitHub release), fonts (GitHub)
command -v ffmpeg >/dev/null || apt-get install -y -q ffmpeg >/dev/null
python3 -c "import kokoro_onnx, cairosvg, soundfile, PIL" 2>/dev/null || \
  pip install -q --break-system-packages kokoro-onnx cairosvg soundfile pillow
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
echo "== render"; python3 "$HERE/render.py" "$EP" "$ROOT/out/$NAME.mp4"
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$ROOT/out/$NAME.mp4")
S=$(du -m "$ROOT/out/$NAME.mp4" | cut -f1)
echo "DONE out/$NAME.mp4 duration=${D}s size=${S}MB"
