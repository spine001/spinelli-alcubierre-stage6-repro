#!/usr/bin/env python3
"""Compare N71 and N81 DELTA_TAU=0.02 versus 0.04 and decide Phase 3."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

TABLES = {
    "stage4A": "stage4_dim4_article_exports/stage4A_dim4_bianchi_validation.csv",
    "stage4B": "stage4_dim4_article_exports/stage4B_dim4_hessian_Q_proxy.csv",
    "stage4C_fit": "stage4_dim4_article_exports/stage4C_dim4_fit_parameters.csv",
    "stage4C_rank": "stage4_dim4_article_exports/stage4C_dim4_candidate_ranking.csv",
    "stage4D": "stage4D_action_Q_comparison_exports/stage4D_action_vs_fitted_Q_summary.csv",
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
    ranks = read_rows(base / TABLES["stage4C_rank"])
    best = next(row for row in ranks if row["rank"] == "1")
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
        "action_residual_penalty_percent": f(
            d, "residual_penalty_percent"
        ),
        "HTR_improvement_over_H": f(c, "improvement_HTR_over_H"),
    }


def percent_change(new: float, reference: float) -> float | None:
    if reference == 0:
        return None
    return 100.0 * (new - reference) / abs(reference)


def ratio(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return abs(numerator) / abs(denominator)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n71-dtau-0p02-dir", required=True, type=Path)
    parser.add_argument("--n71-dtau-0p04-dir", required=True, type=Path)
    parser.add_argument("--n81-dtau-0p02-dir", required=True, type=Path)
    parser.add_argument("--n81-dtau-0p04-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    directories = {
        "N71_dtau_0p02": args.n71_dtau_0p02_dir.resolve(),
        "N71_dtau_0p04": args.n71_dtau_0p04_dir.resolve(),
        "N81_dtau_0p02": args.n81_dtau_0p02_dir.resolve(),
        "N81_dtau_0p04": args.n81_dtau_0p04_dir.resolve(),
    }

    for label, directory in directories.items():
        for relative in TABLES.values():
            if not (directory / relative).is_file():
                raise SystemExit(
                    f"Missing required table for {label}: {directory / relative}"
                )

    values = {label: extract(path) for label, path in directories.items()}
    rows: list[dict[str, Any]] = []

    for metric in values["N81_dtau_0p04"]:
        n71_02 = values["N71_dtau_0p02"][metric]
        n71_04 = values["N71_dtau_0p04"][metric]
        n81_02 = values["N81_dtau_0p02"][metric]
        n81_04 = values["N81_dtau_0p04"][metric]

        dtau_effect_n71 = n71_02 - n71_04
        dtau_effect_n81 = n81_02 - n81_04
        spatial_effect_04 = n81_04 - n71_04
        spatial_effect_02 = n81_02 - n71_02

        rows.append({
            "metric": metric,
            "N71_dtau_0p02": n71_02,
            "N71_dtau_0p04": n71_04,
            "N81_dtau_0p02": n81_02,
            "N81_dtau_0p04": n81_04,
            "N71_fine_vs_baseline_percent": percent_change(n71_02, n71_04),
            "N81_fine_vs_baseline_percent": percent_change(n81_02, n81_04),
            "N71_dtau_absolute_effect": dtau_effect_n71,
            "N81_dtau_absolute_effect": dtau_effect_n81,
            "spatial_N71_to_N81_at_0p04_percent": percent_change(n81_04, n71_04),
            "spatial_N71_to_N81_at_0p02_percent": percent_change(n81_02, n71_02),
            "N81_dtau_to_spatial_effect_ratio": ratio(
                dtau_effect_n81, spatial_effect_04
            ),
            "dtau_effect_amplification_N81_over_N71": ratio(
                dtau_effect_n81, dtau_effect_n71
            ),
        })

    row_map = {row["metric"]: row for row in rows}
    principal_max = max(
        abs(row_map[name]["N81_fine_vs_baseline_percent"])
        for name in PRINCIPAL
    )
    coefficient_max = max(
        abs(row_map[name]["N81_fine_vs_baseline_percent"])
        for name in {"lambda_fit", "beta_fit"}
    )
    tensor_change = abs(
        row_map["action_fit_tensor_difference_percent"][
            "N81_fine_vs_baseline_percent"
        ]
    )
    action_ppm = abs(
        1e6
        * (
            row_map["action_over_fit"]["N81_dtau_0p02"]
            - row_map["action_over_fit"]["N81_dtau_0p04"]
        )
    )
    principal_dtau_to_spatial_max = max(
        row_map[name]["N81_dtau_to_spatial_effect_ratio"] or 0.0
        for name in PRINCIPAL
    )

    thresholds = {
        "principal_fine_percent_max": 1.0,
        "coefficient_fine_percent_max": 1.0,
        "tensor_fine_percent_max": 5.0,
        "action_fit_absolute_change_ppm_max": 25.0,
        "principal_dtau_to_spatial_effect_ratio_max": 0.10,
    }

    passed = (
        principal_max <= thresholds["principal_fine_percent_max"]
        and coefficient_max <= thresholds["coefficient_fine_percent_max"]
        and tensor_change <= thresholds["tensor_fine_percent_max"]
        and action_ppm <= thresholds["action_fit_absolute_change_ppm_max"]
        and principal_dtau_to_spatial_max
        <= thresholds["principal_dtau_to_spatial_effect_ratio_max"]
    )

    if passed:
        recommendation = "BEGIN_MEMORY_OPTIMIZATION_FOR_N91"
        rationale = (
            "N81 fine-step sensitivity is small and remains subordinate to the "
            "N71-to-N81 spatial-resolution effect."
        )
    else:
        recommendation = "RUN_N81_DTAU_0P08_BEFORE_MEMORY_OPTIMIZATION"
        rationale = (
            "At least one N81 sensitivity or scale-separation threshold was exceeded."
        )

    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)

    summary = {
        "confirmation_status": "PASS",
        "directories": {key: str(value) for key, value in directories.items()},
        "rows": rows,
        "thresholds": thresholds,
        "observed_maxima": {
            "principal_fine_percent_max": principal_max,
            "coefficient_fine_percent_max": coefficient_max,
            "tensor_fine_percent": tensor_change,
            "action_fit_absolute_change_ppm": action_ppm,
            "principal_dtau_to_spatial_effect_ratio_max": (
                principal_dtau_to_spatial_max
            ),
        },
        "phase3_recommendation": recommendation,
        "phase3_rationale": rationale,
    }

    json_path = output / "stage4_n81_dtau_confirmation_report.json"
    csv_path = output / "stage4_n81_dtau_confirmation_comparison.csv"
    txt_path = output / "stage4_n81_dtau_confirmation_report.txt"

    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "===== STAGE 4 N81 DELTA_TAU=0.02 CONFIRMATION =====",
        "",
    ]
    for row in rows:
        lines.append(
            f"{row['metric']}: "
            f"N71_0.02={row['N71_dtau_0p02']:.17g} "
            f"N71_0.04={row['N71_dtau_0p04']:.17g} "
            f"N81_0.02={row['N81_dtau_0p02']:.17g} "
            f"N81_0.04={row['N81_dtau_0p04']:.17g} "
            f"N81_fine_change={row['N81_fine_vs_baseline_percent']}% "
            f"dtau_to_spatial={row['N81_dtau_to_spatial_effect_ratio']}"
        )
    lines += [
        "",
        f"N81 principal fine-step maximum change: {principal_max:.9g}%",
        f"N81 coefficient fine-step maximum change: {coefficient_max:.9g}%",
        f"N81 tensor fine-step change: {tensor_change:.9g}%",
        f"N81 Action/Fit absolute change: {action_ppm:.9g} ppm",
        (
            "Maximum principal DELTA_TAU/spatial effect ratio: "
            f"{principal_dtau_to_spatial_max:.9g}"
        ),
        "",
        f"PHASE3_RECOMMENDATION={recommendation}",
        f"PHASE3_RATIONALE={rationale}",
        "STAGE4_N81_DELTA_TAU_CONFIRMATION_RESULT=PASS",
    ]
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
