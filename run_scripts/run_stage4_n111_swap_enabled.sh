#!/usr/bin/env bash
set -euo pipefail

REPO="/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro"
VENV="${SPINELLI_STAGE4_VENV:-$HOME/.venvs/spinelli-stage4-n61}"
PYTHON="$VENV/bin/python"

N61="$REPO/results/stage4_revalidation_N61_20260715_212453"
N71="$REPO/results/stage4_revalidation_N71_20260716_111107"
N81="$REPO/results/stage4_revalidation_N81_20260715_221835"
N91="$REPO/results/stage4_revalidation_N91_optimized_20260717_165255"
N101="$REPO/results/stage4_revalidation_N101_swap_enabled_20260717_202549"

cd "$REPO"

SPINELLI_STAGE4_VENV="$VENV" \
  bash run_scripts/preflight_stage4_n111_swap_enabled.sh

TS="$(date +%Y%m%d_%H%M%S)"
OUT="$REPO/results/stage4_revalidation_N111_swap_enabled_${TS}"
LOG="$OUT/stage4_n111_optimized_swap_enabled.run.log"
SAMPLES="$OUT/stage4_n111_resource_samples.csv"

mkdir -p "$OUT"
ln -sfn "$(basename "$OUT")" \
  "$REPO/results/stage4_revalidation_N111_swap_enabled_latest"

echo "Output directory: $OUT"
echo "Run log: $LOG"
echo "Resource samples: $SAMPLES"
echo "Paging is allowed and measured."
echo "Projected working set: approximately 328.64 GiB."
echo "CPU-bound runtime: approximately 15.1 minutes."

echo \
"timestamp,pid,comm,state,vmrss_kib,vmswap_kib,vmsize_kib,vmhwm_kib,vmpeak_kib,majflt,memavailable_kib,system_swap_used_kib,pswpin_pages,pswpout_pages" \
  > "$SAMPLES"

find_python_pid() {
  ps -eo pid=,comm=,args= |
  awk -v output="$OUT" '
    $2 ~ /^python/ &&
    index($0, "run_stage4_n111_optimized_swap_enabled.py") &&
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

set +e
/usr/bin/time -v \
  nice -n 5 \
  ionice -c2 -n7 \
  "$PYTHON" scripts/run_stage4_n111_optimized_swap_enabled.py \
    --repo "$REPO" \
    --output-dir "$OUT" \
    --target-n 111 \
    --memory-budget-gib 512 \
    --delta-tau 0.04 \
  > "$LOG" 2>&1 &
TIME_PID=$!

while kill -0 "$TIME_PID" 2>/dev/null; do
  PY_PID="$(find_python_pid || true)"

  if [[ -n "$PY_PID" && -r "/proc/$PY_PID/status" ]]; then
    COMM="$(cat "/proc/$PY_PID/comm" 2>/dev/null || echo unknown)"
    STATE="$(
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
"$(date -Is),$PY_PID,$COMM,${STATE:-?},${RSS:-0},${PSWAP:-0},${VSIZE:-0},${VHWM:-0},${VPEAK:-0},${MAJFLT:-0},${MAV:-0},$((ST-SF)),${PSWPIN:-0},${PSWPOUT:-0}" \
      >> "$SAMPLES"

    sleep 5
  else
    sleep 2
  fi
done

wait "$TIME_PID"
RC=$?
set -e

echo "RUN_EXIT_CODE=$RC" | tee -a "$LOG"
echo "OUTPUT_DIR=$OUT" | tee -a "$LOG"
echo "LOG=$LOG" | tee -a "$LOG"

[[ "$RC" -eq 0 ]] || {
  echo "ERROR: N111 failed; review $LOG" >&2
  exit "$RC"
}

grep -q '^STAGE4_N111_SWAP_ENABLED_RUN_RESULT=PASS$' \
  "$OUT/stage4_n111_optimized_swap_enabled_report.txt" || {
    echo "ERROR: N111 PASS marker missing" >&2
    exit 1
  }

"$PYTHON" scripts/postprocess_stage4_n111_six_grid_analysis.py \
  --n61-dir "$N61" \
  --n71-dir "$N71" \
  --n81-dir "$N81" \
  --n91-dir "$N91" \
  --n101-dir "$N101" \
  --n111-dir "$OUT" \
  --output-dir "$OUT" |
  tee -a "$LOG"

grep -q '^STAGE4_N111_SIX_GRID_ANALYSIS_RESULT=PASS$' \
  "$OUT/stage4_n111_six_grid_report.txt" || {
    echo "ERROR: six-grid analysis PASS missing" >&2
    exit 1
  }

PACKAGE="$REPO/results/$(basename "$OUT").zip"
rm -f "$PACKAGE"

"$PYTHON" - "$OUT" "$PACKAGE" <<'PY'
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

echo "STAGE4_N111_SWAP_ENABLED_WRAPPER_RESULT=PASS"
echo "REPORT=$OUT/stage4_n111_six_grid_report.txt"
echo "PACKAGE=$PACKAGE"
echo "OUTPUT_DIR=$OUT"
