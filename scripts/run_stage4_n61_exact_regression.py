#!/usr/bin/env python3
"""Run the original committed Stage 4 notebook code as a terminal regression.

The script:
1. verifies the historical notebook SHA-256;
2. executes every code cell in order with a noninteractive Matplotlib backend;
3. requires the notebook's original memory policy to select DIM=4, N=61;
4. compares generated Stage 4A–4D canonical tables with the recovered tables;
5. writes auditable JSON, CSV, and text comparison reports.

It does not modify the historical directory.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import resource
import shutil
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

TABLE_MAP = {
    "stage4A_dim4_bianchi_validation.csv": (
        "stage4_dim4_article_exports/stage4A_dim4_bianchi_validation.csv",
        "historical/stages1-5/results/stage4/stage4A-C/primary_tables/"
        "stage4A_dim4_bianchi_validation.csv",
    ),
    "stage4B_dim4_hessian_Q_proxy.csv": (
        "stage4_dim4_article_exports/stage4B_dim4_hessian_Q_proxy.csv",
        "historical/stages1-5/results/stage4/stage4A-C/primary_tables/"
        "stage4B_dim4_hessian_Q_proxy.csv",
    ),
    "stage4C_dim4_candidate_ranking.csv": (
        "stage4_dim4_article_exports/stage4C_dim4_candidate_ranking.csv",
        "historical/stages1-5/results/stage4/stage4A-C/primary_tables/"
        "stage4C_dim4_candidate_ranking.csv",
    ),
    "stage4C_dim4_fit_parameters.csv": (
        "stage4_dim4_article_exports/stage4C_dim4_fit_parameters.csv",
        "historical/stages1-5/results/stage4/stage4A-C/primary_tables/"
        "stage4C_dim4_fit_parameters.csv",
    ),
    "stage4D_action_vs_fitted_Q_comparison.csv": (
        "stage4D_action_Q_comparison_exports/"
        "stage4D_action_vs_fitted_Q_comparison.csv",
        "historical/stages1-5/results/stage4/stage4D/primary_tables/"
        "stage4D_action_vs_fitted_Q_comparison.csv",
    ),
    "stage4D_action_vs_fitted_Q_summary.csv": (
        "stage4D_action_Q_comparison_exports/"
        "stage4D_action_vs_fitted_Q_summary.csv",
        "historical/stages1-5/results/stage4/stage4D/primary_tables/"
        "stage4D_action_vs_fitted_Q_summary.csv",
    ),
}

RTOL = 1.0e-8
ATOL = 1.0e-10


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def display_fallback(obj: Any) -> None:
    if hasattr(obj, "to_string"):
        print(obj.to_string())
    else:
        print(obj)


def numeric(value: str) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result


def compare_csv(generated: Path, historical: Path) -> dict[str, Any]:
    with generated.open(newline="", encoding="utf-8-sig") as f:
        grows = list(csv.DictReader(f))
    with historical.open(newline="", encoding="utf-8-sig") as f:
        hrows = list(csv.DictReader(f))

    result: dict[str, Any] = {
        "generated": str(generated),
        "historical": str(historical),
        "generated_rows": len(grows),
        "historical_rows": len(hrows),
        "status": "PASS",
        "differences": [],
        "max_abs_difference": 0.0,
        "max_relative_difference": 0.0,
    }

    if len(grows) != len(hrows):
        result["status"] = "FAIL"
        result["differences"].append(
            f"row count differs: generated={len(grows)} historical={len(hrows)}"
        )
        return result

    if set(grows[0].keys() if grows else []) != set(hrows[0].keys() if hrows else []):
        result["status"] = "FAIL"
        result["differences"].append("column sets differ")
        result["generated_columns"] = list(grows[0].keys() if grows else [])
        result["historical_columns"] = list(hrows[0].keys() if hrows else [])
        return result

    # Preserve canonical row order. The notebook and historical tables use the same order.
    for ridx, (grow, hrow) in enumerate(zip(grows, hrows), 1):
        for col in grow:
            gv = grow[col]
            hv = hrow[col]
            gn = numeric(gv)
            hn = numeric(hv)

            if gn is not None and hn is not None:
                if math.isnan(gn) and math.isnan(hn):
                    continue
                absdiff = abs(gn - hn)
                denom = max(abs(hn), ATOL)
                reldiff = absdiff / denom
                result["max_abs_difference"] = max(
                    result["max_abs_difference"], absdiff
                )
                result["max_relative_difference"] = max(
                    result["max_relative_difference"], reldiff
                )
                if not math.isclose(gn, hn, rel_tol=RTOL, abs_tol=ATOL):
                    result["status"] = "FAIL"
                    result["differences"].append(
                        f"row {ridx} column {col}: generated={gn:.17g} "
                        f"historical={hn:.17g} absdiff={absdiff:.6g} "
                        f"reldiff={reldiff:.6g}"
                    )
            elif gv != hv:
                result["status"] = "FAIL"
                result["differences"].append(
                    f"row {ridx} column {col}: generated={gv!r} historical={hv!r}"
                )

    return result


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
        raise SystemExit(f"Historical notebook not found: {notebook}")

    actual_sha = sha256_file(notebook)
    if actual_sha != EXPECTED_NOTEBOOK_SHA256:
        raise SystemExit(
            f"Notebook SHA mismatch: {actual_sha} != {EXPECTED_NOTEBOOK_SHA256}"
        )

    output.mkdir(parents=True, exist_ok=True)

    allowed_preexisting = {
        "stage4_n61_exact_regression.run.log",
    }
    unexpected_existing = [
        item for item in output.iterdir()
        if item.name not in allowed_preexisting
    ]

    if unexpected_existing:
        names = ", ".join(sorted(item.name for item in unexpected_existing))
        raise SystemExit(
            f"Output directory contains unexpected files: {output}: {names}"
        )

    run_metadata: dict[str, Any] = {
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "repo": str(repo),
        "notebook": str(notebook),
        "notebook_sha256": actual_sha,
        "python": sys.version,
        "rtol": RTOL,
        "atol": ATOL,
        "cells": [],
    }

    nb = json.loads(notebook.read_text(encoding="utf-8"))
    namespace: dict[str, Any] = {
        "__name__": "__main__",
        "__file__": str(notebook),
        "display": display_fallback,
    }

    old_cwd = Path.cwd()
    os.chdir(output)
    try:
        for cell_index, cell in enumerate(nb.get("cells", [])):
            if cell.get("cell_type") != "code":
                continue
            source = "".join(cell.get("source", []))
            if not source.strip():
                continue

            print(f"\n===== EXECUTE NOTEBOOK CELL {cell_index:04d} =====", flush=True)
            started = time.time()
            cell_record: dict[str, Any] = {
                "cell_index": cell_index,
                "execution_count_historical": cell.get("execution_count"),
                "started_utc": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                ),
            }
            try:
                exec(
                    compile(source, f"{notebook.name}:cell-{cell_index}", "exec"),
                    namespace,
                    namespace,
                )
                cell_record["status"] = "PASS"
            except Exception:
                cell_record["status"] = "FAIL"
                cell_record["traceback"] = traceback.format_exc()
                run_metadata["cells"].append(cell_record)
                raise
            finally:
                cell_record["elapsed_seconds"] = time.time() - started
                cell_record["max_rss_kib"] = resource.getrusage(
                    resource.RUSAGE_SELF
                ).ru_maxrss
                run_metadata["cells"].append(cell_record)
                try:
                    import matplotlib.pyplot as plt
                    plt.close("all")
                except Exception:
                    pass

            if cell_index == 3:
                selected_n = int(namespace.get("N", -1))
                selected_dim = int(namespace.get("DIM", -1))
                config = {
                    "DIM": selected_dim,
                    "N": selected_n,
                    "R_BUBBLE": namespace.get("R_BUBBLE"),
                    "SIGMA": namespace.get("SIGMA"),
                    "V_S": namespace.get("V_S"),
                    "EXTENT": namespace.get("EXTENT"),
                    "T_EXTENT": namespace.get("T_EXTENT"),
                    "DELTA_TAU": namespace.get("DELTA_TAU"),
                    "INTERIOR_CROP": namespace.get("INTERIOR_CROP"),
                }
                run_metadata["selected_configuration"] = config
                expected = {
                    "DIM": 4,
                    "N": 61,
                    "R_BUBBLE": 3.0,
                    "SIGMA": 1.0,
                    "V_S": 0.5,
                    "EXTENT": 5.0,
                    "T_EXTENT": 0.4,
                    "DELTA_TAU": 0.04,
                    "INTERIOR_CROP": 3,
                }
                if config != expected:
                    raise RuntimeError(
                        f"Historical configuration mismatch: {config} != {expected}"
                    )

        comparisons = []
        for label, (generated_rel, historical_rel) in TABLE_MAP.items():
            generated = output / generated_rel
            historical = repo / historical_rel
            if not generated.is_file():
                comparisons.append(
                    {
                        "table": label,
                        "status": "FAIL",
                        "differences": [f"generated table missing: {generated}"],
                    }
                )
                continue
            if not historical.is_file():
                comparisons.append(
                    {
                        "table": label,
                        "status": "FAIL",
                        "differences": [f"historical table missing: {historical}"],
                    }
                )
                continue
            item = compare_csv(generated, historical)
            item["table"] = label
            comparisons.append(item)

        overall = (
            "PASS"
            if comparisons and all(x.get("status") == "PASS" for x in comparisons)
            else "FAIL"
        )
        run_metadata["comparisons"] = comparisons
        run_metadata["overall_regression_status"] = overall
        run_metadata["finished_utc"] = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
        )
        run_metadata["max_rss_kib"] = resource.getrusage(
            resource.RUSAGE_SELF
        ).ru_maxrss

        json_path = output / "stage4_n61_exact_regression_report.json"
        json_path.write_text(
            json.dumps(run_metadata, indent=2, default=str), encoding="utf-8"
        )

        csv_path = output / "stage4_n61_exact_regression_comparison.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "table",
                    "status",
                    "generated_rows",
                    "historical_rows",
                    "max_abs_difference",
                    "max_relative_difference",
                    "difference_count",
                ],
            )
            writer.writeheader()
            for item in comparisons:
                writer.writerow(
                    {
                        "table": item.get("table"),
                        "status": item.get("status"),
                        "generated_rows": item.get("generated_rows"),
                        "historical_rows": item.get("historical_rows"),
                        "max_abs_difference": item.get("max_abs_difference"),
                        "max_relative_difference": item.get(
                            "max_relative_difference"
                        ),
                        "difference_count": len(item.get("differences", [])),
                    }
                )

        txt_lines = [
            "===== STAGE 4 N61 EXACT TERMINAL REGRESSION =====",
            f"Notebook: {notebook}",
            f"Notebook SHA256: {actual_sha}",
            f"Output: {output}",
            f"Overall regression status: {overall}",
            "",
        ]
        for item in comparisons:
            txt_lines.append(
                f"{item.get('table')}: {item.get('status')} "
                f"max_abs={item.get('max_abs_difference')} "
                f"max_rel={item.get('max_relative_difference')} "
                f"differences={len(item.get('differences', []))}"
            )
            for diff in item.get("differences", [])[:20]:
                txt_lines.append(f"  {diff}")
        txt_lines.append("")
        txt_lines.append(f"STAGE4_N61_REGRESSION_RESULT={overall}")

        txt_path = output / "stage4_n61_exact_regression_report.txt"
        txt_path.write_text("\n".join(txt_lines) + "\n", encoding="utf-8")

        zip_path = output.parent / f"{output.name}.zip"
        if zip_path.exists():
            zip_path.unlink()
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in output.rglob("*"):
                if path.is_file():
                    zf.write(path, path.relative_to(output))

        print("\n".join(txt_lines), flush=True)
        print(f"PACKAGE={zip_path}", flush=True)
        return 0 if overall == "PASS" else 1

    finally:
        os.chdir(old_cwd)


if __name__ == "__main__":
    raise SystemExit(main())
