#!/usr/bin/env bash
set -u

REPO="/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro"
PY="/home/julio/spinelli-framework/.venv/bin/python"
SCRIPT="$REPO/scripts/spinelli_stage6b_tiled_cli.py"

STAMP="$(date +%Y%m%d_%H%M%S)"
OUTDIR="$REPO/results/stage6C_alcubierre_highres_${STAMP}"
LATEST="$REPO/results/stage6C_alcubierre_highres_latest"
QUEUE_LOG="$OUTDIR/stage6C_alcubierre_highres_queue.log"

mkdir -p "$OUTDIR"
rm -f "$LATEST"
ln -s "$OUTDIR" "$LATEST"

cat > "$OUTDIR/run_config.json" <<CONFIG
{
  "stage": "6C",
  "description": "Alcubierre wall-focused high-resolution extension using direct case mode",
  "solver": "$SCRIPT",
  "N_values": [181, 201, 221],
  "v_s_values": [0.5, 1.0],
  "sigma": 4.0,
  "R": 3.0,
  "wall_k": 3.5,
  "scope": "wall",
  "dtype": "float64",
  "tile_t": 9,
  "tile_x": 41,
  "tile_y": 41,
  "tile_z": 9,
  "halo": 4,
  "created_at": "$(date -Iseconds)",
  "server": "$(hostname)"
}
CONFIG

echo "============================================================" | tee -a "$QUEUE_LOG"
echo "Stage 6C Alcubierre high-resolution extension started at $(date)" | tee -a "$QUEUE_LOG"
echo "Output: $OUTDIR" | tee -a "$QUEUE_LOG"
echo "Cases: N=181,201,221; v_s=0.5,1.0; sigma=4; R=3" | tee -a "$QUEUE_LOG"
echo "wall_k=3.5 scope=wall tile=9x41x41x9 halo=4 dtype=float64" | tee -a "$QUEUE_LOG"
echo "============================================================" | tee -a "$QUEUE_LOG"
free -h | tee -a "$QUEUE_LOG"
swapon --show | tee -a "$QUEUE_LOG"
df -h / | tee -a "$QUEUE_LOG"

run_case () {
    N="$1"
    VS="$2"

    LABEL="N${N}_v${VS}_sigma4_R3"
    LABEL_SAFE="$(echo "$LABEL" | sed 's/\./p/g')"

    echo "============================================================" | tee -a "$QUEUE_LOG"
    echo "Starting $LABEL_SAFE at $(date)" | tee -a "$QUEUE_LOG"
    echo "N=$N v_s=$VS sigma=4 R=3" | tee -a "$QUEUE_LOG"
    echo "============================================================" | tee -a "$QUEUE_LOG"
    free -h | tee -a "$QUEUE_LOG"
    swapon --show | tee -a "$QUEUE_LOG"

    nice -n 10 ionice -c2 -n7 "$PY" "$SCRIPT" case \
      --output-dir "$OUTDIR" \
      --dtype float64 \
      --extent 5.0 \
      --t-extent 0.4 \
      --delta-tau 0.04 \
      --interior-crop 3 \
      --wall-k 3.5 \
      --scope wall \
      --tile-t 9 \
      --tile-x 41 \
      --tile-y 41 \
      --tile-z 9 \
      --halo 4 \
      --log-every 25 \
      --n "$N" \
      --v-s "$VS" \
      --sigma 4.0 \
      --R 3.0 \
      2>&1 | tee "$OUTDIR/${LABEL_SAFE}.run.log"

    STATUS=${PIPESTATUS[0]}

    if [ "$STATUS" -ne 0 ]; then
        echo "FAILED $LABEL_SAFE with status $STATUS at $(date)" | tee -a "$QUEUE_LOG"
        echo "Continuing no further; completed cases remain preserved in $OUTDIR" | tee -a "$QUEUE_LOG"
        dmesg -T | tail -80 | tee -a "$QUEUE_LOG" || true
        summarize_and_bundle
        exit "$STATUS"
    fi

    echo "Finished $LABEL_SAFE at $(date)" | tee -a "$QUEUE_LOG"
    free -h | tee -a "$QUEUE_LOG"
    swapon --show | tee -a "$QUEUE_LOG"
}

summarize_and_bundle () {
    echo "============================================================" | tee -a "$QUEUE_LOG"
    echo "Creating Stage 6C summary and bundle at $(date)" | tee -a "$QUEUE_LOG"
    echo "============================================================" | tee -a "$QUEUE_LOG"

    "$PY" - <<'PY'
from pathlib import Path
import pandas as pd
import json

OUTDIR = Path("/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro/results/stage6C_alcubierre_highres_latest").resolve()

rows = []
for p in sorted(OUTDIR.glob("N*_v*_sigma4_R3/case_summary.csv")):
    try:
        df = pd.read_csv(p)
        df["case_dir"] = p.parent.name
        rows.append(df)
    except Exception as e:
        print("Could not read", p, e)

if rows:
    all_df = pd.concat(rows, ignore_index=True)

    for col in [
        "N", "v_s", "sigma", "R", "lambda_fit", "beta_fit", "lambda_action",
        "action_over_fit", "tensor_difference", "rho_error", "bianchi",
        "residual_fit", "residual_action", "elapsed_seconds"
    ]:
        if col in all_df.columns:
            all_df[col] = pd.to_numeric(all_df[col], errors="coerce")

    if "action_over_fit" in all_df.columns:
        all_df["action_error_percent"] = 100.0 * (all_df["action_over_fit"] - 1.0).abs()

    if "tensor_difference" in all_df.columns:
        all_df["tensor_difference_percent"] = 100.0 * all_df["tensor_difference"]

    if "elapsed_seconds" in all_df.columns:
        all_df["elapsed_hours"] = all_df["elapsed_seconds"] / 3600.0

    all_df = all_df.sort_values([c for c in ["N", "v_s"] if c in all_df.columns])

    out_csv = OUTDIR / "stage6C_alcubierre_highres_results.csv"
    out_json = OUTDIR / "stage6C_alcubierre_highres_results.json"

    all_df.to_csv(out_csv, index=False)
    out_json.write_text(all_df.to_json(orient="records", indent=2))

    print("Wrote:", out_csv)
    print("Wrote:", out_json)

    show_cols = [c for c in ["N","v_s","beta_fit","action_over_fit","tensor_difference","rho_error","bianchi","elapsed_hours"] if c in all_df.columns]
    print(all_df[show_cols].to_string(index=False))
else:
    print("No completed case_summary.csv files found yet.")
PY

    cd "$OUTDIR"
    zip -qr "$REPO/packages/stage6C_alcubierre_highres_$(basename "$OUTDIR").zip" .
    echo "Bundle:" | tee -a "$QUEUE_LOG"
    echo "$REPO/packages/stage6C_alcubierre_highres_$(basename "$OUTDIR").zip" | tee -a "$QUEUE_LOG"
}

for N in 181 201 221; do
    run_case "$N" 0.5
    run_case "$N" 1.0
    summarize_and_bundle
done

echo "============================================================" | tee -a "$QUEUE_LOG"
echo "Stage 6C completed at $(date)" | tee -a "$QUEUE_LOG"
echo "============================================================" | tee -a "$QUEUE_LOG"
summarize_and_bundle
