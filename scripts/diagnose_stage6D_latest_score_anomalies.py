#!/usr/bin/env python3

from pathlib import Path
import json
import csv
import math
import shutil
from collections import defaultdict

REPO = Path("/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro")
RUNBASE = (REPO / "results" / "stage6D_alcubierre_highres_latest").resolve()
OUTDIR = RUNBASE / "diagnostics_score_anomalies_latest"

KEYS = ["Cfit2", "Cact2", "Qfit2", "Qact2", "D2", "G2", "divG2", "n", "qpos_sum", "rho_abs_sum"]
HUGE = 1.0e20


def load_json(p):
    try:
        return json.loads(p.read_text(errors="ignore"))
    except Exception as e:
        return {"__error__": str(e)}


def safe_float(x):
    try:
        y = float(x)
        return y if math.isfinite(y) else None
    except Exception:
        return None


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def scan_case(case_dir):
    score_files = sorted((case_dir / "tiles").glob("*.score.json"))
    key_stats = {}
    huge_rows = []
    top_rows = []

    for p in score_files:
        d = load_json(p)

        for k in KEYS:
            v = safe_float(d.get(k))
            if v is None:
                continue

            st = key_stats.setdefault(k, {
                "case": case_dir.name,
                "key": k,
                "count": 0,
                "sum": 0.0,
                "max_abs": 0.0,
                "max_value": 0.0,
                "max_file": "",
                "huge_count": 0,
            })

            av = abs(v)
            st["count"] += 1
            st["sum"] += v

            if av > st["max_abs"]:
                st["max_abs"] = av
                st["max_value"] = v
                st["max_file"] = p.name

            if av >= HUGE:
                st["huge_count"] += 1
                huge_rows.append({
                    "case": case_dir.name,
                    "file": p.name,
                    "key": k,
                    "value": repr(v),
                    "abs_value": repr(av),
                    "Cfit2": repr(d.get("Cfit2")),
                    "Cact2": repr(d.get("Cact2")),
                    "Qfit2": repr(d.get("Qfit2")),
                    "Qact2": repr(d.get("Qact2")),
                    "D2": repr(d.get("D2")),
                    "G2": repr(d.get("G2")),
                    "divG2": repr(d.get("divG2")),
                    "n": repr(d.get("n")),
                })

            top_rows.append((av, case_dir.name, p.name, k, v))

    summary_rows = []
    for st in key_stats.values():
        total_abs = abs(st["sum"])
        st["max_over_sum_abs"] = st["max_abs"] / total_abs if total_abs else ""
        summary_rows.append(st)

    summary_rows.sort(key=lambda r: r["max_abs"], reverse=True)
    huge_rows.sort(key=lambda r: float(r["abs_value"]), reverse=True)
    top_rows.sort(reverse=True, key=lambda x: x[0])

    case_out = OUTDIR / case_dir.name
    case_out.mkdir(parents=True, exist_ok=True)

    write_csv(
        case_out / "score_key_summary.csv",
        summary_rows,
        ["case", "key", "count", "sum", "max_abs", "max_value", "max_file", "huge_count", "max_over_sum_abs"],
    )

    write_csv(
        case_out / "score_huge_values.csv",
        huge_rows,
        ["case", "file", "key", "value", "abs_value", "Cfit2", "Cact2", "Qfit2", "Qact2", "D2", "G2", "divG2", "n"],
    )

    top_export = []
    for i, (av, case, fname, key, value) in enumerate(top_rows[:200], 1):
        top_export.append({
            "rank": i,
            "case": case,
            "file": fname,
            "key": key,
            "value": repr(value),
            "abs_value": repr(av),
        })

    write_csv(
        case_out / "score_top_abs_values.csv",
        top_export,
        ["rank", "case", "file", "key", "value", "abs_value"],
    )

    copied = set()
    offdir = case_out / "offending_score_jsons"
    offdir.mkdir(exist_ok=True)

    for row in huge_rows[:50]:
        src = case_dir / "tiles" / row["file"]
        if src.exists() and src.name not in copied:
            shutil.copy2(src, offdir / src.name)
            copied.add(src.name)

    return {
        "case": case_dir.name,
        "score_files": len(score_files),
        "summary": summary_rows[:12],
        "huge_count": len(huge_rows),
        "outdir": str(case_out),
    }


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)

    cases = sorted(
        p for p in RUNBASE.glob("N*_v*_sigma4_R3")
        if p.is_dir() and (p / "tiles").exists()
    )

    print(f"RUNBASE={RUNBASE}")
    print(f"OUTDIR={OUTDIR}")
    print()

    for case_dir in cases:
        result = scan_case(case_dir)

        print("=" * 100)
        print(f"CASE: {result['case']}")
        print(f"score files: {result['score_files']}")
        print(f"huge score values >= {HUGE:g}: {result['huge_count']}")
        print(f"diagnostic dir: {result['outdir']}")
        print("Top keys by max_abs:")
        for r in result["summary"]:
            print(
                f"  {r['key']:8s} max_abs={r['max_abs']:.6e} "
                f"huge_count={r['huge_count']} "
                f"max_file={r['max_file']} "
                f"max/sum={r['max_over_sum_abs']}"
            )
        print()

    print(f"Diagnostic files written to: {OUTDIR}")


if __name__ == "__main__":
    main()
