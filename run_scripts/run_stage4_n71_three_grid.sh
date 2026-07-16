#!/usr/bin/env bash
set -euo pipefail
REPO="/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro"
VENV="${SPINELLI_STAGE4_VENV:-$HOME/.venvs/spinelli-stage4-n61}"
PYTHON="$VENV/bin/python"
N61="$REPO/results/stage4_revalidation_N61_20260715_212453"
N81="$REPO/results/stage4_revalidation_N81_20260715_221835"
cd "$REPO"

SPINELLI_STAGE4_VENV="$VENV" bash run_scripts/preflight_stage4_n71_three_grid.sh

TS="$(date +%Y%m%d_%H%M%S)"
OUT="$REPO/results/stage4_revalidation_N71_${TS}"
LOG="$OUT/stage4_n71_three_grid.run.log"
mkdir -p "$OUT"
ln -sfn "$(basename "$OUT")" "$REPO/results/stage4_revalidation_N71_latest"

echo "Output directory: $OUT"
echo "Run log: $LOG"
echo "Projected peak RSS: approximately 104.5 GiB."

set +e
/usr/bin/time -v nice -n 5 ionice -c2 -n7 \
  "$PYTHON" scripts/run_stage4_n71_three_grid_analysis.py \
  --repo "$REPO" --n61-dir "$N61" --n81-dir "$N81" --output-dir "$OUT" \
  > "$LOG" 2>&1
RC=$?
set -e

echo "RUN_EXIT_CODE=$RC" | tee -a "$LOG"
echo "OUTPUT_DIR=$OUT" | tee -a "$LOG"
echo "LOG=$LOG" | tee -a "$LOG"
[[ "$RC" -eq 0 ]] || exit "$RC"

REPORT="$OUT/stage4_n71_three_grid_report.txt"
grep -q '^STAGE4_N71_RUN_RESULT=PASS$' "$REPORT" || {
  echo "ERROR: N71 PASS marker missing"; exit 1; }

echo "STAGE4_N71_WRAPPER_RESULT=PASS"
echo "REPORT=$REPORT"
echo "PACKAGE=$REPO/results/$(basename "$OUT").zip"
