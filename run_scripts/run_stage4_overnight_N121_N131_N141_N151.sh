#!/usr/bin/env bash
set -euo pipefail

REPO="/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro"
VENV="${SPINELLI_STAGE4_VENV:-$HOME/.venvs/spinelli-stage4-n61}"
PYTHON="$VENV/bin/python"
CASES=(121 131 141 151)

N61="$REPO/results/stage4_revalidation_N61_20260715_212453"
N71="$REPO/results/stage4_revalidation_N71_20260716_111107"
N81="$REPO/results/stage4_revalidation_N81_20260715_221835"
N91="$REPO/results/stage4_revalidation_N91_optimized_20260717_165255"
N101="$REPO/results/stage4_revalidation_N101_swap_enabled_20260717_202549"
N111="$REPO/results/stage4_revalidation_N111_swap_enabled_20260718_000258"

cd "$REPO"

SPINELLI_STAGE4_VENV="$VENV" \
  bash run_scripts/preflight_stage4_overnight_N121_N131_N141_N151.sh

TS="$(date +%Y%m%d_%H%M%S)"
BATCH_ROOT="$REPO/results/stage4_overnight_batch_N121_N131_N141_N151_${TS}"
BATCH_LOG="$BATCH_ROOT/stage4_overnight_batch.run.log"
MANIFEST="$BATCH_ROOT/stage4_overnight_batch_manifest.json"

mkdir -p "$BATCH_ROOT"
ln -sfn "$(basename "$BATCH_ROOT")" \
  "$REPO/results/stage4_overnight_batch_latest"

exec > >(tee -a "$BATCH_LOG") 2>&1

echo "===== STAGE 4 OVERNIGHT N121/N131/N141/N151 BATCH ====="
echo "Started: $(date -Is)"
echo "Batch root: $BATCH_ROOT"
echo "Paging is allowed and measured."
echo "The batch stops on a failed run or nonmonotonic principal trend."

COMPLETED=()
STATUS="RUNNING"

find_python_pid() {
  local output="$1"
  ps -eo pid=,comm=,args= |
  awk -v output="$output" '
    $2 ~ /^python/ &&
    index($0, "run_stage4_overnight_batch_case.py") &&
    index($0, output) {
      print $1
      exit
    }
  '
}

read_status_kib() {
  local pid="$1"
  local key="$2"
  awk -v target="$key:" '
    $1 == target {
      print $2
      found=1
      exit
    }
    END {
      if (!found) print 0
    }
  ' "/proc/$pid/status"
}

write_manifest() {
  local batch_status="$1"
  "$PYTHON" - \
    "$MANIFEST" \
    "$batch_status" \
    "$BATCH_ROOT" \
    "${COMPLETED[@]:-}" <<'PY'
from pathlib import Path
import json
import sys

path = Path(sys.argv[1])
status = sys.argv[2]
root = Path(sys.argv[3])
completed = [
    int(value)
    for value in sys.argv[4:]
    if value.strip()
]
data = {
    "batch_status": status,
    "batch_root": str(root),
    "requested_cases": [121, 131, 141],
    "completed_cases": completed,
}
path.write_text(json.dumps(data, indent=2), encoding="utf-8")
PY
}

write_manifest "$STATUS"

for N in "${CASES[@]}"; do
  echo
  echo "================================================================"
  echo " BEGIN N${N}"
  echo " Time: $(date -Is)"
  echo "================================================================"

  OUT="$BATCH_ROOT/N${N}"
  PREFIX="stage4_n${N}_swap_enabled"
  LOG="$OUT/${PREFIX}.run.log"
  SAMPLES="$OUT/stage4_n${N}_resource_samples.csv"

  mkdir -p "$OUT"
  echo \
"timestamp,pid,comm,state,vmrss_kib,vmswap_kib,vmsize_kib,vmhwm_kib,vmpeak_kib,majflt,memavailable_kib,system_swap_used_kib,pswpin_pages,pswpout_pages" \
    > "$SAMPLES"

  set +e
  /usr/bin/time -v \
    nice -n 5 \
    ionice -c2 -n7 \
    "$PYTHON" scripts/run_stage4_overnight_batch_case.py \
      --repo "$REPO" \
      --output-dir "$OUT" \
      --target-n "$N" \
      --memory-budget-gib 1024 \
      --delta-tau 0.04 \
    > "$LOG" 2>&1 &
  TIME_PID=$!

  while kill -0 "$TIME_PID" 2>/dev/null; do
    PY_PID="$(find_python_pid "$OUT" || true)"
    if [[ -n "$PY_PID" && -r "/proc/$PY_PID/status" ]]; then
      COMM="$(cat "/proc/$PY_PID/comm" 2>/dev/null || echo unknown)"
      STATE_CODE="$(
        awk '/^State:/ {print $2; exit}' \
          "/proc/$PY_PID/status"
      )"
      RSS="$(read_status_kib "$PY_PID" VmRSS)"
      PSWAP="$(read_status_kib "$PY_PID" VmSwap)"
      VSIZE="$(read_status_kib "$PY_PID" VmSize)"
      VHWM="$(read_status_kib "$PY_PID" VmHWM)"
      VPEAK="$(read_status_kib "$PY_PID" VmPeak)"
      MAJFLT="$(
        awk '{print $12}' "/proc/$PY_PID/stat" 2>/dev/null ||
        echo 0
      )"
      MAV="$(
        awk '/MemAvailable:/ {print $2; exit}' /proc/meminfo
      )"
      ST="$(
        awk '/SwapTotal:/ {print $2; exit}' /proc/meminfo
      )"
      SF="$(
        awk '/SwapFree:/ {print $2; exit}' /proc/meminfo
      )"
      PSWPIN="$(
        awk '$1=="pswpin" {print $2; exit}' /proc/vmstat
      )"
      PSWPOUT="$(
        awk '$1=="pswpout" {print $2; exit}' /proc/vmstat
      )"

      echo \
"$(date -Is),$PY_PID,$COMM,${STATE_CODE:-?},${RSS:-0},${PSWAP:-0},${VSIZE:-0},${VHWM:-0},${VPEAK:-0},${MAJFLT:-0},${MAV:-0},$((ST-SF)),${PSWPIN:-0},${PSWPOUT:-0}" \
        >> "$SAMPLES"
      sleep 5
    else
      sleep 2
    fi
  done

  wait "$TIME_PID"
  RC=$?
  set -e

  echo "RUN_EXIT_CODE=$RC" >> "$LOG"
  echo "OUTPUT_DIR=$OUT" >> "$LOG"
  echo "LOG=$LOG" >> "$LOG"

  if [[ "$RC" -ne 0 ]]; then
    STATUS="FAILED_N${N}"
    write_manifest "$STATUS"
    echo "ERROR: N${N} failed; stopping batch."
    exit "$RC"
  fi

  MARKER="STAGE4_N${N}_SWAP_ENABLED_RUN_RESULT=PASS"
  grep -q "^${MARKER}$" "$OUT/${PREFIX}_report.txt" || {
    STATUS="MISSING_PASS_N${N}"
    write_manifest "$STATUS"
    echo "ERROR: N${N} PASS marker missing."
    exit 1
  }

  GRID_ARGS=(
    --grid "61=$N61"
    --grid "71=$N71"
    --grid "81=$N81"
    --grid "91=$N91"
    --grid "101=$N101"
    --grid "111=$N111"
  )
  for DONE in "${COMPLETED[@]}"; do
    GRID_ARGS+=(--grid "$DONE=$BATCH_ROOT/N$DONE")
  done
  GRID_ARGS+=(--grid "$N=$OUT")

  "$PYTHON" scripts/postprocess_stage4_spatial_sequence.py \
    "${GRID_ARGS[@]}" \
    --current-n "$N" \
    --output-dir "$OUT" |
    tee -a "$LOG"

  GRID_COUNT=$((6 + ${#COMPLETED[@]} + 1))
  ANALYSIS_MARKER="STAGE4_N${N}_${GRID_COUNT}_GRID_ANALYSIS_RESULT=PASS"
  ANALYSIS_REPORT="$OUT/stage4_n${N}_${GRID_COUNT}_grid_analysis.txt"

  grep -q "^${ANALYSIS_MARKER}$" "$ANALYSIS_REPORT" || {
    STATUS="ANALYSIS_FAILED_N${N}"
    write_manifest "$STATUS"
    echo "ERROR: N${N} cumulative analysis failed."
    exit 1
  }

  grep -q '^Principal spatial monotonicity: True$' \
    "$ANALYSIS_REPORT" || {
      STATUS="NONMONOTONIC_N${N}"
      write_manifest "$STATUS"
      echo "ERROR: principal sequence became nonmonotonic at N${N}."
      exit 1
    }

  CASE_ZIP="$BATCH_ROOT/stage4_batch_N${N}_${TS}.zip"
  "$PYTHON" - "$OUT" "$CASE_ZIP" <<'PY'
from pathlib import Path
import sys
import zipfile

root = Path(sys.argv[1]).resolve()
package = Path(sys.argv[2]).resolve()

with zipfile.ZipFile(
    package,
    "w",
    zipfile.ZIP_DEFLATED,
) as archive:
    for path in root.rglob("*"):
        if path.is_file():
            archive.write(path, path.relative_to(root))

with zipfile.ZipFile(package) as archive:
    bad = archive.testzip()
    if bad:
        raise SystemExit(f"ZIP CRC failure: {bad}")
print(package)
PY

  COMPLETED+=("$N")
  STATUS="COMPLETED_N${N}"
  write_manifest "$STATUS"

  echo "N${N}_RESULT=PASS"
  echo "N${N}_PACKAGE=$CASE_ZIP"
  echo "Completed: $(date -Is)"

  sync
  sleep 30
done

STATUS="PASS"
write_manifest "$STATUS"

FINAL_N="${CASES[-1]}"
FINAL_DIR="$BATCH_ROOT/N${FINAL_N}"
cp -f \
  "$FINAL_DIR/stage4_n${FINAL_N}_10_grid_analysis.txt" \
  "$BATCH_ROOT/"
cp -f \
  "$FINAL_DIR/stage4_n${FINAL_N}_10_grid_analysis.json" \
  "$BATCH_ROOT/"
cp -f \
  "$FINAL_DIR/stage4_n${FINAL_N}_10_grid_analysis_metrics.csv" \
  "$BATCH_ROOT/"
cp -f \
  "$FINAL_DIR/stage4_n${FINAL_N}_10_grid_analysis_resources.csv" \
  "$BATCH_ROOT/"

BATCH_ZIP="$REPO/results/$(basename "$BATCH_ROOT").zip"
rm -f "$BATCH_ZIP"

"$PYTHON" - "$BATCH_ROOT" "$BATCH_ZIP" <<'PY'
from pathlib import Path
import sys
import zipfile

root = Path(sys.argv[1]).resolve()
package = Path(sys.argv[2]).resolve()

with zipfile.ZipFile(
    package,
    "w",
    zipfile.ZIP_DEFLATED,
) as archive:
    for path in root.rglob("*"):
        if path.is_file():
            archive.write(path, path.relative_to(root))

with zipfile.ZipFile(package) as archive:
    bad = archive.testzip()
    if bad:
        raise SystemExit(f"ZIP CRC failure: {bad}")
print(package)
PY

echo
echo "STAGE4_OVERNIGHT_BATCH_RESULT=PASS"
echo "COMPLETED_CASES=${COMPLETED[*]}"
echo "FINAL_REPORT=$BATCH_ROOT/stage4_n151_10_grid_analysis.txt"
echo "PACKAGE=$BATCH_ZIP"
echo "BATCH_ROOT=$BATCH_ROOT"
