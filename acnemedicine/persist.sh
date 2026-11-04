#!/usr/bin/env bash
# Durably store one result file: commit it on acne-data, push, then confirm origin holds exactly this content.
# Exits non-zero unless the result is confirmed on origin. Called by upload.py after every state change.
set -euo pipefail
f="$1"
cd "$(git -C "$(dirname "$f")" rev-parse --show-toplevel)"
rel="acnemedicine/results/$(basename "$f")"
git add -- "$rel"
if ! git diff --cached --quiet -- "$rel"; then
  git commit -q -m "Acne Medicine Johannesburg: result $(basename "$f" .json) $(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("status",""))' "$rel")" -- "$rel"
fi
for i in 1 2 3 4 5; do
  if git push -q origin HEAD:acne-data 2>/dev/null; then break; fi
  git pull -q --rebase origin acne-data 2>/dev/null || git rebase --abort 2>/dev/null || true
  sleep $((i * 2))
done
git fetch -q origin acne-data
git diff --quiet FETCH_HEAD -- "$rel"        # origin has this exact file, or fail
