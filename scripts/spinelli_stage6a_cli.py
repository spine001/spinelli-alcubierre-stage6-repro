#!/usr/bin/env python3
"""
Spinelli Stage 6A command-line runner.

Purpose:
- Run Stage 6A without VS Code/Jupyter.
- Execute each case in a separate Python process.
- Save per-case checkpoints immediately.
- Resume after crash/power interruption.
- Keep outputs separated by N/dtype/case mode.

Important:
- Do not use a RAM disk for this calculation on a 64 GiB machine. A RAM disk consumes RAM.
- For overflow protection, use SSD-backed swap and disk-backed outputs/checkpoints.
"""

from __future__ import annotations

import argparse
import csv
import gc
import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# Non-interactive backend for command-line runs.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Runtime globals. These are set by configure_runtime().
RUN_STAGE6A = True
DTYPE_NAME = "float64"
DTYPE = np.float64
OUTPUT_DIR = Path("stage6A_wall_focused_sigma4_outputs")
EXTENT = 5.0
T_EXTENT = 0.4
DELTA_TAU = 0.04
INTERIOR_CROP = 3
WALL_K = 3.0
SAVE_CASE_PLOTS = True
MAKE_ZIP = True
DPI = 170


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def configure_runtime(args) -> None:
    global DTYPE_NAME, DTYPE, OUTPUT_DIR, EXTENT, T_EXTENT, DELTA_TAU
    global INTERIOR_CROP, WALL_K, SAVE_CASE_PLOTS, MAKE_ZIP, DPI
    DTYPE_NAME = args.dtype
    DTYPE = np.float64 if DTYPE_NAME == "float64" else np.float32
    OUTPUT_DIR = Path(args.output_dir).expanduser().resolve()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    EXTENT = float(args.extent)
    T_EXTENT = float(args.t_extent)
    DELTA_TAU = float(args.delta_tau)
    INTERIOR_CROP = int(args.interior_crop)
    WALL_K = float(args.wall_k)
    SAVE_CASE_PLOTS = bool(args.save_plots)
    MAKE_ZIP = bool(args.make_zip)
    DPI = int(args.dpi)


def get_cases(case_mode: str):
    if case_mode == "sigma4_core":
        return [
            {"v_s": 0.5, "sigma": 4.0, "R": 3.0},
            {"v_s": 1.0, "sigma": 4.0, "R": 3.0},
        ]
    if case_mode == "sigma4_full":
        return [
            {"v_s": v_s, "sigma": 4.0, "R": R}
            for v_s in [0.25, 0.5, 0.75, 1.0]
            for R in [2.0, 3.0, 4.0]
        ]
    if case_mode == "sharp_wall_full":
        return [
            {"v_s": v_s, "sigma": sigma, "R": R}
            for v_s in [0.25, 0.5, 0.75, 1.0]
            for sigma in [2.0, 4.0]
            for R in [2.0, 3.0, 4.0]
        ]
    raise ValueError(f"Unknown case mode: {case_mode}")


def system_report(output_dir: Path):
    try:
        import psutil
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        ram_total = vm.total / (1024**3)
        ram_available = vm.available / (1024**3)
        swap_total = swap.total / (1024**3)
        swap_used = swap.used / (1024**3)
        ram_used_percent = vm.percent
        swap_used_percent = swap.percent
    except Exception:
        ram_total = ram_available = swap_total = swap_used = ram_used_percent = swap_used_percent = float("nan")
    disk = shutil.disk_usage(str(output_dir))
    return {
        "time_utc": now_utc(),
        "platform": platform.platform(),
        "cpu_count_logical": os.cpu_count(),
        "ram_total_GiB": ram_total,
        "ram_available_GiB": ram_available,
        "ram_used_percent": ram_used_percent,
        "swap_total_GiB": swap_total,
        "swap_used_GiB": swap_used,
        "swap_used_percent": swap_used_percent,
        "output_disk_free_GiB": disk.free / (1024**3),
        "output_dir": str(output_dir),
    }


def estimate_stage6a_case_memory_gib(N: int, dtype_name: str):
    bytes_per = 8 if dtype_name == "float64" else 4
    scalar_gib = (N**4) * bytes_per / (1024**3)
    # This implementation transiently holds many scalar-equivalent tensor fields.
    conservative_multiplier = 240
    return scalar_gib, scalar_gib * conservative_multiplier


def preflight_check(N: int, dtype_name: str, output_dir: Path, min_free_ram_gib: float, allow_high_memory: bool):
    report = system_report(output_dir)
    scalar_gib, estimated_gib = estimate_stage6a_case_memory_gib(N, dtype_name)
    print("=" * 72, flush=True)
    print(f"Stage 6A CLI preflight check for N={N}, dtype={dtype_name}", flush=True)
    print("=" * 72, flush=True)
    print(f"Platform: {report['platform']}", flush=True)
    print(f"Logical CPUs: {report['cpu_count_logical']}", flush=True)
    print(f"RAM total: {report['ram_total_GiB']:.2f} GiB", flush=True)
    print(f"RAM available now: {report['ram_available_GiB']:.2f} GiB", flush=True)
    print(f"Swap total: {report['swap_total_GiB']:.2f} GiB", flush=True)
    print(f"Swap used: {report['swap_used_GiB']:.2f} GiB", flush=True)
    print(f"Output disk free: {report['output_disk_free_GiB']:.2f} GiB", flush=True)
    print(f"One scalar field: {scalar_gib:.3f} GiB", flush=True)
    print(f"Conservative estimated case memory: {estimated_gib:.1f} GiB", flush=True)
    print("=" * 72, flush=True)

    ok = True
    if report["ram_available_GiB"] == report["ram_available_GiB"] and report["ram_available_GiB"] < min_free_ram_gib:
        print("WARNING: available RAM is below requested minimum.", flush=True)
        ok = False
    if report["ram_total_GiB"] == report["ram_total_GiB"] and estimated_gib > report["ram_total_GiB"] * 0.90:
        print("WARNING: estimated memory is above safe RAM capacity.", flush=True)
        ok = False
    if not ok and not allow_high_memory:
        return False
    if not ok and allow_high_memory:
        print("Proceeding anyway because --allow-high-memory was supplied.", flush=True)
    return True


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)
    os.replace(tmp, path)


def atomic_write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, index=False)
    os.replace(tmp, path)


# ---- Original numerical routines extracted from Stage 6A notebook ----


# ============================================================
# IMPORTS AND UTILITY FUNCTIONS
# ============================================================

import os
import gc
import json
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

DTYPE = np.float64 if DTYPE_NAME == "float64" else np.float32
DPI = 170

def savefig(path):
    plt.tight_layout()
    plt.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close()

def estimate_scalar_gib(N, dim=4, dtype=DTYPE):
    return (N**dim) * np.dtype(dtype).itemsize / (1024**3)

def alcubierre_shape(rs, R, sigma):
    return (
        np.tanh(sigma * (rs + R)) - np.tanh(sigma * (rs - R))
    ) / (2.0 * np.tanh(sigma * R))

def central_indices(coords):
    it0 = int(np.argmin(np.abs(coords[0])))
    if len(coords) == 4:
        iz0 = int(np.argmin(np.abs(coords[3])))
        return it0, iz0
    return it0, None

def central_slice(field, coords):
    it0, iz0 = central_indices(coords)
    if len(coords) == 4:
        return field[it0, :, :, iz0], coords[1], coords[2]
    return field[it0, :, :], coords[1], coords[2]

def plot_central_scalar(field, coords, title, label, filename):
    data, x, y = central_slice(field, coords)
    plt.figure(figsize=(7, 6))
    plt.imshow(
        data.T,
        extent=[x[0], x[-1], y[0], y[-1]],
        origin="lower",
        aspect="equal"
    )
    plt.colorbar(label=label)
    plt.title(title)
    plt.xlabel("x")
    plt.ylabel("y")
    savefig(filename)

def safe_ratio(a, b):
    return float(a / b) if b not in (0, 0.0) and np.isfinite(b) else np.nan

def make_case_label(N, v_s, sigma, R):
    return f"N{N}_v{v_s:g}_sigma{sigma:g}_R{R:g}".replace(".", "p")

def make_masks(shape, rs, R, sigma, crop=3, wall_k=3.0):
    dim = len(shape)
    interior = np.ones(shape, dtype=bool)
    for ax in range(dim):
        slicer_low = [slice(None)] * dim
        slicer_high = [slice(None)] * dim
        slicer_low[ax] = slice(0, crop)
        slicer_high[ax] = slice(-crop, None)
        interior[tuple(slicer_low)] = False
        interior[tuple(slicer_high)] = False

    wall_half_width = wall_k / sigma
    wall = np.abs(rs - R) <= wall_half_width
    wall_interior = wall & interior

    return interior, wall_interior, wall_half_width

def l2_vector(vec, mask):
    total = 0.0
    for a in range(vec.shape[0]):
        vals = vec[a][mask]
        total += np.mean(vals * vals)
    return float(np.sqrt(total))

def l2_tensor(tensor, mask):
    total = 0.0
    for a in range(tensor.shape[0]):
        for b in range(tensor.shape[1]):
            vals = tensor[a, b][mask]
            total += np.mean(vals * vals)
    return float(np.sqrt(total))

def vector_magnitude(vec):
    return np.sqrt(sum(vec[a]**2 for a in range(vec.shape[0])))

def mixed_tensor(Q_cov, gi):
    dim = Q_cov.shape[0]
    Qmix = np.zeros_like(Q_cov)
    for a in range(dim):
        for b in range(dim):
            total = np.zeros(Q_cov.shape[2:], dtype=Q_cov.dtype)
            for c in range(dim):
                total += gi[a, c] * Q_cov[c, b]
            Qmix[a, b] = total
    return Qmix

def divergence_mixed_tensor(Tmix, Gamma, spacings):
    # C_nu = nabla_mu T^mu_nu
    dim = Tmix.shape[0]
    shape = Tmix.shape[2:]
    C = np.zeros((dim,) + shape, dtype=Tmix.dtype)

    for n in range(dim):
        for m in range(dim):
            C[n] += np.gradient(Tmix[m, n], *spacings, edge_order=2)[m]

        for m in range(dim):
            for l in range(dim):
                C[n] += Gamma[m, m, l] * Tmix[l, n]
                C[n] -= Gamma[l, m, n] * Tmix[m, l]

    return C



# ============================================================
# CORE GEOMETRY BUILD: DIM=4 ALCUBIERRE METRIC
# ============================================================

def build_geometry_dim4(N, v_s, sigma, R, extent=EXTENT, t_extent=T_EXTENT, delta_tau=DELTA_TAU, dtype=DTYPE):
    # Build geometry fields for the DIM=4 Alcubierre metric.
    # This avoids storing the full dGamma tensor.

    t = np.linspace(-t_extent, t_extent, N, dtype=dtype)
    x = np.linspace(-extent, extent, N, dtype=dtype)
    y = np.linspace(-extent, extent, N, dtype=dtype)
    z = np.linspace(-extent, extent, N, dtype=dtype)
    coords = [t, x, y, z]
    spacings = [float(c[1] - c[0]) for c in coords]

    T, X, Y, Z = np.meshgrid(t, x, y, z, indexing="ij")
    shape = T.shape

    def f_shift(dtau):
        rs_shift = np.sqrt((X - dtype(v_s) * (T + dtype(dtau)))**2 + Y**2 + Z**2)
        return alcubierre_shape(rs_shift, dtype(R), dtype(sigma)).astype(dtype)

    rs = np.sqrt((X - dtype(v_s) * T)**2 + Y**2 + Z**2).astype(dtype)
    f = alcubierre_shape(rs, dtype(R), dtype(sigma)).astype(dtype)

    fm = f_shift(-delta_tau)
    fp = f_shift(delta_tau)
    D2f = ((fp - 2.0 * f + fm) / (delta_tau**2)).astype(dtype)
    S = (D2f * D2f).astype(dtype)

    del T, X, Y, Z, fm, fp
    gc.collect()

    dim = 4

    g = np.zeros((dim, dim) + shape, dtype=dtype)
    gi = np.zeros_like(g)

    g[0, 0] = -1.0 + v_s**2 * f**2
    g[0, 1] = -v_s * f
    g[1, 0] = -v_s * f
    g[1, 1] = 1.0
    g[2, 2] = 1.0
    g[3, 3] = 1.0

    gi[0, 0] = -1.0
    gi[0, 1] = -v_s * f
    gi[1, 0] = -v_s * f
    gi[1, 1] = 1.0 - v_s**2 * f**2
    gi[2, 2] = 1.0
    gi[3, 3] = 1.0

    # Gradients of f.
    df = np.zeros((dim,) + shape, dtype=dtype)
    grads_f = np.gradient(f, *spacings, edge_order=2)
    for a in range(dim):
        df[a] = grads_f[a].astype(dtype)
    del grads_f
    gc.collect()

    def dg_component(mu, nu, alpha):
        if mu == 0 and nu == 0:
            return 2.0 * v_s**2 * f * df[alpha]
        if (mu == 0 and nu == 1) or (mu == 1 and nu == 0):
            return -v_s * df[alpha]
        return 0.0

    # Christoffel symbols.
    Gamma = np.zeros((dim, dim, dim) + shape, dtype=dtype)
    for a in range(dim):
        for m in range(dim):
            for n in range(dim):
                total = np.zeros(shape, dtype=dtype)
                for l in range(dim):
                    term = dg_component(n, l, m)
                    term2 = dg_component(m, l, n)
                    term3 = dg_component(m, n, l)

                    # Handle zero scalars without allocating arrays.
                    if not isinstance(term, float):
                        total += gi[a, l] * term
                    elif term != 0.0:
                        total += gi[a, l] * term

                    if not isinstance(term2, float):
                        total += gi[a, l] * term2
                    elif term2 != 0.0:
                        total += gi[a, l] * term2

                    if not isinstance(term3, float):
                        total -= gi[a, l] * term3
                    elif term3 != 0.0:
                        total -= gi[a, l] * term3

                Gamma[a, m, n] = 0.5 * total

    # Ricci tensor, without storing dGamma.
    Ricci = np.zeros((dim, dim) + shape, dtype=dtype)

    for m in range(dim):
        for n in range(dim):
            total = np.zeros(shape, dtype=dtype)

            for a in range(dim):
                total += np.gradient(Gamma[a, m, n], *spacings, edge_order=2)[a]
                total -= np.gradient(Gamma[a, m, a], *spacings, edge_order=2)[n]

                for b in range(dim):
                    total += Gamma[a, a, b] * Gamma[b, m, n]
                    total -= Gamma[a, n, b] * Gamma[b, m, a]

            Ricci[m, n] = total

    Rsc = np.zeros(shape, dtype=dtype)
    for m in range(dim):
        for n in range(dim):
            Rsc += gi[m, n] * Ricci[m, n]

    Einstein = np.zeros((dim, dim) + shape, dtype=dtype)
    for m in range(dim):
        for n in range(dim):
            Einstein[m, n] = Ricci[m, n] - 0.5 * g[m, n] * Rsc

    Gmix = mixed_tensor(Einstein, gi)
    divG = divergence_mixed_tensor(Gmix, Gamma, spacings)

    # Hessian of S.
    dS = np.zeros((dim,) + shape, dtype=dtype)
    grads_S = np.gradient(S, *spacings, edge_order=2)
    for a in range(dim):
        dS[a] = grads_S[a].astype(dtype)
    del grads_S
    gc.collect()

    ddS = np.zeros((dim, dim) + shape, dtype=dtype)
    for a in range(dim):
        grads = np.gradient(dS[a], *spacings, edge_order=2)
        for b in range(dim):
            ddS[a, b] = grads[b].astype(dtype)
        del grads
        gc.collect()

    Hess = np.zeros((dim, dim) + shape, dtype=dtype)
    for a in range(dim):
        for b in range(dim):
            Hess[a, b] = ddS[a, b]
            for l in range(dim):
                Hess[a, b] -= Gamma[l, a, b] * dS[l]

    del ddS
    gc.collect()

    BoxS = np.zeros(shape, dtype=dtype)
    for a in range(dim):
        for b in range(dim):
            BoxS += gi[a, b] * Hess[a, b]

    rho_A = -(v_s**2) / (32.0 * np.pi) * (df[2]**2 + df[3]**2)

    n_vec = np.zeros((dim,) + shape, dtype=dtype)
    n_vec[0] = 1.0
    n_vec[1] = v_s * f

    rho_num = np.zeros(shape, dtype=dtype)
    for a in range(dim):
        for b in range(dim):
            rho_num += Einstein[a, b] * n_vec[a] * n_vec[b]
    rho_num = rho_num / (8.0 * np.pi)

    interior_mask, wall_mask, wall_half_width = make_masks(
        shape=shape,
        rs=rs,
        R=R,
        sigma=sigma,
        crop=INTERIOR_CROP,
        wall_k=WALL_K
    )

    return {
        "dim": dim,
        "N": N,
        "v_s": float(v_s),
        "sigma": float(sigma),
        "R": float(R),
        "extent": float(extent),
        "t_extent": float(t_extent),
        "delta_tau": float(delta_tau),
        "coords": coords,
        "spacings": spacings,
        "shape": shape,
        "wall_half_width": float(wall_half_width),
        "interior_mask": interior_mask,
        "wall_mask": wall_mask,
        "rs": rs,
        "f": f,
        "S": S,
        "g": g,
        "gi": gi,
        "Gamma": Gamma,
        "Ricci": Ricci,
        "Einstein": Einstein,
        "Gmix": Gmix,
        "divG": divG,
        "Hess": Hess,
        "BoxS": BoxS,
        "dS": dS,
        "rho_A": rho_A,
        "rho_num": rho_num,
    }



# ============================================================
# ACTION/FIT TENSOR CONSTRUCTION AND SCORING
# ============================================================

def make_Q_HTR(geom, lam, beta):
    # Q = Hess(S) - g Box(S) - lam g S + beta S G
    dim = geom["dim"]
    g = geom["g"]
    Hess = geom["Hess"]
    BoxS = geom["BoxS"]
    S = geom["S"]
    G = geom["Einstein"]

    Q = np.zeros((dim, dim) + geom["shape"], dtype=g.dtype)

    for a in range(dim):
        for b in range(dim):
            Q[a, b] = Hess[a, b] - g[a, b] * BoxS - lam * g[a, b] * S + beta * S * G[a, b]

    return Q

def analytic_residual_fit(geom, mask):
    # Fit lambda and beta using:
    # A - lambda B + beta D ≈ 0
    dim = geom["dim"]
    Ricci = geom["Ricci"]
    Einstein = geom["Einstein"]
    gi = geom["gi"]
    dS_cov = geom["dS"]

    gradS_up = np.zeros_like(dS_cov)
    for l in range(dim):
        for a in range(dim):
            gradS_up[l] += gi[l, a] * dS_cov[a]

    A = np.zeros_like(dS_cov)
    B = np.zeros_like(dS_cov)
    D = np.zeros_like(dS_cov)

    for nu in range(dim):
        B[nu] = dS_cov[nu]

        for lam in range(dim):
            A[nu] += Ricci[nu, lam] * gradS_up[lam]

        for mu in range(dim):
            D[nu] += Einstein[mu, nu] * gradS_up[mu]

    a = []
    b = []
    d = []

    for nu in range(dim):
        a.append(A[nu][mask].ravel())
        b.append(B[nu][mask].ravel())
        d.append(D[nu][mask].ravel())

    a = np.concatenate(a)
    b = np.concatenate(b)
    d = np.concatenate(d)

    M = np.vstack([-b, d]).T
    target = -a

    params, *_ = np.linalg.lstsq(M, target, rcond=None)
    lam_fit = float(params[0])
    beta_fit = float(params[1])

    res_H = a
    res_HT = a - lam_fit * b
    res_R = a + beta_fit * d
    res_HTR = a - lam_fit * b + beta_fit * d
    res_action = a - lam_fit * b - 1.0 * d

    def rms(v):
        return float(np.sqrt(np.mean(v * v)))

    return {
        "lambda_fit": lam_fit,
        "beta_fit": beta_fit,
        "analytic_residual_H": rms(res_H),
        "analytic_residual_HT": rms(res_HT),
        "analytic_residual_R": rms(res_R),
        "analytic_residual_HTR": rms(res_HTR),
        "analytic_residual_action": rms(res_action),
        "analytic_action_over_fit": safe_ratio(rms(res_action), rms(res_HTR)),
    }

def score_Q(geom, Q, mask):
    Qmix = mixed_tensor(Q, geom["gi"])
    C = divergence_mixed_tensor(Qmix, geom["Gamma"], geom["spacings"])
    Q_L2 = l2_tensor(Qmix, mask)
    C_L2 = l2_vector(C, mask)
    return {
        "Qmix": Qmix,
        "C": C,
        "Q_L2": Q_L2,
        "C_L2": C_L2,
        "normalized_residual": safe_ratio(C_L2, Q_L2),
    }

def relative_tensor_difference(geom, Q_A, Q_B, mask):
    QA = mixed_tensor(Q_A, geom["gi"])
    QB = mixed_tensor(Q_B, geom["gi"])
    D = QA - QB
    D_L2 = l2_tensor(D, mask)
    B_L2 = l2_tensor(QB, mask)
    return safe_ratio(D_L2, B_L2)

def positive_integral_ratio(geom, Q, mask):
    Q00 = Q[0, 0]
    rho = geom["rho_A"]

    dV = np.prod(geom["spacings"][1:])
    pos_Q = np.maximum(Q00[mask], 0.0)
    abs_rho = np.abs(rho[mask])

    num = float(np.sum(pos_Q) * dV)
    den = float(np.sum(abs_rho) * dV)

    ratio = safe_ratio(num, den)
    eta_needed = safe_ratio(1.0, ratio) if ratio and np.isfinite(ratio) else np.nan

    return ratio, eta_needed

def rho_error_metrics(geom, mask):
    err = geom["rho_num"] - geom["rho_A"]
    peak_err = float(np.max(np.abs(err[mask])))
    peak_ref = float(np.max(np.abs(geom["rho_A"][mask])))
    return peak_err, safe_ratio(peak_err, peak_ref)

def bianchi_metric(geom, mask):
    return safe_ratio(l2_vector(geom["divG"], mask), l2_tensor(geom["Gmix"], mask))



# ============================================================
# RUN ONE CASE
# ============================================================

def run_one_stage6A_case(N, v_s, sigma, R, save_plots=SAVE_CASE_PLOTS):
    label = make_case_label(N, v_s, sigma, R)
    case_dir = OUTPUT_DIR / label
    case_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*72)
    print("Running case:", label)
    print(f"N={N}, v_s={v_s}, sigma={sigma}, R={R}")
    print("Estimated one scalar GiB:", estimate_scalar_gib(N, dim=4))
    print("="*72)

    t0 = time.time()

    geom = build_geometry_dim4(N=N, v_s=v_s, sigma=sigma, R=R)

    interior = geom["interior_mask"]
    wall = geom["wall_mask"]

    fit_global = analytic_residual_fit(geom, interior)
    fit_wall = analytic_residual_fit(geom, wall)

    Q_fit_global = make_Q_HTR(geom, lam=fit_global["lambda_fit"], beta=fit_global["beta_fit"])
    Q_action_global = make_Q_HTR(geom, lam=fit_global["lambda_fit"], beta=-1.0)

    Q_fit_wall = make_Q_HTR(geom, lam=fit_wall["lambda_fit"], beta=fit_wall["beta_fit"])
    Q_action_wall = make_Q_HTR(geom, lam=fit_wall["lambda_fit"], beta=-1.0)

    score_fit_global_on_global = score_Q(geom, Q_fit_global, interior)
    score_action_global_on_global = score_Q(geom, Q_action_global, interior)

    score_fit_global_on_wall = score_Q(geom, Q_fit_global, wall)
    score_action_global_on_wall = score_Q(geom, Q_action_global, wall)

    score_fit_wall_on_wall = score_Q(geom, Q_fit_wall, wall)
    score_action_wall_on_wall = score_Q(geom, Q_action_wall, wall)

    rel_diff_global = relative_tensor_difference(geom, Q_action_global, Q_fit_global, interior)
    rel_diff_global_on_wall = relative_tensor_difference(geom, Q_action_global, Q_fit_global, wall)
    rel_diff_wall = relative_tensor_difference(geom, Q_action_wall, Q_fit_wall, wall)

    qratio_global, eta_global = positive_integral_ratio(geom, Q_action_global, interior)
    qratio_wall, eta_wall = positive_integral_ratio(geom, Q_action_wall, wall)

    bianchi_global = bianchi_metric(geom, interior)
    bianchi_wall = bianchi_metric(geom, wall)

    rho_peak_err_global, rho_rel_err_global = rho_error_metrics(geom, interior)
    rho_peak_err_wall, rho_rel_err_wall = rho_error_metrics(geom, wall)

    elapsed = time.time() - t0

    row = {
        "N": N,
        "v_s": v_s,
        "sigma": sigma,
        "R": R,
        "wall_half_width": geom["wall_half_width"],
        "elapsed_seconds": elapsed,

        "lambda_fit_global": fit_global["lambda_fit"],
        "beta_fit_global": fit_global["beta_fit"],
        "lambda_fit_wall": fit_wall["lambda_fit"],
        "beta_fit_wall": fit_wall["beta_fit"],

        "analytic_residual_H_global": fit_global["analytic_residual_H"],
        "analytic_residual_HTR_global": fit_global["analytic_residual_HTR"],
        "analytic_residual_action_global": fit_global["analytic_residual_action"],
        "analytic_action_over_fit_global": fit_global["analytic_action_over_fit"],

        "analytic_residual_H_wall": fit_wall["analytic_residual_H"],
        "analytic_residual_HTR_wall": fit_wall["analytic_residual_HTR"],
        "analytic_residual_action_wall": fit_wall["analytic_residual_action"],
        "analytic_action_over_fit_wall": fit_wall["analytic_action_over_fit"],

        "bianchi_global": bianchi_global,
        "bianchi_wall": bianchi_wall,

        "rho_relative_peak_error_global": rho_rel_err_global,
        "rho_relative_peak_error_wall": rho_rel_err_wall,

        "fit_global_residual_global": score_fit_global_on_global["normalized_residual"],
        "action_global_residual_global": score_action_global_on_global["normalized_residual"],
        "action_over_fit_global": safe_ratio(
            score_action_global_on_global["normalized_residual"],
            score_fit_global_on_global["normalized_residual"]
        ),
        "relative_tensor_difference_global": rel_diff_global,

        "fit_global_residual_wall": score_fit_global_on_wall["normalized_residual"],
        "action_global_residual_wall": score_action_global_on_wall["normalized_residual"],
        "action_over_fit_global_on_wall": safe_ratio(
            score_action_global_on_wall["normalized_residual"],
            score_fit_global_on_wall["normalized_residual"]
        ),
        "relative_tensor_difference_global_on_wall": rel_diff_global_on_wall,

        "fit_wall_residual_wall": score_fit_wall_on_wall["normalized_residual"],
        "action_wall_residual_wall": score_action_wall_on_wall["normalized_residual"],
        "action_over_fit_wall": safe_ratio(
            score_action_wall_on_wall["normalized_residual"],
            score_fit_wall_on_wall["normalized_residual"]
        ),
        "relative_tensor_difference_wall": rel_diff_wall,

        "positive_Q00_over_abs_rho_global": qratio_global,
        "eta_needed_global": eta_global,
        "positive_Q00_over_abs_rho_wall": qratio_wall,
        "eta_needed_wall": eta_wall,
    }

    pd.DataFrame([row]).to_csv(case_dir / "case_summary.csv", index=False)

    with open(case_dir / "case_summary.json", "w", encoding="utf-8") as f:
        json.dump(row, f, indent=2)

    if save_plots:
        coords = geom["coords"]

        plot_central_scalar(geom["rho_A"], coords, f"{label}: known rho_A", "rho_A", case_dir / "rho_A.png")
        plot_central_scalar(geom["rho_num"], coords, f"{label}: rho from Einstein tensor", "rho_num", case_dir / "rho_num.png")
        plot_central_scalar(vector_magnitude(geom["divG"]), coords, f"{label}: Bianchi residual magnitude", "|nabla_mu G^mu_nu|", case_dir / "bianchi_residual.png")
        plot_central_scalar(Q_fit_global[0, 0], coords, f"{label}: fitted global HTR Q00", "Q_fit_00", case_dir / "Q00_fitted_global.png")
        plot_central_scalar(Q_action_global[0, 0], coords, f"{label}: action global beta=-1 Q00", "Q_action_00", case_dir / "Q00_action_global.png")
        plot_central_scalar(Q_action_global[0, 0] - Q_fit_global[0, 0], coords, f"{label}: Q00 action minus fit", "Q_action_00 - Q_fit_00", case_dir / "Q00_action_minus_fit_global.png")
        plot_central_scalar(vector_magnitude(score_action_global_on_global["C"]), coords, f"{label}: action tensor residual magnitude", "|nabla_mu Q_action^mu_nu|", case_dir / "Q_action_residual.png")

        rho_slice, xs, ys = central_slice(geom["rho_A"], coords)
        qfit_slice, _, _ = central_slice(Q_fit_global[0, 0], coords)
        qaction_slice, _, _ = central_slice(Q_action_global[0, 0], coords)

        ix0 = int(np.argmin(np.abs(xs)))
        rho_cut = rho_slice[ix0, :]
        fit_cut = qfit_slice[ix0, :]
        action_cut = qaction_slice[ix0, :]

        rho_norm = rho_cut / np.max(np.abs(rho_cut)) if np.max(np.abs(rho_cut)) > 0 else rho_cut
        fit_norm = fit_cut / np.max(np.abs(fit_cut)) if np.max(np.abs(fit_cut)) > 0 else fit_cut
        action_norm = action_cut / np.max(np.abs(action_cut)) if np.max(np.abs(action_cut)) > 0 else action_cut

        plt.figure(figsize=(8, 5))
        plt.plot(ys, rho_norm, label="rho_A / max|rho_A|")
        plt.plot(ys, fit_norm, label="fitted Q00 / max|Q00|")
        plt.plot(ys, action_norm, "--", label="action Q00 / max|Q00|")
        plt.title(f"{label}: Q00 line cut at x=0")
        plt.xlabel("y")
        plt.ylabel("normalized amplitude")
        plt.legend()
        plt.grid(True, alpha=0.3)
        savefig(case_dir / "Q00_linecut_rho_fit_action.png")

    del geom
    del Q_fit_global, Q_action_global, Q_fit_wall, Q_action_wall
    gc.collect()

    print(f"Finished {label} in {elapsed/60:.2f} minutes")
    return row


# ---- Command-line supervisor and export logic ----



def load_completed_rows(output_dir: Path):
    rows = []
    incremental = output_dir / "stage6A_results_incremental.csv"
    final = output_dir / "stage6A_results.csv"
    source = incremental if incremental.exists() else final
    if source.exists() and source.stat().st_size > 0:
        df = pd.read_csv(source)
        if not df.empty and "N" in df.columns:
            rows = df.to_dict("records")
    return rows


def run_supervisor(args) -> int:
    configure_runtime(args)
    cases = get_cases(args.case_mode)
    n_values = [int(n) for n in args.n]
    print("Stage 6A CLI supervisor")
    print("OUTPUT_DIR:", OUTPUT_DIR)
    print("N values:", n_values)
    print("Case mode:", args.case_mode)
    print("Cases:", cases)
    write_json(OUTPUT_DIR / "run_config.json", {
        "time_utc": now_utc(),
        "n_values": n_values,
        "case_mode": args.case_mode,
        "cases": cases,
        "dtype": args.dtype,
        "save_plots": args.save_plots,
        "output_dir": str(OUTPUT_DIR),
        "system_report": system_report(OUTPUT_DIR),
    })

    rows = load_completed_rows(OUTPUT_DIR)
    completed = {
        (int(r["N"]), float(r["v_s"]), float(r["sigma"]), float(r["R"]))
        for r in rows if "N" in r
    }

    failures = []
    for N in n_values:
        if not preflight_check(N, args.dtype, OUTPUT_DIR, args.min_free_ram_gib, args.allow_high_memory):
            print(f"Skipping all N={N} cases because preflight failed.", flush=True)
            continue
        for case in cases:
            key = (int(N), float(case["v_s"]), float(case["sigma"]), float(case["R"]))
            if key in completed:
                print("Skipping completed case:", key, flush=True)
                continue
            label = make_case_label(N, case["v_s"], case["sigma"], case["R"])
            print("\n" + "#" * 72, flush=True)
            print("Launching worker for", label, flush=True)
            print("#" * 72, flush=True)
            cmd = [
                sys.executable, str(Path(__file__).resolve()), "case",
                "--output-dir", str(OUTPUT_DIR),
                "--dtype", args.dtype,
                "--n", str(N),
                "--v-s", str(case["v_s"]),
                "--sigma", str(case["sigma"]),
                "--R", str(case["R"]),
                "--extent", str(args.extent),
                "--t-extent", str(args.t_extent),
                "--delta-tau", str(args.delta_tau),
                "--interior-crop", str(args.interior_crop),
                "--wall-k", str(args.wall_k),
                "--dpi", str(args.dpi),
            ]
            if args.save_plots:
                cmd.append("--save-plots")
            else:
                cmd.append("--no-save-plots")
            env = os.environ.copy()
            # Prevent BLAS oversubscription on a 4-core machine.
            env.setdefault("OMP_NUM_THREADS", str(args.threads))
            env.setdefault("OPENBLAS_NUM_THREADS", str(args.threads))
            env.setdefault("MKL_NUM_THREADS", str(args.threads))
            env.setdefault("NUMEXPR_NUM_THREADS", str(args.threads))
            start = time.time()
            proc = subprocess.run(cmd, env=env)
            elapsed = time.time() - start
            if proc.returncode != 0:
                failure = {"key": key, "label": label, "returncode": proc.returncode, "elapsed_seconds": elapsed, "time_utc": now_utc()}
                failures.append(failure)
                write_json(OUTPUT_DIR / "failures.json", failures)
                print("Worker failed:", failure, flush=True)
                if not args.continue_on_error:
                    return proc.returncode
                continue
            case_summary = OUTPUT_DIR / label / "case_summary.csv"
            if not case_summary.exists():
                print("Worker ended but case_summary.csv is missing:", case_summary, flush=True)
                if not args.continue_on_error:
                    return 2
                continue
            row = pd.read_csv(case_summary).iloc[0].to_dict()
            rows.append(row)
            completed.add(key)
            df = pd.DataFrame(rows)
            atomic_write_csv(df, OUTPUT_DIR / "stage6A_results_incremental.csv")
            atomic_write_csv(df, OUTPUT_DIR / "stage6A_results.csv")
            print("Supervisor checkpoint saved after", label, flush=True)

    if rows:
        export_summary_and_zip(OUTPUT_DIR, rows, cases, n_values, args.case_mode, args.make_zip)
    else:
        print("No completed rows to summarize.", flush=True)
    return 0


def run_case_command(args) -> int:
    configure_runtime(args)
    label = make_case_label(args.n, args.v_s, args.sigma, args.R)
    case_dir = OUTPUT_DIR / label
    case_dir.mkdir(parents=True, exist_ok=True)
    status_path = case_dir / "status.json"
    write_json(status_path, {
        "status": "started",
        "time_utc": now_utc(),
        "label": label,
        "args": vars(args),
        "system_report": system_report(OUTPUT_DIR),
    })
    try:
        row = run_one_stage6A_case(args.n, args.v_s, args.sigma, args.R, save_plots=args.save_plots)
        write_json(status_path, {"status": "complete", "time_utc": now_utc(), "label": label, "row": row})
        return 0
    except MemoryError as e:
        write_json(status_path, {"status": "memory_error", "time_utc": now_utc(), "label": label, "error": str(e)})
        raise
    except Exception as e:
        write_json(status_path, {"status": "error", "time_utc": now_utc(), "label": label, "error_type": type(e).__name__, "error": str(e)})
        raise


def export_summary_and_zip(output_dir: Path, rows, cases, n_values, case_mode: str, make_zip: bool = True):
    df_results = pd.DataFrame(rows)
    if df_results.empty or "N" not in df_results.columns:
        raise RuntimeError("No completed cases with an N column. Cannot summarize.")
    atomic_write_csv(df_results, output_dir / "stage6A_results.csv")
    summary = {
        "num_cases": int(len(df_results)),
        "N_values": sorted([int(x) for x in df_results["N"].unique()]),
        "median_bianchi_global": float(df_results["bianchi_global"].median()),
        "median_bianchi_wall": float(df_results["bianchi_wall"].median()),
        "median_rho_error_global": float(df_results["rho_relative_peak_error_global"].median()),
        "median_rho_error_wall": float(df_results["rho_relative_peak_error_wall"].median()),
        "median_beta_fit_global": float(df_results["beta_fit_global"].median()),
        "median_beta_fit_wall": float(df_results["beta_fit_wall"].median()),
        "median_action_over_fit_global": float(df_results["action_over_fit_global"].median()),
        "median_action_over_fit_wall": float(df_results["action_over_fit_wall"].median()),
        "median_relative_tensor_difference_global": float(df_results["relative_tensor_difference_global"].median()),
        "median_relative_tensor_difference_wall": float(df_results["relative_tensor_difference_wall"].median()),
        "median_eta_needed_global": float(df_results["eta_needed_global"].median()),
        "median_eta_needed_wall": float(df_results["eta_needed_wall"].median()),
        "time_utc": now_utc(),
        "case_mode": case_mode,
        "cases": cases,
        "n_values_requested": n_values,
    }
    write_json(output_dir / "stage6A_summary.json", summary)
    atomic_write_csv(pd.DataFrame([summary]), output_dir / "stage6A_summary.csv")

    labels = [f"N{int(r.N)} v={r.v_s:g} R={r.R:g}" for _, r in df_results.iterrows()]
    xpos = np.arange(len(df_results))
    if len(df_results) > 0:
        plt.figure(figsize=(10, 5))
        plt.plot(xpos, df_results["beta_fit_global"], marker="o", label="global fit")
        plt.plot(xpos, df_results["beta_fit_wall"], marker="s", label="wall-shell fit")
        plt.axhline(-1.0, linestyle="--", label="action beta=-1")
        plt.xticks(xpos, labels, rotation=45, ha="right")
        plt.title("Stage 6A: beta_fit global versus wall-focused")
        plt.ylabel("beta_fit")
        plt.legend(); plt.grid(True, alpha=0.3)
        savefig(output_dir / "stage6A_beta_global_vs_wall.png")

        plt.figure(figsize=(10, 5))
        plt.plot(xpos, df_results["action_over_fit_global"], marker="o", label="global")
        plt.plot(xpos, df_results["action_over_fit_wall"], marker="s", label="wall-focused")
        plt.axhline(1.0, linestyle="--", label="equal performance")
        plt.xticks(xpos, labels, rotation=45, ha="right")
        plt.title("Stage 6A: action residual / fitted residual")
        plt.ylabel("ratio")
        plt.legend(); plt.grid(True, alpha=0.3)
        savefig(output_dir / "stage6A_action_over_fit_global_vs_wall.png")

        plt.figure(figsize=(10, 5))
        plt.plot(xpos, 100*df_results["relative_tensor_difference_global"], marker="o", label="global")
        plt.plot(xpos, 100*df_results["relative_tensor_difference_wall"], marker="s", label="wall-focused")
        plt.xticks(xpos, labels, rotation=45, ha="right")
        plt.title("Stage 6A: relative tensor difference action vs fit")
        plt.ylabel("relative difference (%)")
        plt.legend(); plt.grid(True, alpha=0.3)
        savefig(output_dir / "stage6A_relative_tensor_difference_global_vs_wall.png")

        plt.figure(figsize=(10, 5))
        plt.plot(xpos, df_results["bianchi_global"], marker="o", label="Bianchi global")
        plt.plot(xpos, df_results["bianchi_wall"], marker="s", label="Bianchi wall")
        plt.plot(xpos, df_results["rho_relative_peak_error_global"], marker="^", label="rho error global")
        plt.plot(xpos, df_results["rho_relative_peak_error_wall"], marker="v", label="rho error wall")
        plt.yscale("log")
        plt.xticks(xpos, labels, rotation=45, ha="right")
        plt.title("Stage 6A: numerical quality metrics")
        plt.ylabel("metric value")
        plt.legend(); plt.grid(True, which="both", alpha=0.3)
        savefig(output_dir / "stage6A_numerical_quality_metrics.png")

        plt.figure(figsize=(10, 5))
        plt.plot(xpos, df_results["eta_needed_global"], marker="o", label="eta global")
        plt.plot(xpos, df_results["eta_needed_wall"], marker="s", label="eta wall")
        plt.yscale("log")
        plt.xticks(xpos, labels, rotation=45, ha="right")
        plt.title("Stage 6A: estimated eta needed")
        plt.ylabel("eta needed")
        plt.legend(); plt.grid(True, which="both", alpha=0.3)
        savefig(output_dir / "stage6A_eta_needed_global_vs_wall.png")

    readme = f"""# Stage 6A command-line outputs

Run completed or checkpointed at: {now_utc()}
Case mode: {case_mode}
N values requested: {n_values}
Output directory: {output_dir}

This command-line version avoids VS Code/Jupyter for long runs. Each case is executed
in a separate Python process and writes its own case_summary.csv/json before the
supervisor continues.

Summary:
{json.dumps(summary, indent=2)}
"""
    (output_dir / "README.txt").write_text(readme, encoding="utf-8")

    if make_zip:
        zip_path = Path(str(output_dir) + ".zip")
        if zip_path.exists():
            zip_path.unlink()
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for file_path in output_dir.rglob("*"):
                zf.write(file_path, arcname=file_path.relative_to(output_dir))
        print("ZIP created:", zip_path.resolve(), flush=True)
    print("Summary:", json.dumps(summary, indent=2), flush=True)


def add_common_args(p):
    p.add_argument("--output-dir", required=True)
    p.add_argument("--dtype", choices=["float64", "float32"], default="float64")
    p.add_argument("--extent", type=float, default=5.0)
    p.add_argument("--t-extent", type=float, default=0.4)
    p.add_argument("--delta-tau", type=float, default=0.04)
    p.add_argument("--interior-crop", type=int, default=3)
    p.add_argument("--wall-k", type=float, default=3.0)
    p.add_argument("--dpi", type=int, default=170)
    p.add_argument("--make-zip", dest="make_zip", action="store_true", default=True)
    p.add_argument("--no-make-zip", dest="make_zip", action="store_false")
    p.add_argument("--save-plots", dest="save_plots", action="store_true", default=True)
    p.add_argument("--no-save-plots", dest="save_plots", action="store_false")


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Spinelli Stage 6A command-line runner")
    sub = parser.add_subparsers(dest="command", required=True)
    runp = sub.add_parser("run", help="Run a batch of cases with resume/checkpointing")
    add_common_args(runp)
    runp.add_argument("--n", type=int, nargs="+", required=True)
    runp.add_argument("--case-mode", choices=["sigma4_core", "sigma4_full", "sharp_wall_full"], default="sigma4_core")
    runp.add_argument("--min-free-ram-gib", type=float, default=12.0)
    runp.add_argument("--allow-high-memory", action="store_true")
    runp.add_argument("--continue-on-error", action="store_true")
    runp.add_argument("--threads", type=int, default=1)

    casep = sub.add_parser("case", help="Run exactly one case; normally called by supervisor")
    add_common_args(casep)
    casep.add_argument("--n", type=int, required=True)
    casep.add_argument("--v-s", type=float, required=True)
    casep.add_argument("--sigma", type=float, required=True)
    casep.add_argument("--R", type=float, required=True)

    sump = sub.add_parser("summarize", help="Rebuild summary/plots/zip from existing case summaries")
    add_common_args(sump)
    sump.add_argument("--case-mode", choices=["sigma4_core", "sigma4_full", "sharp_wall_full"], default="sigma4_core")
    sump.add_argument("--n", type=int, nargs="+", default=[])
    return parser


def summarize_existing(args) -> int:
    configure_runtime(args)
    rows = load_completed_rows(OUTPUT_DIR)
    if not rows:
        # Find per-case summaries if the aggregate CSV was missing.
        for p in sorted(OUTPUT_DIR.glob("N*_v*_sigma*_R*/case_summary.csv")):
            try:
                rows.append(pd.read_csv(p).iloc[0].to_dict())
            except Exception as e:
                print("Could not read", p, e)
    if not rows:
        print("No case summaries found.")
        return 1
    export_summary_and_zip(OUTPUT_DIR, rows, get_cases(args.case_mode), args.n, args.case_mode, args.make_zip)
    return 0


def main(argv=None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        return run_supervisor(args)
    if args.command == "case":
        return run_case_command(args)
    if args.command == "summarize":
        return summarize_existing(args)
    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
