#!/usr/bin/env bash
set -euo pipefail
REPO="/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro"
VENV="${SPINELLI_STAGE4_VENV:-$HOME/.venvs/spinelli-stage4-n61}"
PYTHON="$VENV/bin/python"
NOTEBOOK="$REPO/historical/stages1-5/notebooks/stage4/Spinelli_Alcubierre_Stage4C_DIM4_memory_optimized.ipynb"
N91="$REPO/results/stage4_revalidation_N91_optimized_20260717_165255"
cd "$REPO"
mkdir -p reports
TS="$(date +%Y%m%d_%H%M%S)"
REPORT="$REPO/reports/stage4_n101_swap_enabled_preflight_${TS}.txt"
{
 echo "===== STAGE 4 N101 SWAP-ENABLED PREFLIGHT ====="
 echo "Generated: $(date -Is)"
 echo "HEAD: $(git rev-parse HEAD)"
 [[ -x "$PYTHON" ]] || { echo "ERROR: venv Python missing"; exit 1; }
 [[ "$(sha256sum "$NOTEBOOK"|awk '{print $1}')" == "1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe" ]] || { echo "ERROR: notebook SHA mismatch"; exit 1; }
 [[ "$(sha256sum scripts/run_stage4_n101_optimized_swap_enabled.py|awk '{print $1}')" == "e6f4487391fe183eefa52bd89cc917a6992c3622038c0ce2d0ba76450bde1bc2" ]] || { echo "ERROR: runner SHA mismatch"; exit 1; }
 [[ "$(sha256sum scripts/postprocess_stage4_n101_five_grid_analysis.py|awk '{print $1}')" == "11b5f4a599a7b00bf1bc8bc7fbb8add3585bc24472154a157b935e8731c1671a" ]] || { echo "ERROR: postprocessor SHA mismatch"; exit 1; }
 grep -q '^STAGE4_N91_OPTIMIZED_RUN_RESULT=PASS$' "$N91/stage4_n91_optimized_report.txt" || { echo "ERROR: N91 run PASS missing"; exit 1; }
 grep -q '^STAGE4_N91_OPTIMIZED_ANALYSIS_RESULT=PASS$' "$N91/stage4_n91_four_grid_report.txt" || { echo "ERROR: N91 analysis PASS missing"; exit 1; }
 "$PYTHON" -m py_compile scripts/run_stage4_n101_optimized_swap_enabled.py scripts/postprocess_stage4_n101_five_grid_analysis.py
 echo
 echo "===== MEMORY AND SWAP ====="
 free -h
 MEM_KIB="$(awk '/MemAvailable:/{print $2}' /proc/meminfo)"
 SWAP_TOTAL="$(awk '/SwapTotal:/{print $2}' /proc/meminfo)"
 SWAP_FREE="$(awk '/SwapFree:/{print $2}' /proc/meminfo)"
 echo "MemAvailable GiB: $((MEM_KIB/1048576))"
 echo "SwapFree GiB: $((SWAP_FREE/1048576))"
 [[ "$((MEM_KIB/1048576))" -ge 160 ]] || { echo "ERROR: less than 160 GiB MemAvailable"; exit 1; }
 [[ "$((SWAP_FREE/1048576))" -ge 256 ]] || { echo "ERROR: less than 256 GiB free swap"; exit 1; }
 echo "PAGING_POLICY=ALLOWED"
 echo "SWAP_USAGE_IS_NOT_A_FAILURE"
 echo
 echo "===== STORAGE ====="
 df -h "$REPO"
 FREE_GIB="$(( $(df --output=avail -k "$REPO"|tail -n1)/1048576 ))"
 echo "Free filesystem GiB: $FREE_GIB"
 [[ "$FREE_GIB" -ge 120 ]] || { echo "ERROR: less than 120 GiB filesystem free"; exit 1; }
 echo
 echo "===== HEAVY PROCESS CHECK ====="
 MATCHES="$(pgrep -af 'python.*(run_stage4_n101_optimized_swap_enabled|run_stage4_n91_optimized|stage6_alcubierre|run_stage6E)' || true)"
 [[ -z "$MATCHES" ]] || { echo "$MATCHES"; echo "ERROR: competing heavy process"; exit 1; }
 echo "No competing heavy Python computation detected."
 echo
 echo "Projected N101 peak RSS: 224.725728 GiB"
 echo "CPU-bound runtime projection: 623.92 seconds"
 echo "Actual runtime may be longer if paging occurs."
 echo "PREFLIGHT_RESULT=PASS"
} > "$REPORT" 2>&1
echo "REPORT=$REPORT"
