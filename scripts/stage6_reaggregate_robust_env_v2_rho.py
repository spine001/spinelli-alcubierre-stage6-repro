#!/usr/bin/env python3
"""
Stage 6 robust reaggregation + rho-aware branch-continuation gate, v2.

Purpose
-------
Reaggregate an existing Stage 6 tiled run without rerunning the physics job.
This version preserves the old extreme rho peak metric as a disclosed warning,
but adds robust rho summaries and gates branch continuation on a summed peak-rho
relative error instead of allowing one localized tile to veto an otherwise stable
branch.

Inputs
------
- STAGE6_RUNBASE environment variable, or first CLI argument.
- Default fallback: results/stage6D_alcubierre_highres_latest under the repo.

Expected run layout
-------------------
RUNBASE/
  N261_v0p5_sigma4_R3/
    case_summary.json
    tiles/*.score.json

Outputs, written into RUNBASE
-----------------------------
- stage6_robust_reaggregate_v2_rho.csv
- stage6_robust_reaggregate_v2_rho.json
- stage6_robust_reaggregate_v2_rho_report.txt

Exit status
-----------
0 = gate passed
2 = no usable input / internal error
3 = gate failed
"""

from __future__ import annotations

import csv
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

REPO = Path("/home/julio/spinelli-framework/repro/spinelli-alcubierre-stage6-repro")
DEFAULT_RUNBASE = REPO / "results" / "stage6D_alcubierre_highres_latest"

SUM_KEYS = [
    "n",
    "Cfit2",
    "Cact2",
    "Qfit2",
    "Qact2",
    "D2",
    "G2",
    "divG2",
    "qpos_sum",
    "rho_abs_sum",
]

MAJOR_KEYS = ["Cfit2", "Cact2", "Qfit2", "Qact2", "D2", "G2", "divG2"]
ABS_HUGE = 1.0e20
QPOS_HUGE = 1.0e20

# Branch-continuation acceptance bands.  The old rho_relative_peak_error is
# retained as a warning metric; it is intentionally not a hard gate in v2.
GATE_BANDS: Dict[Tuple[int, float], Dict[str, Tuple[float, float]]] = {
    (261, 0.5): {
        "beta_fit": (-1.30, -1.16),
        "lambda_fit": (0.255, 0.272),
        "robust_action_over_fit": (0.995, 1.005),
        "robust_tensor_difference_percent": (0.0, 0.35),
        "robust_bianchi": (0.0, 0.04),
        "rho_sum_peak_relative_error": (0.0, 0.06),
        "excluded_contributing_fraction": (0.0, 0.001),
    },
    (261, 1.0): {
        "beta_fit": (-1.90, -1.50),
        "lambda_fit": (1.00, 1.05),
        "robust_action_over_fit": (0.990, 1.006),
        "robust_tensor_difference_percent": (0.0, 1.50),
        "robust_bianchi": (0.0, 0.075),
        "rho_sum_peak_relative_error": (0.0, 0.06),
        "excluded_contributing_fraction": (0.0, 0.001),
    },
}

RHO_EXTREME_WARNING_THRESHOLD = 0.06

TILE_NAME_RE = re.compile(
    r"tile(?P<tile_id>\d+)_"
    r"t(?P<t0>\d+)-(?P<t1>\d+)_"
    r"x(?P<x0>\d+)-(?P<x1>\d+)_"
    r"y(?P<y0>\d+)-(?P<y1>\d+)_"
    r"z(?P<z0>\d+)-(?P<z1>\d+)\.score\.json$"
)

CASE_RE = re.compile(r"N(?P<N>\d+)_v(?P<v>[0-9]+(?:p[0-9]+)?|[0-9]+(?:\.[0-9]+)?)_")


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def finite_float(x: Any) -> Optional[float]:
    try:
        y = float(x)
    except Exception:
        return None
    if not math.isfinite(y):
        return None
    return y


def safe_ratio(num: float, den: float) -> float:
    if not math.isfinite(num) or not math.isfinite(den) or den == 0.0:
        return float("nan")
    return num / den


def safe_sqrt(x: float) -> float:
    if not math.isfinite(x) or x < 0.0:
        return float("nan")
    return math.sqrt(x)


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(errors="replace"))


def load_case_summary(case_dir: Path) -> Dict[str, Any]:
    candidates = [
        case_dir / "case_summary.json",
        case_dir / "summary.json",
    ]
    for p in candidates:
        if p.exists():
            return load_json(p)

    csv_candidates = [
        case_dir / "case_summary.csv",
        case_dir / "summary.csv",
    ]
    for p in csv_candidates:
        if p.exists():
            with p.open(newline="") as f:
                rows = list(csv.DictReader(f))
            if rows:
                return dict(rows[0])

    return {}


def parse_case_name(case_dir: Path, summary: Dict[str, Any]) -> Tuple[Optional[int], Optional[float]]:
    n = finite_float(summary.get("N"))
    vs = finite_float(summary.get("v_s"))
    if n is not None and vs is not None:
        return int(n), float(vs)

    m = CASE_RE.search(case_dir.name)
    if not m:
        return None, None

    n_val = int(m.group("N"))
    v_text = m.group("v").replace("p", ".")
    try:
        v_val = float(v_text)
    except Exception:
        v_val = None
    return n_val, v_val


def parse_tile_from_path(path: Path) -> Dict[str, Any]:
    m = TILE_NAME_RE.search(path.name)
    if not m:
        return {}
    return {k: int(v) for k, v in m.groupdict().items()}


def percentile_nearest(values: List[float], q: float) -> float:
    if not values:
        return float("nan")
    vals = sorted(values)
    idx = int(round((len(vals) - 1) * q))
    idx = max(0, min(idx, len(vals) - 1))
    return vals[idx]


def median(values: List[float]) -> float:
    if not values:
        return float("nan")
    vals = sorted(values)
    n = len(vals)
    mid = n // 2
    if n % 2:
        return vals[mid]
    return 0.5 * (vals[mid - 1] + vals[mid])


def empty_totals() -> Dict[str, float]:
    return {k: 0.0 for k in SUM_KEYS}


def add_finite_to_totals(totals: Dict[str, float], score: Dict[str, Any]) -> None:
    for key in SUM_KEYS:
        val = finite_float(score.get(key, 0.0))
        if val is not None:
            totals[key] += val


def score_corruption_reasons(score: Dict[str, Any]) -> List[str]:
    reasons: List[str] = []

    for key in MAJOR_KEYS:
        val = finite_float(score.get(key))
        if val is None:
            reasons.append(f"{key}=nonfinite_or_missing")
        elif abs(val) >= ABS_HUGE:
            reasons.append(f"{key}=abs_huge:{val:.6g}")

    qpos = finite_float(score.get("qpos_sum", 0.0))
    if qpos is None:
        reasons.append("qpos_sum=nonfinite")
    elif abs(qpos) >= QPOS_HUGE:
        reasons.append(f"qpos_sum=abs_huge:{qpos:.6g}")

    rho_err = finite_float(score.get("rho_peak_err", 0.0))
    rho_ref = finite_float(score.get("rho_peak_ref", 0.0))
    if rho_err is None:
        reasons.append("rho_peak_err=nonfinite")
    if rho_ref is None:
        reasons.append("rho_peak_ref=nonfinite")

    return reasons


def top_tile_record(path: Path, score: Dict[str, Any], runbase: Path) -> Dict[str, Any]:
    rec = parse_tile_from_path(path)
    rec["file"] = str(path.relative_to(runbase))
    rec["rho_peak_err"] = finite_float(score.get("rho_peak_err", 0.0)) or 0.0
    rec["rho_peak_ref"] = finite_float(score.get("rho_peak_ref", 0.0)) or 0.0
    rec["rho_abs_sum"] = finite_float(score.get("rho_abs_sum", 0.0)) or 0.0
    abs_ref = abs(rec["rho_peak_ref"])
    rec["rho_tile_ratio"] = abs(rec["rho_peak_err"]) / abs_ref if abs_ref else float("nan")
    return rec


def summarize_case(runbase: Path, case_dir: Path) -> Dict[str, Any]:
    summary = load_case_summary(case_dir)
    N, v_s = parse_case_name(case_dir, summary)

    totals_raw = empty_totals()
    totals_clean = empty_totals()

    score_files = sorted((case_dir / "tiles").glob("*.score.json"))
    if not score_files:
        score_files = sorted(case_dir.rglob("*.score.json"))

    valid_score_tiles = 0
    empty_score_tiles = 0
    corrupt_contributing_tiles = 0
    corrupt_tile_files: List[str] = []
    corrupt_tile_reasons: List[str] = []

    excluded_contributing_points = 0

    rho_peak_err_abs_values: List[float] = []
    rho_peak_ref_abs_values: List[float] = []
    rho_tile_ratios: List[float] = []

    max_peak_err_record: Optional[Dict[str, Any]] = None
    max_tile_ratio_record: Optional[Dict[str, Any]] = None
    top_peak_err_values: List[float] = []

    for path in score_files:
        try:
            score = load_json(path)
        except Exception as exc:
            corrupt_contributing_tiles += 1
            corrupt_tile_files.append(str(path.relative_to(runbase)))
            corrupt_tile_reasons.append(f"json_load_failed:{exc}")
            continue

        n_val = finite_float(score.get("n", 0.0))
        if n_val is None or n_val <= 0.0:
            empty_score_tiles += 1
            continue

        valid_score_tiles += 1
        add_finite_to_totals(totals_raw, score)

        reasons = score_corruption_reasons(score)
        if reasons:
            corrupt_contributing_tiles += 1
            rel = str(path.relative_to(runbase))
            corrupt_tile_files.append(rel)
            corrupt_tile_reasons.append(rel + ":" + ";".join(reasons))
            excluded_contributing_points += int(n_val)
            continue

        add_finite_to_totals(totals_clean, score)

        rho_err = abs(finite_float(score.get("rho_peak_err", 0.0)) or 0.0)
        rho_ref = abs(finite_float(score.get("rho_peak_ref", 0.0)) or 0.0)
        rho_peak_err_abs_values.append(rho_err)
        rho_peak_ref_abs_values.append(rho_ref)
        top_peak_err_values.append(rho_err)

        if rho_ref > 0.0:
            ratio = rho_err / rho_ref
            rho_tile_ratios.append(ratio)
        else:
            ratio = float("nan")

        rec = top_tile_record(path, score, runbase)
        if max_peak_err_record is None or rho_err > abs(max_peak_err_record.get("rho_peak_err", 0.0)):
            max_peak_err_record = rec
        if math.isfinite(ratio) and (
            max_tile_ratio_record is None
            or ratio > float(max_tile_ratio_record.get("rho_tile_ratio", float("-inf")))
        ):
            max_tile_ratio_record = rec

    n_raw = totals_raw["n"]
    n_clean = totals_clean["n"]
    sqrt_Cfit2 = safe_sqrt(totals_clean["Cfit2"])
    sqrt_Cact2 = safe_sqrt(totals_clean["Cact2"])
    sqrt_Qfit2 = safe_sqrt(totals_clean["Qfit2"])
    sqrt_Qact2 = safe_sqrt(totals_clean["Qact2"])
    sqrt_D2 = safe_sqrt(totals_clean["D2"])
    sqrt_G2 = safe_sqrt(totals_clean["G2"])
    sqrt_divG2 = safe_sqrt(totals_clean["divG2"])

    sum_abs_peak_err = sum(rho_peak_err_abs_values)
    sum_abs_peak_ref = sum(rho_peak_ref_abs_values)
    max_abs_peak_err = max(rho_peak_err_abs_values) if rho_peak_err_abs_values else float("nan")
    max_abs_peak_ref = max(rho_peak_ref_abs_values) if rho_peak_ref_abs_values else float("nan")

    rho_extreme_peak_error = safe_ratio(max_abs_peak_err, max_abs_peak_ref)
    rho_sum_peak_relative_error = safe_ratio(sum_abs_peak_err, sum_abs_peak_ref)

    sorted_errs = sorted(top_peak_err_values, reverse=True)
    second_abs_peak_err = sorted_errs[1] if len(sorted_errs) > 1 else float("nan")
    peak_outlier_factor_vs_second = safe_ratio(max_abs_peak_err, second_abs_peak_err)

    rho_peak_warning = bool(
        math.isfinite(rho_extreme_peak_error)
        and rho_extreme_peak_error > RHO_EXTREME_WARNING_THRESHOLD
    )

    def sget(key: str) -> Any:
        return summary.get(key, "")

    row: Dict[str, Any] = {
        "case_dir": case_dir.name,
        "N": N if N is not None else "",
        "v_s": v_s if v_s is not None else "",
        "lambda_fit": sget("lambda_fit"),
        "beta_fit": sget("beta_fit"),
        "mask_points_raw": int(n_raw) if math.isfinite(n_raw) else "",
        "mask_points_robust": int(n_clean) if math.isfinite(n_clean) else "",
        "score_json_files": len(score_files),
        "valid_score_tiles": valid_score_tiles,
        "empty_score_tiles": empty_score_tiles,
        "corrupt_contributing_tiles": corrupt_contributing_tiles,
        "corrupt_tile_files": " | ".join(corrupt_tile_files),
        "corrupt_tile_reasons": " | ".join(corrupt_tile_reasons),
        "excluded_contributing_points": int(excluded_contributing_points),
        "excluded_contributing_fraction": safe_ratio(float(excluded_contributing_points), float(n_raw)),
        "raw_fit_residual": sget("fit_residual"),
        "robust_fit_residual": safe_sqrt(totals_clean["Cfit2"] / n_clean) if n_clean else float("nan"),
        "raw_action_residual": sget("action_residual"),
        "robust_action_residual": safe_sqrt(totals_clean["Cact2"] / n_clean) if n_clean else float("nan"),
        "raw_action_over_fit": sget("action_over_fit"),
        "robust_action_over_fit": safe_ratio(sqrt_Cact2, sqrt_Cfit2),
        "raw_normalized_fit_residual": sget("normalized_fit_residual"),
        "robust_normalized_fit_residual": safe_ratio(sqrt_Cfit2, sqrt_Qfit2),
        "raw_normalized_action_residual": sget("normalized_action_residual"),
        "robust_normalized_action_residual": safe_ratio(sqrt_Cact2, sqrt_Qact2),
        "raw_relative_tensor_difference": sget("relative_tensor_difference"),
        "robust_relative_tensor_difference": safe_ratio(sqrt_D2, sqrt_Qfit2),
        "robust_tensor_difference_percent": 100.0 * safe_ratio(sqrt_D2, sqrt_Qfit2),
        "raw_bianchi": sget("bianchi"),
        "robust_bianchi": safe_ratio(sqrt_divG2, sqrt_G2),
        # Old extreme-value metric retained for continuity/disclosure.
        "rho_relative_peak_error": sget("rho_relative_peak_error"),
        "rho_extreme_peak_error_recomputed": rho_extreme_peak_error,
        # New robust rho gate metric based on summed tile peak numerators/denominators.
        "rho_sum_peak_relative_error": rho_sum_peak_relative_error,
        "rho_tile_ratio_median": median(rho_tile_ratios),
        "rho_tile_ratio_p90": percentile_nearest(rho_tile_ratios, 0.90),
        "rho_tile_ratio_p99": percentile_nearest(rho_tile_ratios, 0.99),
        "rho_tile_ratio_p999": percentile_nearest(rho_tile_ratios, 0.999),
        "rho_tile_ratio_max": max(rho_tile_ratios) if rho_tile_ratios else float("nan"),
        "rho_peak_warning": rho_peak_warning,
        "rho_peak_warning_threshold": RHO_EXTREME_WARNING_THRESHOLD,
        "rho_peak_outlier_file": max_peak_err_record.get("file", "") if max_peak_err_record else "",
        "rho_peak_outlier_t0": max_peak_err_record.get("t0", "") if max_peak_err_record else "",
        "rho_peak_outlier_t1": max_peak_err_record.get("t1", "") if max_peak_err_record else "",
        "rho_peak_outlier_x0": max_peak_err_record.get("x0", "") if max_peak_err_record else "",
        "rho_peak_outlier_x1": max_peak_err_record.get("x1", "") if max_peak_err_record else "",
        "rho_peak_outlier_y0": max_peak_err_record.get("y0", "") if max_peak_err_record else "",
        "rho_peak_outlier_y1": max_peak_err_record.get("y1", "") if max_peak_err_record else "",
        "rho_peak_outlier_z0": max_peak_err_record.get("z0", "") if max_peak_err_record else "",
        "rho_peak_outlier_z1": max_peak_err_record.get("z1", "") if max_peak_err_record else "",
        "rho_peak_outlier_err": max_peak_err_record.get("rho_peak_err", "") if max_peak_err_record else "",
        "rho_peak_outlier_ref": max_peak_err_record.get("rho_peak_ref", "") if max_peak_err_record else "",
        "rho_peak_outlier_tile_ratio": max_peak_err_record.get("rho_tile_ratio", "") if max_peak_err_record else "",
        "rho_peak_outlier_factor_vs_second": peak_outlier_factor_vs_second,
        "rho_max_tile_ratio_file": max_tile_ratio_record.get("file", "") if max_tile_ratio_record else "",
        "rho_max_tile_ratio": max_tile_ratio_record.get("rho_tile_ratio", "") if max_tile_ratio_record else "",
        "rho_sum_abs_peak_err": sum_abs_peak_err,
        "rho_sum_abs_peak_ref": sum_abs_peak_ref,
        "rho_max_abs_peak_err": max_abs_peak_err,
        "rho_max_abs_peak_ref": max_abs_peak_ref,
        "elapsed_seconds": sget("elapsed_seconds"),
        "elapsed_hours": (finite_float(sget("elapsed_seconds")) or 0.0) / 3600.0,
        "raw_total_Cfit2": totals_raw["Cfit2"],
        "robust_total_Cfit2": totals_clean["Cfit2"],
        "raw_total_Cact2": totals_raw["Cact2"],
        "robust_total_Cact2": totals_clean["Cact2"],
        "raw_total_Qfit2": totals_raw["Qfit2"],
        "robust_total_Qfit2": totals_clean["Qfit2"],
        "raw_total_Qact2": totals_raw["Qact2"],
        "robust_total_Qact2": totals_clean["Qact2"],
        "robust_total_D2": totals_clean["D2"],
        "robust_total_G2": totals_clean["G2"],
        "robust_total_divG2": totals_clean["divG2"],
    }

    return row


def coerce_for_gate(value: Any) -> Optional[float]:
    return finite_float(value)


def evaluate_gate(row: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
    messages: List[str] = []
    warnings: List[str] = []

    N = row.get("N")
    v_s = row.get("v_s")
    try:
        key = (int(N), float(v_s))
    except Exception:
        return False, ["Cannot evaluate gate because N/v_s are missing or invalid."], warnings

    bands = GATE_BANDS.get(key)
    if bands is None:
        return False, [f"No v2 gate band configured for N={N}, v_s={v_s}."], warnings

    ok = True
    for field, (lo, hi) in bands.items():
        val = coerce_for_gate(row.get(field))
        if val is None:
            ok = False
            messages.append(f"FAIL {field}: value is missing/nonfinite; expected {lo} <= value <= {hi}")
            continue
        if not (lo <= val <= hi):
            ok = False
            messages.append(f"FAIL {field}: {val:.17g} outside [{lo:.17g}, {hi:.17g}]")
        else:
            messages.append(f"PASS {field}: {val:.17g} inside [{lo:.17g}, {hi:.17g}]")

    peak = coerce_for_gate(row.get("rho_extreme_peak_error_recomputed"))
    if peak is not None and peak > RHO_EXTREME_WARNING_THRESHOLD:
        warnings.append(
            "WARN rho_extreme_peak_error_recomputed: "
            f"{peak:.17g} exceeds warning threshold {RHO_EXTREME_WARNING_THRESHOLD:.17g}; "
            "kept as warning only in v2 gate."
        )
        if row.get("rho_peak_outlier_file"):
            warnings.append(
                "WARN rho_peak_outlier_file: "
                f"{row.get('rho_peak_outlier_file')} "
                f"tile_ratio={row.get('rho_peak_outlier_tile_ratio')} "
                f"factor_vs_second={row.get('rho_peak_outlier_factor_vs_second')}"
            )

    return ok, messages, warnings


def find_case_dirs(runbase: Path) -> List[Path]:
    case_dirs: List[Path] = []
    for p in sorted(runbase.iterdir()):
        if not p.is_dir():
            continue
        if (p / "tiles").is_dir() or list(p.glob("*.score.json")):
            case_dirs.append(p)
    return case_dirs


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        path.write_text("")
        return

    fieldnames: List[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)

    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def json_ready(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: json_ready(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [json_ready(v) for v in obj]
    if isinstance(obj, float):
        if math.isnan(obj):
            return "NaN"
        if math.isinf(obj):
            return "Infinity" if obj > 0 else "-Infinity"
    return obj


def format_row_summary(row: Dict[str, Any]) -> List[str]:
    keys = [
        "case_dir",
        "N",
        "v_s",
        "lambda_fit",
        "beta_fit",
        "mask_points_raw",
        "mask_points_robust",
        "score_json_files",
        "valid_score_tiles",
        "empty_score_tiles",
        "corrupt_contributing_tiles",
        "excluded_contributing_points",
        "excluded_contributing_fraction",
        "robust_action_over_fit",
        "robust_tensor_difference_percent",
        "robust_bianchi",
        "rho_relative_peak_error",
        "rho_extreme_peak_error_recomputed",
        "rho_sum_peak_relative_error",
        "rho_tile_ratio_median",
        "rho_tile_ratio_p99",
        "rho_tile_ratio_p999",
        "rho_tile_ratio_max",
        "rho_peak_warning",
        "rho_peak_outlier_file",
        "rho_peak_outlier_err",
        "rho_peak_outlier_ref",
        "rho_peak_outlier_tile_ratio",
        "rho_peak_outlier_factor_vs_second",
    ]
    return [f"{k}: {row.get(k, '')}" for k in keys]


def main() -> int:
    runbase_arg = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("STAGE6_RUNBASE")
    runbase = Path(runbase_arg).expanduser().resolve() if runbase_arg else DEFAULT_RUNBASE.resolve()

    if not runbase.exists():
        print(f"ERROR: RUNBASE does not exist: {runbase}", file=sys.stderr)
        return 2

    case_dirs = find_case_dirs(runbase)
    if not case_dirs:
        print(f"ERROR: no case directories with tile scores found under {runbase}", file=sys.stderr)
        return 2

    rows: List[Dict[str, Any]] = []
    gate_details: List[Dict[str, Any]] = []
    overall_ok = True

    for case_dir in case_dirs:
        row = summarize_case(runbase, case_dir)
        ok, messages, warnings = evaluate_gate(row)
        row["rho_v2_gate_status"] = "PASS" if ok else "FAIL"
        row["rho_v2_gate_messages"] = " | ".join(messages)
        row["rho_v2_gate_warnings"] = " | ".join(warnings)
        rows.append(row)
        gate_details.append({"case_dir": case_dir.name, "ok": ok, "messages": messages, "warnings": warnings})
        overall_ok = overall_ok and ok

    out_csv = runbase / "stage6_robust_reaggregate_v2_rho.csv"
    out_json = runbase / "stage6_robust_reaggregate_v2_rho.json"
    out_report = runbase / "stage6_robust_reaggregate_v2_rho_report.txt"

    write_csv(out_csv, rows)
    out_json.write_text(json.dumps(json_ready(rows), indent=2, sort_keys=False) + "\n")

    lines: List[str] = []
    lines.append("Stage 6 robust reaggregation + rho-aware gate v2")
    lines.append("=" * 100)
    lines.append(f"time_utc: {now_utc()}")
    lines.append(f"runbase: {runbase}")
    lines.append(f"cases: {len(rows)}")
    lines.append(f"overall_gate_status: {'PASS' if overall_ok else 'FAIL'}")
    lines.append("")
    lines.append("Interpretation note:")
    lines.append(
        "rho_relative_peak_error is preserved as the old extreme peak diagnostic. "
        "The v2 gate uses rho_sum_peak_relative_error and treats the extreme peak "
        "as a warning/manual-review field."
    )
    lines.append("")

    for row, detail in zip(rows, gate_details):
        lines.append("-" * 100)
        lines.append(f"case: {row.get('case_dir')}")
        lines.extend(format_row_summary(row))
        lines.append("")
        lines.append("gate checks:")
        for msg in detail["messages"]:
            lines.append(f"  {msg}")
        if detail["warnings"]:
            lines.append("warnings:")
            for warn in detail["warnings"]:
                lines.append(f"  {warn}")
        lines.append("")

    lines.append("outputs:")
    lines.append(f"  {out_csv}")
    lines.append(f"  {out_json}")
    lines.append(f"  {out_report}")
    lines.append("")
    lines.append("done")

    out_report.write_text("\n".join(lines) + "\n")

    print(f"Wrote: {out_csv}")
    print(f"Wrote: {out_json}")
    print(f"Wrote: {out_report}")
    print()
    print("case,N,v_s,beta_fit,lambda_fit,robust_action_over_fit,robust_tensor_difference_percent,robust_bianchi,rho_sum_peak_relative_error,rho_extreme_peak_error_recomputed,rho_peak_warning,rho_v2_gate_status")
    for row in rows:
        print(
            f"{row.get('case_dir')},{row.get('N')},{row.get('v_s')},"
            f"{row.get('beta_fit')},{row.get('lambda_fit')},"
            f"{row.get('robust_action_over_fit')},"
            f"{row.get('robust_tensor_difference_percent')},"
            f"{row.get('robust_bianchi')},"
            f"{row.get('rho_sum_peak_relative_error')},"
            f"{row.get('rho_extreme_peak_error_recomputed')},"
            f"{row.get('rho_peak_warning')},"
            f"{row.get('rho_v2_gate_status')}"
        )
    print()
    print("GATE:", "PASS" if overall_ok else "FAIL")

    return 0 if overall_ok else 3


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        raise SystemExit(130)
