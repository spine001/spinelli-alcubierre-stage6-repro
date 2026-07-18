#!/usr/bin/env bash
set -euo pipefail

REPO="/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro"
VENV="${SPINELLI_STAGE4_VENV:-$HOME/.venvs/spinelli-stage4-n61}"
PYTHON="$VENV/bin/python"
NOTEBOOK="$REPO/historical/stages1-5/notebooks/stage4/Spinelli_Alcubierre_Stage4C_DIM4_memory_optimized.ipynb"
N101="$REPO/results/stage4_revalidation_N101_swap_enabled_20260717_202549"

EXPECTED_NOTEBOOK_SHA="1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe"
EXPECTED_RUNNER_SHA="4913d0891aaf7d3ca639e956eafd8c6ca5764820874e13d12367ab924c817852"
EXPECTED_POSTPROCESSOR_SHA="41da517f7312b6146f62f9a4eaba660d39221356a6d5d470fd7e50a2b0298ec3"

cd "$REPO"
mkdir -p reports
TS="$(date +%Y%m%d_%H%M%S)"
REPORT="$REPO/reports/stage4_n111_swap_enabled_preflight_${TS}.txt"

{
  echo "===== STAGE 4 N111 SWAP-ENABLED PREFLIGHT ====="
  echo "Generated: $(date -Is)"
  echo "HEAD: $(git rev-parse HEAD)"

  [[ -x "$PYTHON" ]] || {
    echo "ERROR: venv Python missing"
    exit 1
  }
  [[ -f "$NOTEBOOK" ]] || {
    echo "ERROR: notebook missing"
    exit 1
  }
  [[ "$(sha256sum "$NOTEBOOK"|awk '{print $1}')" == "$EXPECTED_NOTEBOOK_SHA" ]] || {
    echo "ERROR: notebook SHA mismatch"
    exit 1
  }
  [[ "$(sha256sum scripts/run_stage4_n111_optimized_swap_enabled.py|awk '{print $1}')" == "$EXPECTED_RUNNER_SHA" ]] || {
    echo "ERROR: N111 runner SHA mismatch"
    exit 1
  }
  [[ "$(sha256sum scripts/postprocess_stage4_n111_six_grid_analysis.py|awk '{print $1}')" == "$EXPECTED_POSTPROCESSOR_SHA" ]] || {
    echo "ERROR: N111 postprocessor SHA mismatch"
    exit 1
  }

  grep -q '^STAGE4_N101_SWAP_ENABLED_RUN_RESULT=PASS$'     "$N101/stage4_n101_optimized_swap_enabled_report.txt" || {
      echo "ERROR: N101 run PASS missing"
      exit 1
    }
  grep -q '^STAGE4_N101_FIVE_GRID_ANALYSIS_RESULT=PASS$'     "$N101/stage4_n101_five_grid_report.txt" || {
      echo "ERROR: N101 analysis PASS missing"
      exit 1
    }
  grep -q '^PHASE6_RECOMMENDATION=BUILD_N111_SWAP_ENABLED_RUNNER$'     "$N101/stage4_n101_five_grid_report.txt" || {
      echo "ERROR: N101 did not authorize N111"
      exit 1
    }

  "$PYTHON" - "$NOTEBOOK" <<'PY'
import hashlib
import json
import sys

notebook = json.load(open(sys.argv[1], encoding="utf-8"))
expected = {
    3: "5a49221d2ba22d35ee05b94fa968dfc9e1628ccc5d228e08712264db8f5291a5",
    23: "18dfd79cd2b9fe41b798714d1e2f80f6a53ffab7f0eb39a4abe3d98954326957",
    24: "6528d7dedf482b7590ebf983c79e21ed9670673a570b319533a4f02367fbf1af",
}
for index, digest in expected.items():
    source = "".join(notebook["cells"][index]["source"])
    actual = hashlib.sha256(source.encode()).hexdigest()
    if actual != digest:
        raise SystemExit(
            f"ERROR: cell {index} SHA {actual} != {digest}"
        )
print("Notebook target cell hashes: PASS")
PY

  "$PYTHON" -m py_compile     scripts/run_stage4_n111_optimized_swap_enabled.py     scripts/postprocess_stage4_n111_six_grid_analysis.py

  echo
  echo "===== MEMORY AND SWAP ====="
  free -h
  swapon --show || true

  MEM_KIB="$(awk '/MemAvailable:/{print $2}' /proc/meminfo)"
  SWAP_FREE_KIB="$(awk '/SwapFree:/{print $2}' /proc/meminfo)"
  echo "MemAvailable GiB: $((MEM_KIB/1048576))"
  echo "SwapFree GiB: $((SWAP_FREE_KIB/1048576))"

  [[ "$((MEM_KIB/1048576))" -ge 128 ]] || {
    echo "ERROR: less than 128 GiB MemAvailable"
    exit 1
  }
  [[ "$((SWAP_FREE_KIB/1048576))" -ge 512 ]] || {
    echo "ERROR: less than 512 GiB free swap"
    exit 1
  }

  echo "PAGING_POLICY=ALLOWED"
  echo "SWAP_USAGE_IS_NOT_A_FAILURE"

  echo
  echo "===== STORAGE ====="
  df -h "$REPO"
  FREE_GIB="$(( $(df --output=avail -k "$REPO"|tail -n1) / 1048576 ))"
  echo "Free filesystem GiB: $FREE_GIB"
  [[ "$FREE_GIB" -ge 120 ]] || {
    echo "ERROR: less than 120 GiB filesystem free"
    exit 1
  }

  echo
  echo "===== HEAVY PROCESS CHECK ====="
  MATCHES="$(
    ps -eo pid=,comm=,args= |
    awk '$2 ~ /^python/ && $0 ~ /(run_stage4_n111_optimized_swap_enabled[.]py|run_stage4_n101_optimized_swap_enabled[.]py|run_stage4_n91_optimized[.]py|stage6_alcubierre|run_stage6E)/ { print }'
  )"
  if [[ -n "$MATCHES" ]]; then
    echo "$MATCHES"
    echo "ERROR: competing heavy Python computation detected"
    exit 1
  fi
  echo "No competing heavy Python computation detected."

  echo
  echo "===== RESOURCE PROJECTION ====="
  echo "Projected N111 working set: 328.640039 GiB"
  echo "CPU-bound runtime projection: 904.81 seconds"
  echo "Notebook selector budget: 512 GiB"
  echo "Paging may substantially increase wall time."

  echo
  echo "PREFLIGHT_RESULT=PASS"
} > "$REPORT" 2>&1

echo "REPORT=$REPORT"
