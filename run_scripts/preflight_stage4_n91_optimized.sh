#!/usr/bin/env bash
set -euo pipefail

REPO="/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro"
VENV="${SPINELLI_STAGE4_VENV:-$HOME/.venvs/spinelli-stage4-n61}"
PYTHON="$VENV/bin/python"
NOTEBOOK="$REPO/historical/stages1-5/notebooks/stage4/Spinelli_Alcubierre_Stage4C_DIM4_memory_optimized.ipynb"
EXPECTED_NOTEBOOK_SHA="1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe"
EXPECTED_RUNNER_SHA="6718cab362dc0c3f3e9a0587ec8bb37056d6582acbf9966b82f4acc252a6574f"
EXPECTED_POSTPROCESSOR_SHA="ded23f039f3167cd9a3d91379bf11e66a1a94e80b3df2cbc6fe2251c9a478e5e"
VALIDATION="$REPO/results/stage4_memory_optimization_validation_20260716_225010"

cd "$REPO"
mkdir -p reports
TS="$(date +%Y%m%d_%H%M%S)"
REPORT="$REPO/reports/stage4_n91_optimized_preflight_${TS}.txt"

{
  echo "===== STAGE 4 OPTIMIZED N91 PREFLIGHT ====="
  echo "Generated: $(date -Is)"
  echo "HEAD: $(git rev-parse HEAD)"

  [[ -x "$PYTHON" ]] || { echo "ERROR: venv Python missing"; exit 1; }
  [[ -f "$NOTEBOOK" ]] || { echo "ERROR: notebook missing"; exit 1; }
  [[ "$(sha256sum "$NOTEBOOK"|awk '{print $1}')" == "$EXPECTED_NOTEBOOK_SHA" ]] || {
    echo "ERROR: notebook SHA mismatch"; exit 1;
  }
  [[ "$(sha256sum scripts/run_stage4_n91_optimized.py|awk '{print $1}')" == "$EXPECTED_RUNNER_SHA" ]] || {
    echo "ERROR: N91 runner SHA mismatch"; exit 1;
  }
  [[ "$(sha256sum scripts/postprocess_stage4_n91_four_grid_analysis.py|awk '{print $1}')" == "$EXPECTED_POSTPROCESSOR_SHA" ]] || {
    echo "ERROR: N91 postprocessor SHA mismatch"; exit 1;
  }

  grep -q '^STAGE4_MEMORY_OPTIMIZATION_VALIDATION_RESULT=PASS$'     "$VALIDATION/stage4_memory_optimization_validation_report.txt" || {
      echo "ERROR: memory-optimization validation PASS missing"; exit 1;
    }
  grep -q '^PHASE4_RECOMMENDATION=BUILD_N91_OPTIMIZED_RUNNER$'     "$VALIDATION/stage4_memory_optimization_validation_report.txt" || {
      echo "ERROR: Phase 4 did not authorize N91"; exit 1;
    }

  "$PYTHON" - "$NOTEBOOK" <<'PY'
import hashlib,json,sys
nb=json.load(open(sys.argv[1],encoding="utf-8"))
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
print("Notebook target cell hashes: PASS")
PY

  "$PYTHON" -m py_compile     scripts/run_stage4_n91_optimized.py     scripts/postprocess_stage4_n91_four_grid_analysis.py

  echo
  echo "===== MEMORY ====="
  free -h
  AVAILABLE_KIB="$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)"
  AVAILABLE_GIB="$((AVAILABLE_KIB/1024/1024))"
  echo "Available RAM GiB: $AVAILABLE_GIB"
  [[ "$AVAILABLE_GIB" -ge 210 ]] || {
    echo "ERROR: less than 210 GiB physical RAM is available"; exit 1;
  }

  SWAP_TOTAL_KIB="$(awk '/SwapTotal:/ {print $2}' /proc/meminfo)"
  SWAP_FREE_KIB="$(awk '/SwapFree:/ {print $2}' /proc/meminfo)"
  awk -v used="$((SWAP_TOTAL_KIB-SWAP_FREE_KIB))" -v total="$SWAP_TOTAL_KIB"     'BEGIN {printf "Swap used: %.3f GiB of %.3f GiB\n",used/1048576,total/1048576}'
  echo "Swap occupancy is informational."
  echo "MemAvailable is the hard memory requirement."

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
    pgrep -af       'python.*(run_stage4_n91_optimized|run_stage4_streaming_export_regression|run_stage4_n81_dense_convergence|stage6_alcubierre|run_stage6E)'       || true
  )"
  if [[ -n "$MATCHES" ]]; then
    echo "$MATCHES"
    echo "ERROR: matching heavy Python computation is active."
    exit 1
  fi
  echo "No matching heavy Python computation detected."

  echo
  echo "===== RESOURCE PROJECTION ====="
  echo "Projected N91 peak RSS: 147.674661 GiB"
  echo "Projected N91 runtime: 414.05 seconds"
  echo "Required available RAM: 210 GiB"
  echo "The process must finish with zero swaps."

  echo
  echo "PREFLIGHT_RESULT=PASS"
} > "$REPORT" 2>&1

echo "REPORT=$REPORT"
