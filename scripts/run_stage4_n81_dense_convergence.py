#!/usr/bin/env python3
"""Execute the recovered Stage 4 notebook at N=81 and compare with verified N=61.

This is a controlled resolution run:
- the historical notebook bytes remain untouched;
- the notebook SHA-256 is verified;
- only the in-memory MANUAL_MEMORY_BUDGET_GIB assignment is changed from 28.0 to 220.0;
- N_REQUESTED remains the notebook's original 81;
- all original Stage 4A–4D code cells execute in their original order;
- generated N81 tables are compared descriptively with the verified N61 run.

With only N61 and N81, this script reports resolution trends, not a formal convergence order.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import resource
import sys
import time
import traceback
import zipfile
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLBACKEND", "Agg")

EXPECTED_NOTEBOOK_SHA256 = (
    "1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe"
)
MEMORY_POLICY_OLD = "MANUAL_MEMORY_BUDGET_GIB = 28.0"
MEMORY_POLICY_NEW = "MANUAL_MEMORY_BUDGET_GIB = 220.0"
TARGET_N = 81

TABLES = {
    "stage4A": "stage4_dim4_article_exports/stage4A_dim4_bianchi_validation.csv",
    "stage4B": "stage4_dim4_article_exports/stage4B_dim4_hessian_Q_proxy.csv",
    "stage4C_fit": "stage4_dim4_article_exports/stage4C_dim4_fit_parameters.csv",
    "stage4C_rank": "stage4_dim4_article_exports/stage4C_dim4_candidate_ranking.csv",
    "stage4D": "stage4D_action_Q_comparison_exports/stage4D_action_vs_fitted_Q_summary.csv",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def display_fallback(obj: Any) -> None:
    if hasattr(obj, "to_string"):
        print(obj.to_string())
    else:
        print(obj)


def read_one(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 1:
        raise RuntimeError(f"Expected one row in {path}, found {len(rows)}")
    return rows[0]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def f(row: dict[str, str], name: str) -> float:
    return float(row[name])


def percent_change(new: float, old: float) -> float:
    return 100.0 * (new - old) / abs(old) if old != 0 else math.nan


def metric(
    name: str,
    n61: float,
    n81: float,
    preferred_direction: str,
) -> dict[str, Any]:
    change = percent_change(n81, n61)
    if preferred_direction == "lower":
        trend = "IMPROVED" if n81 < n61 else ("UNCHANGED" if n81 == n61 else "WORSENED")
    elif preferred_direction == "closer_to_one":
        old_distance = abs(n61 - 1.0)
        new_distance = abs(n81 - 1.0)
        trend = (
            "IMPROVED"
            if new_distance < old_distance
            else ("UNCHANGED" if new_distance == old_distance else "WORSENED")
        )
    else:
        trend = "RECORD_ONLY"
    return {
        "metric": name,
        "N61": n61,
        "N81": n81,
        "percent_change": change,
        "preferred_direction": preferred_direction,
        "trend": trend,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--n61-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    repo = args.repo.resolve()
    n61_dir = args.n61_dir.resolve()
    output = args.output_dir.resolve()
    notebook = (
        repo
        / "historical/stages1-5/notebooks/stage4/"
        "Spinelli_Alcubierre_Stage4C_DIM4_memory_optimized.ipynb"
    )

    if not notebook.is_file():
        raise SystemExit(f"Historical notebook not found: {notebook}")
    notebook_sha = sha256_file(notebook)
    if notebook_sha != EXPECTED_NOTEBOOK_SHA256:
        raise SystemExit(
            f"Notebook SHA mismatch: {notebook_sha} != {EXPECTED_NOTEBOOK_SHA256}"
        )

    for relative in TABLES.values():
        if not (n61_dir / relative).is_file():
            raise SystemExit(f"Verified N61 table missing: {n61_dir / relative}")

    output.mkdir(parents=True, exist_ok=True)
    allowed_preexisting = {"stage4_n81_dense_convergence.run.log"}
    unexpected = [p for p in output.iterdir() if p.name not in allowed_preexisting]
    if unexpected:
        raise SystemExit(
            "Output directory contains unexpected files: "
            + ", ".join(sorted(p.name for p in unexpected))
        )

    notebook_data = json.loads(notebook.read_text(encoding="utf-8"))
    code_cell = notebook_data["cells"][3]
    original_source = "".join(code_cell.get("source", []))
    if original_source.count(MEMORY_POLICY_OLD) != 1:
        raise SystemExit("Historical memory-policy assignment was not found exactly once")
    patched_source = original_source.replace(MEMORY_POLICY_OLD, MEMORY_POLICY_NEW, 1)
    code_cell["source"] = patched_source.splitlines(keepends=True)

    metadata: dict[str, Any] = {
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "repo": str(repo),
        "notebook": str(notebook),
        "notebook_sha256": notebook_sha,
        "python": sys.version,
        "target_N": TARGET_N,
        "in_memory_override": {
            "old": MEMORY_POLICY_OLD,
            "new": MEMORY_POLICY_NEW,
            "historical_notebook_modified_on_disk": False,
            "original_cell_sha256": hashlib.sha256(
                original_source.encode("utf-8")
            ).hexdigest(),
            "patched_cell_sha256": hashlib.sha256(
                patched_source.encode("utf-8")
            ).hexdigest(),
        },
        "n61_dir": str(n61_dir),
        "cells": [],
    }

    namespace: dict[str, Any] = {
        "__name__": "__main__",
        "__file__": str(notebook),
        "display": display_fallback,
    }

    previous_cwd = Path.cwd()
    os.chdir(output)
    try:
        for cell_index, cell in enumerate(notebook_data.get("cells", [])):
            if cell.get("cell_type") != "code":
                continue
            source = "".join(cell.get("source", []))
            if not source.strip():
                continue

            print(f"\n===== EXECUTE NOTEBOOK CELL {cell_index:04d} =====", flush=True)
            started = time.time()
            record: dict[str, Any] = {
                "cell_index": cell_index,
                "historical_execution_count": cell.get("execution_count"),
                "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            try:
                exec(
                    compile(source, f"{notebook.name}:cell-{cell_index}", "exec"),
                    namespace,
                    namespace,
                )
                record["status"] = "PASS"
            except Exception:
                record["status"] = "FAIL"
                record["traceback"] = traceback.format_exc()
                raise
            finally:
                record["elapsed_seconds"] = time.time() - started
                record["max_rss_kib"] = resource.getrusage(
                    resource.RUSAGE_SELF
                ).ru_maxrss
                metadata["cells"].append(record)
                try:
                    import matplotlib.pyplot as plt
                    plt.close("all")
                except Exception:
                    pass

            if cell_index == 3:
                selected = {
                    "DIM": int(namespace.get("DIM", -1)),
                    "N": int(namespace.get("N", -1)),
                    "N_REQUESTED": int(namespace.get("N_REQUESTED", -1)),
                    "MANUAL_MEMORY_BUDGET_GIB": float(
                        namespace.get("MANUAL_MEMORY_BUDGET_GIB", math.nan)
                    ),
                    "R_BUBBLE": float(namespace.get("R_BUBBLE", math.nan)),
                    "SIGMA": float(namespace.get("SIGMA", math.nan)),
                    "V_S": float(namespace.get("V_S", math.nan)),
                    "EXTENT": float(namespace.get("EXTENT", math.nan)),
                    "T_EXTENT": float(namespace.get("T_EXTENT", math.nan)),
                    "DELTA_TAU": float(namespace.get("DELTA_TAU", math.nan)),
                    "INTERIOR_CROP": int(namespace.get("INTERIOR_CROP", -1)),
                }
                metadata["selected_configuration"] = selected
                expected = {
                    "DIM": 4,
                    "N": 81,
                    "N_REQUESTED": 81,
                    "MANUAL_MEMORY_BUDGET_GIB": 220.0,
                    "R_BUBBLE": 3.0,
                    "SIGMA": 1.0,
                    "V_S": 0.5,
                    "EXTENT": 5.0,
                    "T_EXTENT": 0.4,
                    "DELTA_TAU": 0.04,
                    "INTERIOR_CROP": 3,
                }
                if selected != expected:
                    raise RuntimeError(
                        f"Controlled N81 configuration mismatch: {selected} != {expected}"
                    )

        n61_a = read_one(n61_dir / TABLES["stage4A"])
        n81_a = read_one(output / TABLES["stage4A"])
        n61_b = read_one(n61_dir / TABLES["stage4B"])
        n81_b = read_one(output / TABLES["stage4B"])
        n61_c = read_one(n61_dir / TABLES["stage4C_fit"])
        n81_c = read_one(output / TABLES["stage4C_fit"])
        n61_d = read_one(n61_dir / TABLES["stage4D"])
        n81_d = read_one(output / TABLES["stage4D"])
        n61_rank = read_rows(n61_dir / TABLES["stage4C_rank"])
        n81_rank = read_rows(output / TABLES["stage4C_rank"])
        n61_best = next(row for row in n61_rank if row["rank"] == "1")
        n81_best = next(row for row in n81_rank if row["rank"] == "1")

        metrics = [
            metric(
                "relative_Bianchi_residual",
                f(n61_a, "relative_Bianchi_residual"),
                f(n81_a, "relative_Bianchi_residual"),
                "lower",
            ),
            metric(
                "rho_relative_peak_error",
                f(n61_a, "rho_relative_peak_error"),
                f(n81_a, "rho_relative_peak_error"),
                "lower",
            ),
            metric(
                "Hessian_Q_normalized_residual",
                f(n61_b, "normalized_Q_conservation_residual"),
                f(n81_b, "normalized_Q_conservation_residual"),
                "lower",
            ),
            metric(
                "HTR_normalized_residual",
                f(n61_best, "normalized_residual"),
                f(n81_best, "normalized_residual"),
                "lower",
            ),
            metric(
                "lambda_fit",
                f(n61_c, "lambda_fit"),
                f(n81_c, "lambda_fit"),
                "record_only",
            ),
            metric(
                "beta_fit",
                f(n61_c, "beta_fit"),
                f(n81_c, "beta_fit"),
                "record_only",
            ),
            metric(
                "action_over_fit",
                f(n61_d, "residual_ratio_action_over_fit"),
                f(n81_d, "residual_ratio_action_over_fit"),
                "closer_to_one",
            ),
            metric(
                "action_fit_tensor_difference_percent",
                f(n61_d, "relative_tensor_difference_percent"),
                f(n81_d, "relative_tensor_difference_percent"),
                "lower",
            ),
        ]

        primary = {
            item["metric"]: item["trend"]
            for item in metrics
        }
        geometry_trend = (
            "IMPROVED"
            if primary["relative_Bianchi_residual"] == "IMPROVED"
            and primary["rho_relative_peak_error"] == "IMPROVED"
            else "MIXED"
        )
        conservation_trend = (
            "IMPROVED"
            if primary["Hessian_Q_normalized_residual"] == "IMPROVED"
            and primary["HTR_normalized_residual"] == "IMPROVED"
            else "MIXED"
        )

        metadata["resolution_metrics"] = metrics
        metadata["interpretation"] = {
            "geometry_trend": geometry_trend,
            "conservation_trend": conservation_trend,
            "formal_convergence_order_available": False,
            "reason": "Only N61 and N81 are currently available in this controlled series.",
        }
        metadata["finished_utc"] = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
        )
        metadata["max_rss_kib"] = resource.getrusage(
            resource.RUSAGE_SELF
        ).ru_maxrss
        metadata["run_status"] = "PASS"

        json_path = output / "stage4_n81_dense_convergence_report.json"
        json_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        csv_path = output / "stage4_n81_resolution_comparison.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=[
                    "metric",
                    "N61",
                    "N81",
                    "percent_change",
                    "preferred_direction",
                    "trend",
                ],
            )
            writer.writeheader()
            writer.writerows(metrics)

        lines = [
            "===== STAGE 4 N81 DENSE RESOLUTION RUN =====",
            f"Notebook: {notebook}",
            f"Notebook SHA256: {notebook_sha}",
            f"Output: {output}",
            "Historical notebook modified on disk: NO",
            f"In-memory override: {MEMORY_POLICY_OLD} -> {MEMORY_POLICY_NEW}",
            f"Selected N: {namespace['N']}",
            "",
            "===== N61 TO N81 METRICS =====",
        ]
        for item in metrics:
            lines.append(
                f"{item['metric']}: N61={item['N61']:.17g} "
                f"N81={item['N81']:.17g} "
                f"change={item['percent_change']:.6g}% "
                f"trend={item['trend']}"
            )
        lines += [
            "",
            f"Geometry trend: {geometry_trend}",
            f"Conservation trend: {conservation_trend}",
            "Formal convergence order: NOT YET AVAILABLE (two resolutions only)",
            "",
            "STAGE4_N81_RUN_RESULT=PASS",
        ]
        txt_path = output / "stage4_n81_dense_convergence_report.txt"
        txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        package = output.parent / f"{output.name}.zip"
        if package.exists():
            package.unlink()
        with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in output.rglob("*"):
                if path.is_file():
                    archive.write(path, path.relative_to(output))

        print("\n".join(lines), flush=True)
        print(f"PACKAGE={package}", flush=True)
        return 0
    finally:
        os.chdir(previous_cwd)


if __name__ == "__main__":
    raise SystemExit(main())
