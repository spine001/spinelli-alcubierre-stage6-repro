#!/usr/bin/env python3
"""Execute one controlled Stage 4 N71 proper-time-step case.

The historical notebook remains unchanged on disk. In memory only:
- MANUAL_MEMORY_BUDGET_GIB: 28.0 -> 160.0
- N_REQUESTED: 81 -> 71
- DELTA_TAU: 0.04 -> requested value
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
OLD_BUDGET = "MANUAL_MEMORY_BUDGET_GIB = 28.0"
NEW_BUDGET = "MANUAL_MEMORY_BUDGET_GIB = 160.0"
OLD_REQUEST = "N_REQUESTED = 81"
NEW_REQUEST = "N_REQUESTED = 71"
OLD_DTAU = "DELTA_TAU = 0.04"
ALLOWED_DTAU = {0.02, 0.04, 0.08}

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


def f(row: dict[str, str], key: str) -> float:
    return float(row[key])


def tag(value: float) -> str:
    return f"{value:.2f}".replace(".", "p")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--delta-tau", required=True, type=float)
    args = parser.parse_args()

    delta_tau = round(args.delta_tau, 10)
    if delta_tau not in ALLOWED_DTAU:
        raise SystemExit(
            f"Unsupported DELTA_TAU={delta_tau}; allowed values: {sorted(ALLOWED_DTAU)}"
        )

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
    log_name = f"stage4_n71_dtau_{tag(delta_tau)}.run.log"
    allowed_preexisting = {log_name}
    unexpected = [p.name for p in output.iterdir() if p.name not in allowed_preexisting]
    if unexpected:
        raise SystemExit(f"Unexpected preexisting output files: {sorted(unexpected)}")

    notebook_data = json.loads(notebook.read_text(encoding="utf-8"))
    policy_source = "".join(notebook_data["cells"][3].get("source", []))

    anchors = {
        OLD_BUDGET: policy_source.count(OLD_BUDGET),
        OLD_REQUEST: policy_source.count(OLD_REQUEST),
        OLD_DTAU: policy_source.count(OLD_DTAU),
    }
    if any(count != 1 for count in anchors.values()):
        raise SystemExit(f"Notebook patch-anchor mismatch: {anchors}")

    new_dtau = f"DELTA_TAU = {delta_tau:.2f}"
    patched_source = (
        policy_source
        .replace(OLD_BUDGET, NEW_BUDGET, 1)
        .replace(OLD_REQUEST, NEW_REQUEST, 1)
        .replace(OLD_DTAU, new_dtau, 1)
    )
    notebook_data["cells"][3]["source"] = patched_source.splitlines(keepends=True)

    metadata: dict[str, Any] = {
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "repo": str(repo),
        "notebook": str(notebook),
        "notebook_sha256": notebook_sha,
        "python": sys.version,
        "target_N": 71,
        "target_delta_tau": delta_tau,
        "historical_notebook_modified_on_disk": False,
        "in_memory_overrides": [
            f"{OLD_BUDGET} -> {NEW_BUDGET}",
            f"{OLD_REQUEST} -> {NEW_REQUEST}",
            f"{OLD_DTAU} -> {new_dtau}",
        ],
        "cells": [],
    }

    namespace: dict[str, Any] = {
        "__name__": "__main__",
        "__file__": str(notebook),
        "display": display_fallback,
    }

    old_cwd = Path.cwd()
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
                expected = {
                    "DIM": 4,
                    "N": 71,
                    "N_REQUESTED": 71,
                    "MANUAL_MEMORY_BUDGET_GIB": 160.0,
                    "R_BUBBLE": 3.0,
                    "SIGMA": 1.0,
                    "V_S": 0.5,
                    "EXTENT": 5.0,
                    "T_EXTENT": 0.4,
                    "DELTA_TAU": delta_tau,
                    "INTERIOR_CROP": 3,
                }
                if selected != expected:
                    raise RuntimeError(
                        f"Controlled configuration mismatch: {selected} != {expected}"
                    )
                metadata["selected_configuration"] = selected

        a = read_one(output / TABLES["stage4A"])
        b = read_one(output / TABLES["stage4B"])
        c = read_one(output / TABLES["stage4C_fit"])
        d = read_one(output / TABLES["stage4D"])
        ranks = read_rows(output / TABLES["stage4C_rank"])
        best = next(row for row in ranks if row["rank"] == "1")

        metrics = {
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

        metadata["metrics"] = metrics
        metadata["finished_utc"] = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
        )
        metadata["max_rss_kib"] = resource.getrusage(
            resource.RUSAGE_SELF
        ).ru_maxrss
        metadata["run_status"] = "PASS"

        stem = f"stage4_n71_dtau_{tag(delta_tau)}"
        json_path = output / f"{stem}_report.json"
        txt_path = output / f"{stem}_report.txt"
        json_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        lines = [
            f"===== STAGE 4 N71 DELTA_TAU={delta_tau:.2f} =====",
            f"Notebook SHA256: {notebook_sha}",
            "Historical notebook modified on disk: NO",
            f"Selected N: {selected['N']}",
            f"Selected DELTA_TAU: {selected['DELTA_TAU']}",
            "",
            "===== METRICS =====",
        ]
        for name, value in metrics.items():
            lines.append(f"{name}: {value:.17g}")
        lines += [
            "",
            f"STAGE4_N71_DTAU_{tag(delta_tau).upper()}_RESULT=PASS",
        ]
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
        os.chdir(old_cwd)


if __name__ == "__main__":
    raise SystemExit(main())
