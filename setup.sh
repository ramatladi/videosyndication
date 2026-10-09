#!/usr/bin/env bash
# One-time environment setup for a fresh Linux workspace (Ubuntu/Debian).
set -e
export DEBIAN_FRONTEND=noninteractive
if ! command -v text2wave >/dev/null; then
  (apt-get install -y -q festival festvox-us-slt-hts festvox-kallpc16k mbrola-us2 festvox-us2 mbrola-us1 mbrola-us3 mbrola-en1 festvox-us1 festvox-us3 festvox-en1 >/dev/null 2>&1) || \
  (apt-get update -q >/dev/null 2>&1 && apt-get install -y -q festival festvox-us-slt-hts festvox-kallpc16k mbrola-us2 festvox-us2 mbrola-us1 mbrola-us3 mbrola-en1 festvox-us1 festvox-us3 festvox-en1 >/dev/null)
fi
command -v ffmpeg >/dev/null || apt-get install -y -q ffmpeg >/dev/null
python3 -c "import cairo, numpy" 2>/dev/null || pip install -q --break-system-packages pycairo numpy
echo "setup ok"
