#!/usr/bin/env bash
set -euo pipefail

REPO="/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro"
VENV="${SPINELLI_STAGE4_VENV:-$HOME/.venvs/spinelli-stage4-n61}"
PYTHON="$VENV/bin/python"
N61="$REPO/results/stage4_revalidation_N61_20260715_212453"

cd "$REPO"

SPINELLI_STAGE4_VENV="$VENV" \
  bash run_scripts/preflight_stage4_n81_dense_convergence.sh

TS="$(date +%Y%m%d_%H%M%S)"
OUT="$REPO/results/stage4_revalidation_N81_${TS}"
LOG="$OUT/stage4_n81_dense_convergence.run.log"
mkdir -p "$OUT"

ln -sfn "$(basename "$OUT")" \
  "$REPO/results/stage4_revalidation_N81_latest"

echo "Output directory: $OUT"
echo "Run log: $LOG"
echo "This run may use roughly 175-190 GiB RAM based on N61 scaling."

set +e
/usr/bin/time -v \
  nice -n 5 \
  ionice -c2 -n7 \
  "$PYTHON" scripts/run_stage4_n81_dense_convergence.py \
    --repo "$REPO" \
    --n61-dir "$N61" \
    --output-dir "$OUT" \
  > "$LOG" 2>&1
RC=$?
set -e

echo "RUN_EXIT_CODE=$RC" | tee -a "$LOG"
echo "OUTPUT_DIR=$OUT" | tee -a "$LOG"
echo "LOG=$LOG" | tee -a "$LOG"

if [[ "$RC" -ne 0 ]]; then
  echo "Stage 4 N81 run failed. Review: $LOG" >&2
  exit "$RC"
fi

REPORT="$OUT/stage4_n81_dense_convergence_report.txt"
[[ -f "$REPORT" ]] || {
  echo "ERROR: expected N81 report not found: $REPORT" >&2
  exit 1
}
grep -q '^STAGE4_N81_RUN_RESULT=PASS$' "$REPORT" || {
  echo "ERROR: N81 result report does not contain PASS." >&2
  exit 1
}

echo "STAGE4_N81_WRAPPER_RESULT=PASS"
echo "REPORT=$REPORT"
echo "PACKAGE=$REPO/results/$(basename "$OUT").zip"
