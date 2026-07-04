#!/usr/bin/env python3

from pathlib import Path
import json
import csv
import math
from collections import defaultdict

REPO = Path("/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro")
RUNBASE = (REPO / "results" / "stage6D_alcubierre_highres_latest").resolve()

OUT_CSV = RUNBASE / "stage6D_sanitized_reaggregate.csv"
OUT_JSON = RUNBASE / "stage6D_sanitized_reaggregate.json"


def load_json(path):
    return json.loads(path.read_text(errors="ignore"))


def safe_sqrt(x):
    if x < 0 or not math.isfinite(x):
        return float("nan")
    return math.sqrt(x)


def safe_ratio(a, b):
    if b == 0 or not math.isfinite(a) or not math.isfinite(b):
        return float("nan")
    return a / b


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

    return cfit2 > 1.0e20 and (cfit2 / scale) > 1.0e8


def reaggregate_case(case_dir):
    summary = load_json(case_dir / "case_summary.json")

    totals_all = defaultdict(float)
    totals_clean = defaultdict(float)
    outliers = []
    score_files = sorted((case_dir / "tiles").glob("*.score.json"))

    for p in score_files:
        score = load_json(p)
        cfit2_bad = is_cfit2_outlier(score)

        if cfit2_bad:
            outliers.append(
                {
                    "file": p.name,
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

    clean_fit_residual = safe_sqrt(totals_clean["Cfit2"] / n) if n else float("nan")
    clean_action_residual = safe_sqrt(totals_clean["Cact2"] / n) if n else float("nan")
    clean_action_over_fit = safe_ratio(sqrt_Cact2, sqrt_Cfit2)
    clean_tensor_diff = safe_ratio(sqrt_D2, sqrt_Qfit2)
    clean_bianchi = safe_ratio(sqrt_divG2, sqrt_G2)

    return {
        "case_dir": case_dir.name,
        "N": summary.get("N"),
        "v_s": summary.get("v_s"),
        "lambda_fit": summary.get("lambda_fit"),
        "beta_fit": summary.get("beta_fit"),
        "mask_points": summary.get("mask_points"),
        "score_json_files": len(score_files),
        "cfit2_outlier_count": len(outliers),
        "cfit2_outlier_files": ";".join(x["file"] for x in outliers),
        "raw_fit_residual": summary.get("fit_residual"),
        "sanitized_fit_residual": clean_fit_residual,
        "raw_action_residual": summary.get("action_residual"),
        "sanitized_action_residual": clean_action_residual,
        "raw_action_over_fit": summary.get("action_over_fit"),
        "sanitized_action_over_fit": clean_action_over_fit,
        "raw_normalized_fit_residual": summary.get("normalized_fit_residual"),
        "sanitized_normalized_fit_residual": safe_ratio(sqrt_Cfit2, sqrt_Qfit2),
        "raw_normalized_action_residual": summary.get("normalized_action_residual"),
        "sanitized_normalized_action_residual": safe_ratio(sqrt_Cact2, sqrt_Qact2),
        "raw_relative_tensor_difference": summary.get("relative_tensor_difference"),
        "sanitized_relative_tensor_difference": clean_tensor_diff,
        "sanitized_tensor_difference_percent": 100.0 * clean_tensor_diff,
        "raw_bianchi": summary.get("bianchi"),
        "sanitized_bianchi": clean_bianchi,
        "rho_relative_peak_error": summary.get("rho_relative_peak_error"),
        "elapsed_seconds": summary.get("elapsed_seconds"),
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


def main():
    case_dirs = sorted(
        p for p in RUNBASE.glob("N*_v*_sigma4_R3")
        if p.is_dir() and (p / "case_summary.json").exists() and (p / "tiles").exists()
    )

    rows = [reaggregate_case(p) for p in case_dirs]

    rows.sort(key=lambda r: (float(r["N"]), float(r["v_s"])))

    fieldnames = [
        "case_dir", "N", "v_s", "lambda_fit", "beta_fit",
        "mask_points", "score_json_files",
        "cfit2_outlier_count", "cfit2_outlier_files",
        "raw_fit_residual", "sanitized_fit_residual",
        "raw_action_residual", "sanitized_action_residual",
        "raw_action_over_fit", "sanitized_action_over_fit",
        "raw_normalized_fit_residual", "sanitized_normalized_fit_residual",
        "raw_normalized_action_residual", "sanitized_normalized_action_residual",
        "raw_relative_tensor_difference", "sanitized_relative_tensor_difference",
        "sanitized_tensor_difference_percent",
        "raw_bianchi", "sanitized_bianchi",
        "rho_relative_peak_error",
        "elapsed_seconds", "elapsed_hours",
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
    print("case,N,v_s,beta_fit,cfit2_outliers,sanitized_action_over_fit,sanitized_tensor_difference_percent,sanitized_bianchi,rho_relative_peak_error,elapsed_hours")
    for r in rows:
        print(
            f"{r['case_dir']},{r['N']},{r['v_s']},{r['beta_fit']},"
            f"{r['cfit2_outlier_count']},{r['sanitized_action_over_fit']},"
            f"{r['sanitized_tensor_difference_percent']},{r['sanitized_bianchi']},"
            f"{r['rho_relative_peak_error']},{r['elapsed_hours']}"
        )


if __name__ == "__main__":
    main()
