#!/usr/bin/env bash
set -euo pipefail

REPO="/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro"
VENV="${SPINELLI_STAGE4_VENV:-$HOME/.venvs/spinelli-stage4-n61}"
PYTHON="$VENV/bin/python"
NOTEBOOK="$REPO/historical/stages1-5/notebooks/stage4/Spinelli_Alcubierre_Stage4C_DIM4_memory_optimized.ipynb"
EXPECTED_SHA="1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe"
N61="$REPO/results/stage4_revalidation_N61_20260715_212453"
N81="$REPO/results/stage4_revalidation_N81_20260715_221835"
DTAU="$REPO/results/stage4_n81_dtau_0p02_confirmation_20260716_214353"

cd "$REPO"
mkdir -p reports
TS="$(date +%Y%m%d_%H%M%S)"
REPORT="$REPO/reports/stage4_memory_optimization_validation_preflight_${TS}.txt"

{
  echo "===== STAGE 4 MEMORY OPTIMIZATION VALIDATION PREFLIGHT ====="
  echo "Generated: $(date -Is)"
  echo "HEAD: $(git rev-parse HEAD)"

  [[ -x "$PYTHON" ]] || { echo "ERROR: venv Python missing"; exit 1; }
  [[ -f "$NOTEBOOK" ]] || { echo "ERROR: notebook missing"; exit 1; }
  [[ "$(sha256sum "$NOTEBOOK"|awk '{print $1}')" == "$EXPECTED_SHA" ]] || {
    echo "ERROR: notebook SHA mismatch"; exit 1;
  }

  grep -q '^STAGE4_N61_REGRESSION_RESULT=PASS$'     "$N61/stage4_n61_exact_regression_report.txt" || {
      echo "ERROR: N61 baseline PASS missing"; exit 1;
    }
  grep -q '^STAGE4_N81_RUN_RESULT=PASS$'     "$N81/stage4_n81_dense_convergence_report.txt" || {
      echo "ERROR: N81 baseline PASS missing"; exit 1;
    }
  grep -q '^STAGE4_N81_DELTA_TAU_CONFIRMATION_RESULT=PASS$'     "$DTAU/stage4_n81_dtau_confirmation_report.txt" || {
      echo "ERROR: N81 DELTA_TAU confirmation PASS missing"; exit 1;
    }
  grep -q '^PHASE3_RECOMMENDATION=BEGIN_MEMORY_OPTIMIZATION_FOR_N91$'     "$DTAU/stage4_n81_dtau_confirmation_report.txt" || {
      echo "ERROR: Phase 3 did not authorize memory optimization"; exit 1;
    }

  "$PYTHON" - "$NOTEBOOK" <<'PY'
import hashlib,json,sys
p=sys.argv[1]
nb=json.load(open(p,encoding="utf-8"))
expected={
  3:"5a49221d2ba22d35ee05b94fa968dfc9e1628ccc5d228e08712264db8f5291a5",
  23:"18dfd79cd2b9fe41b798714d1e2f80f6a53ffab7f0eb39a4abe3d98954326957",
  24:"6528d7dedf482b7590ebf983c79e21ed9670673a570b319533a4f02367fbf1af",
}
for index,digest in expected.items():
    source="".join(nb["cells"][index]["source"])
    actual=hashlib.sha256(source.encode()).hexdigest()
    if actual != digest:
        raise SystemExit(
            f"ERROR: cell {index} SHA {actual} != {digest}"
        )
print("Notebook and target cell hashes: PASS")
PY

  echo
  echo "===== MEMORY ====="
  free -h
  AVAILABLE_KIB="$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)"
  AVAILABLE_GIB="$((AVAILABLE_KIB/1024/1024))"
  echo "Available RAM GiB: $AVAILABLE_GIB"
  [[ "$AVAILABLE_GIB" -ge 220 ]] || {
    echo "ERROR: less than 220 GiB physical RAM is available"; exit 1;
  }

  SWAP_TOTAL_KIB="$(awk '/SwapTotal:/ {print $2}' /proc/meminfo)"
  SWAP_FREE_KIB="$(awk '/SwapFree:/ {print $2}' /proc/meminfo)"
  awk -v used="$((SWAP_TOTAL_KIB-SWAP_FREE_KIB))" -v total="$SWAP_TOTAL_KIB"     'BEGIN {printf "Swap used: %.3f GiB of %.3f GiB\n",used/1048576,total/1048576}'
  echo "Swap occupancy is informational."

  echo
  echo "===== STORAGE ====="
  df -h "$REPO"
  FREE_GIB="$(( $(df --output=avail -k "$REPO"|tail -n1) /1024/1024 ))"
  echo "Free filesystem GiB: $FREE_GIB"
  [[ "$FREE_GIB" -ge 150 ]] || {
    echo "ERROR: less than 150 GiB filesystem space is free"; exit 1;
  }

  echo
  echo "===== HEAVY PROCESS CHECK ====="
  MATCHES="$(
    pgrep -af       'python.*(run_stage4_streaming_export_regression|run_stage4_n81_dtau_0p02_confirmation|run_stage4_n81_dense_convergence|stage6_alcubierre|run_stage6E)'       || true
  )"
  if [[ -n "$MATCHES" ]]; then
    echo "$MATCHES"
    echo "ERROR: matching heavy Python computation is active."
    exit 1
  fi
  echo "No matching heavy Python computation detected."

  echo
  echo "===== VALIDATION PLAN ====="
  echo "Case 1: optimized N61 versus verified N61"
  echo "Case 2: optimized N81 versus verified N81"
  echo "Cases run sequentially in separate Python processes."
  echo "Canonical table tolerance: rtol=1e-8, atol=1e-10"
  echo "N91 gate: optimized N81 projection <= 190 GiB"

  echo
  echo "PREFLIGHT_RESULT=PASS"
} > "$REPORT" 2>&1

echo "REPORT=$REPORT"
