#!/usr/bin/env python3
"""Execute the recovered Stage 4 notebook at N=81, DELTA_TAU=0.02."""

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
OLD_BUDGET = "MANUAL_MEMORY_BUDGET_GIB = 28.0"
NEW_BUDGET = "MANUAL_MEMORY_BUDGET_GIB = 220.0"
OLD_DTAU = "DELTA_TAU = 0.04"
NEW_DTAU = "DELTA_TAU = 0.02"

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
    print(obj.to_string() if hasattr(obj, "to_string") else obj)


def read_one(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 1:
        raise RuntimeError(f"Expected one row in {path}; found {len(rows)}")
    return rows[0]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def value(row: dict[str, str], key: str) -> float:
    return float(row[key])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    repo = args.repo.resolve()
    output = args.output_dir.resolve()
    notebook = (
        repo
        / "historical/stages1-5/notebooks/stage4/"
        "Spinelli_Alcubierre_Stage4C_DIM4_memory_optimized.ipynb"
    )

    if not notebook.is_file():
        raise SystemExit(f"Notebook missing: {notebook}")
    notebook_sha = sha256_file(notebook)
    if notebook_sha != EXPECTED_NOTEBOOK_SHA256:
        raise SystemExit(
            f"Notebook SHA mismatch: {notebook_sha} != {EXPECTED_NOTEBOOK_SHA256}"
        )

    output.mkdir(parents=True, exist_ok=True)
    allowed = {"stage4_n81_dtau_0p02_confirmation.run.log"}
    unexpected = [p.name for p in output.iterdir() if p.name not in allowed]
    if unexpected:
        raise SystemExit(f"Unexpected preexisting output files: {sorted(unexpected)}")

    notebook_data = json.loads(notebook.read_text(encoding="utf-8"))
    source = "".join(notebook_data["cells"][3].get("source", []))
    anchors = {
        OLD_BUDGET: source.count(OLD_BUDGET),
        OLD_DTAU: source.count(OLD_DTAU),
        "N_REQUESTED = 81": source.count("N_REQUESTED = 81"),
    }
    if any(count != 1 for count in anchors.values()):
        raise SystemExit(f"Notebook patch-anchor mismatch: {anchors}")

    patched = (
        source.replace(OLD_BUDGET, NEW_BUDGET, 1)
        .replace(OLD_DTAU, NEW_DTAU, 1)
    )
    notebook_data["cells"][3]["source"] = patched.splitlines(keepends=True)

    metadata: dict[str, Any] = {
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "repo": str(repo),
        "notebook": str(notebook),
        "notebook_sha256": notebook_sha,
        "python": sys.version,
        "target_N": 81,
        "target_delta_tau": 0.02,
        "historical_notebook_modified_on_disk": False,
        "in_memory_overrides": [
            f"{OLD_BUDGET} -> {NEW_BUDGET}",
            f"{OLD_DTAU} -> {NEW_DTAU}",
        ],
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
        for index, cell in enumerate(notebook_data.get("cells", [])):
            if cell.get("cell_type") != "code":
                continue
            code = "".join(cell.get("source", []))
            if not code.strip():
                continue

            print(f"\n===== EXECUTE NOTEBOOK CELL {index:04d} =====", flush=True)
            started = time.time()
            record: dict[str, Any] = {
                "cell_index": index,
                "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            try:
                exec(
                    compile(code, f"{notebook.name}:cell-{index}", "exec"),
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

            if index == 3:
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
                    "DELTA_TAU": 0.02,
                    "INTERIOR_CROP": 3,
                }
                if selected != expected:
                    raise RuntimeError(
                        f"Controlled N81/DELTA_TAU configuration mismatch: "
                        f"{selected} != {expected}"
                    )
                metadata["selected_configuration"] = selected

        a = read_one(output / TABLES["stage4A"])
        b = read_one(output / TABLES["stage4B"])
        c = read_one(output / TABLES["stage4C_fit"])
        d = read_one(output / TABLES["stage4D"])
        ranking = read_rows(output / TABLES["stage4C_rank"])
        best = next(row for row in ranking if row["rank"] == "1")

        metrics = {
            "relative_Bianchi_residual": value(
                a, "relative_Bianchi_residual"
            ),
            "rho_relative_peak_error": value(a, "rho_relative_peak_error"),
            "Hessian_Q_normalized_residual": value(
                b, "normalized_Q_conservation_residual"
            ),
            "HTR_normalized_residual": value(best, "normalized_residual"),
            "lambda_fit": value(c, "lambda_fit"),
            "beta_fit": value(c, "beta_fit"),
            "action_over_fit": value(d, "residual_ratio_action_over_fit"),
            "action_fit_tensor_difference_percent": value(
                d, "relative_tensor_difference_percent"
            ),
            "action_residual_penalty_percent": value(
                d, "residual_penalty_percent"
            ),
            "HTR_improvement_over_H": value(c, "improvement_HTR_over_H"),
        }

        metadata["metrics"] = metrics
        metadata["finished_utc"] = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
        )
        metadata["max_rss_kib"] = resource.getrusage(
            resource.RUSAGE_SELF
        ).ru_maxrss
        metadata["run_status"] = "PASS"

        json_path = output / "stage4_n81_dtau_0p02_case_report.json"
        txt_path = output / "stage4_n81_dtau_0p02_case_report.txt"
        json_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        lines = [
            "===== STAGE 4 N81 DELTA_TAU=0.02 CASE =====",
            f"Notebook SHA256: {notebook_sha}",
            "Historical notebook modified on disk: NO",
            "Selected N: 81",
            "Selected DELTA_TAU: 0.02",
            "",
            "===== METRICS =====",
        ]
        for name, metric_value in metrics.items():
            lines.append(f"{name}: {metric_value:.17g}")
        lines += ["", "STAGE4_N81_DTAU_0P02_CASE_RESULT=PASS"]
        txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("\n".join(lines), flush=True)
        return 0
    finally:
        os.chdir(previous_cwd)


if __name__ == "__main__":
    raise SystemExit(main())
