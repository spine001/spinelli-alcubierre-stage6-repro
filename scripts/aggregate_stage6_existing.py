from pathlib import Path
import pandas as pd

root = Path(__file__).resolve().parents[1]
results = root / "results"

frames = []

for f in sorted(results.glob("stage6B_N*_results.csv")):
    try:
        df = pd.read_csv(f)
        df["source_file"] = f.name
        frames.append(df)
        print(f"Loaded {f.name}: {len(df)} rows")
    except Exception as e:
        print(f"Could not load {f}: {e}")

if not frames:
    print("No Stage 6B result files found.")
    raise SystemExit

all_df = pd.concat(frames, ignore_index=True)

summary = all_df.groupby("N").agg(
    cases=("N", "count"),
    median_bianchi=("bianchi_wall", "median") if "bianchi_wall" in all_df.columns else ("bianchi_global", "median"),
    median_rho_error=("rho_relative_peak_error_wall", "median") if "rho_relative_peak_error_wall" in all_df.columns else ("rho_relative_peak_error_global", "median"),
    median_beta_fit=("beta_fit_wall", "median") if "beta_fit_wall" in all_df.columns else ("beta_fit_global", "median"),
    median_action_over_fit=("action_over_fit_wall", "median") if "action_over_fit_wall" in all_df.columns else ("action_over_fit_global", "median"),
    median_tensor_difference=("relative_tensor_difference_wall", "median") if "relative_tensor_difference_wall" in all_df.columns else ("relative_tensor_difference_global", "median"),
).reset_index()

out_all = results / "stage6B_tiled_all_available_results.csv"
out_summary = results / "stage6B_tiled_summary_available_results.csv"

all_df.to_csv(out_all, index=False)
summary.to_csv(out_summary, index=False)

print()
print(summary.to_string(index=False))
print()
print("Saved:")
print(out_all)
print(out_summary)
