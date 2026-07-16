#!/usr/bin/env python3
"""Postprocess the N71 DELTA_TAU=0.02/0.04/0.08 sensitivity matrix."""

from __future__ import annotations

import argparse
import csv
import json
import math
import zipfile
from pathlib import Path
from typing import Any

TABLES = {
    "stage4A": "stage4_dim4_article_exports/stage4A_dim4_bianchi_validation.csv",
    "stage4B": "stage4_dim4_article_exports/stage4B_dim4_hessian_Q_proxy.csv",
    "stage4C_fit": "stage4_dim4_article_exports/stage4C_dim4_fit_parameters.csv",
    "stage4C_rank": "stage4_dim4_article_exports/stage4C_dim4_candidate_ranking.csv",
    "stage4D": "stage4D_action_Q_comparison_exports/stage4D_action_vs_fitted_Q_summary.csv",
}

NONNEGATIVE = {
    "relative_Bianchi_residual",
    "rho_relative_peak_error",
    "Hessian_Q_normalized_residual",
    "HTR_normalized_residual",
    "action_fit_tensor_difference_percent",
    "action_residual_penalty_percent",
    "HTR_improvement_over_H",
}

PRINCIPAL = {
    "relative_Bianchi_residual",
    "rho_relative_peak_error",
    "Hessian_Q_normalized_residual",
    "HTR_normalized_residual",
}


def read_one(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 1:
        raise RuntimeError(f"Expected one row in {path}; found {len(rows)}")
    return rows[0]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def f(row: dict[str, str], key: str) -> float:
    return float(row[key])


def extract(base: Path) -> dict[str, float]:
    a = read_one(base / TABLES["stage4A"])
    b = read_one(base / TABLES["stage4B"])
    c = read_one(base / TABLES["stage4C_fit"])
    d = read_one(base / TABLES["stage4D"])
    rank = read_rows(base / TABLES["stage4C_rank"])
    best = next(row for row in rank if row["rank"] == "1")
    return {
        "relative_Bianchi_residual": f(a, "relative_Bianchi_residual"),
        "rho_relative_peak_error": f(a, "rho_relative_peak_error"),
        "Hessian_Q_normalized_residual": f(
            b, "normalized_Q_conservation_residual"
        ),
        "HTR_normalized_residual": f(best, "normalized_residual"),
        "lambda_fit": f(c, "lambda_fit"),
        "beta_fit": f(c, "beta_fit"),
        "action_over_fit": f(d, "residual_ratio_action_over_fit"),
        "action_fit_tensor_difference_percent": f(
            d, "relative_tensor_difference_percent"
        ),
        "action_residual_penalty_percent": f(d, "residual_penalty_percent"),
        "HTR_improvement_over_H": f(c, "improvement_HTR_over_H"),
    }


def rel_change(value: float, reference: float) -> float | None:
    if reference == 0:
        return None
    return 100.0 * (value - reference) / abs(reference)


def dtau_fit(q02: float, q04: float, q08: float, metric: str) -> dict[str, Any]:
    d_fine = q04 - q02
    d_coarse = q08 - q04
    monotonic = (q02 < q04 < q08) or (q02 > q04 > q08)

    result: dict[str, Any] = {
        "monotonic": monotonic,
        "raw_order": None,
        "raw_zero_dtau_estimate": None,
        "accepted_zero_dtau_estimate": None,
        "fit_status": "NOT_AVAILABLE",
    }

    if d_fine == 0 or d_coarse == 0 or d_fine * d_coarse <= 0:
        result["fit_status"] = "NONMONOTONIC_OR_DEGENERATE"
        return result

    ratio = abs(d_coarse / d_fine)
    if ratio <= 0:
        result["fit_status"] = "INVALID_RATIO"
        return result

    order = math.log(ratio, 2.0)
    result["raw_order"] = order

    if order <= 0 or order > 8:
        result["fit_status"] = "IMPLAUSIBLE_ORDER"
        return result

    denominator = 2.0**order - 1.0
    if denominator == 0:
        result["fit_status"] = "SINGULAR_EXTRAPOLATION"
        return result

    estimate = q02 + (q02 - q04) / denominator
    result["raw_zero_dtau_estimate"] = estimate

    if metric in NONNEGATIVE and estimate < 0:
        result["fit_status"] = "REJECTED_NEGATIVE_LIMIT_FOR_NONNEGATIVE_METRIC"
        return result

    result["accepted_zero_dtau_estimate"] = estimate
    result["fit_status"] = "PROVISIONAL_THREE_STEP_EXTRAPOLATION"
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dtau-0p02-dir", required=True, type=Path)
    parser.add_argument("--dtau-0p04-dir", required=True, type=Path)
    parser.add_argument("--dtau-0p08-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    paths = {
        "0.02": args.dtau_0p02_dir.resolve(),
        "0.04": args.dtau_0p04_dir.resolve(),
        "0.08": args.dtau_0p08_dir.resolve(),
    }
    for label, base in paths.items():
        for relative in TABLES.values():
            if not (base / relative).is_file():
                raise SystemExit(f"Missing DELTA_TAU={label} table: {base / relative}")

    values = {label: extract(base) for label, base in paths.items()}
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for metric in values["0.04"]:
        q02 = values["0.02"][metric]
        q04 = values["0.04"][metric]
        q08 = values["0.08"][metric]
        fit = dtau_fit(q02, q04, q08, metric)
        row = {
            "metric": metric,
            "dtau_0p02": q02,
            "dtau_0p04": q04,
            "dtau_0p08": q08,
            "fine_vs_baseline_percent": rel_change(q02, q04),
            "coarse_vs_baseline_percent": rel_change(q08, q04),
            "full_span_percent_of_baseline": (
                100.0 * abs(q08 - q02) / abs(q04) if q04 != 0 else None
            ),
            **fit,
        }
        if metric == "action_over_fit":
            row["fine_vs_baseline_ppm"] = 1e6 * (q02 - q04)
            row["coarse_vs_baseline_ppm"] = 1e6 * (q08 - q04)
        else:
            row["fine_vs_baseline_ppm"] = None
            row["coarse_vs_baseline_ppm"] = None
        rows.append(row)

    row_map = {row["metric"]: row for row in rows}
    principal_fine_max = max(
        abs(row_map[name]["fine_vs_baseline_percent"]) for name in PRINCIPAL
    )
    principal_coarse_max = max(
        abs(row_map[name]["coarse_vs_baseline_percent"]) for name in PRINCIPAL
    )
    coefficient_fine_max = max(
        abs(row_map[name]["fine_vs_baseline_percent"])
        for name in {"lambda_fit", "beta_fit"}
    )
    tensor_fine = abs(
        row_map["action_fit_tensor_difference_percent"]["fine_vs_baseline_percent"]
    )
    action_ppm = abs(row_map["action_over_fit"]["fine_vs_baseline_ppm"])

    if (
        principal_fine_max <= 1.0
        and coefficient_fine_max <= 1.0
        and tensor_fine <= 5.0
        and action_ppm <= 25.0
    ):
        phase2 = "N81_DTAU_0P02_CONFIRMATION_ONLY"
        rationale = (
            "The fine-step N71 changes are small; confirm only DELTA_TAU=0.02 at N81."
        )
    else:
        phase2 = "N81_FULL_DTAU_MATRIX"
        rationale = (
            "At least one fine-step sensitivity threshold was exceeded; run "
            "DELTA_TAU=0.02, 0.04, 0.08 at N81."
        )

    summary = {
        "matrix_status": "PASS",
        "paths": {key: str(value) for key, value in paths.items()},
        "rows": rows,
        "decision_thresholds": {
            "principal_fine_percent_max": 1.0,
            "coefficient_fine_percent_max": 1.0,
            "tensor_fine_percent_max": 5.0,
            "action_fit_absolute_change_ppm_max": 25.0,
        },
        "observed_maxima": {
            "principal_fine_percent_max": principal_fine_max,
            "principal_coarse_percent_max": principal_coarse_max,
            "coefficient_fine_percent_max": coefficient_fine_max,
            "tensor_fine_percent": tensor_fine,
            "action_fit_absolute_change_ppm": action_ppm,
        },
        "phase2_recommendation": phase2,
        "phase2_rationale": rationale,
    }

    json_path = output / "stage4_n71_delta_tau_matrix_report.json"
    csv_path = output / "stage4_n71_delta_tau_matrix_comparison.csv"
    txt_path = output / "stage4_n71_delta_tau_matrix_report.txt"

    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "===== STAGE 4 N71 DELTA_TAU SENSITIVITY MATRIX =====",
        "DELTA_TAU values: 0.02, 0.04, 0.08",
        "",
    ]
    for row in rows:
        lines.append(
            f"{row['metric']}: "
            f"0.02={row['dtau_0p02']:.17g} "
            f"0.04={row['dtau_0p04']:.17g} "
            f"0.08={row['dtau_0p08']:.17g} "
            f"fine_change={row['fine_vs_baseline_percent']}% "
            f"coarse_change={row['coarse_vs_baseline_percent']}% "
            f"raw_order={row['raw_order']} "
            f"fit_status={row['fit_status']}"
        )
    lines += [
        "",
        f"Principal fine-step maximum change: {principal_fine_max:.8g}%",
        f"Principal coarse-step maximum change: {principal_coarse_max:.8g}%",
        f"Coefficient fine-step maximum change: {coefficient_fine_max:.8g}%",
        f"Tensor fine-step change: {tensor_fine:.8g}%",
        f"Action/Fit fine-step absolute change: {action_ppm:.8g} ppm",
        "",
        f"PHASE2_RECOMMENDATION={phase2}",
        f"PHASE2_RATIONALE={rationale}",
        "STAGE4_N71_DELTA_TAU_MATRIX_RESULT=PASS",
    ]
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    package = output.parent / f"{output.name}.zip"
    if package.exists():
        package.unlink()
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in output.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(output))

    print("\n".join(lines))
    print(f"PACKAGE={package}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
