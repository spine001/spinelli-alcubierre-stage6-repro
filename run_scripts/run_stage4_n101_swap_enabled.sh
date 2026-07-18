#!/usr/bin/env bash
set -euo pipefail
REPO="/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro"
VENV="${SPINELLI_STAGE4_VENV:-$HOME/.venvs/spinelli-stage4-n61}"
PYTHON="$VENV/bin/python"
N61="$REPO/results/stage4_revalidation_N61_20260715_212453"
N71="$REPO/results/stage4_revalidation_N71_20260716_111107"
N81="$REPO/results/stage4_revalidation_N81_20260715_221835"
N91="$REPO/results/stage4_revalidation_N91_optimized_20260717_165255"
cd "$REPO"
SPINELLI_STAGE4_VENV="$VENV" bash run_scripts/preflight_stage4_n101_swap_enabled.sh
TS="$(date +%Y%m%d_%H%M%S)"
OUT="$REPO/results/stage4_revalidation_N101_swap_enabled_${TS}"
LOG="$OUT/stage4_n101_optimized_swap_enabled.run.log"
SAMPLES="$OUT/stage4_n101_resource_samples.csv"
mkdir -p "$OUT"
ln -sfn "$(basename "$OUT")" "$REPO/results/stage4_revalidation_N101_swap_enabled_latest"
echo "Output directory: $OUT"
echo "Run log: $LOG"
echo "Resource samples: $SAMPLES"
echo "Paging is allowed and measured."
echo "timestamp,pid,state,vmrss_kib,vmswap_kib,memavailable_kib,system_swap_used_kib" > "$SAMPLES"

set +e
/usr/bin/time -v nice -n 5 ionice -c2 -n7 \
 "$PYTHON" scripts/run_stage4_n101_optimized_swap_enabled.py \
 --repo "$REPO" --output-dir "$OUT" --target-n 101 \
 --memory-budget-gib 220 --delta-tau 0.04 > "$LOG" 2>&1 &
TIME_PID=$!

while kill -0 "$TIME_PID" 2>/dev/null; do
 PY_PID="$(pgrep -f 'python.*run_stage4_n101_optimized_swap_enabled[.]py' | head -n1 || true)"
 if [[ -n "$PY_PID" && -r "/proc/$PY_PID/status" ]]; then
   STATE="$(awk '/^State:/{print $2}' "/proc/$PY_PID/status")"
   RSS="$(awk '/^VmRSS:/{print $2}' "/proc/$PY_PID/status")"
   PSWAP="$(awk '/^VmSwap:/{print $2}' "/proc/$PY_PID/status")"
   MAV="$(awk '/MemAvailable:/{print $2}' /proc/meminfo)"
   ST="$(awk '/SwapTotal:/{print $2}' /proc/meminfo)"
   SF="$(awk '/SwapFree:/{print $2}' /proc/meminfo)"
   echo "$(date -Is),$PY_PID,$STATE,${RSS:-0},${PSWAP:-0},${MAV:-0},$((ST-SF))" >> "$SAMPLES"
 fi
 sleep 5
done
wait "$TIME_PID"
RC=$?
set -e

echo "RUN_EXIT_CODE=$RC" | tee -a "$LOG"
echo "OUTPUT_DIR=$OUT" | tee -a "$LOG"
echo "LOG=$LOG" | tee -a "$LOG"
[[ "$RC" -eq 0 ]] || { echo "ERROR: N101 failed; review $LOG"; exit "$RC"; }
grep -q '^STAGE4_N101_SWAP_ENABLED_RUN_RESULT=PASS$' "$OUT/stage4_n101_optimized_swap_enabled_report.txt" || {
 echo "ERROR: N101 PASS marker missing"; exit 1;
}

"$PYTHON" scripts/postprocess_stage4_n101_five_grid_analysis.py \
 --n61-dir "$N61" --n71-dir "$N71" --n81-dir "$N81" --n91-dir "$N91" \
 --n101-dir "$OUT" --output-dir "$OUT" | tee -a "$LOG"

grep -q '^STAGE4_N101_FIVE_GRID_ANALYSIS_RESULT=PASS$' "$OUT/stage4_n101_five_grid_report.txt" || {
 echo "ERROR: five-grid analysis PASS missing"; exit 1;
}

PACKAGE="$REPO/results/$(basename "$OUT").zip"
rm -f "$PACKAGE"
"$PYTHON" - "$OUT" "$PACKAGE" <<'PY'
from pathlib import Path
import sys,zipfile
root=Path(sys.argv[1]).resolve(); package=Path(sys.argv[2]).resolve()
with zipfile.ZipFile(package,"w",zipfile.ZIP_DEFLATED) as z:
    for p in root.rglob("*"):
        if p.is_file(): z.write(p,p.relative_to(root))
print(package)
PY
echo "STAGE4_N101_SWAP_ENABLED_WRAPPER_RESULT=PASS"
echo "REPORT=$OUT/stage4_n101_five_grid_report.txt"
echo "PACKAGE=$PACKAGE"
echo "OUTPUT_DIR=$OUT"
