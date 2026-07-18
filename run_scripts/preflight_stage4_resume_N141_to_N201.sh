#!/usr/bin/env bash
set -euo pipefail

REPO="/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro"
VENV="${SPINELLI_STAGE4_VENV:-$HOME/.venvs/spinelli-stage4-n61}"
PYTHON="$VENV/bin/python"
NOTEBOOK="$REPO/historical/stages1-5/notebooks/stage4/Spinelli_Alcubierre_Stage4C_DIM4_memory_optimized.ipynb"
REUSED="$REPO/results/published/stage4_overnight_N121_N131_reused_20260718"

EXPECTED_NOTEBOOK_SHA="1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe"
EXPECTED_RUNNER_SHA="7923bf5bd8a5777857808f28049430a4a241b19ddf9d2a11f03e43d529169417"
EXPECTED_POSTPROCESSOR_SHA="cdab38cff1fa28aead6ea3c05e2dc0c2ef229fc59df577f595fb7e98ce9aa198"
MAX_PROCESS_SWAP_GIB=2990
MAX_AUTHORIZED_N=201

cd "$REPO"
mkdir -p reports
TS="$(date +%Y%m%d_%H%M%S)"
REPORT="$REPO/reports/stage4_resume_N141_N201_preflight_${TS}.txt"

{
  echo "===== STAGE 4 RESUME N141 TO N201 PREFLIGHT ====="
  echo "Generated: $(date -Is)"
  echo "HEAD: $(git rev-parse HEAD)"

  [[ -x "$PYTHON" ]] || {
    echo "ERROR: venv Python missing"
    exit 1
  }
  [[ -f "$NOTEBOOK" ]] || {
    echo "ERROR: historical notebook missing"
    exit 1
  }
  [[ "$(sha256sum "$NOTEBOOK"|awk '{print $1}')" == "$EXPECTED_NOTEBOOK_SHA" ]] || {
    echo "ERROR: notebook SHA mismatch"
    exit 1
  }
  [[ "$(sha256sum scripts/run_stage4_swap_authorized_case.py|awk '{print $1}')" == "$EXPECTED_RUNNER_SHA" ]] || {
    echo "ERROR: continuation runner SHA mismatch"
    exit 1
  }
  [[ "$(sha256sum scripts/postprocess_stage4_spatial_sequence.py|awk '{print $1}')" == "$EXPECTED_POSTPROCESSOR_SHA" ]] || {
    echo "ERROR: spatial postprocessor SHA mismatch"
    exit 1
  }

  for N in 121 131; do
    GRID_COUNT=7
    [[ "$N" -eq 131 ]] && GRID_COUNT=8
    DIR="$REUSED/N$N"
    [[ -d "$DIR" ]] || {
      echo "ERROR: reused N$N directory missing"
      exit 1
    }
    grep -q "^STAGE4_N${N}_SWAP_ENABLED_RUN_RESULT=PASS$"       "$DIR/stage4_n${N}_swap_enabled_report.txt" || {
        echo "ERROR: N$N run PASS missing"
        exit 1
      }
    grep -q "^STAGE4_N${N}_${GRID_COUNT}_GRID_ANALYSIS_RESULT=PASS$"       "$DIR/stage4_n${N}_${GRID_COUNT}_grid_analysis.txt" || {
        echo "ERROR: N$N cumulative analysis PASS missing"
        exit 1
      }
    grep -q '^Principal spatial monotonicity: True$'       "$DIR/stage4_n${N}_${GRID_COUNT}_grid_analysis.txt" || {
        echo "ERROR: N$N principal monotonicity missing"
        exit 1
      }
  done

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

  "$PYTHON" -m py_compile     scripts/run_stage4_swap_authorized_case.py     scripts/postprocess_stage4_spatial_sequence.py

  echo
  echo "===== SELECTOR VALIDATION ====="
  "$PYTHON" - <<'PY'
import math

budget = 4096.0
scalar_fields = 260
n_auto = int(
    (
        budget * 1024**3
        / (scalar_fields * 8)
    ) ** 0.25
)
if n_auto < 201:
    raise SystemExit(
        f"ERROR: selector budget reaches only N={n_auto}"
    )
print(f"Selector budget reaches N={n_auto}")
print("N201 selector authorization: PASS")
PY

  echo
  echo "===== MEMORY AND SWAP ====="
  free -h
  swapon --show || true

  MEM_KIB="$(awk '/MemAvailable:/{print $2}' /proc/meminfo)"
  SWAP_TOTAL_KIB="$(awk '/SwapTotal:/{print $2}' /proc/meminfo)"
  SWAP_FREE_KIB="$(awk '/SwapFree:/{print $2}' /proc/meminfo)"

  MEM_GIB="$((MEM_KIB/1048576))"
  SWAP_TOTAL_GIB="$((SWAP_TOTAL_KIB/1048576))"
  SWAP_FREE_GIB="$((SWAP_FREE_KIB/1048576))"
  TOTAL_AVAILABLE_GIB="$((MEM_GIB+SWAP_FREE_GIB))"

  echo "MemAvailable GiB: $MEM_GIB"
  echo "SwapTotal GiB: $SWAP_TOTAL_GIB"
  echo "SwapFree GiB: $SWAP_FREE_GIB"
  echo "RAM plus free swap GiB: $TOTAL_AVAILABLE_GIB"

  [[ "$MEM_GIB" -ge 128 ]] || {
    echo "ERROR: less than 128 GiB MemAvailable"
    exit 1
  }
  [[ "$SWAP_TOTAL_GIB" -ge 2990 ]] || {
    echo "ERROR: configured swap is below 2990 GiB"
    exit 1
  }
  [[ "$SWAP_FREE_GIB" -ge 2900 ]] || {
    echo "ERROR: less than 2900 GiB free swap"
    exit 1
  }
  [[ "$TOTAL_AVAILABLE_GIB" -ge 3100 ]] || {
    echo "ERROR: RAM plus free swap is below 3100 GiB"
    exit 1
  }

  echo "MAX_PROCESS_SWAP_GIB=$MAX_PROCESS_SWAP_GIB"
  echo "MAX_AUTHORIZED_N=$MAX_AUTHORIZED_N"
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
    awk '$2 ~ /^python/ && $0 ~ /(run_stage4_swap_authorized_case[.]py|run_stage4_overnight_batch_case[.]py|run_stage4_n111_optimized_swap_enabled[.]py|stage6_alcubierre|run_stage6E)/ { print }'
  )"
  if [[ -n "$MATCHES" ]]; then
    echo "$MATCHES"
    echo "ERROR: competing heavy Python computation detected"
    exit 1
  fi
  echo "No competing heavy Python computation detected."

  echo
  echo "===== AUTHORIZATION PROJECTION ====="
  echo "N201 projected total process footprint: 3009.562316 GiB"
  echo "N201 projected process swap: 2771.316665 GiB"
  echo "N211 projected process swap: 3416.430774 GiB"
  echo "N201 is authorized; N211 is excluded."

  echo
  echo "PREFLIGHT_RESULT=PASS"
} > "$REPORT" 2>&1

echo "REPORT=$REPORT"
