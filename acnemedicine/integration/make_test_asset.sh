#!/usr/bin/env bash
# Build the harmless integration-test video: a 10 s vertical title card on a plain background with a quiet tone.
# No people, products, claims or synthetic imagery. Output path is the first argument (not committed anywhere).
set -euo pipefail
out="${1:-/tmp/amj-test001.mp4}"
font=$(fc-match -f '%{file}' 'DejaVu Sans:bold' 2>/dev/null || true)
ff=${font:+fontfile=$font:}
ffmpeg -y -loglevel error \
  -f lavfi -i "color=c=0xF4EFEA:s=1080x1920:r=30:d=10" \
  -f lavfi -i "sine=frequency=440:sample_rate=48000:duration=10" \
  -vf "drawtext=${ff}text='Acne Medicine Johannesburg':fontcolor=0x2B2B2B:fontsize=64:x=(w-text_w)/2:y=h/2-90,\
drawtext=${ff}text='Upload test':fontcolor=0x6B6B6B:fontsize=48:x=(w-text_w)/2:y=h/2+10" \
  -af "volume=0.05" -c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p -c:a aac -b:a 96k -shortest \
  -movflags +faststart "$out"
echo "$out"
