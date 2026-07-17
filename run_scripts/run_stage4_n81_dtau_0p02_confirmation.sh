#!/usr/bin/env bash
set -euo pipefail

REPO="/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro"
VENV="${SPINELLI_STAGE4_VENV:-$HOME/.venvs/spinelli-stage4-n61}"
PYTHON="$VENV/bin/python"
N71_MATRIX="$REPO/results/stage4_n71_delta_tau_matrix_20260716_194346"
N71_02="$N71_MATRIX/dtau_0p02"
N71_04="$REPO/results/stage4_revalidation_N71_20260716_111107"
N81_04="$REPO/results/stage4_revalidation_N81_20260715_221835"

cd "$REPO"

SPINELLI_STAGE4_VENV="$VENV" \
  bash run_scripts/preflight_stage4_n81_dtau_0p02_confirmation.sh

TS="$(date +%Y%m%d_%H%M%S)"
OUT="$REPO/results/stage4_n81_dtau_0p02_confirmation_${TS}"
LOG="$OUT/stage4_n81_dtau_0p02_confirmation.run.log"

mkdir -p "$OUT"
ln -sfn "$(basename "$OUT")" \
  "$REPO/results/stage4_n81_dtau_0p02_confirmation_latest"

echo "Output directory: $OUT"
echo "Run log: $LOG"
echo "Projected peak RSS: approximately 177 GiB."
echo "Projected runtime: approximately 4 minutes 15 seconds."

set +e
/usr/bin/time -v \
  nice -n 5 \
  ionice -c2 -n7 \
  "$PYTHON" scripts/run_stage4_n81_dtau_0p02_confirmation.py \
    --repo "$REPO" \
    --output-dir "$OUT" \
  > "$LOG" 2>&1
RC=$?
set -e

echo "RUN_EXIT_CODE=$RC" | tee -a "$LOG"
echo "OUTPUT_DIR=$OUT" | tee -a "$LOG"
echo "LOG=$LOG" | tee -a "$LOG"

[[ "$RC" -eq 0 ]] || {
  echo "ERROR: N81 DELTA_TAU=0.02 case failed; review $LOG" >&2
  exit "$RC"
}

grep -q '^STAGE4_N81_DTAU_0P02_CASE_RESULT=PASS$' \
  "$OUT/stage4_n81_dtau_0p02_case_report.txt" || {
    echo "ERROR: case PASS marker missing" >&2
    exit 1
  }

echo
echo "===== POSTPROCESS N81 CONFIRMATION ====="
"$PYTHON" scripts/postprocess_stage4_n81_dtau_confirmation.py \
  --n71-dtau-0p02-dir "$N71_02" \
  --n71-dtau-0p04-dir "$N71_04" \
  --n81-dtau-0p02-dir "$OUT" \
  --n81-dtau-0p04-dir "$N81_04" \
  --output-dir "$OUT" \
  | tee -a "$LOG"

REPORT="$OUT/stage4_n81_dtau_confirmation_report.txt"
grep -q '^STAGE4_N81_DELTA_TAU_CONFIRMATION_RESULT=PASS$' "$REPORT" || {
  echo "ERROR: confirmation PASS marker missing" >&2
  exit 1
}

PACKAGE="$REPO/results/$(basename "$OUT").zip"
rm -f "$PACKAGE"
"$PYTHON" - "$OUT" "$PACKAGE" <<'PY'
from pathlib import Path
import sys,zipfile
root=Path(sys.argv[1]).resolve()
package=Path(sys.argv[2]).resolve()
with zipfile.ZipFile(package,"w",zipfile.ZIP_DEFLATED) as zf:
    for path in root.rglob("*"):
        if path.is_file():
            zf.write(path,path.relative_to(root))
print(package)
PY

echo
echo "STAGE4_N81_DTAU_CONFIRMATION_WRAPPER_RESULT=PASS"
echo "REPORT=$REPORT"
echo "PACKAGE=$PACKAGE"
echo "OUTPUT_DIR=$OUT"
