#!/usr/bin/env bash
# Usage: ./veritas/make.sh veritas/jobs/vraNNN.json  ->  out/vraNNN.mp4 (Short 1080x1920 under 60 s, or video 1920x1080)
#        and out/vraNNN_thumb.jpg (thumbnail with the employer's official logo)
set -e
JOB="$1"; [ -f "$JOB" ] || { echo "usage: $0 veritas/jobs/vraNNN.json"; exit 1; }
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$(cd "$HERE/.." && pwd)"; NAME="$(basename "$JOB" .json)"
export WORK="/tmp/veritas_$NAME"; rm -rf "$WORK"; mkdir -p "$WORK" "$ROOT/out"
# one-time setup: libraries, the voice model (GitHub release) and open-licence fonts (GitHub)
command -v ffmpeg >/dev/null || apt-get install -y -q ffmpeg >/dev/null
python3 -c "import kokoro_onnx, soundfile, PIL, numpy, pyloudnorm, cairosvg" 2>/dev/null || pip install -q --break-system-packages kokoro-onnx soundfile pillow numpy pyloudnorm cairosvg
M=~/.cache/kokoro; mkdir -p $M
[ -s $M/kokoro.onnx ] || curl -sSL -o $M/kokoro.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
[ -s $M/voices.bin ] || curl -sSL -o $M/voices.bin https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
F="$HERE/fonts"; mkdir -p "$F"
[ -s "$F/SourceSerif4-Bold.ttf" ] || curl -sSL -o "$F/SourceSerif4-Bold.ttf" https://raw.githubusercontent.com/adobe-fonts/source-serif/release/TTF/SourceSerif4-Bold.ttf
for w in Bold SemiBold Medium Regular; do
  [ -s "$F/IBMPlexSans-$w.ttf" ] || curl -sSL -o "$F/IBMPlexSans-$w.ttf" https://raw.githubusercontent.com/IBM/plex/master/packages/plex-sans/fonts/complete/ttf/IBMPlexSans-$w.ttf
done
python3 "$HERE/describe.py" "$JOB" > "$WORK/describe.json"
echo "== voice"; python3 "$HERE/tts.py" "$JOB"
echo "== render"; python3 "$HERE/render.py" "$JOB" "$ROOT/out/$NAME.mp4" | grep -v " frame "
echo "== thumbnail"; python3 "$HERE/thumb.py" "$JOB" "$ROOT/out/${NAME}_thumb.jpg"
f="$ROOT/out/$NAME.mp4"
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")
WH=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "$f")
echo "DONE out/$NAME.mp4 ${WH} duration=${D}s size=$(du -m "$f" | cut -f1)MB"
