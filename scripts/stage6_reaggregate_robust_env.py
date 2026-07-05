#!/usr/bin/env python3

from pathlib import Path
import os
import json
import csv
import math
from collections import defaultdict

REPO = Path("/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro")
RUNBASE = Path(os.environ.get("STAGE6_RUNBASE", str(REPO / "results" / "stage6D_alcubierre_highres_latest"))).resolve()

OUT_CSV = RUNBASE / "stage6_robust_reaggregate.csv"
OUT_JSON = RUNBASE / "stage6_robust_reaggregate.json"

SUM_KEYS = ["n", "Cfit2", "Cact2", "Qfit2", "Qact2", "D2", "G2", "divG2", "qpos_sum", "rho_abs_sum"]
MAJOR_KEYS = ["Cfit2", "Cact2", "Qfit2", "Qact2"]
ABS_HUGE = 1.0e20
QPOS_HUGE = 1.0e20


def load_json(path):
    return json.loads(path.read_text(errors="ignore"))


def finite_float(x):
    try:
        y = float(x)
        return y if math.isfinite(y) else None
    except Exception:
        return None


def safe_sqrt(x):
    if x < 0 or not math.isfinite(x):
        return float("nan")
    return math.sqrt(x)


def safe_ratio(a, b):
    if b == 0 or not math.isfinite(a) or not math.isfinite(b):
        return float("nan")
    return a / b


def classify_tile(score):
    """
    Empty/noncontributing score tiles are not corrupt.
    A tile is corrupt only if it contributes points or major norms and has impossible values.
    """
    n = finite_float(score.get("n"))
    major_vals = {k: finite_float(score.get(k)) for k in MAJOR_KEYS}
    d2 = finite_float(score.get("D2"))
    g2 = finite_float(score.get("G2"))
    divg2 = finite_float(score.get("divG2"))
    qpos = finite_float(score.get("qpos_sum"))

    has_any_contribution = False

    if n is not None and n > 0:
        has_any_contribution = True

    for v in list(major_vals.values()) + [d2, g2, divg2, qpos]:
        if v is not None and abs(v) > 0:
            has_any_contribution = True

    if not has_any_contribution:
        return "empty", []

    reasons = []

    if n is None:
        reasons.append("n missing/nonfinite on contributing tile")
    elif n < 0:
        reasons.append("n negative")

    for k, v in major_vals.items():
        if v is None:
            reasons.append(f"{k} missing/nonfinite on contributing tile")
        elif v < 0:
            reasons.append(f"{k} negative")
        elif v > ABS_HUGE:
            reasons.append(f"{k}>{ABS_HUGE:g}")

    if qpos is not None and abs(qpos) > QPOS_HUGE:
        reasons.append(f"qpos_sum>{QPOS_HUGE:g}")

    return ("corrupt" if reasons else "valid"), reasons


def reaggregate_case(case_dir):
    summary = load_json(case_dir / "case_summary.json")

    totals_raw = defaultdict(float)
    totals_clean = defaultdict(float)

    score_files = sorted((case_dir / "tiles").glob("*.score.json"))

    empty_count = 0
    valid_count = 0
    corrupt_tiles = []

    for p in score_files:
        score = load_json(p)
        classification, reasons = classify_tile(score)

        if classification == "empty":
            empty_count += 1
            continue

        if classification == "valid":
            valid_count += 1
        else:
            corrupt_tiles.append({
                "file": p.name,
                "reasons": ";".join(reasons),
                "n": score.get("n"),
                "Cfit2": score.get("Cfit2"),
                "Cact2": score.get("Cact2"),
                "Qfit2": score.get("Qfit2"),
                "Qact2": score.get("Qact2"),
                "D2": score.get("D2"),
                "G2": score.get("G2"),
                "divG2": score.get("divG2"),
                "qpos_sum": score.get("qpos_sum"),
            })

        for key in SUM_KEYS:
            val = finite_float(score.get(key))
            if val is not None:
                totals_raw[key] += val
                if classification == "valid":
                    totals_clean[key] += val

    n = totals_clean["n"]

    sqrt_Cfit2 = safe_sqrt(totals_clean["Cfit2"])
    sqrt_Cact2 = safe_sqrt(totals_clean["Cact2"])
    sqrt_Qfit2 = safe_sqrt(totals_clean["Qfit2"])
    sqrt_Qact2 = safe_sqrt(totals_clean["Qact2"])
    sqrt_D2 = safe_sqrt(totals_clean["D2"])
    sqrt_G2 = safe_sqrt(totals_clean["G2"])
    sqrt_divG2 = safe_sqrt(totals_clean["divG2"])

    return {
        "case_dir": case_dir.name,
        "N": summary.get("N"),
        "v_s": summary.get("v_s"),
        "lambda_fit": summary.get("lambda_fit"),
        "beta_fit": summary.get("beta_fit"),
        "mask_points_raw": summary.get("mask_points"),
        "mask_points_robust": int(n),
        "score_json_files": len(score_files),
        "valid_score_tiles": valid_count,
        "empty_score_tiles": empty_count,
        "corrupt_contributing_tiles": len(corrupt_tiles),
        "corrupt_tile_files": ";".join(x["file"] for x in corrupt_tiles),
        "corrupt_tile_reasons": " | ".join(f"{x['file']}:{x['reasons']}" for x in corrupt_tiles),
        "excluded_contributing_points": int(totals_raw["n"] - totals_clean["n"]),
        "excluded_contributing_fraction": (totals_raw["n"] - totals_clean["n"]) / totals_raw["n"] if totals_raw["n"] else 0.0,
        "raw_fit_residual": summary.get("fit_residual"),
        "robust_fit_residual": safe_sqrt(totals_clean["Cfit2"] / n) if n else float("nan"),
        "raw_action_residual": summary.get("action_residual"),
        "robust_action_residual": safe_sqrt(totals_clean["Cact2"] / n) if n else float("nan"),
        "raw_action_over_fit": summary.get("action_over_fit"),
        "robust_action_over_fit": safe_ratio(sqrt_Cact2, sqrt_Cfit2),
        "raw_normalized_fit_residual": summary.get("normalized_fit_residual"),
        "robust_normalized_fit_residual": safe_ratio(sqrt_Cfit2, sqrt_Qfit2),
        "raw_normalized_action_residual": summary.get("normalized_action_residual"),
        "robust_normalized_action_residual": safe_ratio(sqrt_Cact2, sqrt_Qact2),
        "raw_relative_tensor_difference": summary.get("relative_tensor_difference"),
        "robust_relative_tensor_difference": safe_ratio(sqrt_D2, sqrt_Qfit2),
        "robust_tensor_difference_percent": 100.0 * safe_ratio(sqrt_D2, sqrt_Qfit2),
        "raw_bianchi": summary.get("bianchi"),
        "robust_bianchi": safe_ratio(sqrt_divG2, sqrt_G2),
        "rho_relative_peak_error": summary.get("rho_relative_peak_error"),
        "elapsed_seconds": summary.get("elapsed_seconds"),
        "elapsed_hours": float(summary.get("elapsed_seconds", 0.0)) / 3600.0,
        "raw_total_Cfit2": totals_raw["Cfit2"],
        "robust_total_Cfit2": totals_clean["Cfit2"],
        "raw_total_Cact2": totals_raw["Cact2"],
        "robust_total_Cact2": totals_clean["Cact2"],
        "raw_total_Qfit2": totals_raw["Qfit2"],
        "robust_total_Qfit2": totals_clean["Qfit2"],
        "raw_total_Qact2": totals_raw["Qact2"],
        "robust_total_Qact2": totals_clean["Qact2"],
        "robust_total_D2": totals_clean["D2"],
        "robust_total_G2": totals_clean["G2"],
        "robust_total_divG2": totals_clean["divG2"],
        "corrupt_tile_details": corrupt_tiles,
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
        "mask_points_raw", "mask_points_robust",
        "score_json_files", "valid_score_tiles", "empty_score_tiles",
        "corrupt_contributing_tiles", "corrupt_tile_files", "corrupt_tile_reasons",
        "excluded_contributing_points", "excluded_contributing_fraction",
        "raw_fit_residual", "robust_fit_residual",
        "raw_action_residual", "robust_action_residual",
        "raw_action_over_fit", "robust_action_over_fit",
        "raw_normalized_fit_residual", "robust_normalized_fit_residual",
        "raw_normalized_action_residual", "robust_normalized_action_residual",
        "raw_relative_tensor_difference", "robust_relative_tensor_difference",
        "robust_tensor_difference_percent",
        "raw_bianchi", "robust_bianchi",
        "rho_relative_peak_error",
        "elapsed_seconds", "elapsed_hours",
        "raw_total_Cfit2", "robust_total_Cfit2",
        "raw_total_Cact2", "robust_total_Cact2",
        "raw_total_Qfit2", "robust_total_Qfit2",
        "raw_total_Qact2", "robust_total_Qact2",
        "robust_total_D2", "robust_total_G2", "robust_total_divG2",
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
    print("case,N,v_s,beta_fit,corrupt_contributing_tiles,excluded_points,excluded_fraction,robust_action_over_fit,robust_tensor_difference_percent,robust_bianchi,rho_relative_peak_error")
    for r in rows:
        print(
            f"{r['case_dir']},{r['N']},{r['v_s']},{r['beta_fit']},"
            f"{r['corrupt_contributing_tiles']},{r['excluded_contributing_points']},"
            f"{r['excluded_contributing_fraction']},"
            f"{r['robust_action_over_fit']},{r['robust_tensor_difference_percent']},"
            f"{r['robust_bianchi']},{r['rho_relative_peak_error']}"
        )


if __name__ == "__main__":
    main()
