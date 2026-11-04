#!/usr/bin/env bash
# Process every queue item on acne-data (run from a checkout of acne-data). Safe to run repeatedly:
#   - VERIFIED items: only clean up their temporary media branch (after re-confirming the result on origin)
#   - FAILED / NEEDS_REVIEW items: left alone for a person
#   - everything else: upload.py uploads, reconciles or re-verifies
# Each video waits on its own temporary branch acne-media/<id> (one file: acnemedicine/<id>.mp4).
set -uo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cd "$here/.."
rc=0; work="$(mktemp -d)"
status_of() { python3 -c 'import json,sys,os;p=sys.argv[1];print(json.load(open(p)).get("status","") if os.path.exists(p) else "")' "$1"; }

cleanup() {   # $1 = id. Delete acne-media/<id> only when origin's copy of the result says VERIFIED.
  local id="$1"
  git fetch -q origin acne-data || { echo "$id: cannot confirm result on origin; keeping media"; return 1; }
  local st
  st=$(git show "FETCH_HEAD:acnemedicine/results/$id.json" 2>/dev/null | python3 -c 'import json,sys;print(json.load(sys.stdin).get("status",""))' 2>/dev/null || true)
  if [ "$st" != "VERIFIED" ]; then echo "$id: origin result is '$st'; keeping media"; return 1; fi
  if git ls-remote --exit-code -q origin "refs/heads/acne-media/$id" >/dev/null 2>&1; then
    git push -q origin --delete "acne-media/$id" && echo "$id: temporary media branch deleted"
  fi
}

shopt -s nullglob
for q in acnemedicine/queue/*.json; do
  id=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("id",""))' "$q" 2>/dev/null || true)
  if ! [[ "$id" =~ ^[a-z0-9][a-z0-9_-]{2,40}$ ]] || [ "$(basename "$q")" != "$id.json" ]; then
    echo "$q: invalid id or file name; skipped"; rc=1; continue
  fi
  res="acnemedicine/results/$id.json"; st=$(status_of "$res")
  case "$st" in
    VERIFIED) cleanup "$id" || rc=1; continue ;;
    FAILED|NEEDS_REVIEW) echo "$id: $st - needs a person"; rc=1; continue ;;
  esac
  video="$work/$id.mp4"; : > "$video"
  has_vid=$(python3 -c 'import json,sys,os;p=sys.argv[1];print(1 if os.path.exists(p) and json.load(open(p)).get("video_id") else 0)' "$res")
  if [ "$has_vid" = 0 ] && [ "$st" != "UPLOADING" ]; then
    if ! git fetch -q --depth 1 origin "refs/heads/acne-media/$id" 2>/dev/null \
       || ! git show "FETCH_HEAD:acnemedicine/$id.mp4" > "$video" 2>/dev/null; then
      echo "$id: media branch acne-media/$id with acnemedicine/$id.mp4 not found"; rc=1; continue
    fi
  fi
  python3 acnemedicine/upload.py "$q" "$video" acnemedicine/results "$here/persist.sh"; ec=$?
  rm -f "$video"
  case $ec in
    0) cleanup "$id" || rc=1 ;;
    2) echo "$id: still processing on YouTube; will re-check next run" ;;
    *) rc=1 ;;
  esac
done
rm -rf "$work"
exit $rc
