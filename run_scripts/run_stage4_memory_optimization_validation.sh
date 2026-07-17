#!/usr/bin/env bash
set -euo pipefail

REPO="/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro"
VENV="${SPINELLI_STAGE4_VENV:-$HOME/.venvs/spinelli-stage4-n61}"
PYTHON="$VENV/bin/python"
N61_REF="$REPO/results/stage4_revalidation_N61_20260715_212453"
N81_REF="$REPO/results/stage4_revalidation_N81_20260715_221835"

cd "$REPO"

SPINELLI_STAGE4_VENV="$VENV" \
  bash run_scripts/preflight_stage4_memory_optimization_validation.sh

TS="$(date +%Y%m%d_%H%M%S)"
ROOT="$REPO/results/stage4_memory_optimization_validation_${TS}"
N61_OUT="$ROOT/N61"
N81_OUT="$ROOT/N81"
MASTER_LOG="$ROOT/stage4_memory_optimization_validation.run.log"

mkdir -p "$N61_OUT" "$N81_OUT"
ln -sfn "$(basename "$ROOT")" \
  "$REPO/results/stage4_memory_optimization_validation_latest"

exec > >(tee -a "$MASTER_LOG") 2>&1

echo "===== STAGE 4 MEMORY OPTIMIZATION VALIDATION ====="
echo "Root: $ROOT"
echo "N61 output: $N61_OUT"
echo "N81 output: $N81_OUT"

run_case() {
  local n="$1"
  local reference="$2"
  local output="$3"
  local log="$output/stage4_streaming_N${n}.run.log"

  echo
  echo "===== START OPTIMIZED N${n} ====="
  set +e
  /usr/bin/time -v \
    nice -n 5 \
    ionice -c2 -n7 \
    "$PYTHON" scripts/run_stage4_streaming_export_regression.py \
      --repo "$REPO" \
      --output-dir "$output" \
      --reference-dir "$reference" \
      --target-n "$n" \
      --memory-budget-gib 220 \
      --delta-tau 0.04 \
      --rtol 1e-8 \
      --atol 1e-10 \
    > "$log" 2>&1
  local rc=$?
  set -e

  echo "RUN_EXIT_CODE=$rc" | tee -a "$log"
  echo "OUTPUT_DIR=$output" | tee -a "$log"
  echo "LOG=$log" | tee -a "$log"

  [[ "$rc" -eq 0 ]] || {
    echo "ERROR: optimized N${n} failed; review $log"
    exit "$rc"
  }

  grep -q '^STAGE4_STREAMING_EXPORT_REGRESSION_RESULT=PASS$' \
    "$output/stage4_streaming_N${n}_report.txt" || {
      echo "ERROR: optimized N${n} regression PASS missing"
      exit 1
    }

  grep -q '^[[:space:]]*Swaps:[[:space:]]*0[[:space:]]*$' "$log" || {
    echo "ERROR: optimized N${n} used swap"
    exit 1
  }

  echo "OPTIMIZED_N${n}_RESULT=PASS"
}

run_case 61 "$N61_REF" "$N61_OUT"
run_case 81 "$N81_REF" "$N81_OUT"

echo
echo "===== POSTPROCESS MEMORY GATE ====="
"$PYTHON" scripts/postprocess_stage4_memory_optimization_validation.py \
  --n61-dir "$N61_OUT" \
  --n81-dir "$N81_OUT" \
  --output-dir "$ROOT" \
  | tee -a "$MASTER_LOG"

REPORT="$ROOT/stage4_memory_optimization_validation_report.txt"
grep -q '^STAGE4_MEMORY_OPTIMIZATION_VALIDATION_RESULT=PASS$' \
  "$REPORT" || {
    echo "ERROR: memory optimization validation PASS missing"
    exit 1
  }

PACKAGE="$REPO/results/$(basename "$ROOT").zip"
rm -f "$PACKAGE"
"$PYTHON" - "$ROOT" "$PACKAGE" <<'PY'
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
echo "STAGE4_MEMORY_OPTIMIZATION_WRAPPER_RESULT=PASS"
echo "REPORT=$REPORT"
echo "PACKAGE=$PACKAGE"
echo "ROOT=$ROOT"
