#!/usr/bin/env python3
"""Analyze N61/N71/N81/N91/N101/N111 and recommend N121."""

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
GRIDS = [61, 71, 81, 91, 101, 111]
PRINCIPAL = [
    "relative_Bianchi_residual",
    "rho_relative_peak_error",
    "Hessian_Q_normalized_residual",
    "HTR_normalized_residual",
]


def one(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 1:
        raise RuntimeError(
            f"Expected one row in {path}; found {len(rows)}"
        )
    return rows[0]


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def extract(base: Path) -> dict[str, float]:
    stage4a = one(base / TABLES["stage4A"])
    stage4b = one(base / TABLES["stage4B"])
    stage4c = one(base / TABLES["stage4C_fit"])
    stage4d = one(base / TABLES["stage4D"])
    best = next(
        row
        for row in rows(base / TABLES["stage4C_rank"])
        if row["rank"] == "1"
    )
    return {
        "relative_Bianchi_residual": float(
            stage4a["relative_Bianchi_residual"]
        ),
        "rho_relative_peak_error": float(
            stage4a["rho_relative_peak_error"]
        ),
        "Hessian_Q_normalized_residual": float(
            stage4b["normalized_Q_conservation_residual"]
        ),
        "HTR_normalized_residual": float(
            best["normalized_residual"]
        ),
        "lambda_fit": float(stage4c["lambda_fit"]),
        "beta_fit": float(stage4c["beta_fit"]),
        "action_over_fit": float(
            stage4d["residual_ratio_action_over_fit"]
        ),
        "action_fit_tensor_difference_percent": float(
            stage4d["relative_tensor_difference_percent"]
        ),
        "action_residual_penalty_percent": float(
            stage4d["residual_penalty_percent"]
        ),
        "HTR_improvement_over_H": float(
            stage4c["improvement_HTR_over_H"]
        ),
    }


def effective_order(
    coarse: float,
    fine: float,
    h_coarse: float,
    h_fine: float,
) -> float | None:
    if coarse <= 0 or fine <= 0:
        return None
    return math.log(coarse / fine) / math.log(h_coarse / h_fine)


def parse_time(path: Path) -> dict[str, Any]:
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
        elapsed_seconds = sum(
            float(value) * 60 ** index
            for index, value in enumerate(reversed(parts))
        )

    return {
        "maximum_resident_set_size_kib": integer(
            r"Maximum resident set size \(kbytes\):\s*(\d+)"
        ),
        "swaps": integer(r"Swaps:\s*(\d+)"),
        "exit_status": integer(r"Exit status:\s*(\d+)"),
        "elapsed_seconds": elapsed_seconds,
        "major_page_faults": integer(
            r"Major \(requiring I/O\) page faults:\s*(\d+)"
        ),
    }


def read_samples(path: Path) -> dict[str, Any]:
    with path.open(newline="", encoding="utf-8") as stream:
        raw = list(csv.DictReader(stream))

    records: list[dict[str, int | str]] = []
    for row in raw:
        try:
            record = {
                "pid": int(row["pid"]),
                "comm": row["comm"],
                "vmrss_kib": int(row["vmrss_kib"]),
                "vmswap_kib": int(row["vmswap_kib"]),
                "vmsize_kib": int(row["vmsize_kib"]),
                "vmhwm_kib": int(row["vmhwm_kib"]),
                "vmpeak_kib": int(row["vmpeak_kib"]),
                "majflt": int(row["majflt"]),
                "memavailable_kib": int(row["memavailable_kib"]),
                "system_swap_used_kib": int(
                    row["system_swap_used_kib"]
                ),
                "pswpin_pages": int(row["pswpin_pages"]),
                "pswpout_pages": int(row["pswpout_pages"]),
            }
        except (KeyError, ValueError):
            continue
        records.append(record)

    def maximum(key: str) -> int:
        return max(
            (int(record[key]) for record in records),
            default=0,
        )

    def minimum(key: str) -> int:
        return min(
            (int(record[key]) for record in records),
            default=0,
        )

    max_combined = max(
        (
            int(record["vmrss_kib"])
            + int(record["vmswap_kib"])
            for record in records
        ),
        default=0,
    )
    pswpin_delta = 0
    pswpout_delta = 0
    if records:
        pswpin_delta = (
            int(records[-1]["pswpin_pages"])
            - int(records[0]["pswpin_pages"])
        )
        pswpout_delta = (
            int(records[-1]["pswpout_pages"])
            - int(records[0]["pswpout_pages"])
        )

    return {
        "sample_count": len(records),
        "distinct_python_pids": sorted(
            {int(record["pid"]) for record in records}
        ),
        "process_names": sorted(
            {str(record["comm"]) for record in records}
        ),
        "max_vmrss_gib": maximum("vmrss_kib") / 1048576,
        "max_vmswap_gib": maximum("vmswap_kib") / 1048576,
        "max_vmrss_plus_vmswap_gib": max_combined / 1048576,
        "max_vmsize_gib": maximum("vmsize_kib") / 1048576,
        "max_vmhwm_gib": maximum("vmhwm_kib") / 1048576,
        "max_vmpeak_gib": maximum("vmpeak_kib") / 1048576,
        "max_process_major_faults": maximum("majflt"),
        "min_memavailable_gib": (
            minimum("memavailable_kib") / 1048576
        ),
        "max_system_swap_used_gib": (
            maximum("system_swap_used_kib") / 1048576
        ),
        "pswpin_delta_pages": pswpin_delta,
        "pswpout_delta_pages": pswpout_delta,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    for grid in GRIDS:
        parser.add_argument(
            f"--n{grid}-dir",
            required=True,
            type=Path,
        )
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    directories = {
        grid: getattr(args, f"n{grid}_dir").resolve()
        for grid in GRIDS
    }
    values = {
        grid: extract(directory)
        for grid, directory in directories.items()
    }
    spacings = {
        grid: 10.0 / (grid - 1)
        for grid in GRIDS
    }

    pairs = list(zip(GRIDS[:-1], GRIDS[1:]))
    metric_rows: list[dict[str, Any]] = []
    for metric in values[GRIDS[0]]:
        row: dict[str, Any] = {"metric": metric}
        for grid in GRIDS:
            row[f"N{grid}"] = values[grid][metric]
        for coarse, fine in pairs:
            row[f"order_N{coarse}_N{fine}"] = effective_order(
                values[coarse][metric],
                values[fine][metric],
                spacings[coarse],
                spacings[fine],
            )
        row["descriptive_six_grid_log_slope"] = (
            float(
                np.polyfit(
                    np.log([spacings[grid] for grid in GRIDS]),
                    np.log([values[grid][metric] for grid in GRIDS]),
                    1,
                )[0]
            )
            if (
                metric in PRINCIPAL
                and all(values[grid][metric] > 0 for grid in GRIDS)
            )
            else None
        )
        metric_rows.append(row)

    principal_monotonic = all(
        all(
            values[coarse][metric]
            > values[fine][metric]
            for coarse, fine in pairs
        )
        for metric in PRINCIPAL
    )

    n111_dir = directories[111]
    n111_report = json.loads(
        (
            n111_dir
            / "stage4_n111_optimized_swap_enabled_report.json"
        ).read_text(encoding="utf-8")
    )
    timing = parse_time(
        n111_dir
        / "stage4_n111_optimized_swap_enabled.run.log"
    )
    samples = read_samples(
        n111_dir / "stage4_n111_resource_samples.csv"
    )

    process_pass = (
        n111_report.get("run_status") == "PASS"
        and timing["exit_status"] == 0
        and all(
            cell.get("status") == "PASS"
            for cell in n111_report.get("cells", [])
        )
    )
    sampler_pass = (
        samples["sample_count"] > 0
        and len(samples["distinct_python_pids"]) == 1
        and all(
            str(name).startswith("python")
            for name in samples["process_names"]
        )
        and samples["max_vmrss_gib"] > 1.0
    )

    time_peak_gib = n111_report["max_rss_kib"] / 1048576
    sampled_footprint_gib = samples[
        "max_vmrss_plus_vmswap_gib"
    ]
    projection_basis_gib = max(
        time_peak_gib,
        sampled_footprint_gib,
    )
    projected_n121_gib = (
        projection_basis_gib * (121 / 111) ** 4
    )

    if not process_pass:
        recommendation = "REPAIR_N111_EXECUTION_BEFORE_N121"
        rationale = "N111 did not complete cleanly."
    elif not principal_monotonic:
        recommendation = (
            "INVESTIGATE_N111_SPATIAL_TREND_BEFORE_N121"
        )
        rationale = (
            "At least one principal residual did not continue "
            "its monotonic decrease."
        )
    else:
        recommendation = "BUILD_N121_SWAP_ENABLED_RUNNER"
        rationale = (
            "N111 passed and the principal six-grid trends "
            "remain monotonic; paging remains an accepted resource."
        )

    summary = {
        "analysis_status": "PASS" if process_pass else "FAIL",
        "principal_spatial_monotonic_N61_to_N111": (
            principal_monotonic
        ),
        "resource_sampler_status": (
            "PASS" if sampler_pass else "WARN"
        ),
        "metric_rows": metric_rows,
        "resource": {
            "time_max_rss_gib": time_peak_gib,
            "measured_runtime_seconds": timing["elapsed_seconds"],
            "time_swaps": timing["swaps"],
            "time_major_page_faults": timing[
                "major_page_faults"
            ],
            "exit_status": timing["exit_status"],
            "resource_samples": samples,
            "projection_basis_gib": projection_basis_gib,
            "projected_N121_peak_from_measured_N111_gib": (
                projected_n121_gib
            ),
        },
        "phase7_recommendation": recommendation,
        "phase7_rationale": rationale,
        "execution_policy": "SWAP_ALLOWED_AND_MEASURED",
    }

    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)

    (
        output / "stage4_n111_six_grid_report.json"
    ).write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    with (
        output / "stage4_n111_six_grid_metrics.csv"
    ).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=list(metric_rows[0].keys()),
        )
        writer.writeheader()
        writer.writerows(metric_rows)

    resource_row = {
        "time_max_rss_gib": time_peak_gib,
        "sampled_max_vmrss_gib": samples["max_vmrss_gib"],
        "sampled_max_vmswap_gib": samples["max_vmswap_gib"],
        "sampled_max_vmrss_plus_vmswap_gib": (
            samples["max_vmrss_plus_vmswap_gib"]
        ),
        "sampled_max_vmsize_gib": samples["max_vmsize_gib"],
        "sampled_max_vmhwm_gib": samples["max_vmhwm_gib"],
        "sampled_max_vmpeak_gib": samples["max_vmpeak_gib"],
        "min_memavailable_gib": samples[
            "min_memavailable_gib"
        ],
        "max_system_swap_used_gib": samples[
            "max_system_swap_used_gib"
        ],
        "pswpin_delta_pages": samples["pswpin_delta_pages"],
        "pswpout_delta_pages": samples["pswpout_delta_pages"],
        "time_major_page_faults": timing["major_page_faults"],
        "sampled_max_process_major_faults": samples[
            "max_process_major_faults"
        ],
        "measured_runtime_seconds": timing["elapsed_seconds"],
        "projected_N121_peak_gib": projected_n121_gib,
    }
    with (
        output / "stage4_n111_resource_validation.csv"
    ).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=list(resource_row.keys()),
        )
        writer.writeheader()
        writer.writerow(resource_row)

    lines = [
        "===== STAGE 4 N111 SIX-GRID ANALYSIS =====",
        (
            "Principal spatial monotonicity: "
            f"{principal_monotonic}"
        ),
        f"Resource sampler status: {summary['resource_sampler_status']}",
        f"Time max RSS: {time_peak_gib:.6f} GiB",
        (
            "Sampled max process VmSwap: "
            f"{samples['max_vmswap_gib']:.6f} GiB"
        ),
        (
            "Sampled max RSS+swap: "
            f"{samples['max_vmrss_plus_vmswap_gib']:.6f} GiB"
        ),
        (
            "Maximum sampled system swap used: "
            f"{samples['max_system_swap_used_gib']:.6f} GiB"
        ),
        (
            "Kernel pswpin delta pages: "
            f"{samples['pswpin_delta_pages']}"
        ),
        (
            "Kernel pswpout delta pages: "
            f"{samples['pswpout_delta_pages']}"
        ),
        (
            "Measured runtime: "
            f"{timing['elapsed_seconds']} seconds"
        ),
        (
            "Projected N121 peak: "
            f"{projected_n121_gib:.6f} GiB"
        ),
        f"PHASE7_RECOMMENDATION={recommendation}",
        f"PHASE7_RATIONALE={rationale}",
        (
            "STAGE4_N111_SIX_GRID_ANALYSIS_RESULT="
            f"{summary['analysis_status']}"
        ),
    ]
    (
        output / "stage4_n111_six_grid_report.txt"
    ).write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    print("\n".join(lines))
    return 0 if process_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
