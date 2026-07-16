#!/usr/bin/env python3
"""Run Stage 4 at N71 and perform generalized N61/N71/N81 three-grid analysis."""

from __future__ import annotations
import argparse, csv, hashlib, json, math, os, resource, sys, time, traceback, zipfile
from pathlib import Path
from typing import Any
from scipy.optimize import brentq

os.environ.setdefault("MPLBACKEND", "Agg")

EXPECTED_NOTEBOOK_SHA256 = "1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe"
OLD_BUDGET = "MANUAL_MEMORY_BUDGET_GIB = 28.0"
NEW_BUDGET = "MANUAL_MEMORY_BUDGET_GIB = 160.0"
OLD_REQUEST = "N_REQUESTED = 81"
NEW_REQUEST = "N_REQUESTED = 71"

TABLES = {
    "stage4A": "stage4_dim4_article_exports/stage4A_dim4_bianchi_validation.csv",
    "stage4B": "stage4_dim4_article_exports/stage4B_dim4_hessian_Q_proxy.csv",
    "stage4C_fit": "stage4_dim4_article_exports/stage4C_dim4_fit_parameters.csv",
    "stage4C_rank": "stage4_dim4_article_exports/stage4C_dim4_candidate_ranking.csv",
    "stage4D": "stage4D_action_Q_comparison_exports/stage4D_action_vs_fitted_Q_summary.csv",
}

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def display_fallback(obj: Any) -> None:
    print(obj.to_string() if hasattr(obj, "to_string") else obj)

def read_one(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 1:
        raise RuntimeError(f"Expected one row in {path}; found {len(rows)}")
    return rows[0]

def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def fv(row: dict[str, str], key: str) -> float:
    return float(row[key])

def generalized_order(q1: float, q2: float, q3: float, h1: float, h2: float, h3: float):
    d12, d23 = q1-q2, q2-q3
    if d12 == 0 or d23 == 0 or d12*d23 <= 0:
        return None
    observed = d12/d23
    def func(p):
        denom = h2**p - h3**p
        if denom == 0:
            return math.nan
        return (h1**p - h2**p)/denom - observed
    roots = []
    grid = [0.05 + i*(12.0-0.05)/800 for i in range(801)]
    prev_p, prev_f = grid[0], func(grid[0])
    for p in grid[1:]:
        cur_f = func(p)
        if math.isfinite(prev_f) and math.isfinite(cur_f) and prev_f*cur_f < 0:
            roots.append(brentq(func, prev_p, p))
        prev_p, prev_f = p, cur_f
    if not roots:
        return None
    p = roots[0]
    c = (q2-q3)/(h2**p-h3**p)
    q_inf = q3 - c*h3**p
    fine_error = abs(q3-q_inf)
    fine_rel = fine_error/max(abs(q_inf), 1e-30)
    return {"order": p, "continuum_estimate": q_inf,
            "fine_abs_error_estimate": fine_error,
            "fine_relative_error_estimate": fine_rel}

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--n61-dir", type=Path, required=True)
    ap.add_argument("--n81-dir", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()

    repo, n61, n81, out = map(lambda p: p.resolve(),
                              [args.repo,args.n61_dir,args.n81_dir,args.output_dir])
    notebook = repo/"historical/stages1-5/notebooks/stage4/Spinelli_Alcubierre_Stage4C_DIM4_memory_optimized.ipynb"
    if sha256_file(notebook) != EXPECTED_NOTEBOOK_SHA256:
        raise SystemExit("Notebook SHA mismatch")
    for base in (n61,n81):
        for rel in TABLES.values():
            if not (base/rel).is_file():
                raise SystemExit(f"Missing baseline table: {base/rel}")

    out.mkdir(parents=True, exist_ok=True)
    allowed = {"stage4_n71_three_grid.run.log"}
    unexpected = [p.name for p in out.iterdir() if p.name not in allowed]
    if unexpected:
        raise SystemExit(f"Unexpected preexisting output files: {unexpected}")

    nb = json.loads(notebook.read_text(encoding="utf-8"))
    source = "".join(nb["cells"][3].get("source", []))
    if source.count(OLD_BUDGET) != 1 or source.count(OLD_REQUEST) != 1:
        raise SystemExit("Expected notebook assignments were not found exactly once")
    patched = source.replace(OLD_BUDGET, NEW_BUDGET, 1).replace(OLD_REQUEST, NEW_REQUEST, 1)
    nb["cells"][3]["source"] = patched.splitlines(keepends=True)

    meta: dict[str, Any] = {
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "notebook_sha256": EXPECTED_NOTEBOOK_SHA256,
        "historical_notebook_modified_on_disk": False,
        "in_memory_overrides": [f"{OLD_BUDGET} -> {NEW_BUDGET}",
                                f"{OLD_REQUEST} -> {NEW_REQUEST}"],
        "cells": [],
    }
    ns = {"__name__":"__main__", "__file__":str(notebook), "display":display_fallback}
    old_cwd = Path.cwd()
    os.chdir(out)
    try:
        for idx, cell in enumerate(nb.get("cells", [])):
            if cell.get("cell_type") != "code":
                continue
            code = "".join(cell.get("source", []))
            if not code.strip():
                continue
            print(f"\n===== EXECUTE NOTEBOOK CELL {idx:04d} =====", flush=True)
            t0=time.time()
            rec={"cell_index":idx}
            try:
                exec(compile(code, f"{notebook.name}:cell-{idx}", "exec"), ns, ns)
                rec["status"]="PASS"
            except Exception:
                rec["status"]="FAIL"; rec["traceback"]=traceback.format_exc(); raise
            finally:
                rec["elapsed_seconds"]=time.time()-t0
                rec["max_rss_kib"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                meta["cells"].append(rec)
                try:
                    import matplotlib.pyplot as plt
                    plt.close("all")
                except Exception:
                    pass
            if idx == 3:
                selected={
                    "DIM":int(ns.get("DIM",-1)), "N":int(ns.get("N",-1)),
                    "N_REQUESTED":int(ns.get("N_REQUESTED",-1)),
                    "MANUAL_MEMORY_BUDGET_GIB":float(ns.get("MANUAL_MEMORY_BUDGET_GIB",math.nan)),
                    "R_BUBBLE":float(ns.get("R_BUBBLE",math.nan)),
                    "SIGMA":float(ns.get("SIGMA",math.nan)),
                    "V_S":float(ns.get("V_S",math.nan)),
                    "EXTENT":float(ns.get("EXTENT",math.nan)),
                    "T_EXTENT":float(ns.get("T_EXTENT",math.nan)),
                    "DELTA_TAU":float(ns.get("DELTA_TAU",math.nan)),
                    "INTERIOR_CROP":int(ns.get("INTERIOR_CROP",-1))}
                expected={"DIM":4,"N":71,"N_REQUESTED":71,"MANUAL_MEMORY_BUDGET_GIB":160.0,
                          "R_BUBBLE":3.0,"SIGMA":1.0,"V_S":0.5,"EXTENT":5.0,
                          "T_EXTENT":0.4,"DELTA_TAU":0.04,"INTERIOR_CROP":3}
                if selected != expected:
                    raise RuntimeError(f"N71 configuration mismatch: {selected}")
                meta["selected_configuration"]=selected

        def tables(base):
            a=read_one(base/TABLES["stage4A"])
            b=read_one(base/TABLES["stage4B"])
            c=read_one(base/TABLES["stage4C_fit"])
            d=read_one(base/TABLES["stage4D"])
            ranks=read_rows(base/TABLES["stage4C_rank"])
            best=next(r for r in ranks if r["rank"]=="1")
            return a,b,c,d,best

        t61,t71,t81=tables(n61),tables(out),tables(n81)
        specs=[
          ("relative_Bianchi_residual",0,"relative_Bianchi_residual"),
          ("rho_relative_peak_error",0,"rho_relative_peak_error"),
          ("Hessian_Q_normalized_residual",1,"normalized_Q_conservation_residual"),
          ("HTR_normalized_residual",4,"normalized_residual"),
          ("lambda_fit",2,"lambda_fit"),
          ("beta_fit",2,"beta_fit"),
          ("action_over_fit",3,"residual_ratio_action_over_fit"),
          ("action_fit_tensor_difference_percent",3,"relative_tensor_difference_percent"),
        ]
        h61,h71,h81=10/60,10/70,10/80
        rows=[]
        for name,ix,key in specs:
            q61,q71,q81=fv(t61[ix],key),fv(t71[ix],key),fv(t81[ix],key)
            monotonic=(q61<q71<q81) or (q61>q71>q81)
            fit=generalized_order(q61,q71,q81,h61,h71,h81) if monotonic else None
            row={"metric":name,"N61":q61,"N71":q71,"N81":q81,
                 "monotonic":monotonic,
                 "observed_order":fit["order"] if fit else None,
                 "continuum_estimate":fit["continuum_estimate"] if fit else None,
                 "N81_abs_error_estimate":fit["fine_abs_error_estimate"] if fit else None,
                 "N81_relative_error_estimate":fit["fine_relative_error_estimate"] if fit else None}
            rows.append(row)

        meta["three_grid_metrics"]=rows
        meta["finished_utc"]=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        meta["max_rss_kib"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        meta["run_status"]="PASS"

        (out/"stage4_n71_three_grid_report.json").write_text(json.dumps(meta,indent=2),encoding="utf-8")
        with (out/"stage4_n71_three_grid_comparison.csv").open("w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

        lines=["===== STAGE 4 N61/N71/N81 THREE-GRID ANALYSIS =====",
               f"Notebook SHA256: {EXPECTED_NOTEBOOK_SHA256}",
               "Historical notebook modified on disk: NO",""]
        for r in rows:
            lines.append(f"{r['metric']}: N61={r['N61']:.17g} N71={r['N71']:.17g} "
                         f"N81={r['N81']:.17g} monotonic={r['monotonic']} "
                         f"observed_order={r['observed_order']} continuum={r['continuum_estimate']}")
        lines += ["","STAGE4_N71_RUN_RESULT=PASS"]
        (out/"stage4_n71_three_grid_report.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")

        package=out.parent/f"{out.name}.zip"
        with zipfile.ZipFile(package,"w",zipfile.ZIP_DEFLATED) as zf:
            for p in out.rglob("*"):
                if p.is_file(): zf.write(p,p.relative_to(out))
        print("\n".join(lines),flush=True)
        print(f"PACKAGE={package}",flush=True)
        return 0
    finally:
        os.chdir(old_cwd)

if __name__ == "__main__":
    raise SystemExit(main())
