#!/usr/bin/env bash
set -u

REPO="/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro"
PY="/home/julio/spinelli-framework/.venv/bin/python"
SCRIPT="$REPO/scripts/spinelli_stage6b_tiled_cli.py"

# Defaults are the full Stage 6D ladder.
# To run only N241 first:
#   STAGE6D_N_LIST="241" bash run_scripts/run_stage6D_alcubierre_highres_N241_N301.sh
N_LIST="${STAGE6D_N_LIST:-241 261 301}"
VS_LIST="${STAGE6D_VS_LIST:-0.5 1.0}"

STAMP="$(date +%Y%m%d_%H%M%S)"
OUTDIR="$REPO/results/stage6D_alcubierre_highres_${STAMP}"
LATEST="$REPO/results/stage6D_alcubierre_highres_latest"
QUEUE_LOG="$OUTDIR/stage6D_alcubierre_highres_queue.log"

mkdir -p "$OUTDIR" "$REPO/packages"
rm -f "$LATEST"
ln -s "$OUTDIR" "$LATEST"

cat > "$OUTDIR/run_config.json" <<CONFIG
{
  "stage": "6D",
  "description": "Alcubierre wall-focused higher-resolution extension after Stage 6C",
  "solver": "$SCRIPT",
  "N_list": "$N_LIST",
  "v_s_list": "$VS_LIST",
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

summarize_and_bundle () {
    echo "============================================================" | tee -a "$QUEUE_LOG"
    echo "Creating Stage 6D summary and bundle at $(date)" | tee -a "$QUEUE_LOG"
    echo "============================================================" | tee -a "$QUEUE_LOG"

    "$PY" - <<'PY'
from pathlib import Path
import pandas as pd

REPO = Path("/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro")
OUTDIR = (REPO / "results" / "stage6D_alcubierre_highres_latest").resolve()

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

    numeric_cols = [
        "N", "v_s", "sigma", "R", "lambda_fit", "beta_fit", "lambda_action",
        "action_over_fit", "relative_tensor_difference", "tensor_difference",
        "rho_error", "rho_relative_peak_error", "bianchi", "elapsed_seconds"
    ]

    for col in numeric_cols:
        if col in all_df.columns:
            all_df[col] = pd.to_numeric(all_df[col], errors="coerce")

    if "action_over_fit" in all_df.columns:
        all_df["action_error_percent"] = 100.0 * (all_df["action_over_fit"] - 1.0).abs()

    if "relative_tensor_difference" in all_df.columns:
        all_df["tensor_difference_percent"] = 100.0 * all_df["relative_tensor_difference"]
    elif "tensor_difference" in all_df.columns:
        all_df["tensor_difference_percent"] = 100.0 * all_df["tensor_difference"]

    if "elapsed_seconds" in all_df.columns:
        all_df["elapsed_hours"] = all_df["elapsed_seconds"] / 3600.0

    sort_cols = [c for c in ["N", "v_s"] if c in all_df.columns]
    if sort_cols:
        all_df = all_df.sort_values(sort_cols)

    out_csv = OUTDIR / "stage6D_alcubierre_highres_results.csv"
    out_json = OUTDIR / "stage6D_alcubierre_highres_results.json"

    all_df.to_csv(out_csv, index=False)
    out_json.write_text(all_df.to_json(orient="records", indent=2))

    print("Wrote:", out_csv)
    print("Wrote:", out_json)

    show_cols = [
        "N", "v_s", "beta_fit", "action_over_fit",
        "tensor_difference_percent", "bianchi",
        "rho_relative_peak_error", "elapsed_hours"
    ]
    show_cols = [c for c in show_cols if c in all_df.columns]
    print(all_df[show_cols].to_string(index=False))
else:
    print("No completed case_summary.csv files found yet.")
PY

    cd "$OUTDIR" || exit 1
    BUNDLE="$REPO/packages/stage6D_alcubierre_highres_$(basename "$OUTDIR").zip"
    zip -qr "$BUNDLE" .
    echo "Bundle: $BUNDLE" | tee -a "$QUEUE_LOG"
}

run_case () {
    N="$1"
    VS="$2"
    LABEL="$(label_for_case "$N" "$VS")"

    echo "============================================================" | tee -a "$QUEUE_LOG"
    echo "Starting $LABEL at $(date)" | tee -a "$QUEUE_LOG"
    echo "N=$N v_s=$VS sigma=4 R=3" | tee -a "$QUEUE_LOG"
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
      2>&1 | tee "$OUTDIR/${LABEL}.run.log"

    STATUS=${PIPESTATUS[0]}

    if [ "$STATUS" -ne 0 ]; then
        echo "FAILED $LABEL with status $STATUS at $(date)" | tee -a "$QUEUE_LOG"
        echo "Completed cases remain preserved in $OUTDIR" | tee -a "$QUEUE_LOG"
        dmesg -T | tail -100 | tee -a "$QUEUE_LOG" || true
        summarize_and_bundle
        exit "$STATUS"
    fi

    echo "Finished $LABEL at $(date)" | tee -a "$QUEUE_LOG"
    summarize_and_bundle
}

echo "============================================================" | tee -a "$QUEUE_LOG"
echo "Stage 6D Alcubierre higher-resolution extension started at $(date)" | tee -a "$QUEUE_LOG"
echo "Output: $OUTDIR" | tee -a "$QUEUE_LOG"
echo "N_LIST=$N_LIST" | tee -a "$QUEUE_LOG"
echo "VS_LIST=$VS_LIST" | tee -a "$QUEUE_LOG"
echo "sigma=4 R=3 wall_k=3.5 scope=wall tile=9x41x41x9 halo=4 dtype=float64" | tee -a "$QUEUE_LOG"
echo "============================================================" | tee -a "$QUEUE_LOG"

for N in $N_LIST; do
    for VS in $VS_LIST; do
        run_case "$N" "$VS"
    done
done

echo "============================================================" | tee -a "$QUEUE_LOG"
echo "Stage 6D completed at $(date)" | tee -a "$QUEUE_LOG"
echo "============================================================" | tee -a "$QUEUE_LOG"

summarize_and_bundle
