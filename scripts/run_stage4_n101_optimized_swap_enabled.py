#!/usr/bin/env python3
"""Optimized Stage 4 N101 swap-enabled production runner.

The historical notebook is SHA-verified and never modified on disk.
Only configuration cell 3 and late cells 23/24 are changed in memory.
This production runner emits canonical tables, metrics, and a memory profile.
"""

from __future__ import annotations

import argparse
import csv
import ctypes
import gc
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

import numpy as np
import pandas as pd

EXPECTED_NOTEBOOK_SHA256 = "1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe"
EXPECTED_CELL3_SHA256 = "5a49221d2ba22d35ee05b94fa968dfc9e1628ccc5d228e08712264db8f5291a5"
EXPECTED_CELL23_SHA256 = "18dfd79cd2b9fe41b798714d1e2f80f6a53ffab7f0eb39a4abe3d98954326957"
EXPECTED_CELL24_SHA256 = "6528d7dedf482b7590ebf983c79e21ed9670673a570b319533a4f02367fbf1af"

OLD_BUDGET = "MANUAL_MEMORY_BUDGET_GIB = 28.0"
OLD_REQUEST = "N_REQUESTED = 81"
OLD_DTAU = "DELTA_TAU = 0.04"

TABLES = [
    (
        "stage4A",
        "stage4_dim4_article_exports/"
        "stage4A_dim4_bianchi_validation.csv",
    ),
    (
        "stage4B",
        "stage4_dim4_article_exports/"
        "stage4B_dim4_hessian_Q_proxy.csv",
    ),
    (
        "stage4C_fit",
        "stage4_dim4_article_exports/"
        "stage4C_dim4_fit_parameters.csv",
    ),
    (
        "stage4C_ranking",
        "stage4_dim4_article_exports/"
        "stage4C_dim4_candidate_ranking.csv",
    ),
    (
        "stage4D_comparison",
        "stage4D_action_Q_comparison_exports/"
        "stage4D_action_vs_fitted_Q_comparison.csv",
    ),
    (
        "stage4D_summary",
        "stage4D_action_Q_comparison_exports/"
        "stage4D_action_vs_fitted_Q_summary.csv",
    ),
]

OPTIMIZED_CELL24 = '\n# ============================================================\n# STAGE 4D / ACTION-DERIVED Q TEST — STREAMING MEMORY VERSION\n# ============================================================\n\nimport numpy as np\nimport pandas as pd\nimport matplotlib.pyplot as plt\nfrom pathlib import Path\nimport zipfile\nimport json\nimport gc\nimport ctypes\n\nEXPORT_DIR = Path("stage4D_action_Q_comparison_exports")\nEXPORT_DIR.mkdir(parents=True, exist_ok=True)\n\nDPI = 180\nBETA_ACTION = -1.0\nLAMBDA_ACTION = float(lambda_fit)\nBETA_FIT = float(beta_fit)\nLAMBDA_FIT = float(lambda_fit)\n\nprint("Stage 4D action-derived Q comparison")\nprint(f"lambda_fit  = {LAMBDA_FIT}")\nprint(f"beta_fit    = {BETA_FIT}")\nprint(f"beta_action = {BETA_ACTION}")\nprint("Memory mode = streaming sequential tensor scoring")\n\n\ndef savefig(path):\n    plt.tight_layout()\n    plt.savefig(path, dpi=DPI, bbox_inches="tight")\n    plt.close()\n\n\ndef central_slice_scalar(field, geom):\n    coords = geom["coords"]\n    dim = geom["dim"]\n    if dim == 3:\n        t, x, y = coords\n        it0 = int(np.argmin(np.abs(t)))\n        return field[it0, :, :].copy(), x, y\n    if dim == 4:\n        t, x, y, z = coords\n        it0 = int(np.argmin(np.abs(t)))\n        iz0 = int(np.argmin(np.abs(z)))\n        return field[it0, :, :, iz0].copy(), x, y\n    raise ValueError("Only DIM=3 or DIM=4 supported.")\n\n\ndef central_residual_slice(C, geom):\n    coords = geom["coords"]\n    if geom["dim"] == 3:\n        t, x, y = coords\n        it0 = int(np.argmin(np.abs(t)))\n        data = np.zeros((len(x), len(y)), dtype=C.dtype)\n        for a in range(C.shape[0]):\n            data += C[a, it0, :, :] ** 2\n        return np.sqrt(data), x, y\n    t, x, y, z = coords\n    it0 = int(np.argmin(np.abs(t)))\n    iz0 = int(np.argmin(np.abs(z)))\n    data = np.zeros((len(x), len(y)), dtype=C.dtype)\n    for a in range(C.shape[0]):\n        data += C[a, it0, :, :, iz0] ** 2\n    return np.sqrt(data), x, y\n\n\ndef plot_slice(data, x, y, title, colorbar_label, filename):\n    plt.figure(figsize=(7, 6))\n    plt.imshow(\n        data.T,\n        extent=[x[0], x[-1], y[0], y[-1]],\n        origin="lower",\n        aspect="equal",\n    )\n    plt.colorbar(label=colorbar_label)\n    plt.title(title)\n    plt.xlabel("x")\n    plt.ylabel("y")\n    savefig(EXPORT_DIR / filename)\n\n\ndef release_memory():\n    gc.collect()\n    try:\n        ctypes.CDLL("libc.so.6").malloc_trim(0)\n    except Exception:\n        pass\n\n\ndef score_and_capture(label, Q_cov):\n    Q_mix = mix_tensor_up_down(Q_cov, geom["gi"])\n    C = divergence_mixed(Q_mix, geom["Gamma"], geom["spacings"])\n\n    Q_L2 = float(l2_norm_tensor(Q_mix, crop=INTERIOR_CROP))\n    C_L2 = float(l2_norm_tensor(C, crop=INTERIOR_CROP))\n    normalized = C_L2 / Q_L2 if Q_L2 > 0 else np.nan\n\n    q00_slice, xs, ys = central_slice_scalar(Q_cov[0, 0], geom)\n    residual_slice, _, _ = central_residual_slice(C, geom)\n\n    score = {\n        "label": label,\n        "Q_L2": Q_L2,\n        "C_L2": C_L2,\n        "normalized_residual": normalized,\n    }\n\n    del Q_mix, C\n    release_memory()\n    return score, q00_slice, residual_slice, xs, ys\n\n\n# Best fitted HTR\nQ_fit, _ = make_Q_candidate(\n    geom,\n    candidate="HTR",\n    lam=LAMBDA_FIT,\n    beta=BETA_FIT,\n    aux=aux_H,\n)\nscore_fit, Qfit_slice, Cfit_slice, xs, ys = score_and_capture(\n    "Best fitted HTR", Q_fit\n)\ndel Q_fit\nrelease_memory()\n\n# Action-predicted HTR\nQ_action, _ = make_Q_candidate(\n    geom,\n    candidate="HTR",\n    lam=LAMBDA_ACTION,\n    beta=BETA_ACTION,\n    aux=aux_H,\n)\nscore_action, Qaction_slice, Caction_slice, _, _ = score_and_capture(\n    "Action-predicted beta=-1", Q_action\n)\ndel Q_action\nrelease_memory()\n\n# Difference can be generated directly:\n# Q_action - Q_fit = (beta_action - beta_fit) S G\nQ_difference = np.empty_like(geom["Einstein"])\nnp.multiply(geom["Einstein"], geom["S"], out=Q_difference)\nQ_difference *= BETA_ACTION - BETA_FIT\n\nscore_difference, Qdiff_slice, Cdiff_slice, _, _ = score_and_capture(\n    "Difference action - fit", Q_difference\n)\ndel Q_difference\nrelease_memory()\n\nrelative_diff_action_vs_fit = (\n    score_difference["Q_L2"] / score_fit["Q_L2"]\n    if score_fit["Q_L2"] > 0\n    else np.nan\n)\ndiff_L2 = score_difference["Q_L2"]\nfit_L2 = score_fit["Q_L2"]\n\nresidual_ratio_action_over_fit = (\n    score_action["normalized_residual"] / score_fit["normalized_residual"]\n    if score_fit["normalized_residual"] > 0\n    else np.nan\n)\nresidual_penalty_percent = 100.0 * (residual_ratio_action_over_fit - 1.0)\nrelative_tensor_difference_percent = 100.0 * relative_diff_action_vs_fit\n\ndf_stage4D = pd.DataFrame([\n    {\n        "case": "Best fitted HTR",\n        "lambda": LAMBDA_FIT,\n        "beta": BETA_FIT,\n        "Q_L2": score_fit["Q_L2"],\n        "C_L2": score_fit["C_L2"],\n        "normalized_residual": score_fit["normalized_residual"],\n        "relative_tensor_difference_vs_fit": 0.0,\n    },\n    {\n        "case": "Action-predicted beta=-1",\n        "lambda": LAMBDA_ACTION,\n        "beta": BETA_ACTION,\n        "Q_L2": score_action["Q_L2"],\n        "C_L2": score_action["C_L2"],\n        "normalized_residual": score_action["normalized_residual"],\n        "relative_tensor_difference_vs_fit": relative_diff_action_vs_fit,\n    },\n    {\n        "case": "Difference action - fit",\n        "lambda": np.nan,\n        "beta": BETA_ACTION - BETA_FIT,\n        "Q_L2": score_difference["Q_L2"],\n        "C_L2": score_difference["C_L2"],\n        "normalized_residual": score_difference["normalized_residual"],\n        "relative_tensor_difference_vs_fit": relative_diff_action_vs_fit,\n    },\n])\n\ndf_stage4D.to_csv(\n    EXPORT_DIR / "stage4D_action_vs_fitted_Q_comparison.csv",\n    index=False,\n)\ndisplay(df_stage4D)\n\nprint("\\nKey interpretation numbers")\nprint(\n    f"Relative tensor difference action vs fit: "\n    f"{relative_tensor_difference_percent:.4f}%"\n)\nprint(f"Action residual / fitted residual: {residual_ratio_action_over_fit:.6f}")\nprint(f"Residual penalty of action tensor: {residual_penalty_percent:.4f}%")\n\nsummary = {\n    "DIM": int(geom["dim"]),\n    "N": int(geom["N"]),\n    "lambda_fit": LAMBDA_FIT,\n    "beta_fit": BETA_FIT,\n    "beta_action": BETA_ACTION,\n    "relative_tensor_difference_action_vs_fit": float(\n        relative_diff_action_vs_fit\n    ),\n    "relative_tensor_difference_percent": float(\n        relative_tensor_difference_percent\n    ),\n    "fitted_normalized_residual": float(\n        score_fit["normalized_residual"]\n    ),\n    "action_normalized_residual": float(\n        score_action["normalized_residual"]\n    ),\n    "residual_ratio_action_over_fit": float(\n        residual_ratio_action_over_fit\n    ),\n    "residual_penalty_percent": float(residual_penalty_percent),\n}\n\nwith open(\n    EXPORT_DIR / "stage4D_action_vs_fitted_Q_summary.json",\n    "w",\n    encoding="utf-8",\n) as stream:\n    json.dump(summary, stream, indent=2)\n\npd.DataFrame([summary]).to_csv(\n    EXPORT_DIR / "stage4D_action_vs_fitted_Q_summary.csv",\n    index=False,\n)\n\nplt.figure(figsize=(8, 5))\nplt.barh(\n    df_stage4D["case"],\n    df_stage4D["normalized_residual"],\n)\nplt.xscale("log")\nplt.title("Stage 4D: conservation residual comparison")\nplt.xlabel("normalized residual")\nplt.gca().invert_yaxis()\nplt.grid(True, which="both", axis="x", alpha=0.3)\nsavefig(EXPORT_DIR / "stage4D_residual_comparison.png")\n\nplt.figure(figsize=(8, 5))\nplt.barh(\n    ["Action vs fitted tensor difference"],\n    [relative_tensor_difference_percent],\n)\nplt.title("Stage 4D: action-predicted tensor difference from fitted HTR")\nplt.xlabel("relative tensor difference (%)")\nplt.grid(True, axis="x", alpha=0.3)\nsavefig(EXPORT_DIR / "stage4D_relative_tensor_difference_percent.png")\n\nplot_slice(\n    Qfit_slice,\n    xs,\n    ys,\n    "Stage 4D: fitted HTR Q_00",\n    "Q_fit_00",\n    "stage4D_Q00_fitted_HTR.png",\n)\nplot_slice(\n    Qaction_slice,\n    xs,\n    ys,\n    "Stage 4D: action-predicted Q_00, beta=-1",\n    "Q_action_00",\n    "stage4D_Q00_action_beta_minus_1.png",\n)\nplot_slice(\n    Qdiff_slice,\n    xs,\n    ys,\n    "Stage 4D: Q_00 difference, action minus fitted",\n    "Q_action_00 - Q_fit_00",\n    "stage4D_Q00_difference_action_minus_fit.png",\n)\n\nplot_slice(\n    Cfit_slice,\n    xs,\n    ys,\n    "Stage 4D: fitted HTR residual magnitude",\n    "|nabla_mu Q_fit^mu_nu|",\n    "stage4D_residual_map_fitted_HTR.png",\n)\nplot_slice(\n    Caction_slice,\n    xs,\n    ys,\n    "Stage 4D: action-predicted residual magnitude",\n    "|nabla_mu Q_action^mu_nu|",\n    "stage4D_residual_map_action_beta_minus_1.png",\n)\nplot_slice(\n    Cdiff_slice,\n    xs,\n    ys,\n    "Stage 4D: residual difference magnitude",\n    "|nabla_mu (Q_action - Q_fit)^mu_nu|",\n    "stage4D_residual_map_difference.png",\n)\n\nrho_slice, _, _ = central_slice_scalar(geom["rho_A"], geom)\nix0 = int(np.argmin(np.abs(xs)))\nrho_cut = rho_slice[ix0, :]\nfit_cut = Qfit_slice[ix0, :]\naction_cut = Qaction_slice[ix0, :]\ndiff_cut = Qdiff_slice[ix0, :]\n\nrho_norm = (\n    rho_cut / np.max(np.abs(rho_cut))\n    if np.max(np.abs(rho_cut)) > 0\n    else rho_cut\n)\nfit_norm = (\n    fit_cut / np.max(np.abs(fit_cut))\n    if np.max(np.abs(fit_cut)) > 0\n    else fit_cut\n)\naction_norm = (\n    action_cut / np.max(np.abs(action_cut))\n    if np.max(np.abs(action_cut)) > 0\n    else action_cut\n)\n\nplt.figure(figsize=(8, 5))\nplt.plot(ys, rho_norm, label="rho_A / max|rho_A|")\nplt.plot(ys, fit_norm, label="fitted HTR Q_00 / max|Q_00|")\nplt.plot(\n    ys,\n    action_norm,\n    label="action beta=-1 Q_00 / max|Q_00|",\n    linestyle="--",\n)\nplt.title("Stage 4D: fitted vs action-predicted Q_00 at x=0")\nplt.xlabel("y")\nplt.ylabel("normalized amplitude")\nplt.legend()\nplt.grid(True, alpha=0.3)\nsavefig(EXPORT_DIR / "stage4D_Q00_linecut_fitted_vs_action_vs_rhoA.png")\n\nplt.figure(figsize=(8, 5))\nplt.plot(ys, diff_cut, label="Q_action_00 - Q_fit_00")\nplt.title("Stage 4D: Q_00 difference line cut at x=0")\nplt.xlabel("y")\nplt.ylabel("difference amplitude")\nplt.legend()\nplt.grid(True, alpha=0.3)\nsavefig(EXPORT_DIR / "stage4D_Q00_difference_linecut.png")\n\nreadme = f"""# Stage 4D action-derived Q comparison\n\nMemory mode: streaming sequential tensor scoring.\n\nDIM = {int(geom["dim"])}\nN = {int(geom["N"])}\nlambda_fit = {LAMBDA_FIT}\nbeta_fit = {BETA_FIT}\nbeta_action = {BETA_ACTION}\n\nRelative tensor difference action vs fit = {relative_tensor_difference_percent:.6f} %\nFitted normalized residual = {score_fit["normalized_residual"]}\nAction normalized residual = {score_action["normalized_residual"]}\nAction residual / fitted residual = {residual_ratio_action_over_fit}\nResidual penalty percent = {residual_penalty_percent:.6f} %\n"""\n\nwith open(EXPORT_DIR / "README.txt", "w", encoding="utf-8") as stream:\n    stream.write(readme)\n\nzip_path = Path(str(EXPORT_DIR) + ".zip")\nif zip_path.exists():\n    zip_path.unlink()\n\nwith zipfile.ZipFile(\n    zip_path,\n    "w",\n    compression=zipfile.ZIP_DEFLATED,\n) as archive:\n    for file_path in EXPORT_DIR.rglob("*"):\n        archive.write(\n            file_path,\n            arcname=file_path.relative_to(EXPORT_DIR),\n        )\n\nprint("\\nEXPORT COMPLETE")\nprint("Folder:", EXPORT_DIR.resolve())\nprint("ZIP:", zip_path.resolve())\n\nfor name in [\n    "Qfit_slice",\n    "Qaction_slice",\n    "Qdiff_slice",\n    "Cfit_slice",\n    "Caction_slice",\n    "Cdiff_slice",\n    "rho_slice",\n    "rho_cut",\n    "fit_cut",\n    "action_cut",\n    "diff_cut",\n    "rho_norm",\n    "fit_norm",\n    "action_norm",\n]:\n    globals().pop(name, None)\nrelease_memory()\n'


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def current_rss_kib() -> int:
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    except Exception:
        pass
    return 0


def release_memory() -> None:
    gc.collect()
    try:
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except Exception:
        pass


def display_fallback(obj: Any) -> None:
    print(obj.to_string() if hasattr(obj, "to_string") else obj)


def array_inventory(namespace: dict[str, Any]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    seen: set[int] = set()

    def add(name: str, value: Any) -> None:
        if not isinstance(value, np.ndarray):
            return
        identity = id(value)
        if identity in seen:
            return
        seen.add(identity)
        records.append({
            "name": name,
            "shape": list(value.shape),
            "dtype": str(value.dtype),
            "nbytes": int(value.nbytes),
        })

    for name, value in namespace.items():
        add(name, value)
        if isinstance(value, dict) and name in {"geom", "aux_H"}:
            for key, child in value.items():
                add(f"{name}.{key}", child)

    records.sort(key=lambda item: item["nbytes"], reverse=True)
    return {
        "total_unique_array_bytes": sum(item["nbytes"] for item in records),
        "array_count": len(records),
        "largest_arrays": records[:30],
    }


def patch_cell23(source: str) -> str:
    ranking_start = source.index("df_direct_candidates = None")
    ranking_end = source.index(
        'df_direct_candidates = df_direct_candidates.sort_values',
        ranking_start,
    )

    streaming_ranking = r"""
import ctypes

rows = []

for candidate, lam, beta, label in DIRECT_CANDIDATE_SPECS:
    print(f"Computing direct candidate: {label}")
    t0 = time.time()

    Q, Qmix, C, score = make_tensor_candidate_and_score(
        geom,
        candidate=candidate,
        lam=lam,
        beta=beta,
        aux=aux_H,
    )

    score["candidate"] = label
    rows.append(score)

    print(
        f"  done in {time.time() - t0:.1f} s, "
        f"C/Q={score['C_over_Q']:.6g}"
    )

    del Q, Qmix, C
    gc.collect()
    try:
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except Exception:
        pass

df_direct_candidates = pd.DataFrame(rows)

"""
    source = (
        source[:ranking_start]
        + streaming_ranking
        + source[ranking_end:]
    )

    best_start = source.index(
        "if best_candidate_label not in candidate_details:"
    )
    best_end = source.index(
        "# -----------------------------\n# Summary README",
        best_start,
    )

    streaming_best = r"""
if best_candidate_label.startswith("H ") or best_candidate_label == "H":
    cand, lam, beta = "H", 0.0, 0.0
elif best_candidate_label.startswith("HTR"):
    cand, lam, beta = "HTR", lambda_fit, beta_fit
elif best_candidate_label.startswith("HT"):
    cand, lam, beta = "HT", lambda_fit, 0.0
elif best_candidate_label.startswith("R"):
    cand, lam, beta = "R", 0.0, beta_fit
else:
    cand, lam, beta = "HTR", lambda_fit, beta_fit

Q_best, Qmix_best, C_best, _ = make_tensor_candidate_and_score(
    geom,
    candidate=cand,
    lam=lam,
    beta=beta,
    aux=aux_H,
)

C_best_mag = make_residual_magnitude(C_best)

plot_central_scalar(
    Q_best[0, 0],
    geom,
    f"Stage 4C DIM=4: best candidate Q_00 ({best_candidate_label})",
    "Q_best_00",
    "stage4C_dim4_best_Q00.png",
)

plot_central_scalar(
    C_best_mag,
    geom,
    f"Stage 4C DIM=4: best candidate residual magnitude ({best_candidate_label})",
    "|nabla_mu Q^mu_nu|",
    "stage4C_dim4_best_residual_map.png",
)

Qbest_slice, xs, ys = central_slice_scalar(Q_best[0, 0], geom)
rho_slice, _, _ = central_slice_scalar(rho_A, geom)

ix0 = int(np.argmin(np.abs(xs)))
rho_cut = rho_slice[ix0, :]
Q_cut = Qbest_slice[ix0, :]

rho_norm = (
    rho_cut / np.max(np.abs(rho_cut))
    if np.max(np.abs(rho_cut)) > 0
    else rho_cut
)
Q_norm = (
    Q_cut / np.max(np.abs(Q_cut))
    if np.max(np.abs(Q_cut)) > 0
    else Q_cut
)

plt.figure(figsize=(8, 5))
plt.plot(ys, rho_norm, label="rho_A / max|rho_A|")
plt.plot(
    ys,
    Q_norm,
    label=f"{best_candidate_label} Q_00 / max|Q_00|",
)
plt.title("Stage 4C DIM=4: best Q_00 proxy versus classical rho_A at x=0")
plt.xlabel("y")
plt.ylabel("normalized amplitude")
plt.legend()
plt.grid(True, alpha=0.3)
savefig(EXPORT_DIR / "stage4C_dim4_best_Q00_vs_rhoA_cut.png")

del Q_best, Qmix_best, C_best, C_best_mag
gc.collect()
try:
    ctypes.CDLL("libc.so.6").malloc_trim(0)
except Exception:
    pass

"""
    source = source[:best_start] + streaming_best + source[best_end:]

    source += r"""

# Release all full late-export arrays before Stage 4D.
for _large_name in [
    "rho_num",
    "rho_error",
    "divG_mag",
    "C_H_mag",
    "A",
    "B",
    "D",
    "a",
    "b",
    "d",
    "M",
    "target",
    "res_H",
    "res_HT",
    "res_R",
    "res_HTR",
    "Q_H",
    "Qmix_H",
    "C_H",
    "df_candidates",
]:
    globals().pop(_large_name, None)
gc.collect()
try:
    ctypes.CDLL("libc.so.6").malloc_trim(0)
except Exception:
    pass
"""
    return source


def compare_tables(
    output: Path,
    reference: Path,
    rtol: float,
    atol: float,
) -> tuple[bool, list[dict[str, Any]]]:
    results: list[dict[str, Any]] = []
    overall = True

    for label, relative in TABLES:
        produced_path = output / relative
        reference_path = reference / relative

        produced = pd.read_csv(produced_path)
        expected = pd.read_csv(reference_path)

        record: dict[str, Any] = {
            "table": label,
            "relative_path": relative,
            "shape_produced": list(produced.shape),
            "shape_reference": list(expected.shape),
            "columns_match": list(produced.columns) == list(expected.columns),
            "max_abs_difference": 0.0,
            "max_relative_difference": 0.0,
            "numeric_outside_tolerance": 0,
            "text_mismatches": 0,
            "status": "PASS",
        }

        if produced.shape != expected.shape or not record["columns_match"]:
            record["status"] = "FAIL"
            overall = False
            results.append(record)
            continue

        for column in produced.columns:
            pcol = produced[column]
            ecol = expected[column]

            if pd.api.types.is_numeric_dtype(pcol) and pd.api.types.is_numeric_dtype(ecol):
                pa = pcol.to_numpy(dtype=float)
                ea = ecol.to_numpy(dtype=float)

                both_nan = np.isnan(pa) & np.isnan(ea)
                valid = ~both_nan
                close = np.isclose(
                    pa,
                    ea,
                    rtol=rtol,
                    atol=atol,
                    equal_nan=True,
                )
                record["numeric_outside_tolerance"] += int(
                    np.count_nonzero(~close)
                )

                if np.any(valid):
                    abs_diff = np.abs(pa[valid] - ea[valid])
                    denom = np.maximum(np.abs(ea[valid]), atol)
                    rel_diff = abs_diff / denom
                    record["max_abs_difference"] = max(
                        record["max_abs_difference"],
                        float(np.max(abs_diff)),
                    )
                    record["max_relative_difference"] = max(
                        record["max_relative_difference"],
                        float(np.max(rel_diff)),
                    )
            else:
                ps = pcol.fillna("<NA>").astype(str).to_numpy()
                es = ecol.fillna("<NA>").astype(str).to_numpy()
                record["text_mismatches"] += int(np.count_nonzero(ps != es))

        if (
            record["numeric_outside_tolerance"] > 0
            or record["text_mismatches"] > 0
        ):
            record["status"] = "FAIL"
            overall = False

        results.append(record)

    return overall, results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--target-n", type=int, default=101)
    parser.add_argument("--memory-budget-gib", type=float, default=220.0)
    parser.add_argument("--delta-tau", type=float, default=0.04)
    parser.add_argument("--rtol", type=float, default=1e-8)
    parser.add_argument("--atol", type=float, default=1e-10)
    args = parser.parse_args()

    if args.target_n != 101:
        raise SystemExit(
            f"This production runner is locked to N=101; got {args.target_n}"
        )

    repo = args.repo.resolve()
    output = args.output_dir.resolve()
    notebook = (
        repo
        / "historical/stages1-5/notebooks/stage4/"
        "Spinelli_Alcubierre_Stage4C_DIM4_memory_optimized.ipynb"
    )

    if sha256_file(notebook) != EXPECTED_NOTEBOOK_SHA256:
        raise SystemExit("Notebook SHA mismatch")

    notebook_data = json.loads(notebook.read_text(encoding="utf-8"))
    original_cell3 = "".join(notebook_data["cells"][3]["source"])
    original_cell23 = "".join(notebook_data["cells"][23]["source"])
    original_cell24 = "".join(notebook_data["cells"][24]["source"])

    cell_hashes = {
        "cell3": sha256_text(original_cell3),
        "cell23": sha256_text(original_cell23),
        "cell24": sha256_text(original_cell24),
    }
    expected_hashes = {
        "cell3": EXPECTED_CELL3_SHA256,
        "cell23": EXPECTED_CELL23_SHA256,
        "cell24": EXPECTED_CELL24_SHA256,
    }
    if cell_hashes != expected_hashes:
        raise SystemExit(
            f"Notebook cell-source hash mismatch: {cell_hashes}"
        )

    target_budget = (
        f"MANUAL_MEMORY_BUDGET_GIB = {args.memory_budget_gib:.1f}"
    )
    target_request = f"N_REQUESTED = {args.target_n}"
    target_dtau = f"DELTA_TAU = {args.delta_tau:.12g}"

    for anchor in [OLD_BUDGET, OLD_REQUEST, OLD_DTAU]:
        if original_cell3.count(anchor) != 1:
            raise SystemExit(f"Configuration anchor mismatch: {anchor}")

    patched_cell3 = (
        original_cell3
        .replace(OLD_BUDGET, target_budget, 1)
        .replace(OLD_REQUEST, target_request, 1)
        .replace(OLD_DTAU, target_dtau, 1)
    )
    patched_cell23 = patch_cell23(original_cell23)

    notebook_data["cells"][3]["source"] = patched_cell3.splitlines(
        keepends=True
    )
    notebook_data["cells"][23]["source"] = patched_cell23.splitlines(
        keepends=True
    )
    notebook_data["cells"][24]["source"] = OPTIMIZED_CELL24.splitlines(
        keepends=True
    )

    output.mkdir(parents=True, exist_ok=True)
    allowed = {
        "stage4_n101_optimized_swap_enabled.run.log",
    }
    unexpected = [
        path.name for path in output.iterdir()
        if path.name not in allowed
    ]
    if unexpected:
        raise SystemExit(
            f"Unexpected preexisting output files: {sorted(unexpected)}"
        )

    metadata: dict[str, Any] = {
        "started_utc": time.strftime(
            "%Y-%m-%dT%H:%M:%SZ",
            time.gmtime(),
        ),
        "notebook_sha256": EXPECTED_NOTEBOOK_SHA256,
        "historical_notebook_modified_on_disk": False,
        "original_cell_hashes": cell_hashes,
        "patched_cell_hashes": {
            "cell3": sha256_text(patched_cell3),
            "cell23": sha256_text(patched_cell23),
            "cell24": sha256_text(OPTIMIZED_CELL24),
        },
        "target_N": args.target_n,
        "target_delta_tau": args.delta_tau,
        "memory_budget_gib": args.memory_budget_gib,
        "optimization": {
            "cell23": "stream_candidates_and_release",
            "cell24": "sequential_fit_action_difference_scoring",
        },
        "cells": [],
    }

    namespace: dict[str, Any] = {
        "__name__": "__main__",
        "__file__": str(notebook),
        "display": display_fallback,
    }

    previous_cwd = Path.cwd()
    os.chdir(output)
    run_error = None
    try:
        for index, cell in enumerate(notebook_data.get("cells", [])):
            if cell.get("cell_type") != "code":
                continue
            source = "".join(cell.get("source", []))
            if not source.strip():
                continue

            print(
                f"\n===== EXECUTE NOTEBOOK CELL {index:04d} =====",
                flush=True,
            )
            started = time.time()
            record: dict[str, Any] = {
                "cell_index": index,
                "started_utc": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ",
                    time.gmtime(),
                ),
                "current_rss_before_kib": current_rss_kib(),
                "max_rss_before_kib": resource.getrusage(
                    resource.RUSAGE_SELF
                ).ru_maxrss,
            }
            try:
                exec(
                    compile(
                        source,
                        f"{notebook.name}:cell-{index}",
                        "exec",
                    ),
                    namespace,
                    namespace,
                )
                record["status"] = "PASS"
            except Exception:
                record["status"] = "FAIL"
                record["traceback"] = traceback.format_exc()
                run_error = record["traceback"]
                raise
            finally:
                release_memory()
                record["elapsed_seconds"] = time.time() - started
                record["current_rss_after_kib"] = current_rss_kib()
                record["max_rss_after_kib"] = resource.getrusage(
                    resource.RUSAGE_SELF
                ).ru_maxrss
                record["array_inventory_after"] = array_inventory(namespace)
                metadata["cells"].append(record)

            if index == 3:
                selected = {
                    "DIM": int(namespace.get("DIM", -1)),
                    "N": int(namespace.get("N", -1)),
                    "N_REQUESTED": int(
                        namespace.get("N_REQUESTED", -1)
                    ),
                    "MANUAL_MEMORY_BUDGET_GIB": float(
                        namespace.get(
                            "MANUAL_MEMORY_BUDGET_GIB",
                            math.nan,
                        )
                    ),
                    "DELTA_TAU": float(
                        namespace.get("DELTA_TAU", math.nan)
                    ),
                }
                expected = {
                    "DIM": 4,
                    "N": args.target_n,
                    "N_REQUESTED": args.target_n,
                    "MANUAL_MEMORY_BUDGET_GIB": args.memory_budget_gib,
                    "DELTA_TAU": args.delta_tau,
                }
                if selected != expected:
                    raise RuntimeError(
                        f"Selected configuration mismatch: "
                        f"{selected} != {expected}"
                    )
                metadata["selected_configuration"] = selected

        # Extract canonical metrics for production reporting.
        def one_row(relative: str) -> dict[str, str]:
            with (output / relative).open(
                newline="",
                encoding="utf-8-sig",
            ) as stream:
                rows = list(csv.DictReader(stream))
            if len(rows) != 1:
                raise RuntimeError(
                    f"Expected one row in {relative}; found {len(rows)}"
                )
            return rows[0]

        stage4a = one_row(TABLES[0][1])
        stage4b = one_row(TABLES[1][1])
        stage4c = one_row(TABLES[2][1])
        stage4d = one_row(TABLES[5][1])
        with (output / TABLES[3][1]).open(
            newline="",
            encoding="utf-8-sig",
        ) as stream:
            ranking_rows = list(csv.DictReader(stream))
        best = next(row for row in ranking_rows if row["rank"] == "1")

        metrics = {
            "relative_Bianchi_residual": float(
                stage4a["relative_Bianchi_residual"]
            ),
            "rho_relative_peak_error": float(
                stage4a["rho_relative_peak_error"]
            ),
            "Hessian_Q_normalized_residual": float(
                stage4b["normalized_Q_conservation_residual"]
            ),
            "HTR_normalized_residual": float(
                best["normalized_residual"]
            ),
            "lambda_fit": float(stage4c["lambda_fit"]),
            "beta_fit": float(stage4c["beta_fit"]),
            "action_over_fit": float(
                stage4d["residual_ratio_action_over_fit"]
            ),
            "action_fit_tensor_difference_percent": float(
                stage4d["relative_tensor_difference_percent"]
            ),
            "action_residual_penalty_percent": float(
                stage4d["residual_penalty_percent"]
            ),
            "HTR_improvement_over_H": float(
                stage4c["improvement_HTR_over_H"]
            ),
        }

        metadata["metrics"] = metrics
        metadata["comparison_status"] = "NOT_APPLICABLE_PRODUCTION"
        metadata["finished_utc"] = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ",
            time.gmtime(),
        )
        metadata["max_rss_kib"] = resource.getrusage(
            resource.RUSAGE_SELF
        ).ru_maxrss
        metadata["current_rss_final_kib"] = current_rss_kib()
        metadata["run_status"] = "PASS"

        report_json = output / "stage4_n101_optimized_swap_enabled_report.json"
        report_txt = output / "stage4_n101_optimized_swap_enabled_report.txt"
        profile_csv = output / "stage4_n101_optimized_swap_enabled_memory_profile.csv"
        metrics_csv = output / "stage4_n101_optimized_swap_enabled_metrics.csv"

        report_json.write_text(
            json.dumps(metadata, indent=2),
            encoding="utf-8",
        )

        with profile_csv.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as stream:
            fields = [
                "cell_index",
                "status",
                "elapsed_seconds",
                "current_rss_before_kib",
                "current_rss_after_kib",
                "max_rss_before_kib",
                "max_rss_after_kib",
                "array_bytes_after",
                "array_count_after",
            ]
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for record in metadata["cells"]:
                inventory = record["array_inventory_after"]
                writer.writerow({
                    "cell_index": record["cell_index"],
                    "status": record["status"],
                    "elapsed_seconds": record["elapsed_seconds"],
                    "current_rss_before_kib": record[
                        "current_rss_before_kib"
                    ],
                    "current_rss_after_kib": record[
                        "current_rss_after_kib"
                    ],
                    "max_rss_before_kib": record[
                        "max_rss_before_kib"
                    ],
                    "max_rss_after_kib": record[
                        "max_rss_after_kib"
                    ],
                    "array_bytes_after": inventory[
                        "total_unique_array_bytes"
                    ],
                    "array_count_after": inventory["array_count"],
                })

        with metrics_csv.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=["N", "DELTA_TAU", *metrics.keys()],
            )
            writer.writeheader()
            writer.writerow({
                "N": args.target_n,
                "DELTA_TAU": args.delta_tau,
                **metrics,
            })

        lines = [
            "===== STAGE 4 N101 OPTIMIZED SWAP-ENABLED PRODUCTION RUN =====",
            f"Notebook SHA256: {EXPECTED_NOTEBOOK_SHA256}",
            "Historical notebook modified on disk: NO",
            f"Selected N: {args.target_n}",
            f"Selected DELTA_TAU: {args.delta_tau}",
            (
                "Peak RSS GiB: "
                f"{metadata['max_rss_kib']/1048576:.9f}"
            ),
            "",
            "===== METRICS =====",
        ]
        for name, metric_value in metrics.items():
            lines.append(f"{name}: {metric_value:.17g}")
        lines += [
            "",
            "STAGE4_N101_SWAP_ENABLED_RUN_RESULT=PASS",
        ]
        report_txt.write_text(
            "\n".join(lines) + "\n",
            encoding="utf-8",
        )
        print("\n".join(lines), flush=True)

        package = output.parent / f"{output.name}.zip"
        if package.exists():
            package.unlink()
        with zipfile.ZipFile(
            package,
            "w",
            zipfile.ZIP_DEFLATED,
        ) as archive:
            for path in output.rglob("*"):
                if path.is_file():
                    archive.write(path, path.relative_to(output))
        print(f"PACKAGE={package}", flush=True)
        return 0
    finally:
        os.chdir(previous_cwd)


if __name__ == "__main__":
    raise SystemExit(main())
