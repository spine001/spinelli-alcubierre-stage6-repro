#!/usr/bin/env python3
"""Evaluate N61/N81 optimized regression and authorize or reject N91."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_time_log(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")

    def number(pattern: str) -> int | None:
        match = re.search(pattern, text)
        return int(match.group(1)) if match else None

    return {
        "maximum_resident_set_size_kib": number(
            r"Maximum resident set size \(kbytes\):\s*(\d+)"
        ),
        "swaps": number(r"Swaps:\s*(\d+)"),
        "exit_status": number(r"Exit status:\s*(\d+)"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n61-dir", required=True, type=Path)
    parser.add_argument("--n81-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    n61_dir = args.n61_dir.resolve()
    n81_dir = args.n81_dir.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)

    n61 = read_json(n61_dir / "stage4_streaming_N61_report.json")
    n81 = read_json(n81_dir / "stage4_streaming_N81_report.json")
    n61_time = parse_time_log(
        n61_dir / "stage4_streaming_N61.run.log"
    )
    n81_time = parse_time_log(
        n81_dir / "stage4_streaming_N81.run.log"
    )

    baseline_n61_kib = 59516844
    baseline_n81_kib = 185580896

    optimized_n61_kib = int(n61["max_rss_kib"])
    optimized_n81_kib = int(n81["max_rss_kib"])

    n61_reduction = 100.0 * (
        baseline_n61_kib - optimized_n61_kib
    ) / baseline_n61_kib
    n81_reduction = 100.0 * (
        baseline_n81_kib - optimized_n81_kib
    ) / baseline_n81_kib

    optimized_n81_gib = optimized_n81_kib / 1048576
    projected_n91_gib = optimized_n81_gib * (91 / 81) ** 4
    projected_n101_gib = optimized_n81_gib * (101 / 81) ** 4

    regression_pass = (
        n61.get("run_status") == "PASS"
        and n81.get("run_status") == "PASS"
    )
    process_pass = (
        n61_time["exit_status"] == 0
        and n81_time["exit_status"] == 0
        and n61_time["swaps"] == 0
        and n81_time["swaps"] == 0
    )
    n91_memory_pass = projected_n91_gib <= 190.0

    if regression_pass and process_pass and n91_memory_pass:
        recommendation = "BUILD_N91_OPTIMIZED_RUNNER"
        rationale = (
            "Both canonical regressions passed without swap and the "
            "optimized N81 peak projects N91 below 190 GiB."
        )
    else:
        recommendation = "FURTHER_OPTIMIZE_BEFORE_N91"
        rationale = (
            "Regression, process, or N91 physical-memory safety gate failed."
        )

    if projected_n101_gib <= 210.0:
        n101_outlook = "POTENTIALLY_FEASIBLE_AFTER_MEASURED_N91"
    else:
        n101_outlook = "REQUIRES_FURTHER_OPTIMIZATION_OR_MORE_RAM"

    summary = {
        "validation_status": (
            "PASS"
            if regression_pass and process_pass
            else "FAIL"
        ),
        "baseline_peak_rss_kib": {
            "N61": baseline_n61_kib,
            "N81": baseline_n81_kib,
        },
        "optimized_peak_rss_kib": {
            "N61": optimized_n61_kib,
            "N81": optimized_n81_kib,
        },
        "memory_reduction_percent": {
            "N61": n61_reduction,
            "N81": n81_reduction,
        },
        "projected_peak_rss_gib": {
            "N91": projected_n91_gib,
            "N101": projected_n101_gib,
        },
        "time_logs": {
            "N61": n61_time,
            "N81": n81_time,
        },
        "gates": {
            "regression_pass": regression_pass,
            "process_exit_and_swap_pass": process_pass,
            "N91_projected_peak_at_most_190_gib": n91_memory_pass,
        },
        "phase4_recommendation": recommendation,
        "phase4_rationale": rationale,
        "N101_outlook": n101_outlook,
    }

    json_path = (
        output
        / "stage4_memory_optimization_validation_report.json"
    )
    txt_path = (
        output
        / "stage4_memory_optimization_validation_report.txt"
    )
    csv_path = (
        output
        / "stage4_memory_optimization_validation_summary.csv"
    )

    json_path.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    rows = [
        {
            "N": 61,
            "baseline_peak_rss_gib": baseline_n61_kib / 1048576,
            "optimized_peak_rss_gib": optimized_n61_kib / 1048576,
            "reduction_percent": n61_reduction,
        },
        {
            "N": 81,
            "baseline_peak_rss_gib": baseline_n81_kib / 1048576,
            "optimized_peak_rss_gib": optimized_n81_kib / 1048576,
            "reduction_percent": n81_reduction,
        },
    ]
    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=list(rows[0].keys()),
        )
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "===== STAGE 4 MEMORY OPTIMIZATION VALIDATION =====",
        (
            f"N61: baseline={baseline_n61_kib/1048576:.6f} GiB "
            f"optimized={optimized_n61_kib/1048576:.6f} GiB "
            f"reduction={n61_reduction:.6f}%"
        ),
        (
            f"N81: baseline={baseline_n81_kib/1048576:.6f} GiB "
            f"optimized={optimized_n81_kib/1048576:.6f} GiB "
            f"reduction={n81_reduction:.6f}%"
        ),
        f"Projected N91 peak: {projected_n91_gib:.6f} GiB",
        f"Projected N101 peak: {projected_n101_gib:.6f} GiB",
        f"N101_OUTLOOK={n101_outlook}",
        "",
        f"PHASE4_RECOMMENDATION={recommendation}",
        f"PHASE4_RATIONALE={rationale}",
        (
            "STAGE4_MEMORY_OPTIMIZATION_VALIDATION_RESULT="
            f"{summary['validation_status']}"
        ),
    ]
    txt_path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    print("\n".join(lines))
    return 0 if summary["validation_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
