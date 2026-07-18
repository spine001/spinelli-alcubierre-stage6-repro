#!/usr/bin/env bash
set -euo pipefail

REPO="/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro"
VENV="${SPINELLI_STAGE4_VENV:-$HOME/.venvs/spinelli-stage4-n61}"
PYTHON="$VENV/bin/python"

CASES=(141 151 161 171 181 191 201)
MAX_AUTHORIZED_N=201
MAX_PROCESS_SWAP_GIB=2990
MAX_SYSTEM_SWAP_USED_GIB=2990
MAX_PROCESS_SWAP_KIB=$((MAX_PROCESS_SWAP_GIB * 1048576))
MAX_SYSTEM_SWAP_USED_KIB=$((MAX_SYSTEM_SWAP_USED_GIB * 1048576))

N61="$REPO/results/stage4_revalidation_N61_20260715_212453"
N71="$REPO/results/stage4_revalidation_N71_20260716_111107"
N81="$REPO/results/stage4_revalidation_N81_20260715_221835"
N91="$REPO/results/stage4_revalidation_N91_optimized_20260717_165255"
N101="$REPO/results/stage4_revalidation_N101_swap_enabled_20260717_202549"
N111="$REPO/results/stage4_revalidation_N111_swap_enabled_20260718_000258"
REUSED="$REPO/results/published/stage4_overnight_N121_N131_reused_20260718"
N121="$REUSED/N121"
N131="$REUSED/N131"

cd "$REPO"

SPINELLI_STAGE4_VENV="$VENV" \
  bash run_scripts/preflight_stage4_resume_N141_to_N201.sh

TS="$(date +%Y%m%d_%H%M%S)"
BATCH_ROOT="$REPO/results/stage4_resume_N141_to_N201_${TS}"
BATCH_LOG="$BATCH_ROOT/stage4_resume_N141_to_N201.run.log"
MANIFEST="$BATCH_ROOT/stage4_resume_N141_to_N201_manifest.json"
LATEST="$REPO/results/stage4_resume_N141_to_N201_latest"

mkdir -p "$BATCH_ROOT"
ln -sfn "$(basename "$BATCH_ROOT")" "$LATEST"

COMPLETED=()
STATUS="RUNNING"
CURRENT_N=""
FINAL_ANALYSIS=""
FINALIZED=0

exec > >(tee -a "$BATCH_LOG") 2>&1

write_manifest() {
  local status="$1"
  "$PYTHON" - \
    "$MANIFEST" \
    "$status" \
    "$BATCH_ROOT" \
    "$CURRENT_N" \
    "$MAX_AUTHORIZED_N" \
    "$MAX_PROCESS_SWAP_GIB" \
    "${COMPLETED[@]:-}" <<'PY'
from pathlib import Path
import json
import sys

path = Path(sys.argv[1])
status = sys.argv[2]
root = Path(sys.argv[3])
current = sys.argv[4]
max_n = int(sys.argv[5])
max_swap = float(sys.argv[6])
completed = [
    int(value)
    for value in sys.argv[7:]
    if value.strip()
]
data = {
    "batch_status": status,
    "batch_root": str(root),
    "reused_cases": [121, 131],
    "requested_continuation_cases": [
        141, 151, 161, 171, 181, 191, 201
    ],
    "completed_continuation_cases": completed,
    "current_n": int(current) if current else None,
    "max_authorized_n": max_n,
    "max_process_swap_gib": max_swap,
}
path.write_text(json.dumps(data, indent=2), encoding="utf-8")
PY
}

create_aggregate_zip() {
  local package="$REPO/results/$(basename "$BATCH_ROOT").zip"
  rm -f "$package"

  "$PYTHON" - "$BATCH_ROOT" "$package" <<'PY'
from pathlib import Path
import sys
import zipfile

root = Path(sys.argv[1]).resolve()
package = Path(sys.argv[2]).resolve()

with zipfile.ZipFile(
    package,
    "w",
    zipfile.ZIP_DEFLATED,
    allowZip64=True,
) as archive:
    for path in root.rglob("*"):
        if path.is_file():
            archive.write(path, path.relative_to(root))

with zipfile.ZipFile(package) as archive:
    bad = archive.testzip()
    if bad:
        raise SystemExit(f"ZIP CRC failure: {bad}")

print(f"AGGREGATE_PACKAGE={package}")
print(f"AGGREGATE_FILES={len(zipfile.ZipFile(package).namelist())}")
PY
}

finalize() {
  local rc=$?
  trap - EXIT
  set +e

  if [[ "$FINALIZED" -eq 1 ]]; then
    exit "$rc"
  fi
  FINALIZED=1

  write_manifest "$STATUS"

  {
    echo "===== STAGE 4 N141 TO N201 RESUME FINAL STATUS ====="
    echo "Finished: $(date -Is)"
    echo "Status: $STATUS"
    echo "Reused cases: N121 N131"
    echo "Completed continuation cases: ${COMPLETED[*]:-none}"
    echo "Current N at exit: ${CURRENT_N:-none}"
    echo "Maximum authorized N: $MAX_AUTHORIZED_N"
    echo "Maximum authorized process swap: $MAX_PROCESS_SWAP_GIB GiB"
    echo "Final analysis: ${FINAL_ANALYSIS:-none}"
    if [[ "$STATUS" == PASS* ]]; then
      echo "STAGE4_SWAP_AUTHORIZED_RESUME_RESULT=PASS"
    else
      echo "STAGE4_SWAP_AUTHORIZED_RESUME_RESULT=FAIL"
    fi
  } | tee "$BATCH_ROOT/stage4_resume_N141_to_N201_report.txt"

  sync
  create_aggregate_zip
  PACKAGE="$REPO/results/$(basename "$BATCH_ROOT").zip"
  echo "PACKAGE=$PACKAGE"
  echo "BATCH_ROOT=$BATCH_ROOT"

  exit "$rc"
}

trap finalize EXIT

find_python_pid() {
  local output="$1"
  ps -eo pid=,comm=,args= |
  awk -v output="$output" '
    $2 ~ /^python/ &&
    index($0, "run_stage4_swap_authorized_case.py") &&
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

terminate_for_limit() {
  local pid="$1"
  local reason="$2"

  echo "RESOURCE_AUTHORIZATION_LIMIT=$reason"
  echo "Terminating Python PID $pid because the authorized limit was reached."
  kill -TERM "$pid" 2>/dev/null || true

  for _ in $(seq 1 60); do
    kill -0 "$pid" 2>/dev/null || return 0
    sleep 1
  done

  kill -KILL "$pid" 2>/dev/null || true
}

write_manifest "$STATUS"

echo "===== STAGE 4 SWAP-AUTHORIZED RESUME N141 TO N201 ====="
echo "Started: $(date -Is)"
echo "Batch root: $BATCH_ROOT"
echo "Reusing N121 and N131 without recomputation."
echo "Process-swap ceiling: $MAX_PROCESS_SWAP_GIB GiB"
echo "System-swap ceiling: $MAX_SYSTEM_SWAP_USED_GIB GiB"
echo "Every exit path creates an aggregate ZIP."

for N in "${CASES[@]}"; do
  CURRENT_N="$N"
  STATUS="RUNNING_N${N}"
  write_manifest "$STATUS"

  echo
  echo "================================================================"
  echo " BEGIN N${N}"
  echo " Time: $(date -Is)"
  echo "================================================================"

  OUT="$BATCH_ROOT/N${N}"
  PREFIX="stage4_n${N}_swap_enabled"
  LOG="$OUT/${PREFIX}.run.log"
  SAMPLES="$OUT/stage4_n${N}_resource_samples.csv"
  LIMIT_FILE="$OUT/stage4_n${N}_authorization_limit.txt"

  mkdir -p "$OUT"
  echo \
"timestamp,pid,comm,state,vmrss_kib,vmswap_kib,vmsize_kib,vmhwm_kib,vmpeak_kib,majflt,memavailable_kib,system_swap_used_kib,pswpin_pages,pswpout_pages" \
    > "$SAMPLES"

  LIMIT_REASON=""

  set +e
  /usr/bin/time -v \
    nice -n 5 \
    ionice -c2 -n7 \
    "$PYTHON" scripts/run_stage4_swap_authorized_case.py \
      --repo "$REPO" \
      --output-dir "$OUT" \
      --target-n "$N" \
      --memory-budget-gib 4096 \
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
      SYSTEM_SWAP_USED=$((ST-SF))
      PSWPIN="$(
        awk '$1=="pswpin" {print $2; exit}' /proc/vmstat
      )"
      PSWPOUT="$(
        awk '$1=="pswpout" {print $2; exit}' /proc/vmstat
      )"

      echo \
"$(date -Is),$PY_PID,$COMM,${STATE_CODE:-?},${RSS:-0},${PSWAP:-0},${VSIZE:-0},${VHWM:-0},${VPEAK:-0},${MAJFLT:-0},${MAV:-0},${SYSTEM_SWAP_USED:-0},${PSWPIN:-0},${PSWPOUT:-0}" \
        >> "$SAMPLES"

      if [[ "${PSWAP:-0}" -ge "$MAX_PROCESS_SWAP_KIB" ]]; then
        LIMIT_REASON="PROCESS_SWAP_${PSWAP}_KIB"
        echo "$LIMIT_REASON" > "$LIMIT_FILE"
        terminate_for_limit "$PY_PID" "$LIMIT_REASON"
      elif [[ "${SYSTEM_SWAP_USED:-0}" -ge "$MAX_SYSTEM_SWAP_USED_KIB" ]]; then
        LIMIT_REASON="SYSTEM_SWAP_${SYSTEM_SWAP_USED}_KIB"
        echo "$LIMIT_REASON" > "$LIMIT_FILE"
        terminate_for_limit "$PY_PID" "$LIMIT_REASON"
      fi

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

  if [[ -n "$LIMIT_REASON" ]]; then
    STATUS="AUTHORIZATION_LIMIT_N${N}"
    write_manifest "$STATUS"
    echo "ERROR: N${N} reached an authorized swap limit."
    exit 1
  fi

  if [[ "$RC" -ne 0 ]]; then
    STATUS="FAILED_N${N}"
    write_manifest "$STATUS"
    echo "ERROR: N${N} failed; stopping continuation."
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
    --grid "121=$N121"
    --grid "131=$N131"
  )
  for DONE in "${COMPLETED[@]}"; do
    GRID_ARGS+=(--grid "$DONE=$BATCH_ROOT/N$DONE")
  done
  GRID_ARGS+=(--grid "$N=$OUT")

  "$PYTHON" scripts/postprocess_stage4_spatial_sequence.py \
    "${GRID_ARGS[@]}" \
    --current-n "$N" \
    --max-authorized-n "$MAX_AUTHORIZED_N" \
    --max-process-swap-gib "$MAX_PROCESS_SWAP_GIB" \
    --output-dir "$OUT" |
    tee -a "$LOG"

  GRID_COUNT=$((8 + ${#COMPLETED[@]} + 1))
  STEM="stage4_n${N}_${GRID_COUNT}_grid_analysis"
  ANALYSIS_REPORT="$OUT/${STEM}.txt"
  ANALYSIS_JSON="$OUT/${STEM}.json"
  ANALYSIS_MARKER="STAGE4_N${N}_${GRID_COUNT}_GRID_ANALYSIS_RESULT=PASS"

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

  CASE_ZIP="$BATCH_ROOT/stage4_resume_N${N}_${TS}.zip"
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
    allowZip64=True,
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
  FINAL_ANALYSIS="$ANALYSIS_REPORT"
  STATUS="COMPLETED_N${N}"
  write_manifest "$STATUS"

  NEXT_RECOMMENDATION="$(
    "$PYTHON" - "$ANALYSIS_JSON" <<'PY'
import json
import sys
print(json.load(open(sys.argv[1]))["next_recommendation"])
PY
  )"

  echo "N${N}_RESULT=PASS"
  echo "N${N}_PACKAGE=$CASE_ZIP"
  echo "NEXT_RECOMMENDATION=$NEXT_RECOMMENDATION"
  echo "Completed: $(date -Is)"

  if [[ "$NEXT_RECOMMENDATION" == "SWAP_AUTHORIZATION_CEILING_REACHED" ]]; then
    STATUS="PASS_AUTHORIZATION_CEILING_N${N}"
    write_manifest "$STATUS"
    echo "Authorized ladder ceiling reached at N${N}."
    break
  fi

  if [[ "$NEXT_RECOMMENDATION" == STOP_BEFORE_* ]]; then
    STATUS="PASS_PROJECTED_SWAP_CEILING_AFTER_N${N}"
    write_manifest "$STATUS"
    echo "Stopping safely because the next projected case exceeds the swap authorization."
    break
  fi

  EXPECTED_NEXT=$((N+10))
  if [[ "$NEXT_RECOMMENDATION" != "BUILD_N${EXPECTED_NEXT}_SWAP_ENABLED_RUNNER" ]]; then
    STATUS="UNEXPECTED_RECOMMENDATION_N${N}"
    write_manifest "$STATUS"
    echo "ERROR: unexpected recommendation after N${N}: $NEXT_RECOMMENDATION"
    exit 1
  fi

  sync
  sleep 60
done

if [[ "$STATUS" == COMPLETED_* ]]; then
  STATUS="PASS_COMPLETED_REQUESTED_CASES"
fi
write_manifest "$STATUS"
