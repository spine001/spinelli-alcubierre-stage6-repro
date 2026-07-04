#!/usr/bin/env python3

from pathlib import Path
import json
import csv
import math
from collections import defaultdict

REPO = Path("/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro")
RUNBASE = (REPO / "results" / "stage6D_alcubierre_highres_latest").resolve()

CASES = [
    "N241_v0p5_sigma4_R3",
    "N241_v1_sigma4_R3",
]

OUT_CSV = RUNBASE / "stage6D_N241_sanitized_reaggregate.csv"
OUT_JSON = RUNBASE / "stage6D_N241_sanitized_reaggregate.json"


def load_json(path):
    return json.loads(path.read_text(errors="ignore"))


def safe_sqrt(x):
    try:
        if x < 0 or not math.isfinite(x):
            return float("nan")
        return math.sqrt(x)
    except Exception:
        return float("nan")


def safe_ratio(a, b):
    try:
        if b == 0 or not math.isfinite(a) or not math.isfinite(b):
            return float("nan")
        return a / b
    except Exception:
        return float("nan")


def is_cfit2_outlier(score):
    cfit2 = float(score.get("Cfit2", 0.0))
    if not math.isfinite(cfit2):
        return True

    scale = max(
        abs(float(score.get("Cact2", 0.0))),
        abs(float(score.get("Qfit2", 0.0))),
        abs(float(score.get("Qact2", 0.0))),
        abs(float(score.get("D2", 0.0))),
        1.0,
    )

    # Conservative guard: only removes values that are astronomically
    # inconsistent with every other norm in the same tile.
    return cfit2 > 1.0e20 and (cfit2 / scale) > 1.0e8


def reaggregate_case(case):
    case_dir = RUNBASE / case
    summary = load_json(case_dir / "case_summary.json")

    totals_all = defaultdict(float)
    totals_clean = defaultdict(float)
    count_files = 0
    outliers = []

    for p in sorted((case_dir / "tiles").glob("*.score.json")):
        score = load_json(p)
        count_files += 1

        cfit2_bad = is_cfit2_outlier(score)

        if cfit2_bad:
            outliers.append(
                {
                    "file": str(p),
                    "Cfit2": score.get("Cfit2"),
                    "Cact2": score.get("Cact2"),
                    "Qfit2": score.get("Qfit2"),
                    "Qact2": score.get("Qact2"),
                    "D2": score.get("D2"),
                    "n": score.get("n"),
                }
            )

        for key in ["n", "Cfit2", "Cact2", "Qfit2", "Qact2", "D2", "G2", "divG2", "qpos_sum", "rho_abs_sum"]:
            val = score.get(key)
            if isinstance(val, (int, float)) and math.isfinite(float(val)):
                totals_all[key] += float(val)

                if not (key == "Cfit2" and cfit2_bad):
                    totals_clean[key] += float(val)

    n = totals_clean["n"]

    sqrt_Cfit2 = safe_sqrt(totals_clean["Cfit2"])
    sqrt_Cact2 = safe_sqrt(totals_clean["Cact2"])
    sqrt_Qfit2 = safe_sqrt(totals_clean["Qfit2"])
    sqrt_Qact2 = safe_sqrt(totals_clean["Qact2"])
    sqrt_D2 = safe_sqrt(totals_clean["D2"])
    sqrt_G2 = safe_sqrt(totals_clean["G2"])
    sqrt_divG2 = safe_sqrt(totals_clean["divG2"])

    row = {
        "case_dir": case,
        "N": summary.get("N"),
        "v_s": summary.get("v_s"),
        "lambda_fit": summary.get("lambda_fit"),
        "beta_fit": summary.get("beta_fit"),
        "mask_points_original": summary.get("mask_points"),
        "mask_points_reaggregated": int(n),
        "score_json_files": count_files,
        "cfit2_outlier_count": len(outliers),
        "cfit2_outlier_files": ";".join(Path(x["file"]).name for x in outliers),
        "original_fit_residual": summary.get("fit_residual"),
        "sanitized_fit_residual": safe_sqrt(totals_clean["Cfit2"] / n) if n else float("nan"),
        "original_action_residual": summary.get("action_residual"),
        "sanitized_action_residual": safe_sqrt(totals_clean["Cact2"] / n) if n else float("nan"),
        "original_action_over_fit": summary.get("action_over_fit"),
        "sanitized_action_over_fit": safe_ratio(sqrt_Cact2, sqrt_Cfit2),
        "original_normalized_fit_residual": summary.get("normalized_fit_residual"),
        "sanitized_normalized_fit_residual": safe_ratio(sqrt_Cfit2, sqrt_Qfit2),
        "original_normalized_action_residual": summary.get("normalized_action_residual"),
        "sanitized_normalized_action_residual": safe_ratio(sqrt_Cact2, sqrt_Qact2),
        "original_relative_tensor_difference": summary.get("relative_tensor_difference"),
        "sanitized_relative_tensor_difference": safe_ratio(sqrt_D2, sqrt_Qfit2),
        "sanitized_tensor_difference_percent": 100.0 * safe_ratio(sqrt_D2, sqrt_Qfit2),
        "original_bianchi": summary.get("bianchi"),
        "sanitized_bianchi": safe_ratio(sqrt_divG2, sqrt_G2),
        "rho_relative_peak_error": summary.get("rho_relative_peak_error"),
        "elapsed_hours": float(summary.get("elapsed_seconds", 0.0)) / 3600.0,
        "total_Cfit2_all": totals_all["Cfit2"],
        "total_Cfit2_sanitized": totals_clean["Cfit2"],
        "total_Cact2": totals_clean["Cact2"],
        "total_Qfit2": totals_clean["Qfit2"],
        "total_Qact2": totals_clean["Qact2"],
        "total_D2": totals_clean["D2"],
        "total_G2": totals_clean["G2"],
        "total_divG2": totals_clean["divG2"],
        "outlier_details": outliers,
    }

    return row


def main():
    rows = [reaggregate_case(case) for case in CASES]

    fieldnames = [
        "case_dir", "N", "v_s", "lambda_fit", "beta_fit",
        "mask_points_original", "mask_points_reaggregated",
        "score_json_files", "cfit2_outlier_count", "cfit2_outlier_files",
        "original_fit_residual", "sanitized_fit_residual",
        "original_action_residual", "sanitized_action_residual",
        "original_action_over_fit", "sanitized_action_over_fit",
        "original_normalized_fit_residual", "sanitized_normalized_fit_residual",
        "original_normalized_action_residual", "sanitized_normalized_action_residual",
        "original_relative_tensor_difference", "sanitized_relative_tensor_difference",
        "sanitized_tensor_difference_percent",
        "original_bianchi", "sanitized_bianchi",
        "rho_relative_peak_error", "elapsed_hours",
        "total_Cfit2_all", "total_Cfit2_sanitized", "total_Cact2",
        "total_Qfit2", "total_Qact2", "total_D2", "total_G2", "total_divG2",
    ]

    with OUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fieldnames})

    OUT_JSON.write_text(json.dumps(rows, indent=2))

    print(f"Wrote: {OUT_CSV}")
    print(f"Wrote: {OUT_JSON}")
    print()
    print("case,N,v_s,beta_fit,cfit2_outliers,sanitized_action_over_fit,sanitized_tensor_difference_percent,sanitized_bianchi,sanitized_fit_residual,sanitized_action_residual")
    for r in rows:
        print(
            f"{r['case_dir']},{r['N']},{r['v_s']},{r['beta_fit']},"
            f"{r['cfit2_outlier_count']},{r['sanitized_action_over_fit']},"
            f"{r['sanitized_tensor_difference_percent']},{r['sanitized_bianchi']},"
            f"{r['sanitized_fit_residual']},{r['sanitized_action_residual']}"
        )


if __name__ == "__main__":
    main()

