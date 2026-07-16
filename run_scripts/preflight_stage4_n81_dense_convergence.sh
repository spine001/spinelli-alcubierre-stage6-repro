#!/usr/bin/env bash
set -euo pipefail

REPO="/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro"
VENV="${SPINELLI_STAGE4_VENV:-$HOME/.venvs/spinelli-stage4-n61}"
PYTHON="$VENV/bin/python"
NOTEBOOK="$REPO/historical/stages1-5/notebooks/stage4/Spinelli_Alcubierre_Stage4C_DIM4_memory_optimized.ipynb"
EXPECTED_SHA="1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe"
N61="$REPO/results/stage4_revalidation_N61_20260715_212453"

cd "$REPO"
mkdir -p reports
TS="$(date +%Y%m%d_%H%M%S)"
REPORT="$REPO/reports/stage4_n81_dense_convergence_preflight_${TS}.txt"

{
  echo "===== STAGE 4 N81 DENSE CONVERGENCE PREFLIGHT ====="
  echo "Generated: $(date -Is)"
  echo "Repository: $REPO"
  echo "HEAD: $(git rev-parse HEAD)"
  echo

  [[ -x "$PYTHON" ]] || {
    echo "ERROR: virtual-environment Python not found: $PYTHON"
    exit 1
  }

  [[ -f "$NOTEBOOK" ]] || {
    echo "ERROR: historical notebook not found"
    exit 1
  }
  ACTUAL_SHA="$(sha256sum "$NOTEBOOK" | awk '{print $1}')"
  echo "Notebook SHA256: $ACTUAL_SHA"
  [[ "$ACTUAL_SHA" == "$EXPECTED_SHA" ]] || {
    echo "ERROR: notebook SHA mismatch"
    exit 1
  }

  echo
  echo "===== PYTHON ENVIRONMENT ====="
  "$PYTHON" - <<'PY'
import sys
import numpy
import pandas
import matplotlib
import scipy
import psutil
print("python", sys.version)
print("numpy", numpy.__version__)
print("pandas", pandas.__version__)
print("matplotlib", matplotlib.__version__)
print("scipy", scipy.__version__)
print("psutil", psutil.__version__)
PY

  echo
  echo "===== VERIFIED N61 BASELINE ====="
  [[ -f "$N61/stage4_n61_exact_regression_report.txt" ]] || {
    echo "ERROR: N61 report missing"
    exit 1
  }
  grep -q '^STAGE4_N61_REGRESSION_RESULT=PASS$' \
    "$N61/stage4_n61_exact_regression_report.txt" || {
      echo "ERROR: N61 baseline does not contain PASS"
      exit 1
    }
  echo "N61 baseline: $N61"
  echo "N61 regression status: PASS"

  echo
  echo "===== MEMORY AND STORAGE ====="
  free -h
  echo
  df -h "$REPO"

  AVAILABLE_KIB="$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)"
  AVAILABLE_GIB="$((AVAILABLE_KIB / 1024 / 1024))"
  echo "Available RAM GiB (integer): $AVAILABLE_GIB"
  if [[ "$AVAILABLE_GIB" -lt 220 ]]; then
    echo "ERROR: N81 requires at least 220 GiB currently available RAM."
    exit 1
  fi

  SWAP_TOTAL_KIB="$(awk '/SwapTotal:/ {print $2}' /proc/meminfo)"
  SWAP_FREE_KIB="$(awk '/SwapFree:/ {print $2}' /proc/meminfo)"
  SWAP_USED_KIB="$((SWAP_TOTAL_KIB - SWAP_FREE_KIB))"

  awk \
    -v used="$SWAP_USED_KIB" \
    -v total="$SWAP_TOTAL_KIB" \
    'BEGIN {
       printf "Swap used: %.3f GiB of %.3f GiB\n",
              used / 1048576,
              total / 1048576
     }'

  echo "Existing swap occupancy is informational."
  echo "MemAvailable is the hard memory requirement."

  FREE_KIB="$(df --output=avail -k "$REPO" | tail -n 1 | tr -d ' ')"
  FREE_GIB="$((FREE_KIB / 1024 / 1024))"
  echo "Free filesystem GiB (integer): $FREE_GIB"
  if [[ "$FREE_GIB" -lt 100 ]]; then
    echo "ERROR: less than 100 GiB filesystem space is available."
    exit 1
  fi

  echo
  echo "===== HEAVY COMPUTE PROCESS CHECK ====="
  MATCHES="$(
    pgrep -af \
      'python.*(run_stage4_n61_exact_regression|run_stage4_n81_dense_convergence|stage6_alcubierre|run_stage6E)' \
      || true
  )"
  if [[ -n "$MATCHES" ]]; then
    echo "$MATCHES"
    echo "ERROR: matching heavy-compute process appears active."
    exit 1
  fi
  echo "No matching heavy-compute process detected."

  echo
  echo "===== RESOURCE PROJECTION ====="
  echo "Measured N61 peak RSS: 56.7597 GiB"
  echo "N^4-scaled N81 projection: 176.466 GiB"
  echo "Required available RAM: 220 GiB"
  echo "Swap is emergency protection only; this run should remain resident in RAM."

  echo
  echo "PREFLIGHT_RESULT=PASS"
} > "$REPORT" 2>&1

echo "REPORT=$REPORT"
