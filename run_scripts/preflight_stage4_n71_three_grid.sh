#!/usr/bin/env bash
set -euo pipefail
REPO="/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro"
VENV="${SPINELLI_STAGE4_VENV:-$HOME/.venvs/spinelli-stage4-n61}"
PYTHON="$VENV/bin/python"
NOTEBOOK="$REPO/historical/stages1-5/notebooks/stage4/Spinelli_Alcubierre_Stage4C_DIM4_memory_optimized.ipynb"
EXPECTED_SHA="1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe"
N61="$REPO/results/stage4_revalidation_N61_20260715_212453"
N81="$REPO/results/stage4_revalidation_N81_20260715_221835"

cd "$REPO"; mkdir -p reports
TS="$(date +%Y%m%d_%H%M%S)"
REPORT="$REPO/reports/stage4_n71_three_grid_preflight_${TS}.txt"

{
 echo "===== STAGE 4 N71 THREE-GRID PREFLIGHT ====="
 echo "Generated: $(date -Is)"
 echo "HEAD: $(git rev-parse HEAD)"
 [[ -x "$PYTHON" ]] || { echo "ERROR: venv Python missing"; exit 1; }
 [[ "$(sha256sum "$NOTEBOOK" | awk '{print $1}')" == "$EXPECTED_SHA" ]] || {
   echo "ERROR: notebook SHA mismatch"; exit 1; }
 grep -q '^STAGE4_N61_REGRESSION_RESULT=PASS$' "$N61/stage4_n61_exact_regression_report.txt" || {
   echo "ERROR: N61 PASS missing"; exit 1; }
 grep -q '^STAGE4_N81_RUN_RESULT=PASS$' "$N81/stage4_n81_dense_convergence_report.txt" || {
   echo "ERROR: N81 PASS missing"; exit 1; }

 "$PYTHON" - "$NOTEBOOK" <<'PY'
import json,sys
nb=json.load(open(sys.argv[1],encoding="utf-8"))
src="".join(nb["cells"][3]["source"])
assert src.count("MANUAL_MEMORY_BUDGET_GIB = 28.0")==1
assert src.count("N_REQUESTED = 81")==1
print("Notebook patch anchors: PASS")
PY

 free -h
 AVAILABLE_KIB="$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)"
 AVAILABLE_GIB="$((AVAILABLE_KIB/1024/1024))"
 echo "Available RAM GiB: $AVAILABLE_GIB"
 [[ "$AVAILABLE_GIB" -ge 150 ]] || { echo "ERROR: less than 150 GiB available RAM"; exit 1; }

 SWAP_TOTAL_KIB="$(awk '/SwapTotal:/ {print $2}' /proc/meminfo)"
 SWAP_FREE_KIB="$(awk '/SwapFree:/ {print $2}' /proc/meminfo)"
 awk -v used="$((SWAP_TOTAL_KIB-SWAP_FREE_KIB))" -v total="$SWAP_TOTAL_KIB" \
   'BEGIN {printf "Swap used: %.3f GiB of %.3f GiB\n",used/1048576,total/1048576}'
 echo "Swap occupancy is informational."

 MATCHES="$(pgrep -af 'python.*(run_stage4_n61_exact_regression|run_stage4_n71_three_grid_analysis|run_stage4_n81_dense_convergence|stage6_alcubierre|run_stage6E)' || true)"
 [[ -z "$MATCHES" ]] || { echo "$MATCHES"; echo "ERROR: heavy Python computation active"; exit 1; }

 FREE_GIB="$(( $(df --output=avail -k "$REPO" | tail -n1) /1024/1024 ))"
 echo "Free filesystem GiB: $FREE_GIB"
 [[ "$FREE_GIB" -ge 100 ]] || { echo "ERROR: less than 100 GiB free"; exit 1; }

 echo "Projected N71 peak RSS: 104.48 GiB"
 echo "Projected N71 runtime: about 150 seconds"
 echo "PREFLIGHT_RESULT=PASS"
} > "$REPORT" 2>&1
echo "REPORT=$REPORT"
