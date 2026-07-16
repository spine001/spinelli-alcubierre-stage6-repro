#!/usr/bin/env bash
set -euo pipefail

REPO="/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro"
VENV="${SPINELLI_STAGE4_VENV:-$HOME/.venvs/spinelli-stage4-n61}"
PYTHON="$VENV/bin/python"
BASELINE="$REPO/results/stage4_revalidation_N71_20260716_111107"

cd "$REPO"

SPINELLI_STAGE4_VENV="$VENV" \
  bash run_scripts/preflight_stage4_n71_delta_tau_matrix.sh

TS="$(date +%Y%m%d_%H%M%S)"
MATRIX="$REPO/results/stage4_n71_delta_tau_matrix_${TS}"
CASE02="$MATRIX/dtau_0p02"
CASE08="$MATRIX/dtau_0p08"
MASTER_LOG="$MATRIX/stage4_n71_delta_tau_matrix.run.log"

mkdir -p "$CASE02" "$CASE08"
ln -sfn "$(basename "$MATRIX")" \
  "$REPO/results/stage4_n71_delta_tau_matrix_latest"

exec > >(tee -a "$MASTER_LOG") 2>&1

echo "===== STAGE 4 N71 DELTA_TAU MATRIX ====="
echo "Matrix directory: $MATRIX"
echo "Existing baseline DELTA_TAU=0.04: $BASELINE"
echo "New case DELTA_TAU=0.02: $CASE02"
echo "New case DELTA_TAU=0.08: $CASE08"
echo "Cases run sequentially."

run_case() {
  local value="$1"
  local tag="$2"
  local output="$3"
  local log="$output/stage4_n71_dtau_${tag}.run.log"

  echo
  echo "===== START DELTA_TAU=$value ====="
  echo "Output: $output"
  echo "Log: $log"

  set +e
  /usr/bin/time -v \
    nice -n 5 \
    ionice -c2 -n7 \
    "$PYTHON" scripts/run_stage4_n71_delta_tau_case.py \
      --repo "$REPO" \
      --output-dir "$output" \
      --delta-tau "$value" \
    > "$log" 2>&1
  local rc=$?
  set -e

  echo "RUN_EXIT_CODE=$rc" | tee -a "$log"
  echo "OUTPUT_DIR=$output" | tee -a "$log"
  echo "LOG=$log" | tee -a "$log"

  [[ "$rc" -eq 0 ]] || {
    echo "ERROR: DELTA_TAU=$value failed; review $log"
    exit "$rc"
  }

  local marker="STAGE4_N71_DTAU_${tag^^}_RESULT=PASS"
  local report="$output/stage4_n71_dtau_${tag}_report.txt"
  grep -q "^${marker}$" "$report" || {
    echo "ERROR: PASS marker missing for DELTA_TAU=$value"
    exit 1
  }

  echo "DELTA_TAU=$value RESULT=PASS"
}

run_case "0.02" "0p02" "$CASE02"
run_case "0.08" "0p08" "$CASE08"

echo
echo "===== POSTPROCESS MATRIX ====="
"$PYTHON" scripts/postprocess_stage4_n71_delta_tau_matrix.py \
  --dtau-0p02-dir "$CASE02" \
  --dtau-0p04-dir "$BASELINE" \
  --dtau-0p08-dir "$CASE08" \
  --output-dir "$MATRIX"

REPORT="$MATRIX/stage4_n71_delta_tau_matrix_report.txt"
grep -q '^STAGE4_N71_DELTA_TAU_MATRIX_RESULT=PASS$' "$REPORT" || {
  echo "ERROR: matrix PASS marker missing"
  exit 1
}

PACKAGE="$REPO/results/$(basename "$MATRIX").zip"
rm -f "$PACKAGE"
"$PYTHON" - "$MATRIX" "$PACKAGE" <<'PY'
from pathlib import Path
import sys, zipfile
root=Path(sys.argv[1]).resolve()
package=Path(sys.argv[2]).resolve()
with zipfile.ZipFile(package,"w",zipfile.ZIP_DEFLATED) as zf:
    for path in root.rglob("*"):
        if path.is_file():
            zf.write(path,path.relative_to(root))
print(package)
PY

echo
echo "STAGE4_N71_DELTA_TAU_WRAPPER_RESULT=PASS"
echo "REPORT=$REPORT"
echo "PACKAGE=$PACKAGE"
echo "MATRIX_DIR=$MATRIX"
