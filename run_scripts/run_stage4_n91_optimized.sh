#!/usr/bin/env bash
set -euo pipefail

REPO="/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro"
VENV="${SPINELLI_STAGE4_VENV:-$HOME/.venvs/spinelli-stage4-n61}"
PYTHON="$VENV/bin/python"

N61="$REPO/results/stage4_revalidation_N61_20260715_212453"
N71="$REPO/results/stage4_revalidation_N71_20260716_111107"
N81="$REPO/results/stage4_revalidation_N81_20260715_221835"

cd "$REPO"

SPINELLI_STAGE4_VENV="$VENV" \
  bash run_scripts/preflight_stage4_n91_optimized.sh

TS="$(date +%Y%m%d_%H%M%S)"
OUT="$REPO/results/stage4_revalidation_N91_optimized_${TS}"
LOG="$OUT/stage4_n91_optimized.run.log"

mkdir -p "$OUT"
ln -sfn "$(basename "$OUT")" \
  "$REPO/results/stage4_revalidation_N91_optimized_latest"

echo "Output directory: $OUT"
echo "Run log: $LOG"
echo "Projected peak RSS: approximately 147.7 GiB."
echo "Projected runtime: approximately 6.9 minutes."

set +e
/usr/bin/time -v \
  nice -n 5 \
  ionice -c2 -n7 \
  "$PYTHON" scripts/run_stage4_n91_optimized.py \
    --repo "$REPO" \
    --output-dir "$OUT" \
    --target-n 91 \
    --memory-budget-gib 220 \
    --delta-tau 0.04 \
  > "$LOG" 2>&1
RC=$?
set -e

echo "RUN_EXIT_CODE=$RC" | tee -a "$LOG"
echo "OUTPUT_DIR=$OUT" | tee -a "$LOG"
echo "LOG=$LOG" | tee -a "$LOG"

[[ "$RC" -eq 0 ]] || {
  echo "ERROR: optimized N91 failed; review $LOG" >&2
  exit "$RC"
}

grep -q '^STAGE4_N91_OPTIMIZED_RUN_RESULT=PASS$' \
  "$OUT/stage4_n91_optimized_report.txt" || {
    echo "ERROR: N91 PASS marker missing" >&2
    exit 1
  }

grep -q '^[[:space:]]*Swaps:[[:space:]]*0[[:space:]]*$' "$LOG" || {
  echo "ERROR: optimized N91 used swap" >&2
  exit 1
}

echo
echo "===== POSTPROCESS FOUR-GRID ANALYSIS ====="
"$PYTHON" scripts/postprocess_stage4_n91_four_grid_analysis.py \
  --n61-dir "$N61" \
  --n71-dir "$N71" \
  --n81-dir "$N81" \
  --n91-dir "$OUT" \
  --output-dir "$OUT" \
  | tee -a "$LOG"

REPORT="$OUT/stage4_n91_four_grid_report.txt"
grep -q '^STAGE4_N91_OPTIMIZED_ANALYSIS_RESULT=PASS$' "$REPORT" || {
  echo "ERROR: N91 four-grid analysis PASS missing" >&2
  exit 1
}

PACKAGE="$REPO/results/$(basename "$OUT").zip"
rm -f "$PACKAGE"
"$PYTHON" - "$OUT" "$PACKAGE" <<'PY'
from pathlib import Path
import sys,zipfile
root=Path(sys.argv[1]).resolve()
package=Path(sys.argv[2]).resolve()
with zipfile.ZipFile(package,"w",zipfile.ZIP_DEFLATED) as archive:
    for path in root.rglob("*"):
        if path.is_file():
            archive.write(path,path.relative_to(root))
print(package)
PY

echo
echo "STAGE4_N91_OPTIMIZED_WRAPPER_RESULT=PASS"
echo "REPORT=$REPORT"
echo "PACKAGE=$PACKAGE"
echo "OUTPUT_DIR=$OUT"
