#!/usr/bin/env python3
"""Postprocess optimized N91 into a four-grid Stage 4 analysis."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np

TABLES = {
    "stage4A": (
        "stage4_dim4_article_exports/"
        "stage4A_dim4_bianchi_validation.csv"
    ),
    "stage4B": (
        "stage4_dim4_article_exports/"
        "stage4B_dim4_hessian_Q_proxy.csv"
    ),
    "stage4C_fit": (
        "stage4_dim4_article_exports/"
        "stage4C_dim4_fit_parameters.csv"
    ),
    "stage4C_rank": (
        "stage4_dim4_article_exports/"
        "stage4C_dim4_candidate_ranking.csv"
    ),
    "stage4D": (
        "stage4D_action_Q_comparison_exports/"
        "stage4D_action_vs_fitted_Q_summary.csv"
    ),
}

PRINCIPAL = [
    "relative_Bianchi_residual",
    "rho_relative_peak_error",
    "Hessian_Q_normalized_residual",
    "HTR_normalized_residual",
]


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
    ranking = read_rows(base / TABLES["stage4C_rank"])
    best = next(row for row in ranking if row["rank"] == "1")

    return {
        "relative_Bianchi_residual": f(
            a, "relative_Bianchi_residual"
        ),
        "rho_relative_peak_error": f(
            a, "rho_relative_peak_error"
        ),
        "Hessian_Q_normalized_residual": f(
            b, "normalized_Q_conservation_residual"
        ),
        "HTR_normalized_residual": f(
            best, "normalized_residual"
        ),
        "lambda_fit": f(c, "lambda_fit"),
        "beta_fit": f(c, "beta_fit"),
        "action_over_fit": f(
            d, "residual_ratio_action_over_fit"
        ),
        "action_fit_tensor_difference_percent": f(
            d, "relative_tensor_difference_percent"
        ),
        "action_residual_penalty_percent": f(
            d, "residual_penalty_percent"
        ),
        "HTR_improvement_over_H": f(
            c, "improvement_HTR_over_H"
        ),
    }


def pairwise_order(
    coarse: float,
    fine: float,
    h_coarse: float,
    h_fine: float,
) -> float | None:
    if coarse <= 0 or fine <= 0:
        return None
    return math.log(coarse / fine) / math.log(h_coarse / h_fine)


def percent_change(new: float, reference: float) -> float | None:
    if reference == 0:
        return None
    return 100.0 * (new - reference) / abs(reference)


def parse_time_log(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")

    def integer(pattern: str) -> int | None:
        match = re.search(pattern, text)
        return int(match.group(1)) if match else None

    elapsed_match = re.search(
        r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\):\s*(\S+)",
        text,
    )
    elapsed_seconds = None
    if elapsed_match:
        parts = elapsed_match.group(1).split(":")
        if len(parts) == 2:
            elapsed_seconds = float(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            elapsed_seconds = (
                float(parts[0]) * 3600
                + float(parts[1]) * 60
                + float(parts[2])
            )

    return {
        "maximum_resident_set_size_kib": integer(
            r"Maximum resident set size \(kbytes\):\s*(\d+)"
        ),
        "swaps": integer(r"Swaps:\s*(\d+)"),
        "exit_status": integer(r"Exit status:\s*(\d+)"),
        "elapsed_seconds": elapsed_seconds,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n61-dir", required=True, type=Path)
    parser.add_argument("--n71-dir", required=True, type=Path)
    parser.add_argument("--n81-dir", required=True, type=Path)
    parser.add_argument("--n91-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    grids = {
        61: args.n61_dir.resolve(),
        71: args.n71_dir.resolve(),
        81: args.n81_dir.resolve(),
        91: args.n91_dir.resolve(),
    }
    values = {n: extract(path) for n, path in grids.items()}
    h = {n: 10.0 / (n - 1) for n in grids}

    metric_rows: list[dict[str, Any]] = []
    for metric in values[61]:
        orders = {}
        for coarse, fine in [(61, 71), (71, 81), (81, 91)]:
            orders[(coarse, fine)] = pairwise_order(
                values[coarse][metric],
                values[fine][metric],
                h[coarse],
                h[fine],
            )

        descriptive_log_slope = None
        if metric in PRINCIPAL and all(values[n][metric] > 0 for n in grids):
            descriptive_log_slope = float(
                np.polyfit(
                    np.log([h[n] for n in grids]),
                    np.log([values[n][metric] for n in grids]),
                    1,
                )[0]
            )

        metric_rows.append({
            "metric": metric,
            "N61": values[61][metric],
            "N71": values[71][metric],
            "N81": values[81][metric],
            "N91": values[91][metric],
            "N91_vs_N81_percent": percent_change(
                values[91][metric],
                values[81][metric],
            ),
            "order_N61_N71": orders[(61, 71)],
            "order_N71_N81": orders[(71, 81)],
            "order_N81_N91": orders[(81, 91)],
            "descriptive_four_grid_log_slope": descriptive_log_slope,
        })

    row_map = {row["metric"]: row for row in metric_rows}
    principal_monotonic = all(
        values[61][metric]
        > values[71][metric]
        > values[81][metric]
        > values[91][metric]
        for metric in PRINCIPAL
    )

    n91_report = json.loads(
        (args.n91_dir / "stage4_n91_optimized_report.json").read_text(
            encoding="utf-8"
        )
    )
    time_data = parse_time_log(
        args.n91_dir / "stage4_n91_optimized.run.log"
    )

    actual_peak_kib = int(n91_report["max_rss_kib"])
    actual_peak_gib = actual_peak_kib / 1048576
    projected_n91_gib = 147.67466083915258
    projected_runtime_seconds = 414.04589477349526

    memory_projection_error_percent = (
        100.0
        * (actual_peak_gib - projected_n91_gib)
        / projected_n91_gib
    )
    runtime_projection_error_percent = None
    if time_data["elapsed_seconds"] is not None:
        runtime_projection_error_percent = (
            100.0
            * (
                time_data["elapsed_seconds"]
                - projected_runtime_seconds
            )
            / projected_runtime_seconds
        )

    projected_n101_gib = actual_peak_gib * (101 / 91) ** 4

    process_pass = (
        time_data["exit_status"] == 0
        and time_data["swaps"] == 0
        and n91_report.get("run_status") == "PASS"
        and all(
            cell.get("status") == "PASS"
            for cell in n91_report.get("cells", [])
        )
    )

    if not principal_monotonic:
        recommendation = (
            "INVESTIGATE_N91_SPATIAL_TREND_BEFORE_N101"
        )
        rationale = (
            "At least one principal residual did not continue its "
            "monotonic N61-to-N91 decrease."
        )
    elif process_pass and projected_n101_gib <= 205.0:
        recommendation = "BUILD_N101_OPTIMIZED_RUNNER"
        rationale = (
            "N91 passed without swap, spatial trends remained valid, "
            "and measured N91 projects N101 at or below 205 GiB."
        )
    else:
        recommendation = "FURTHER_OPTIMIZE_BEFORE_N101"
        rationale = (
            "N91 passed, but the measured N91 peak does not provide "
            "the required physical-memory margin for N101."
        )

    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)

    summary = {
        "analysis_status": "PASS" if process_pass else "FAIL",
        "principal_spatial_monotonic_N61_to_N91": principal_monotonic,
        "metric_rows": metric_rows,
        "resource": {
            "projected_N91_peak_gib": projected_n91_gib,
            "measured_N91_peak_gib": actual_peak_gib,
            "N91_memory_projection_error_percent": (
                memory_projection_error_percent
            ),
            "projected_N91_runtime_seconds": projected_runtime_seconds,
            "measured_N91_runtime_seconds": time_data["elapsed_seconds"],
            "N91_runtime_projection_error_percent": (
                runtime_projection_error_percent
            ),
            "projected_N101_peak_from_measured_N91_gib": (
                projected_n101_gib
            ),
            "swaps": time_data["swaps"],
            "exit_status": time_data["exit_status"],
        },
        "phase5_recommendation": recommendation,
        "phase5_rationale": rationale,
    }

    json_path = output / "stage4_n91_four_grid_report.json"
    txt_path = output / "stage4_n91_four_grid_report.txt"
    csv_path = output / "stage4_n91_four_grid_metrics.csv"
    resource_csv = output / "stage4_n91_resource_validation.csv"

    json_path.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=list(metric_rows[0].keys()),
        )
        writer.writeheader()
        writer.writerows(metric_rows)

    with resource_csv.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as stream:
        row = {
            "projected_N91_peak_gib": projected_n91_gib,
            "measured_N91_peak_gib": actual_peak_gib,
            "memory_projection_error_percent": (
                memory_projection_error_percent
            ),
            "projected_N91_runtime_seconds": projected_runtime_seconds,
            "measured_N91_runtime_seconds": time_data["elapsed_seconds"],
            "runtime_projection_error_percent": (
                runtime_projection_error_percent
            ),
            "projected_N101_peak_gib": projected_n101_gib,
            "swaps": time_data["swaps"],
            "exit_status": time_data["exit_status"],
        }
        writer = csv.DictWriter(stream, fieldnames=list(row.keys()))
        writer.writeheader()
        writer.writerow(row)

    lines = [
        "===== STAGE 4 N91 FOUR-GRID ANALYSIS =====",
        f"Principal spatial monotonicity: {principal_monotonic}",
        "",
        "===== PRINCIPAL METRICS =====",
    ]
    for metric in PRINCIPAL:
        row = row_map[metric]
        lines.append(
            f"{metric}: "
            f"N61={row['N61']:.17g} "
            f"N71={row['N71']:.17g} "
            f"N81={row['N81']:.17g} "
            f"N91={row['N91']:.17g} "
            f"p81_91={row['order_N81_N91']}"
        )

    lines += [
        "",
        "===== RESOURCES =====",
        f"Projected N91 peak: {projected_n91_gib:.6f} GiB",
        f"Measured N91 peak: {actual_peak_gib:.6f} GiB",
        (
            "N91 memory projection error: "
            f"{memory_projection_error_percent:.6f}%"
        ),
        (
            "Measured N91 runtime: "
            f"{time_data['elapsed_seconds']} seconds"
        ),
        (
            "Projected N101 peak from measured N91: "
            f"{projected_n101_gib:.6f} GiB"
        ),
        f"Swaps: {time_data['swaps']}",
        f"Exit status: {time_data['exit_status']}",
        "",
        f"PHASE5_RECOMMENDATION={recommendation}",
        f"PHASE5_RATIONALE={rationale}",
        (
            "STAGE4_N91_OPTIMIZED_ANALYSIS_RESULT="
            f"{summary['analysis_status']}"
        ),
    ]
    txt_path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    print("\n".join(lines))
    return 0 if summary["analysis_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
