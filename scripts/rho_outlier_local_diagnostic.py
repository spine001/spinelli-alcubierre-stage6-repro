#!/usr/bin/env python3
"""
Localized rho outlier diagnostic for Stage 6E tiled Alcubierre runs.

Read-only diagnostic. It analyzes a target rho peak outlier at tile-summary level
and reports whether it looks isolated, boundary/halo-like, or part of a local
neighboring structure.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import re
import statistics
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

FILENAME_RE = re.compile(
    r"tile(?P<tile_id>\d+)_"
    r"t(?P<t0>-?\d+)-(?P<t1>-?\d+)_"
    r"x(?P<x0>-?\d+)-(?P<x1>-?\d+)_"
    r"y(?P<y0>-?\d+)-(?P<y1>-?\d+)_"
    r"z(?P<z0>-?\d+)-(?P<z1>-?\d+)"
    r"\.score\.json$"
)


def as_float(x: Any, default: float = float("nan")) -> float:
    try:
        y = float(x)
        return y if math.isfinite(y) else default
    except Exception:
        return default


def as_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default


def percentile(values: List[float], q: float) -> float:
    vals = sorted(v for v in values if math.isfinite(v))
    if not vals:
        return float("nan")
    if len(vals) == 1:
        return vals[0]
    pos = (len(vals) - 1) * (q / 100.0)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return vals[lo]
    frac = pos - lo
    return vals[lo] * (1.0 - frac) + vals[hi] * frac


def safe_div(a: float, b: float) -> float:
    if not math.isfinite(a) or not math.isfinite(b) or b == 0.0:
        return float("nan")
    return a / b


def fnum(x: Any, digits: int = 6) -> str:
    try:
        y = float(x)
        if not math.isfinite(y):
            return "nan"
        if abs(y) >= 1e5 or (0 < abs(y) < 1e-4):
            return f"{y:.{digits}e}"
        return f"{y:.{digits}g}"
    except Exception:
        return str(x)


def parse_tile_from_name(path: Path) -> Optional[Dict[str, int]]:
    m = FILENAME_RE.search(path.name)
    if not m:
        return None
    return {k: int(v) for k, v in m.groupdict().items()}


def load_record(path: Path, case_dir: Path) -> Optional[Dict[str, Any]]:
    coords = parse_tile_from_name(path)
    if not coords:
        return None
    try:
        data = json.loads(path.read_text(errors="replace"))
    except Exception as e:
        data = {"_json_error": str(e)}

    rec: Dict[str, Any] = dict(coords)
    rec["file"] = str(path.relative_to(case_dir.parent))
    rec["path"] = str(path)
    rec["n"] = as_int(data.get("n", data.get("count", 0)), 0)
    rec["rho_peak_err"] = as_float(data.get("rho_peak_err"))
    rec["rho_peak_ref"] = as_float(data.get("rho_peak_ref"))
    rec["rho_abs_sum"] = as_float(data.get("rho_abs_sum"))
    rec["rho_tile_ratio"] = safe_div(abs(rec["rho_peak_err"]), abs(rec["rho_peak_ref"]))
    rec["valid"] = bool(
        rec["n"] > 0
        and math.isfinite(rec["rho_peak_err"])
        and math.isfinite(rec["rho_peak_ref"])
        and rec["rho_peak_ref"] != 0.0
    )
    rec["empty"] = bool(rec["n"] <= 0)
    rec["json_error"] = data.get("_json_error", "")
    return rec


def tile_distance_index(target: Dict[str, Any], rec: Dict[str, Any], steps: Dict[str, int]) -> Tuple[int, int, int, int]:
    out = []
    for axis in ("t", "x", "y", "z"):
        c0 = (target[f"{axis}0"] + target[f"{axis}1"]) / 2.0
        c1 = (rec[f"{axis}0"] + rec[f"{axis}1"]) / 2.0
        st = max(1, int(steps[axis]))
        out.append(int(round(abs(c1 - c0) / st)))
    return tuple(out)  # type: ignore[return-value]


def relation_to_target(target: Dict[str, Any], rec: Dict[str, Any], steps: Dict[str, int]) -> str:
    dt_i, dx_i, dy_i, dz_i = tile_distance_index(target, rec, steps)
    dist_axes = [dt_i, dx_i, dy_i, dz_i]
    if max(dist_axes) == 0:
        return "TARGET"
    if max(dist_axes) <= 1:
        changed = [name for name, v in zip(("t", "x", "y", "z"), dist_axes) if v != 0]
        if len(changed) == 1:
            return "FACE_" + changed[0]
        if len(changed) == 2:
            return "EDGE_" + "".join(changed)
        return "CORNER_4D"
    if max(dist_axes) <= 2:
        return "RING2"
    return "FAR"


def find_target_file(case_dir: Path, tile_id: int, target_file: Optional[str]) -> Path:
    if target_file:
        p = Path(target_file)
        candidates = [p]
        if not p.is_absolute():
            candidates += [case_dir.parent / p, case_dir / p, case_dir / "tiles" / p.name]
        for c in candidates:
            if c.exists():
                return c.resolve()
        return candidates[-1].resolve()

    matches = sorted((case_dir / "tiles").glob(f"tile{int(tile_id):06d}_*.score.json"))
    if not matches:
        raise SystemExit(f"ERROR: no score file found for tile id {tile_id} in {case_dir/'tiles'}")
    if len(matches) > 1:
        raise SystemExit(f"ERROR: multiple score files found for tile id {tile_id}: {matches[:5]}")
    return matches[0].resolve()


def classify(target: Dict[str, Any], local: List[Dict[str, Any]], global_stats: Dict[str, Any]) -> Tuple[str, List[str]]:
    target_ratio = target["rho_tile_ratio"]
    target_err = abs(target["rho_peak_err"])
    p99 = global_stats["ratio_p99"]
    p999 = global_stats["ratio_p999"]
    p999_err = global_stats["err_p999"]

    valid_neighbors = [r for r in local if r.get("relation") != "TARGET" and r.get("valid")]
    ring1 = [r for r in valid_neighbors if r.get("cheb_distance") == 1]
    ring2 = [r for r in valid_neighbors if r.get("cheb_distance") == 2]

    high_ratio_threshold = max(0.06, p99)
    extreme_ratio_threshold = max(0.20, p999)
    high_err_threshold = p999_err

    high_ring1 = [r for r in ring1 if r["rho_tile_ratio"] >= high_ratio_threshold or abs(r["rho_peak_err"]) >= high_err_threshold]
    extreme_ring1 = [r for r in ring1 if r["rho_tile_ratio"] >= extreme_ratio_threshold]
    high_ring2 = [r for r in ring2 if r["rho_tile_ratio"] >= high_ratio_threshold or abs(r["rho_peak_err"]) >= high_err_threshold]

    max_neighbor_ratio = max([r["rho_tile_ratio"] for r in valid_neighbors], default=float("nan"))
    max_neighbor_err = max([abs(r["rho_peak_err"]) for r in valid_neighbors], default=float("nan"))
    neighbor_factor_ratio = safe_div(target_ratio, max_neighbor_ratio)
    neighbor_factor_err = safe_div(target_err, max_neighbor_err)

    global_boundary_axes = []
    for axis in ("t", "x", "y", "z"):
        if target[f"{axis}0"] == global_stats.get(f"min_{axis}0"):
            global_boundary_axes.append(f"{axis}=low_global")
        if target[f"{axis}1"] == global_stats.get(f"max_{axis}1"):
            global_boundary_axes.append(f"{axis}=high_global")

    reasons: List[str] = []
    reasons.append(f"target_ratio={fnum(target_ratio)}; global p99={fnum(p99)}, p999={fnum(p999)}")
    reasons.append(f"target_abs_err={fnum(target_err)}; global err p999={fnum(p999_err)}")
    reasons.append(f"ring1 valid neighbors={len(ring1)}, high ring1 neighbors={len(high_ring1)}, extreme ring1 neighbors={len(extreme_ring1)}")
    reasons.append(f"ring2 valid neighbors={len(ring2)}, high ring2 neighbors={len(high_ring2)}")
    reasons.append(f"target/max_neighbor ratio factor={fnum(neighbor_factor_ratio)}, err factor={fnum(neighbor_factor_err)}")
    if global_boundary_axes:
        reasons.append("target touches inferred global boundary axes: " + ", ".join(global_boundary_axes))
    else:
        reasons.append("target does not touch an inferred global grid boundary")

    if global_boundary_axes and len(high_ring1) <= 2:
        label = "LIKELY_BOUNDARY_OR_HALO_ARTIFACT"
        reasons.append("reason: target touches global boundary and high-neighbor support is weak")
    elif len(high_ring1) == 0 and (neighbor_factor_ratio > 3 or neighbor_factor_err > 3):
        label = "LIKELY_ISOLATED_TILE_ARTIFACT"
        reasons.append("reason: no immediate high neighbors and target strongly exceeds all local neighbors")
    elif len(high_ring1) <= 2 and neighbor_factor_ratio > 5:
        label = "LIKELY_ISOLATED_TILE_ARTIFACT"
        reasons.append("reason: only weak local support and target is much larger than neighboring tiles")
    elif len(high_ring1) >= 4 or len(extreme_ring1) >= 2:
        label = "POSSIBLE_REAL_NEIGHBORING_STRUCTURE"
        reasons.append("reason: multiple immediate neighbors are also high/extreme")
    elif len(high_ring1) > 0 or len(high_ring2) >= 3:
        label = "MIXED_LOCAL_SUPPORT_REQUIRES_REVIEW"
        reasons.append("reason: there is some local support, but not enough for a clear structure classification")
    else:
        label = "LIKELY_ISOLATED_TILE_ARTIFACT"
        reasons.append("reason: local support is weak at tile granularity")

    return label, reasons


def git_cmd(repo: Path, args: List[str]) -> str:
    try:
        return subprocess.check_output(args, cwd=repo, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser(description="Diagnose a localized rho outlier at tile-summary level.")
    ap.add_argument("--runbase", default=None, help="Stage 6E runbase. Defaults to results/stage6E_alcubierre_robust_tile_latest")
    ap.add_argument("--case", default="N301_v0p5_sigma4_R3")
    ap.add_argument("--tile-id", type=int, default=53234)
    ap.add_argument("--target-file", default=None)
    ap.add_argument("--ring", type=int, default=2, help="Chebyshev tile-neighborhood radius")
    ap.add_argument("--top", type=int, default=25)
    args = ap.parse_args()

    repo = Path.cwd()
    runbase = Path(args.runbase) if args.runbase else repo / "results" / "stage6E_alcubierre_robust_tile_latest"
    runbase = runbase.resolve()
    case_dir = (runbase / args.case).resolve()
    tiles_dir = case_dir / "tiles"

    if not tiles_dir.exists():
        raise SystemExit(f"ERROR: tiles directory not found: {tiles_dir}")

    target_path = find_target_file(case_dir, args.tile_id, args.target_file)
    if not target_path.exists():
        raise SystemExit(f"ERROR: target score file not found: {target_path}")

    print(f"RUNBASE={runbase}")
    print(f"CASE={case_dir.name}")
    print(f"TARGET={target_path}")

    score_files = sorted(tiles_dir.glob("*.score.json"))
    records: List[Dict[str, Any]] = []
    for i, p in enumerate(score_files, 1):
        rec = load_record(p, case_dir)
        if rec:
            records.append(rec)
        if i % 25000 == 0:
            print(f"loaded {i}/{len(score_files)} score files", flush=True)

    if not records:
        raise SystemExit("ERROR: no readable score files found")

    target_rel = str(target_path.relative_to(case_dir.parent))
    target = None
    for r in records:
        if r["file"] == target_rel or Path(r["path"]).resolve() == target_path:
            target = r
            break
    if target is None:
        raise SystemExit("ERROR: target record not found among loaded score files")

    valid = [r for r in records if r.get("valid")]
    ratios = [r["rho_tile_ratio"] for r in valid]
    errs = [abs(r["rho_peak_err"]) for r in valid]
    refs = [abs(r["rho_peak_ref"]) for r in valid]

    steps: Dict[str, int] = {}
    for axis in ("t", "x", "y", "z"):
        starts = sorted(set(int(r[f"{axis}0"]) for r in records))
        deltas = [b - a for a, b in zip(starts, starts[1:]) if b > a]
        steps[axis] = int(statistics.median(deltas)) if deltas else max(1, int(target[f"{axis}1"] - target[f"{axis}0"]))

    global_stats: Dict[str, Any] = {
        "score_files": len(score_files),
        "loaded_records": len(records),
        "valid_records": len(valid),
        "empty_records": sum(1 for r in records if r.get("empty")),
        "ratio_median": percentile(ratios, 50),
        "ratio_p90": percentile(ratios, 90),
        "ratio_p99": percentile(ratios, 99),
        "ratio_p999": percentile(ratios, 99.9),
        "ratio_max": max(ratios) if ratios else float("nan"),
        "err_median": percentile(errs, 50),
        "err_p90": percentile(errs, 90),
        "err_p99": percentile(errs, 99),
        "err_p999": percentile(errs, 99.9),
        "err_max": max(errs) if errs else float("nan"),
        "ref_median": percentile(refs, 50),
        "ref_p99": percentile(refs, 99),
        "ref_max": max(refs) if refs else float("nan"),
    }
    for axis in ("t", "x", "y", "z"):
        global_stats[f"min_{axis}0"] = min(r[f"{axis}0"] for r in records)
        global_stats[f"max_{axis}1"] = max(r[f"{axis}1"] for r in records)
        global_stats[f"step_{axis}"] = steps[axis]

    sorted_by_ratio = sorted(valid, key=lambda r: r["rho_tile_ratio"], reverse=True)
    sorted_by_err = sorted(valid, key=lambda r: abs(r["rho_peak_err"]), reverse=True)
    ratio_rank = next((i + 1 for i, r in enumerate(sorted_by_ratio) if r["file"] == target["file"]), None)
    err_rank = next((i + 1 for i, r in enumerate(sorted_by_err) if r["file"] == target["file"]), None)

    local: List[Dict[str, Any]] = []
    for r in records:
        dist_tuple = tile_distance_index(target, r, steps)
        cheb = max(dist_tuple)
        if cheb <= args.ring:
            rr = dict(r)
            rr["dtile_t"], rr["dtile_x"], rr["dtile_y"], rr["dtile_z"] = dist_tuple
            rr["cheb_distance"] = cheb
            rr["relation"] = relation_to_target(target, rr, steps)
            rr["abs_err"] = abs(rr["rho_peak_err"]) if math.isfinite(rr["rho_peak_err"]) else float("nan")
            local.append(rr)

    local_sorted = sorted(
        local,
        key=lambda r: (
            r.get("cheb_distance", 99),
            -float(r.get("rho_tile_ratio", float("-inf")) if math.isfinite(float(r.get("rho_tile_ratio", float("nan")))) else float("-inf")),
            r.get("tile_id", 0),
        ),
    )

    classification, reasons = classify(target, local, global_stats)
    top_ratio = sorted_by_ratio[: args.top]
    top_err = sorted_by_err[: args.top]

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"rho_outlier_local_diagnostic_{case_dir.name}_tile{int(target['tile_id']):06d}_{stamp}"
    txt_path = runbase / f"{base_name}.txt"
    csv_path = runbase / f"{base_name}.csv"
    json_path = runbase / f"{base_name}.json"

    csv_fields = [
        "section", "rank", "relation", "cheb_distance",
        "tile_id", "t0", "t1", "x0", "x1", "y0", "y1", "z0", "z1",
        "n", "rho_peak_err", "rho_peak_ref", "rho_tile_ratio", "rho_abs_sum", "file",
    ]
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=csv_fields)
        w.writeheader()
        def write_row(section: str, rank: int, r: Dict[str, Any]) -> None:
            row = {k: r.get(k, "") for k in csv_fields}
            row["section"] = section
            row["rank"] = rank
            w.writerow(row)
        for idx, r in enumerate(local_sorted, 1):
            write_row("local_ring", idx, r)
        for idx, r in enumerate(top_ratio, 1):
            write_row("global_top_ratio", idx, r)
        for idx, r in enumerate(top_err, 1):
            write_row("global_top_abs_err", idx, r)

    json_payload = {
        "runbase": str(runbase),
        "case": case_dir.name,
        "target_file": target["file"],
        "target": target,
        "global_stats": global_stats,
        "target_ratio_rank": ratio_rank,
        "target_abs_err_rank": err_rank,
        "classification": classification,
        "classification_reasons": reasons,
        "local_ring_radius": args.ring,
        "local_records": local_sorted,
        "top_by_ratio": top_ratio,
        "top_by_abs_err": top_err,
        "outputs": {"txt": str(txt_path), "csv": str(csv_path), "json": str(json_path)},
        "git_head": git_cmd(repo, ["git", "rev-parse", "--short", "HEAD"]),
        "git_branch": git_cmd(repo, ["git", "branch", "--show-current"]),
    }
    json_path.write_text(json.dumps(json_payload, indent=2, sort_keys=True))

    lines: List[str] = []
    lines.append("===== LOCALIZED RHO OUTLIER DIAGNOSTIC =====")
    lines.append(f"Generated: {dt.datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"Runbase: {runbase}")
    lines.append(f"Case: {case_dir.name}")
    lines.append(f"Target: {target['file']}")
    lines.append(f"Git branch: {json_payload['git_branch']}")
    lines.append(f"Git HEAD: {json_payload['git_head']}")
    lines.append("")
    lines.append("===== EXECUTIVE CLASSIFICATION =====")
    lines.append(f"Classification: {classification}")
    for reason in reasons:
        lines.append(f"- {reason}")
    lines.append("")
    lines.append("Important limitation: this diagnostic uses per-tile score JSON summaries. It can identify tile-level")
    lines.append("local clustering and boundary patterns, but it cannot inspect within-tile pointwise rho fields unless")
    lines.append("those fields were saved separately.")
    lines.append("")
    lines.append("===== TARGET TILE =====")
    lines.append(f"tile_id: {target['tile_id']}")
    lines.append(f"coords: t{target['t0']}-{target['t1']} x{target['x0']}-{target['x1']} y{target['y0']}-{target['y1']} z{target['z0']}-{target['z1']}")
    lines.append(f"n: {target['n']}")
    lines.append(f"rho_peak_err: {target['rho_peak_err']}")
    lines.append(f"rho_peak_ref: {target['rho_peak_ref']}")
    lines.append(f"rho_tile_ratio: {target['rho_tile_ratio']}")
    lines.append(f"rho_abs_sum: {target['rho_abs_sum']}")
    lines.append(f"global ratio rank: {ratio_rank} / {len(valid)}")
    lines.append(f"global abs_err rank: {err_rank} / {len(valid)}")
    lines.append("")
    lines.append("===== GLOBAL DISTRIBUTION =====")
    for k in [
        "score_files", "loaded_records", "valid_records", "empty_records",
        "ratio_median", "ratio_p90", "ratio_p99", "ratio_p999", "ratio_max",
        "err_median", "err_p90", "err_p99", "err_p999", "err_max",
        "ref_median", "ref_p99", "ref_max",
        "step_t", "step_x", "step_y", "step_z",
    ]:
        lines.append(f"{k}: {global_stats.get(k)}")
    lines.append("")
    lines.append("===== LOCAL RING SUMMARY =====")
    for cheb in range(args.ring + 1):
        members = [r for r in local if r.get("cheb_distance") == cheb]
        valid_members = [r for r in members if r.get("valid")]
        high_threshold = max(0.06, global_stats["ratio_p99"])
        high = [r for r in valid_members if r["rho_tile_ratio"] >= high_threshold]
        max_ratio = max([r["rho_tile_ratio"] for r in valid_members], default=float("nan"))
        max_err = max([abs(r["rho_peak_err"]) for r in valid_members], default=float("nan"))
        lines.append(
            f"cheb_distance={cheb}: total={len(members)} valid={len(valid_members)} "
            f"high_ratio_or_p99_count={len(high)} max_ratio={fnum(max_ratio)} max_abs_err={fnum(max_err)}"
        )
    lines.append("")
    lines.append("===== LOCAL NEIGHBOR TABLE, sorted by ring then ratio =====")
    lines.append("rank rel cheb tile_id coords n rho_err rho_ref ratio file")
    for idx, r in enumerate(local_sorted[:250], 1):
        lines.append(
            f"{idx:03d} {r.get('relation','')} {r.get('cheb_distance','')} "
            f"{int(r.get('tile_id', -1)):06d} "
            f"t{r.get('t0')}-{r.get('t1')} x{r.get('x0')}-{r.get('x1')} "
            f"y{r.get('y0')}-{r.get('y1')} z{r.get('z0')}-{r.get('z1')} "
            f"n={r.get('n')} err={fnum(r.get('rho_peak_err'))} ref={fnum(r.get('rho_peak_ref'))} "
            f"ratio={fnum(r.get('rho_tile_ratio'))} file={r.get('file')}"
        )
    lines.append("")
    lines.append("===== GLOBAL TOP RATIO OUTLIERS =====")
    lines.append("rank tile_id coords n rho_err rho_ref ratio file")
    for idx, r in enumerate(top_ratio, 1):
        lines.append(
            f"{idx:03d} {int(r.get('tile_id', -1)):06d} "
            f"t{r.get('t0')}-{r.get('t1')} x{r.get('x0')}-{r.get('x1')} "
            f"y{r.get('y0')}-{r.get('y1')} z{r.get('z0')}-{r.get('z1')} "
            f"n={r.get('n')} err={fnum(r.get('rho_peak_err'))} ref={fnum(r.get('rho_peak_ref'))} "
            f"ratio={fnum(r.get('rho_tile_ratio'))} file={r.get('file')}"
        )
    lines.append("")
    lines.append("===== GLOBAL TOP ABS_ERR OUTLIERS =====")
    lines.append("rank tile_id coords n rho_err rho_ref ratio file")
    for idx, r in enumerate(top_err, 1):
        lines.append(
            f"{idx:03d} {int(r.get('tile_id', -1)):06d} "
            f"t{r.get('t0')}-{r.get('t1')} x{r.get('x0')}-{r.get('x1')} "
            f"y{r.get('y0')}-{r.get('y1')} z{r.get('z0')}-{r.get('z1')} "
            f"n={r.get('n')} err={fnum(r.get('rho_peak_err'))} ref={fnum(r.get('rho_peak_ref'))} "
            f"ratio={fnum(r.get('rho_tile_ratio'))} file={r.get('file')}"
        )
    lines.append("")
    lines.append("===== OUTPUT FILES =====")
    lines.append(f"Text report: {txt_path}")
    lines.append(f"CSV detail: {csv_path}")
    lines.append(f"JSON detail: {json_path}")
    lines.append("")
    lines.append("STATUS: diagnostic complete")

    txt_path.write_text("\n".join(lines))

    print("")
    print("===== DIAGNOSTIC COMPLETE =====")
    print(f"Classification: {classification}")
    print(f"Text report: {txt_path}")
    print(f"CSV detail: {csv_path}")
    print(f"JSON detail: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
