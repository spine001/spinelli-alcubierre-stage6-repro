#!/usr/bin/env bash
set -euo pipefail

REPO="/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro"
NOTEBOOK="$REPO/historical/stages1-5/notebooks/stage4/Spinelli_Alcubierre_Stage4C_DIM4_memory_optimized.ipynb"
EXPECTED_SHA="1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe"

cd "$REPO"
mkdir -p reports
TS="$(date +%Y%m%d_%H%M%S)"
REPORT="$REPO/reports/stage4_n61_exact_regression_preflight_${TS}.txt"

{
  echo "===== STAGE 4 N61 EXACT REGRESSION PREFLIGHT ====="
  echo "Generated: $(date -Is)"
  echo "Repository: $REPO"
  echo "HEAD: $(git rev-parse HEAD)"
  echo

  [[ -f "$NOTEBOOK" ]] || { echo "ERROR: notebook missing"; exit 1; }
  ACTUAL_SHA="$(sha256sum "$NOTEBOOK" | awk '{print $1}')"
  echo "Notebook SHA256: $ACTUAL_SHA"
  [[ "$ACTUAL_SHA" == "$EXPECTED_SHA" ]] || {
    echo "ERROR: notebook hash mismatch"
    exit 1
  }

  echo
  echo "===== PYTHON DEPENDENCIES ====="
  python3 - <<'PY'
import json
import numpy
import pandas
import matplotlib
import scipy
try:
    import psutil
    psutil_version = psutil.__version__
except Exception:
    psutil_version = "not installed; notebook metadata will leave memory fields null"
print("Python dependencies import successfully.")
print("numpy", numpy.__version__)
print("pandas", pandas.__version__)
print("matplotlib", matplotlib.__version__)
print("scipy", scipy.__version__)
print("psutil", psutil_version)
PY

  echo
  echo "===== MEMORY AND STORAGE ====="
  free -h
  echo
  df -h "$REPO"
  AVAILABLE_KIB="$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)"
  AVAILABLE_GIB="$((AVAILABLE_KIB / 1024 / 1024))"
  echo "Available RAM GiB (integer): $AVAILABLE_GIB"
  if [[ "$AVAILABLE_GIB" -lt 80 ]]; then
    echo "ERROR: less than 80 GiB RAM is currently available."
    exit 1
  fi

  FREE_KIB="$(df --output=avail -k "$REPO" | tail -n 1 | tr -d ' ')"
  FREE_GIB="$((FREE_KIB / 1024 / 1024))"
  echo "Free filesystem GiB (integer): $FREE_GIB"
  if [[ "$FREE_GIB" -lt 50 ]]; then
    echo "ERROR: less than 50 GiB filesystem space is available."
    exit 1
  fi

  echo
  echo "===== HEAVY COMPUTE PROCESS CHECK ====="
  MATCHES="$(pgrep -af 'stage6_alcubierre|run_stage6E|N301_v|python3 .*run_stage4_n61_exact_regression\.py' || true)"
  if [[ -n "$MATCHES" ]]; then
    echo "$MATCHES"
    echo "ERROR: a matching heavy-compute process appears active."
    exit 1
  fi
  echo "No matching heavy-compute process detected."

  echo
  echo "===== HISTORICAL REFERENCE TABLES ====="
  refs=(
    historical/stages1-5/results/stage4/stage4A-C/primary_tables/stage4A_dim4_bianchi_validation.csv
    historical/stages1-5/results/stage4/stage4A-C/primary_tables/stage4B_dim4_hessian_Q_proxy.csv
    historical/stages1-5/results/stage4/stage4A-C/primary_tables/stage4C_dim4_candidate_ranking.csv
    historical/stages1-5/results/stage4/stage4A-C/primary_tables/stage4C_dim4_fit_parameters.csv
    historical/stages1-5/results/stage4/stage4D/primary_tables/stage4D_action_vs_fitted_Q_comparison.csv
    historical/stages1-5/results/stage4/stage4D/primary_tables/stage4D_action_vs_fitted_Q_summary.csv
  )
  for f in "${refs[@]}"; do
    [[ -f "$f" ]] || { echo "ERROR: missing $f"; exit 1; }
    echo "OK $f"
  done

  echo
  echo "PREFLIGHT_RESULT=PASS"
} > "$REPORT" 2>&1

echo "REPORT=$REPORT"
