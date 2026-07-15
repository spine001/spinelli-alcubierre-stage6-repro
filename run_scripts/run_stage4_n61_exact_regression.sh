#!/usr/bin/env bash
set -euo pipefail

REPO="/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro"
cd "$REPO"

bash run_scripts/preflight_stage4_n61_exact_regression.sh

TS="$(date +%Y%m%d_%H%M%S)"
OUT="$REPO/results/stage4_revalidation_N61_${TS}"
LOG="$OUT/stage4_n61_exact_regression.run.log"
mkdir -p "$OUT"

ln -sfn "$(basename "$OUT")" "$REPO/results/stage4_revalidation_N61_latest"

echo "Output directory: $OUT"
echo "Run log: $LOG"

set +e
/usr/bin/time -v \
  nice -n 5 \
  ionice -c2 -n7 \
  python3 scripts/run_stage4_n61_exact_regression.py \
    --repo "$REPO" \
    --output-dir "$OUT" \
  > "$LOG" 2>&1
RC=$?
set -e

echo "RUN_EXIT_CODE=$RC" | tee -a "$LOG"
echo "OUTPUT_DIR=$OUT" | tee -a "$LOG"
echo "LOG=$LOG" | tee -a "$LOG"

if [[ "$RC" -ne 0 ]]; then
  echo "Stage 4 N61 regression failed. Review: $LOG" >&2
  exit "$RC"
fi

REPORT="$OUT/stage4_n61_exact_regression_report.txt"
[[ -f "$REPORT" ]] || {
  echo "ERROR: expected regression report not found: $REPORT" >&2
  exit 1
}

grep -q '^STAGE4_N61_REGRESSION_RESULT=PASS$' "$REPORT" || {
  echo "ERROR: numerical regression did not pass." >&2
  exit 1
}

echo "STAGE4_N61_RUN_RESULT=PASS"
echo "REPORT=$REPORT"
echo "PACKAGE=$REPO/results/$(basename "$OUT").zip"
