#!/usr/bin/env python3
"""Corrected Stage 4 three-grid postprocessing.

Preserves the raw exact three-point fit but rejects negative continuum estimates for
nonnegative metrics and reports adjacent-grid zero-limit effective orders.
"""
from __future__ import annotations
import argparse, csv, json, math
from pathlib import Path

NONNEGATIVE = {
    "relative_Bianchi_residual",
    "rho_relative_peak_error",
    "Hessian_Q_normalized_residual",
    "HTR_normalized_residual",
    "action_fit_tensor_difference_percent",
}

def pairwise(qc, qf, hc, hf):
    if qc == 0 or qf == 0 or qc*qf <= 0:
        return None
    return math.log(abs(qc/qf))/math.log(hc/hf)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input-json",required=True,type=Path)
    ap.add_argument("--output-csv",required=True,type=Path)
    args=ap.parse_args()
    data=json.loads(args.input_json.read_text(encoding="utf-8"))
    h61,h71,h81=10/60,10/70,10/80
    rows=[]
    for m in data["three_grid_metrics"]:
        p1=pairwise(m["N61"],m["N71"],h61,h71)
        p2=pairwise(m["N71"],m["N81"],h71,h81)
        raw=m.get("continuum_estimate")
        if not m.get("monotonic"):
            status="NO_EXTRAPOLATION_NONMONOTONIC"; accepted=None
        elif m["metric"] in NONNEGATIVE and raw is not None and raw < 0:
            status="REJECTED_NEGATIVE_LIMIT_FOR_NONNEGATIVE_METRIC"; accepted=None
        elif raw is None:
            status="NO_EXTRAPOLATION"; accepted=None
        else:
            status="PROVISIONAL_EXACT_THREE_POINT_FIT"; accepted=raw
        rows.append({
            "metric":m["metric"],"N61":m["N61"],"N71":m["N71"],"N81":m["N81"],
            "monotonic":m["monotonic"],
            "pairwise_order_N61_N71":p1,
            "pairwise_order_N71_N81":p2,
            "raw_exact_three_point_order":m.get("observed_order"),
            "raw_exact_three_point_continuum":raw,
            "accepted_continuum":accepted,
            "extrapolation_status":status,
        })
    args.output_csv.parent.mkdir(parents=True,exist_ok=True)
    with args.output_csv.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"CORRECTED_POSTPROCESS_RESULT=PASS")
    print(args.output_csv)

if __name__=="__main__":
    main()
