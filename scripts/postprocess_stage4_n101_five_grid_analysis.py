#!/usr/bin/env python3
"""Create N61/N71/N81/N91/N101 analysis and recommend N111 execution mode."""

from __future__ import annotations
import argparse, csv, json, math, re
from pathlib import Path
from typing import Any
import numpy as np

TABLES = {
    "stage4A": "stage4_dim4_article_exports/stage4A_dim4_bianchi_validation.csv",
    "stage4B": "stage4_dim4_article_exports/stage4B_dim4_hessian_Q_proxy.csv",
    "stage4C_fit": "stage4_dim4_article_exports/stage4C_dim4_fit_parameters.csv",
    "stage4C_rank": "stage4_dim4_article_exports/stage4C_dim4_candidate_ranking.csv",
    "stage4D": "stage4D_action_Q_comparison_exports/stage4D_action_vs_fitted_Q_summary.csv",
}
PRINCIPAL = [
    "relative_Bianchi_residual",
    "rho_relative_peak_error",
    "Hessian_Q_normalized_residual",
    "HTR_normalized_residual",
]

def one(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows=list(csv.DictReader(f))
    if len(rows)!=1:
        raise RuntimeError(f"Expected one row in {path}; found {len(rows)}")
    return rows[0]

def rows(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def extract(base: Path):
    a=one(base/TABLES["stage4A"])
    b=one(base/TABLES["stage4B"])
    c=one(base/TABLES["stage4C_fit"])
    d=one(base/TABLES["stage4D"])
    best=next(r for r in rows(base/TABLES["stage4C_rank"]) if r["rank"]=="1")
    return {
        "relative_Bianchi_residual":float(a["relative_Bianchi_residual"]),
        "rho_relative_peak_error":float(a["rho_relative_peak_error"]),
        "Hessian_Q_normalized_residual":float(b["normalized_Q_conservation_residual"]),
        "HTR_normalized_residual":float(best["normalized_residual"]),
        "lambda_fit":float(c["lambda_fit"]),
        "beta_fit":float(c["beta_fit"]),
        "action_over_fit":float(d["residual_ratio_action_over_fit"]),
        "action_fit_tensor_difference_percent":float(d["relative_tensor_difference_percent"]),
        "action_residual_penalty_percent":float(d["residual_penalty_percent"]),
        "HTR_improvement_over_H":float(c["improvement_HTR_over_H"]),
    }

def order(qc,qf,hc,hf):
    if qc<=0 or qf<=0: return None
    return math.log(qc/qf)/math.log(hc/hf)

def parse_time(path: Path):
    text=path.read_text(encoding="utf-8",errors="replace")
    def integer(pattern):
        m=re.search(pattern,text)
        return int(m.group(1)) if m else None
    m=re.search(r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\):\s*(\S+)",text)
    elapsed=None
    if m:
        p=m.group(1).split(":")
        elapsed=sum(float(x)*60**i for i,x in enumerate(reversed(p)))
    return {
        "maximum_resident_set_size_kib":integer(r"Maximum resident set size \(kbytes\):\s*(\d+)"),
        "swaps":integer(r"Swaps:\s*(\d+)"),
        "exit_status":integer(r"Exit status:\s*(\d+)"),
        "elapsed_seconds":elapsed,
    }

def read_samples(path: Path):
    with path.open(newline="",encoding="utf-8") as f:
        data=list(csv.DictReader(f))
    numeric=[]
    for r in data:
        try:
            numeric.append({
                "vmrss_kib":int(r["vmrss_kib"]),
                "vmswap_kib":int(r["vmswap_kib"]),
                "memavailable_kib":int(r["memavailable_kib"]),
                "system_swap_used_kib":int(r["system_swap_used_kib"]),
            })
        except (ValueError,KeyError):
            pass
    return {
        "sample_count":len(numeric),
        "max_vmrss_gib":max((r["vmrss_kib"] for r in numeric),default=0)/1048576,
        "max_vmswap_gib":max((r["vmswap_kib"] for r in numeric),default=0)/1048576,
        "min_memavailable_gib":min((r["memavailable_kib"] for r in numeric),default=0)/1048576,
        "max_system_swap_used_gib":max((r["system_swap_used_kib"] for r in numeric),default=0)/1048576,
    }

def main():
    ap=argparse.ArgumentParser()
    for n in [61,71,81,91,101]:
        ap.add_argument(f"--n{n}-dir",required=True,type=Path)
    ap.add_argument("--output-dir",required=True,type=Path)
    args=ap.parse_args()
    grids={n:getattr(args,f"n{n}_dir").resolve() for n in [61,71,81,91,101]}
    vals={n:extract(p) for n,p in grids.items()}
    h={n:10/(n-1) for n in grids}
    pairs=[(61,71),(71,81),(81,91),(91,101)]
    outrows=[]
    for metric in vals[61]:
        row={"metric":metric}
        for n in grids: row[f"N{n}"]=vals[n][metric]
        for c,f in pairs: row[f"order_N{c}_N{f}"]=order(vals[c][metric],vals[f][metric],h[c],h[f])
        row["descriptive_five_grid_log_slope"]=(
            float(np.polyfit(np.log([h[n] for n in grids]),np.log([vals[n][metric] for n in grids]),1)[0])
            if metric in PRINCIPAL and all(vals[n][metric]>0 for n in grids) else None
        )
        outrows.append(row)

    monotonic=all(
        vals[61][m]>vals[71][m]>vals[81][m]>vals[91][m]>vals[101][m]
        for m in PRINCIPAL
    )
    n101_report=json.loads((grids[101]/"stage4_n101_optimized_swap_enabled_report.json").read_text())
    timing=parse_time(grids[101]/"stage4_n101_optimized_swap_enabled.run.log")
    samples=read_samples(grids[101]/"stage4_n101_resource_samples.csv")
    peak_gib=n101_report["max_rss_kib"]/1048576
    projected_n111=peak_gib*(111/101)**4
    process_pass=(
        n101_report.get("run_status")=="PASS"
        and timing["exit_status"]==0
        and all(c.get("status")=="PASS" for c in n101_report.get("cells",[]))
    )

    if not process_pass:
        recommendation="REPAIR_N101_EXECUTION_BEFORE_N111"
        rationale="N101 did not complete cleanly."
    elif not monotonic:
        recommendation="INVESTIGATE_N101_SPATIAL_TREND_BEFORE_N111"
        rationale="At least one principal residual did not continue its monotonic decrease."
    else:
        recommendation="BUILD_N111_SWAP_ENABLED_RUNNER"
        rationale="N101 passed and the principal five-grid trends remain monotonic; physical RAM is not a hard gate."

    summary={
        "analysis_status":"PASS" if process_pass else "FAIL",
        "principal_spatial_monotonic_N61_to_N101":monotonic,
        "metric_rows":outrows,
        "resource":{
            "measured_N101_peak_rss_gib":peak_gib,
            "measured_N101_runtime_seconds":timing["elapsed_seconds"],
            "time_swaps":timing["swaps"],
            "exit_status":timing["exit_status"],
            "resource_samples":samples,
            "projected_N111_peak_from_measured_N101_gib":projected_n111,
        },
        "phase6_recommendation":recommendation,
        "phase6_rationale":rationale,
        "execution_policy":"SWAP_ALLOWED_AND_MEASURED",
    }
    out=args.output_dir.resolve()
    out.mkdir(parents=True,exist_ok=True)
    (out/"stage4_n101_five_grid_report.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    with (out/"stage4_n101_five_grid_metrics.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(outrows[0].keys())); w.writeheader(); w.writerows(outrows)
    lines=[
        "===== STAGE 4 N101 FIVE-GRID ANALYSIS =====",
        f"Principal spatial monotonicity: {monotonic}",
        f"Measured N101 peak RSS: {peak_gib:.6f} GiB",
        f"Measured N101 runtime: {timing['elapsed_seconds']} seconds",
        f"Maximum sampled process VmSwap: {samples['max_vmswap_gib']:.6f} GiB",
        f"Maximum sampled system swap used: {samples['max_system_swap_used_gib']:.6f} GiB",
        f"Projected N111 peak: {projected_n111:.6f} GiB",
        f"PHASE6_RECOMMENDATION={recommendation}",
        f"PHASE6_RATIONALE={rationale}",
        f"STAGE4_N101_FIVE_GRID_ANALYSIS_RESULT={summary['analysis_status']}",
    ]
    (out/"stage4_n101_five_grid_report.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines))
    return 0 if process_pass else 1

if __name__=="__main__":
    raise SystemExit(main())
