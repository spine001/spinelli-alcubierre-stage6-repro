#!/usr/bin/env bash
set -euo pipefail

REPO="/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro"
RUNBASE="$REPO/results/stage6E_alcubierre_robust_tile31_20260712_115959"
CASE="N301_v1_sigma4_R3"
TARGET="N301_v1_sigma4_R3/tiles/tile000864_t0-9_x62-93_y155-186_z126-135.score.json"

cd "$REPO"

if [[ ! -f scripts/rho_outlier_local_diagnostic.py ]]; then
  echo "ERROR: scripts/rho_outlier_local_diagnostic.py not found." >&2
  exit 1
fi
if [[ ! -f "$RUNBASE/$TARGET" ]]; then
  echo "ERROR: target tile not found: $RUNBASE/$TARGET" >&2
  exit 1
fi

TS="$(date +%Y%m%d_%H%M%S)"
REPORT="$REPO/reports/N301_v1_rho_outlier_diagnostic_run_${TS}.txt"
mkdir -p "$REPO/reports"

{
  echo "===== N301 v_s=1 RHO OUTLIER LOCAL DIAGNOSTIC ====="
  echo "Generated: $(date -Is)"
  echo "Runbase: $RUNBASE"
  echo "Case: $CASE"
  echo "Target: $TARGET"
  echo
  python3 scripts/rho_outlier_local_diagnostic.py \
    --runbase "$RUNBASE" \
    --case "$CASE" \
    --target-file "$TARGET" \
    --ring 2 \
    --top 50
  echo
  echo "DIAGNOSTIC_RUN_RESULT=PASS"
} > "$REPORT" 2>&1

echo "REPORT=$REPORT"
