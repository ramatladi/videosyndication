#!/usr/bin/env bash
# Usage: ./djvelvetgrey/make.sh djvelvetgrey/tracks/dvgNNN.json [--check]   (--check: validate track file + brief only, no render; motif not required yet)
# Fail-closed build of one release (engine v3, all 12 styles):
#   music -> export (codec headroom: final MP3 + AAC <= -1.3 dBTP decoded) -> video (copies the exact AAC)
#   -> blocking QC on the FINAL wav/mp3/mp4 -> manifest (hashes + versions).
# Any failure exits non-zero and leaves NO manifest, so release_gate.py refuses to publish.
# Outputs in out/: NAME.mp4 NAME.mp3 NAME.m4a NAME.delivery.wav NAME.meta.json NAME.export.json NAME.qc.json NAME.manifest.json
set -euo pipefail
TJ="${1:-}"; [ -f "$TJ" ] || { echo "usage: $0 djvelvetgrey/tracks/dvgNNN.json" >&2; exit 1; }
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$(cd "$HERE/.." && pwd)"
NAME="$(basename "$TJ" .json)"; OUT="$ROOT/out"; mkdir -p "$OUT"
[ "${2:-}" = "--check" ] || rm -f "$OUT/$NAME".{manifest.json,qc.json,export.json,meta.json,mp4,mp3,m4a,delivery.wav}
command -v ffmpeg >/dev/null || apt-get install -y -q ffmpeg >/dev/null
python3 -c "import numpy, scipy, PIL" 2>/dev/null || pip install -q --break-system-packages numpy scipy pillow
python3 -c "import pyloudnorm" 2>/dev/null || pip install -q --break-system-packages pyloudnorm
F="$HERE/fonts"; mkdir -p "$F"
[ -s "$F/SourceSerif4-Bold.ttf" ] || curl -sSLf -o "$F/SourceSerif4-Bold.ttf" https://raw.githubusercontent.com/adobe-fonts/source-serif/release/TTF/SourceSerif4-Bold.ttf
[ -s "$F/IBMPlexSans-SemiBold.ttf" ] || curl -sSLf -o "$F/IBMPlexSans-SemiBold.ttf" https://raw.githubusercontent.com/IBM/plex/master/packages/plex-sans/fonts/complete/ttf/IBMPlexSans-SemiBold.ttf

# validate the track file (exits non-zero on anything missing)
python3 - "$TJ" "${2:-}" <<'PY'
import json, sys
t = json.load(open(sys.argv[1])); check_only = sys.argv[2] == '--check'
if t.get('engine') != 'v2': sys.exit('track file must use "engine": "v2" (legacy v1 is not allowed for releases)')
for k in ('title', 'image', 'credit', 'brief'):
    if not t.get(k): sys.exit(f'track file missing {k}')
if 'motif' not in t['brief'] and not check_only: sys.exit('brief has no selected motif (run previews.py + select_motif.py)')
PY
# field KEY [brief]: prints a non-empty field, or fails the build (never prints "None")
field() { python3 -c "
import json,sys
t=json.load(open(sys.argv[1])); src=t['brief'] if len(sys.argv)>3 else t; v=src.get(sys.argv[2])
if v in (None,''): sys.exit('track file missing '+sys.argv[2])
print(v)" "$TJ" "$@"; }
TITLE="$(field title)"; IMG="$(field image)"; CREDIT="$(field credit)"; STYLE="$(field style brief)"
[ -f "$IMG" ] || { echo "image not found: $IMG" >&2; exit 1; }
python3 -c "
import json,sys; sys.path.insert(0,'$HERE/v2'); import styles as S, make_track as MT
b=json.load(open(sys.argv[1]))['brief']; st=S.ALIASES.get(b['style'],b['style'])
e=MT.validate(b,S.STYLES[st]) if st in S.STYLES else ['unknown style '+st]
sys.exit('brief does not fit the style profile: '+'; '.join(e) if e else 0)" "$TJ"
if [ "${2:-}" = "--check" ]; then echo "CHECK OK $NAME style=$STYLE"; exit 0; fi

echo "== music ($STYLE)"
python3 "$HERE/v2/make_track.py" "$TJ" "/tmp/$NAME.master.wav" "$OUT/$NAME.meta.json"
echo "== export (codec headroom)"
python3 "$HERE/v2/export.py" "/tmp/$NAME.master.wav" "$OUT" "$NAME" --title "$TITLE"
echo "== video"
python3 "$HERE/video.py" --image "$IMG" --audio "$OUT/$NAME.delivery.wav" --aac "$OUT/$NAME.m4a" \
  --title "$TITLE" --style "$STYLE" --credit "$CREDIT" --out "$OUT/$NAME.mp4"
echo "== QC (blocking, final files; automated technical checks, not a listening assessment)"
if ! python3 "$HERE/v2/qc.py" --wav "$OUT/$NAME.delivery.wav" --mp3 "$OUT/$NAME.mp3" --mp4 "$OUT/$NAME.mp4" \
     --meta "$OUT/$NAME.meta.json" --out "$OUT/$NAME.qc.json" > /dev/null; then
  echo "QC FAILED:" >&2
  python3 -c "import json,sys;[print(' -', f['category'], ':', f['check']) for f in json.load(open(sys.argv[1]))['failures']]" "$OUT/$NAME.qc.json" >&2 || true
  exit 2
fi
python3 "$HERE/v2/manifest.py" "$TJ" "$OUT" "$NAME"
S=$(du -m "$OUT/$NAME.mp4" | cut -f1)
echo "DONE out/$NAME.mp4 size=${S}MB (QC pass; manifest written)"
