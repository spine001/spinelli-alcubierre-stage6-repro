#!/usr/bin/env python3

from pathlib import Path
import json
import csv
import math
import shutil
from collections import defaultdict

REPO = Path("/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro")
RUNBASE = (REPO / "results" / "stage6D_alcubierre_highres_latest").resolve()
OUTDIR = RUNBASE / "diagnostics_N241_residuals"

CASES = [
    "N241_v0p5_sigma4_R3",
    "N241_v1_sigma4_R3",
]

HUGE_THRESHOLD = 1.0e12


def load_json(path):
    try:
        return json.loads(path.read_text(errors="ignore"))
    except Exception as e:
        return {"__read_error__": str(e)}


def flatten(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            yield from flatten(v, key)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            key = f"{prefix}[{i}]"
            yield from flatten(v, key)
    elif isinstance(obj, bool):
        return
    elif isinstance(obj, (int, float)):
        yield prefix, float(obj)


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def scan_kind(case_dir, case_out, kind):
    files = sorted((case_dir / "tiles").glob(f"*.{kind}.json"))

    stats = {}
    huge = []
    nonfinite = []
    top_abs = []

    for i, p in enumerate(files, 1):
        data = load_json(p)

        for key, value in flatten(data):
            rec = stats.setdefault(
                key,
                {
                    "key": key,
                    "n": 0,
                    "sum": 0.0,
                    "sum_abs": 0.0,
                    "min": value,
                    "max": value,
                    "max_abs": abs(value),
                    "max_abs_file": str(p),
                    "max_abs_value": value,
                },
            )

            rec["n"] += 1

            if math.isfinite(value):
                rec["sum"] += value
                rec["sum_abs"] += abs(value)
                rec["min"] = min(rec["min"], value)
                rec["max"] = max(rec["max"], value)

                av = abs(value)
                if av > rec["max_abs"]:
                    rec["max_abs"] = av
                    rec["max_abs_file"] = str(p)
                    rec["max_abs_value"] = value

                if av >= HUGE_THRESHOLD:
                    huge.append(
                        {
                            "file": str(p),
                            "key": key,
                            "value": repr(value),
                            "abs_value": repr(av),
                        }
                    )

                top_abs.append((av, str(p), key, value))
            else:
                nonfinite.append(
                    {
                        "file": str(p),
                        "key": key,
                        "value": repr(value),
                    }
                )

    summary_rows = []
    for rec in stats.values():
        n = rec["n"]
        rec["mean"] = rec["sum"] / n if n else ""
        summary_rows.append(rec)

    summary_rows.sort(key=lambda r: r["max_abs"], reverse=True)

    write_csv(
        case_out / f"{kind}_numeric_key_summary.csv",
        summary_rows,
        [
            "key",
            "n",
            "sum",
            "sum_abs",
            "mean",
            "min",
            "max",
            "max_abs",
            "max_abs_value",
            "max_abs_file",
        ],
    )

    write_csv(
        case_out / f"{kind}_huge_values.csv",
        huge,
        ["file", "key", "value", "abs_value"],
    )

    write_csv(
        case_out / f"{kind}_nonfinite_values.csv",
        nonfinite,
        ["file", "key", "value"],
    )

    top_abs.sort(reverse=True, key=lambda x: x[0])
    top_rows = [
        {
            "rank": j + 1,
            "abs_value": repr(av),
            "file": f,
            "key": k,
            "value": repr(v),
        }
        for j, (av, f, k, v) in enumerate(top_abs[:200])
    ]

    write_csv(
        case_out / f"{kind}_top_abs_values.csv",
        top_rows,
        ["rank", "abs_value", "file", "key", "value"],
    )

    # Preserve the actual offending tile JSONs, but only a small unique set.
    offending_dir = case_out / f"{kind}_offending_tile_jsons"
    offending_dir.mkdir(parents=True, exist_ok=True)

    copied = set()
    for row in huge[:50]:
        src = Path(row["file"])
        if src.exists() and src not in copied:
            shutil.copy2(src, offending_dir / src.name)
            copied.add(src)

    return {
        "kind": kind,
        "file_count": len(files),
        "huge_count": len(huge),
        "nonfinite_count": len(nonfinite),
        "top_keys": summary_rows[:20],
    }


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)

    console_lines = []
    console_lines.append(f"RUNBASE={RUNBASE}")
    console_lines.append(f"OUTDIR={OUTDIR}")
    console_lines.append("")

    for case in CASES:
        case_dir = RUNBASE / case
        case_out = OUTDIR / case
        case_out.mkdir(parents=True, exist_ok=True)

        console_lines.append("=" * 100)
        console_lines.append(f"CASE: {case}")
        console_lines.append("=" * 100)

        for fname in ["case_summary.json", "fit_parameters.json", "status.json"]:
            src = case_dir / fname
            if src.exists():
                shutil.copy2(src, case_out / fname)
                console_lines.append(f"Copied {src}")

        summary = load_json(case_dir / "case_summary.json")
        console_lines.append("")
        console_lines.append("Case summary key diagnostics:")
        for k in [
            "lambda_fit",
            "beta_fit",
            "fit_residual",
            "action_residual",
            "fit_Q_L2",
            "action_Q_L2",
            "normalized_fit_residual",
            "normalized_action_residual",
            "action_over_fit",
            "relative_tensor_difference",
            "bianchi",
            "rho_relative_peak_error",
            "mask_points",
            "elapsed_seconds",
        ]:
            console_lines.append(f"  {k}: {summary.get(k)}")

        for kind in ["fit", "score"]:
            result = scan_kind(case_dir, case_out, kind)
            console_lines.append("")
            console_lines.append(
                f"{kind}.json files: {result['file_count']}; "
                f"huge values >= {HUGE_THRESHOLD:g}: {result['huge_count']}; "
                f"nonfinite: {result['nonfinite_count']}"
            )
            console_lines.append(f"Top numeric keys by max_abs for {kind}:")
            for row in result["top_keys"][:12]:
                console_lines.append(
                    f"  key={row['key']} max_abs={row['max_abs']:.6e} "
                    f"value={row['max_abs_value']:.6e} file={Path(row['max_abs_file']).name}"
                )

        console_lines.append("")

    report = "\n".join(console_lines)
    (OUTDIR / "diagnostic_report.txt").write_text(report)
    print(report)
    print("")
    print(f"Diagnostic files written to: {OUTDIR}")


if __name__ == "__main__":
    main()

