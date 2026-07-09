#!/usr/bin/env bash
set -u

REPO="/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro"
PY="/home/julio/spinelli-framework/.venv/bin/python"
SCRIPT="$REPO/scripts/spinelli_stage6b_tiled_cli.py"
ROBUST="$REPO/scripts/stage6_reaggregate_robust_env_v2_rho.py"

# Default: controlled N261 v_s=0.5 rerun only.
# Later:
#   STAGE6E_VS_LIST="1.0" bash run_scripts/run_stage6E_alcubierre_robust_N261_tile31.sh
N_LIST=261
VS_LIST=1.0

TILE_T="${STAGE6E_TILE_T:-9}"
TILE_X="${STAGE6E_TILE_X:-31}"
TILE_Y="${STAGE6E_TILE_Y:-31}"
TILE_Z="${STAGE6E_TILE_Z:-9}"
HALO="${STAGE6E_HALO:-4}"

STAMP="$(date +%Y%m%d_%H%M%S)"
OUTDIR="$REPO/results/stage6E_alcubierre_robust_tile31_${STAMP}"
LATEST="$REPO/results/stage6E_alcubierre_robust_tile_latest"
QUEUE_LOG="$OUTDIR/stage6E_alcubierre_robust_queue.log"

mkdir -p "$OUTDIR" "$REPO/packages"
rm -f "$LATEST"
ln -s "$OUTDIR" "$LATEST"

cat > "$OUTDIR/run_config.json" <<CONFIG
{
  "stage": "6E",
  "description": "Robust branch-continuation rerun of Stage 6D N261 using smaller spatial tiles and disclosed artifact quarantine",
  "solver": "$SCRIPT",
  "N_list": "$N_LIST",
  "v_s_list": "$VS_LIST",
  "sigma": 4.0,
  "R": 3.0,
  "wall_k": 3.5,
  "scope": "wall",
  "dtype": "float64",
  "tile_t": $TILE_T,
  "tile_x": $TILE_X,
  "tile_y": $TILE_Y,
  "tile_z": $TILE_Z,
  "halo": $HALO,
  "artifact_guard": {
    "major_norm_abs_huge": 1.0e20,
    "qpos_abs_huge": 1.0e20,
    "method": "preserve raw scores; quarantine corrupt contributing score tiles from robust aggregate; disclose excluded count and fraction"
  },
  "branch_continuation_acceptance": {
    "N261_v0p5": {
      "beta_fit": [-1.30, -1.16],
      "lambda_fit": [0.255, 0.272],
      "robust_action_over_fit": [0.995, 1.005],
      "robust_tensor_difference_percent": [0.0, 0.35],
      "robust_bianchi": [0.0, 0.04],
      "rho_sum_peak_relative_error": [0.0, 0.06],
      "excluded_contributing_fraction": [0.0, 0.001]
    },
    "N261_v1": {
      "beta_fit": [-1.90, -1.50],
      "lambda_fit": [1.00, 1.05],
      "robust_action_over_fit": [0.990, 1.006],
      "robust_tensor_difference_percent": [0.0, 1.50],
      "robust_bianchi": [0.0, 0.075],
      "rho_sum_peak_relative_error": [0.0, 0.06],
      "excluded_contributing_fraction": [0.0, 0.001]
    }
  },
  "created_at": "$(date -Iseconds)",
  "server": "$(hostname)"
}
CONFIG

label_for_case () {
    N="$1"
    VS="$2"

    if [ "$VS" = "0.5" ]; then
        echo "N${N}_v0p5_sigma4_R3"
    elif [ "$VS" = "1.0" ] || [ "$VS" = "1" ]; then
        echo "N${N}_v1_sigma4_R3"
    else
        VS_SAFE="$(echo "$VS" | sed 's/\./p/g')"
        echo "N${N}_v${VS_SAFE}_sigma4_R3"
    fi
}

robust_and_gate () {
    echo "============================================================" | tee -a "$QUEUE_LOG"
    echo "Robust reaggregation and branch-continuation gate at $(date)" | tee -a "$QUEUE_LOG"
    echo "============================================================" | tee -a "$QUEUE_LOG"

    STAGE6_RUNBASE="$OUTDIR" "$PY" "$ROBUST" 2>&1 | tee -a "$QUEUE_LOG"
    AGG_STATUS=${PIPESTATUS[0]}

    if [ "$AGG_STATUS" -ne 0 ]; then
        echo "Robust aggregation failed with status $AGG_STATUS" | tee -a "$QUEUE_LOG"
        exit "$AGG_STATUS"
    fi

    "$PY" - "$OUTDIR" <<'PY'
from pathlib import Path
import csv
import sys

outdir = Path(sys.argv[1])
csv_path = outdir / "stage6_robust_reaggregate.csv"

bands = {
    (261, 0.5): {
        "beta_fit": (-1.30, -1.16),
        "lambda_fit": (0.255, 0.272),
        "robust_action_over_fit": (0.995, 1.005),
        "robust_tensor_difference_percent": (0.0, 0.35),
        "robust_bianchi": (0.0, 0.04),
        "rho_sum_peak_relative_error": (0.0, 0.06),
        "excluded_contributing_fraction": (0.0, 0.001),
    },
    (261, 1.0): {
        "beta_fit": (-1.90, -1.50),
        "lambda_fit": (1.00, 1.05),
        "robust_action_over_fit": (0.990, 1.006),
        "robust_tensor_difference_percent": (0.0, 1.50),
        "robust_bianchi": (0.0, 0.075),
        "rho_sum_peak_relative_error": (0.0, 0.06),
        "excluded_contributing_fraction": (0.0, 0.001),
    },
}

rows = list(csv.DictReader(csv_path.open()))
overall_ok = True

print()
print("Stage 6E branch-continuation acceptance gate")
print("=" * 100)

for r in rows:
    N = int(float(r["N"]))
    vs = float(r["v_s"])
    key = (N, vs)
    row_ok = True

    print(f"Case: {r['case_dir']}")

    if key not in bands:
        print("  WARN: no branch-continuation band defined for this case")
        overall_ok = False
        continue

    for metric, (lo, hi) in bands[key].items():
        val = float(r[metric])
        ok = lo <= val <= hi
        row_ok = row_ok and ok
        status = "PASS" if ok else "FAIL"
        print(f"  {status:4s} {metric:38s} value={val:.12g} band=[{lo}, {hi}]")

    print()

    if not row_ok:
        overall_ok = False

print("=" * 100)
print("GATE:", "PASS" if overall_ok else "FAIL")

sys.exit(0 if overall_ok else 3)
PY

    GATE_STATUS=$?

    if [ "$GATE_STATUS" -ne 0 ]; then
        echo "Branch-continuation gate FAILED with status $GATE_STATUS" | tee -a "$QUEUE_LOG"
        echo "Stopping before any further cases." | tee -a "$QUEUE_LOG"
        exit "$GATE_STATUS"
    fi

    echo "Branch-continuation gate PASSED" | tee -a "$QUEUE_LOG"

    cd "$OUTDIR" || exit 1
    BUNDLE="$REPO/packages/stage6E_alcubierre_robust_tile31_$(basename "$OUTDIR").zip"
    zip -qr "$BUNDLE" .
    echo "Bundle: $BUNDLE" | tee -a "$QUEUE_LOG"
}

run_case () {
    N="$1"
    VS="$2"
    LABEL="$(label_for_case "$N" "$VS")"

    echo "============================================================" | tee -a "$QUEUE_LOG"
    echo "Starting $LABEL at $(date)" | tee -a "$QUEUE_LOG"
    echo "N=$N v_s=$VS sigma=4 R=3 tile=${TILE_T}x${TILE_X}x${TILE_Y}x${TILE_Z} halo=$HALO" | tee -a "$QUEUE_LOG"
    echo "============================================================" | tee -a "$QUEUE_LOG"

    free -h | tee -a "$QUEUE_LOG"
    swapon --show | tee -a "$QUEUE_LOG"
    df -h / | tee -a "$QUEUE_LOG"

    nice -n 10 ionice -c2 -n7 "$PY" "$SCRIPT" case \
      --output-dir "$OUTDIR" \
      --dtype float64 \
      --extent 5.0 \
      --t-extent 0.4 \
      --delta-tau 0.04 \
      --interior-crop 3 \
      --wall-k 3.5 \
      --scope wall \
      --tile-t "$TILE_T" \
      --tile-x "$TILE_X" \
      --tile-y "$TILE_Y" \
      --tile-z "$TILE_Z" \
      --halo "$HALO" \
      --log-every 50 \
      --n "$N" \
      --v-s "$VS" \
      --sigma 4.0 \
      --R 3.0 \
      2>&1 | tee "$OUTDIR/${LABEL}.run.log"

    STATUS=${PIPESTATUS[0]}

    if [ "$STATUS" -ne 0 ]; then
        echo "FAILED $LABEL with status $STATUS at $(date)" | tee -a "$QUEUE_LOG"
        dmesg -T | tail -100 | tee -a "$QUEUE_LOG" || true
        robust_and_gate || true
        exit "$STATUS"
    fi

    echo "Finished $LABEL at $(date)" | tee -a "$QUEUE_LOG"
    robust_and_gate
}

echo "============================================================" | tee -a "$QUEUE_LOG"
echo "Stage 6E robust branch-continuation v1 run started at $(date)" | tee -a "$QUEUE_LOG"
echo "Output: $OUTDIR" | tee -a "$QUEUE_LOG"
echo "N_LIST=$N_LIST" | tee -a "$QUEUE_LOG"
echo "VS_LIST=$VS_LIST" | tee -a "$QUEUE_LOG"
echo "tile=${TILE_T}x${TILE_X}x${TILE_Y}x${TILE_Z} halo=$HALO" | tee -a "$QUEUE_LOG"
echo "============================================================" | tee -a "$QUEUE_LOG"

for N in $N_LIST; do
    for VS in $VS_LIST; do
        run_case "$N" "$VS"
    done
done

echo "============================================================" | tee -a "$QUEUE_LOG"
echo "Stage 6E completed at $(date)" | tee -a "$QUEUE_LOG"
echo "============================================================" | tee -a "$QUEUE_LOG"

robust_and_gate
