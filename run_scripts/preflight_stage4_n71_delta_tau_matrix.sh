#!/usr/bin/env bash
set -euo pipefail

REPO="/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro"
VENV="${SPINELLI_STAGE4_VENV:-$HOME/.venvs/spinelli-stage4-n61}"
PYTHON="$VENV/bin/python"
NOTEBOOK="$REPO/historical/stages1-5/notebooks/stage4/Spinelli_Alcubierre_Stage4C_DIM4_memory_optimized.ipynb"
EXPECTED_SHA="1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe"
BASELINE="$REPO/results/stage4_revalidation_N71_20260716_111107"

cd "$REPO"
mkdir -p reports
TS="$(date +%Y%m%d_%H%M%S)"
REPORT="$REPO/reports/stage4_n71_delta_tau_matrix_preflight_${TS}.txt"

{
  echo "===== STAGE 4 N71 DELTA_TAU MATRIX PREFLIGHT ====="
  echo "Generated: $(date -Is)"
  echo "HEAD: $(git rev-parse HEAD)"

  [[ -x "$PYTHON" ]] || { echo "ERROR: venv Python missing"; exit 1; }
  [[ -f "$NOTEBOOK" ]] || { echo "ERROR: notebook missing"; exit 1; }
  [[ "$(sha256sum "$NOTEBOOK" | awk '{print $1}')" == "$EXPECTED_SHA" ]] || {
    echo "ERROR: notebook SHA mismatch"; exit 1;
  }

  grep -q '^STAGE4_N71_RUN_RESULT=PASS$' \
    "$BASELINE/stage4_n71_three_grid_report.txt" || {
      echo "ERROR: verified N71 DELTA_TAU=0.04 baseline missing"; exit 1;
    }

  "$PYTHON" - "$NOTEBOOK" <<'PY'
import json, sys
nb=json.load(open(sys.argv[1],encoding="utf-8"))
src="".join(nb["cells"][3]["source"])
required={
 "MANUAL_MEMORY_BUDGET_GIB = 28.0":1,
 "N_REQUESTED = 81":1,
 "DELTA_TAU = 0.04":1,
}
for anchor,count in required.items():
    actual=src.count(anchor)
    if actual != count:
        raise SystemExit(f"ERROR: anchor {anchor!r} count={actual}, expected={count}")
print("Notebook patch anchors: PASS")
PY

  echo
  echo "===== MEMORY ====="
  free -h
  AVAILABLE_KIB="$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)"
  AVAILABLE_GIB="$((AVAILABLE_KIB/1024/1024))"
  echo "Available RAM GiB: $AVAILABLE_GIB"
  [[ "$AVAILABLE_GIB" -ge 150 ]] || {
    echo "ERROR: less than 150 GiB physical RAM is available"; exit 1;
  }

  SWAP_TOTAL_KIB="$(awk '/SwapTotal:/ {print $2}' /proc/meminfo)"
  SWAP_FREE_KIB="$(awk '/SwapFree:/ {print $2}' /proc/meminfo)"
  awk -v used="$((SWAP_TOTAL_KIB-SWAP_FREE_KIB))" -v total="$SWAP_TOTAL_KIB" \
    'BEGIN {printf "Swap used: %.3f GiB of %.3f GiB\n",used/1048576,total/1048576}'
  echo "Swap occupancy is informational."

  echo
  echo "===== STORAGE ====="
  df -h "$REPO"
  FREE_GIB="$(( $(df --output=avail -k "$REPO" | tail -n1) /1024/1024 ))"
  echo "Free filesystem GiB: $FREE_GIB"
  [[ "$FREE_GIB" -ge 120 ]] || {
    echo "ERROR: less than 120 GiB filesystem space is free"; exit 1;
  }

  echo
  echo "===== HEAVY PROCESS CHECK ====="
  MATCHES="$(
    pgrep -af \
      'python.*(run_stage4_n71_delta_tau_case|run_stage4_n71_three_grid_analysis|run_stage4_n81_dense_convergence|stage6_alcubierre|run_stage6E)' \
      || true
  )"
  if [[ -n "$MATCHES" ]]; then
    echo "$MATCHES"
    echo "ERROR: matching heavy Python computation is active."
    exit 1
  fi
  echo "No matching heavy Python computation detected."

  echo
  echo "===== EXPECTED RESOURCES ====="
  echo "New cases: DELTA_TAU=0.02 and 0.08"
  echo "Existing baseline reused: DELTA_TAU=0.04"
  echo "Each new case projected peak RSS: approximately 104.5 GiB"
  echo "Each new case projected runtime: approximately 151 seconds"
  echo "Cases execute sequentially in separate Python processes."

  echo
  echo "PREFLIGHT_RESULT=PASS"
} > "$REPORT" 2>&1

echo "REPORT=$REPORT"
