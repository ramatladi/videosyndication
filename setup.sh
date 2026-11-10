#!/usr/bin/env bash
# One-time environment setup for a fresh Linux workspace (Ubuntu/Debian).
set -e
export DEBIAN_FRONTEND=noninteractive
command -v ffmpeg >/dev/null || apt-get install -y -q ffmpeg >/dev/null
python3 -c "import cairo, numpy" 2>/dev/null || pip install -q --break-system-packages pycairo numpy
# (timeout + retry: a stalled pip download once hung a run for over 10 minutes)
python3 -c "import kokoro_onnx, soundfile" 2>/dev/null || timeout 240 pip install -q --progress-bar off --break-system-packages kokoro-onnx soundfile || timeout 240 pip install -q --progress-bar off --break-system-packages kokoro-onnx soundfile
# natural human voices (Kokoro model, from GitHub releases)
M=~/.cache/kokoro; mkdir -p $M
[ -s $M/kokoro.onnx ] || curl -sSL -o $M/kokoro.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
[ -s $M/voices.bin ] || curl -sSL -o $M/voices.bin https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
echo "setup ok"
