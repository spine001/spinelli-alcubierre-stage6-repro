#!/usr/bin/env bash
set -euo pipefail

REPO="/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro"
VENV="${SPINELLI_STAGE4_VENV:-$HOME/.venvs/spinelli-stage4-n61}"
PYTHON="$VENV/bin/python"
NOTEBOOK="$REPO/historical/stages1-5/notebooks/stage4/Spinelli_Alcubierre_Stage4C_DIM4_memory_optimized.ipynb"
N111="$REPO/results/stage4_revalidation_N111_swap_enabled_20260718_000258"
N111_ZIP="$REPO/results/stage4_revalidation_N111_swap_enabled_20260718_000258.zip"

EXPECTED_NOTEBOOK_SHA="1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe"
EXPECTED_N111_ZIP_SHA="3ee2802b63b6cd430987a80f3f7301546444ef8ab1f3dbefbfe04939d4370d9a"
EXPECTED_RUNNER_SHA="c36294f9e538b3eda6bc881fe1d946c798166973d041a58ed443c0ce9cd6c6e2"
EXPECTED_POSTPROCESSOR_SHA="287987cbef7bba5cdb6757c929c69ece2e349e593413fd496dc910c1ee71b3bc"

cd "$REPO"
mkdir -p reports
TS="$(date +%Y%m%d_%H%M%S)"
REPORT="$REPO/reports/stage4_overnight_N121_N131_N141_N151_preflight_${TS}.txt"

{
  echo "===== STAGE 4 OVERNIGHT N121/N131/N141/N151 PREFLIGHT ====="
  echo "Generated: $(date -Is)"
  echo "HEAD: $(git rev-parse HEAD)"

  [[ -x "$PYTHON" ]] || { echo "ERROR: venv Python missing"; exit 1; }
  [[ "$(sha256sum "$NOTEBOOK"|awk '{print $1}')" == "$EXPECTED_NOTEBOOK_SHA" ]] || {
    echo "ERROR: notebook SHA mismatch"; exit 1;
  }
  [[ "$(sha256sum scripts/run_stage4_overnight_batch_case.py|awk '{print $1}')" == "$EXPECTED_RUNNER_SHA" ]] || {
    echo "ERROR: batch runner SHA mismatch"; exit 1;
  }
  [[ "$(sha256sum scripts/postprocess_stage4_spatial_sequence.py|awk '{print $1}')" == "$EXPECTED_POSTPROCESSOR_SHA" ]] || {
    echo "ERROR: postprocessor SHA mismatch"; exit 1;
  }
  [[ "$(sha256sum "$N111_ZIP"|awk '{print $1}')" == "$EXPECTED_N111_ZIP_SHA" ]] || {
    echo "ERROR: N111 ZIP SHA mismatch"; exit 1;
  }

  grep -q '^STAGE4_N111_SWAP_ENABLED_RUN_RESULT=PASS$'     "$N111/stage4_n111_optimized_swap_enabled_report.txt" || {
      echo "ERROR: N111 PASS missing"; exit 1;
    }
  grep -q '^STAGE4_N111_SIX_GRID_ANALYSIS_RESULT=PASS$'     "$N111/stage4_n111_six_grid_report.txt" || {
      echo "ERROR: N111 analysis PASS missing"; exit 1;
    }
  grep -q '^PHASE7_RECOMMENDATION=BUILD_N121_SWAP_ENABLED_RUNNER$'     "$N111/stage4_n111_six_grid_report.txt" || {
      echo "ERROR: N111 did not authorize N121"; exit 1;
    }

  "$PYTHON" - "$NOTEBOOK" <<'PY'
import hashlib, json, sys
nb=json.load(open(sys.argv[1],encoding="utf-8"))
expected={3:"5a49221d2ba22d35ee05b94fa968dfc9e1628ccc5d228e08712264db8f5291a5",23:"18dfd79cd2b9fe41b798714d1e2f80f6a53ffab7f0eb39a4abe3d98954326957",24:"6528d7dedf482b7590ebf983c79e21ed9670673a570b319533a4f02367fbf1af"}
for i,d in expected.items():
    a=hashlib.sha256("".join(nb["cells"][i]["source"]).encode()).hexdigest()
    if a!=d: raise SystemExit(f"ERROR: cell {i} SHA mismatch")
print("Notebook target cell hashes: PASS")
PY

  "$PYTHON" -m py_compile scripts/run_stage4_overnight_batch_case.py scripts/postprocess_stage4_spatial_sequence.py

  echo
  echo "===== MEMORY AND SWAP ====="
  free -h
  swapon --show || true
  MEM_KIB="$(awk '/MemAvailable:/{print $2}' /proc/meminfo)"
  SWAP_FREE_KIB="$(awk '/SwapFree:/{print $2}' /proc/meminfo)"
  echo "MemAvailable GiB: $((MEM_KIB/1048576))"
  echo "SwapFree GiB: $((SWAP_FREE_KIB/1048576))"
  [[ "$((MEM_KIB/1048576))" -ge 128 ]] || {
    echo "ERROR: less than 128 GiB MemAvailable"; exit 1;
  }
  [[ "$((SWAP_FREE_KIB/1048576))" -ge 1800 ]] || {
    echo "ERROR: less than 1800 GiB free swap"; exit 1;
  }
  echo "PAGING_POLICY=ALLOWED"
  echo "SWAP_USAGE_IS_NOT_A_FAILURE"

  echo
  echo "===== STORAGE ====="
  df -h "$REPO"
  FREE_GIB="$(( $(df --output=avail -k "$REPO"|tail -n1) / 1048576 ))"
  echo "Free filesystem GiB: $FREE_GIB"
  [[ "$FREE_GIB" -ge 120 ]] || {
    echo "ERROR: less than 120 GiB filesystem free"; exit 1;
  }

  echo
  echo "===== HEAVY PROCESS CHECK ====="
  MATCHES="$(
    ps -eo pid=,comm=,args= |
    awk '$2 ~ /^python/ && $0 ~ /(run_stage4_overnight_batch_case[.]py|run_stage4_n111_optimized_swap_enabled[.]py|run_stage4_n101_optimized_swap_enabled[.]py|run_stage4_n91_optimized[.]py|stage6_alcubierre|run_stage6E)/ { print }'
  )"
  [[ -z "$MATCHES" ]] || {
    echo "$MATCHES"; echo "ERROR: competing heavy process"; exit 1;
  }
  echo "No competing heavy Python computation detected."

  echo
  echo "Cases: N121 N131 N141 N151"
  echo "Notebook selector budget: 1024 GiB"
  echo "Projected N151 working set: 1063.890 GiB"
  echo "The batch stops on failure or nonmonotonicity."
  echo "PREFLIGHT_RESULT=PASS"
} > "$REPORT" 2>&1

echo "REPORT=$REPORT"
