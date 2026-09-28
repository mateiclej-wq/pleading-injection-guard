#!/usr/bin/env bash
# Runs scan.py over every fixture in attacks/manifest.tsv and prints expected vs actual.
# Usage: bash run_attacks.sh [--regen]     (--regen rebuilds the fixtures first)
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
SCAN="$HOME/.claude/skills/pleading-injection-guard/scan.py"
A="$HERE/attacks"
if [ "${1:-}" = "--regen" ]; then
  rm -f "$A/manifest.tsv"
  python3 "$HERE/gen_pdf.py" && python3 -W ignore "$HERE/gen_docx.py" && python3 "$HERE/gen_html_eml.py" && python3 "$HERE/gen_text.py" || exit 1
fi
mkdir -p "$HERE/results"
TIMEOUT=${TIMEOUT:-60}
printf "%-42s %-28s %-24s %s\n" FILE EXPECTED PREDICTED ACTUAL
while IFS=$'\t' read -r f expected predicted desc; do
  [ -z "$f" ] && continue
  out="$HERE/results/${f//\//_}.txt"
  vis="$HERE/results/${f//\//_}.visible.txt"
  start=$(date +%s)
  # macOS has no coreutils timeout by default; use perl alarm
  perl -e 'alarm shift; exec @ARGV' "$TIMEOUT" python3 "$SCAN" --emit-visible "$vis" "$A/$f" >"$out" 2>&1
  rc=$?
  secs=$(( $(date +%s) - start ))
  if [ $rc -eq 142 ] || [ $rc -eq 14 ]; then actual="TIMEOUT(${TIMEOUT}s)"
  elif grep -q "^Traceback" "$out"; then actual="CRASH rc=$rc ($(grep -E '^[A-Za-z_.]+(Error|Exception)' "$out" | tail -1 | cut -c1-40))"
  else actual="$(grep -o 'OVERALL: [A-Z]*' "$out" | head -1 | cut -d' ' -f2) rc=$rc"
  fi
  leak=""
  if [ -f "$vis" ] && grep -qiE "ignore your previous|advise your client|do not mention|automated review|consent to extradition" "$vis"; then leak=" LEAK"; fi
  printf "%-42s %-28s %-24s %s%s (%ss)\n" "$f" "$expected" "$predicted" "$actual" "$leak" "$secs"
done < "$A/manifest.tsv"
