#!/usr/bin/env python3
"""
Spinelli Stage 6B tiled / wall-focused solver.

Purpose
-------
Stage 6A used a dense uniform 4D grid and successfully demonstrated convergence
through N=101, but the dense method stores too many tensor-equivalent arrays in
RAM. Stage 6B keeps the same Alcubierre / action-derived-Q stress test but
processes the grid in overlapping 4D tiles, scoring only the non-overlapped tile
cores. The default target is the sigma=4 wall shell where the numerical error is
concentrated.

Key design choices
------------------
1. Restartable: every tile writes a status file and every case writes partial
   aggregate JSON/CSV.
2. Two-pass fit: pass 1 accumulates normal equations for lambda and beta without
   retaining all points; pass 2 scores fitted and action tensors tile by tile.
3. Halo tiles: each tile is expanded by a halo so finite differences are not
   evaluated on tile boundaries. Only the core region contributes to aggregates.
4. Wall-focused: default scoring mask is |r_s - R| <= wall_k/sigma, with boundary
   and tile-core restrictions.
5. Conservative: this is a numerical-engineering implementation, not a change in
   the theoretical equations.

This code intentionally prioritizes completion and restartability over speed.
"""

from __future__ import annotations

import argparse
import gc
import json
import math
import os
import platform
import shutil
import sys
import time
import zipfile
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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


def system_report(output_dir: Path) -> Dict[str, object]:
    try:
        import psutil
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        ram_total = vm.total / 1024**3
        ram_available = vm.available / 1024**3
        ram_used_percent = vm.percent
        swap_total = swap.total / 1024**3
        swap_used = swap.used / 1024**3
        swap_used_percent = swap.percent
    except Exception:
        ram_total = ram_available = ram_used_percent = float("nan")
        swap_total = swap_used = swap_used_percent = float("nan")
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
        "output_disk_free_GiB": disk.free / 1024**3,
        "output_dir": str(output_dir),
    }


def dtype_from_name(name: str):
    if name == "float64":
        return np.float64
    if name == "float32":
        return np.float32
    raise ValueError(f"Unsupported dtype {name}")


def scalar_gib(shape, dtype) -> float:
    return np.prod(shape) * np.dtype(dtype).itemsize / 1024**3


def alcubierre_shape(rs, R, sigma):
    return (np.tanh(sigma * (rs + R)) - np.tanh(sigma * (rs - R))) / (2.0 * np.tanh(sigma * R))


def safe_ratio(a, b):
    return float(a / b) if b not in (0, 0.0) and np.isfinite(b) else np.nan


def make_case_label(N, v_s, sigma, R):
    return f"N{N}_v{v_s:g}_sigma{sigma:g}_R{R:g}".replace(".", "p")


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
    raise ValueError(f"Unknown case mode {case_mode}")


@dataclass(frozen=True)
class Tile:
    tile_id: int
    t0: int; t1: int
    x0: int; x1: int
    y0: int; y1: int
    z0: int; z1: int
    ht0: int; ht1: int
    hx0: int; hx1: int
    hy0: int; hy1: int
    hz0: int; hz1: int

    def label(self) -> str:
        return f"tile{self.tile_id:06d}_t{self.t0}-{self.t1}_x{self.x0}-{self.x1}_y{self.y0}-{self.y1}_z{self.z0}-{self.z1}"


def tile_ranges(N: int, tile: int) -> Iterable[Tuple[int, int]]:
    start = 0
    while start < N:
        end = min(N, start + tile)
        yield start, end
        start = end


def iter_tiles(N: int, tile_t: int, tile_x: int, tile_y: int, tile_z: int, halo: int) -> Iterable[Tile]:
    tid = 0
    for t0, t1 in tile_ranges(N, tile_t):
        for x0, x1 in tile_ranges(N, tile_x):
            for y0, y1 in tile_ranges(N, tile_y):
                for z0, z1 in tile_ranges(N, tile_z):
                    yield Tile(
                        tile_id=tid,
                        t0=t0, t1=t1, x0=x0, x1=x1, y0=y0, y1=y1, z0=z0, z1=z1,
                        ht0=max(0, t0-halo), ht1=min(N, t1+halo),
                        hx0=max(0, x0-halo), hx1=min(N, x1+halo),
                        hy0=max(0, y0-halo), hy1=min(N, y1+halo),
                        hz0=max(0, z0-halo), hz1=min(N, z1+halo),
                    )
                    tid += 1


def local_core_slices(tile: Tile) -> Tuple[slice, slice, slice, slice]:
    return (
        slice(tile.t0-tile.ht0, tile.t1-tile.ht0),
        slice(tile.x0-tile.hx0, tile.x1-tile.hx0),
        slice(tile.y0-tile.hy0, tile.y1-tile.hy0),
        slice(tile.z0-tile.hz0, tile.z1-tile.hz0),
    )


def build_tile_geometry(N: int, tile: Tile, v_s: float, sigma: float, R: float,
                        extent: float, t_extent: float, delta_tau: float, dtype) -> Dict[str, object]:
    # Global coordinate vectors, then tile-halo sub-vectors.
    t_full = np.linspace(-t_extent, t_extent, N, dtype=dtype)
    x_full = np.linspace(-extent, extent, N, dtype=dtype)
    y_full = np.linspace(-extent, extent, N, dtype=dtype)
    z_full = np.linspace(-extent, extent, N, dtype=dtype)

    t = t_full[tile.ht0:tile.ht1]
    x = x_full[tile.hx0:tile.hx1]
    y = y_full[tile.hy0:tile.hy1]
    z = z_full[tile.hz0:tile.hz1]
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

    Gamma = np.zeros((dim, dim, dim) + shape, dtype=dtype)
    for a in range(dim):
        for m in range(dim):
            for n in range(dim):
                total = np.zeros(shape, dtype=dtype)
                for l in range(dim):
                    term = dg_component(n, l, m)
                    term2 = dg_component(m, l, n)
                    term3 = dg_component(m, n, l)
                    if not isinstance(term, float): total += gi[a, l] * term
                    elif term != 0.0: total += gi[a, l] * term
                    if not isinstance(term2, float): total += gi[a, l] * term2
                    elif term2 != 0.0: total += gi[a, l] * term2
                    if not isinstance(term3, float): total -= gi[a, l] * term3
                    elif term3 != 0.0: total -= gi[a, l] * term3
                Gamma[a, m, n] = 0.5 * total

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
    del Rsc
    gc.collect()

    dS = np.zeros((dim,) + shape, dtype=dtype)
    grads_S = np.gradient(S, *spacings, edge_order=2)
    for a in range(dim):
        dS[a] = grads_S[a].astype(dtype)
    del grads_S
    gc.collect()

    ddS = np.zeros((dim, dim) + shape, dtype=dtype)
    for a in range(dim):
        grads = np.gradient(dS[a], *spacings, edge_order=2)
        for b in range(dim): ddS[a, b] = grads[b].astype(dtype)
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

    # Mixed Einstein and Bianchi divergence on tile.
    Gmix = mixed_tensor(Einstein, gi)
    divG = divergence_mixed_tensor(Gmix, Gamma, spacings)

    rho_A = -(v_s**2) / (32.0 * np.pi) * (df[2]**2 + df[3]**2)
    n_vec = np.zeros((dim,) + shape, dtype=dtype)
    n_vec[0] = 1.0
    n_vec[1] = v_s * f
    rho_num = np.zeros(shape, dtype=dtype)
    for a in range(dim):
        for b in range(dim):
            rho_num += Einstein[a, b] * n_vec[a] * n_vec[b]
    rho_num = rho_num / (8.0 * np.pi)

    return {
        "dim": dim, "coords": coords, "spacings": spacings, "shape": shape,
        "rs": rs, "f": f, "S": S, "g": g, "gi": gi, "Gamma": Gamma,
        "Ricci": Ricci, "Einstein": Einstein, "Gmix": Gmix, "divG": divG,
        "Hess": Hess, "BoxS": BoxS, "dS": dS,
        "rho_A": rho_A, "rho_num": rho_num,
    }


def mixed_tensor(Q_cov, gi):
    dim = Q_cov.shape[0]
    Qmix = np.zeros_like(Q_cov)
    for a in range(dim):
        for b in range(dim):
            total = np.zeros(Q_cov.shape[2:], dtype=Q_cov.dtype)
            for c in range(dim): total += gi[a, c] * Q_cov[c, b]
            Qmix[a, b] = total
    return Qmix


def divergence_mixed_tensor(Tmix, Gamma, spacings):
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


def make_Q_HTR(geom, lam, beta):
    dim = geom["dim"]
    Q = np.zeros((dim, dim) + geom["shape"], dtype=geom["g"].dtype)
    for a in range(dim):
        for b in range(dim):
            Q[a,b] = geom["Hess"][a,b] - geom["g"][a,b]*geom["BoxS"] - lam*geom["g"][a,b]*geom["S"] + beta*geom["S"]*geom["Einstein"][a,b]
    return Q


def wall_mask_for_tile(geom, tile: Tile, R: float, sigma: float, wall_k: float, interior_crop: int, scope: str):
    core = np.zeros(geom["shape"], dtype=bool)
    core[local_core_slices(tile)] = True
    # Remove a small global-edge band when local halo touches global domain edge.
    interior = core.copy()
    if tile.t0 < interior_crop: interior[:(interior_crop - tile.ht0), :, :, :] = False
    if tile.x0 < interior_crop: interior[:, :(interior_crop - tile.hx0), :, :] = False
    if tile.y0 < interior_crop: interior[:, :, :(interior_crop - tile.hy0), :] = False
    if tile.z0 < interior_crop: interior[:, :, :, :(interior_crop - tile.hz0)] = False
    if scope == "interior":
        return interior
    half_width = wall_k / sigma
    wall = np.abs(geom["rs"] - R) <= half_width
    return interior & wall


def accum_vector_l2(vec, mask):
    s = 0.0; n = int(mask.sum())
    if n == 0: return 0.0, 0
    for a in range(vec.shape[0]):
        vals = vec[a][mask].astype(np.float64, copy=False)
        s += float(np.sum(vals*vals))
    return s, n


def accum_tensor_l2(tensor, mask):
    s = 0.0; n = int(mask.sum())
    if n == 0: return 0.0, 0
    for a in range(tensor.shape[0]):
        for b in range(tensor.shape[1]):
            vals = tensor[a,b][mask].astype(np.float64, copy=False)
            s += float(np.sum(vals*vals))
    return s, n


def fit_accumulator_from_tile(geom, mask):
    dim = geom["dim"]
    if int(mask.sum()) == 0:
        return np.zeros((2,2)), np.zeros(2), 0
    Ricci = geom["Ricci"]
    Einstein = geom["Einstein"]
    gi = geom["gi"]
    dS_cov = geom["dS"]
    gradS_up = np.zeros_like(dS_cov)
    for l in range(dim):
        for a in range(dim): gradS_up[l] += gi[l,a] * dS_cov[a]
    MTM = np.zeros((2,2), dtype=np.float64)
    MTy = np.zeros(2, dtype=np.float64)
    count = 0
    for nu in range(dim):
        B = dS_cov[nu]
        A = np.zeros_like(B)
        D = np.zeros_like(B)
        for lam in range(dim): A += Ricci[nu,lam] * gradS_up[lam]
        for mu in range(dim): D += Einstein[mu,nu] * gradS_up[mu]
        m0 = (-B[mask]).astype(np.float64, copy=False)
        m1 = (D[mask]).astype(np.float64, copy=False)
        y = (-A[mask]).astype(np.float64, copy=False)
        MTM[0,0] += float(np.dot(m0,m0))
        MTM[0,1] += float(np.dot(m0,m1))
        MTM[1,0] += float(np.dot(m1,m0))
        MTM[1,1] += float(np.dot(m1,m1))
        MTy[0] += float(np.dot(m0,y))
        MTy[1] += float(np.dot(m1,y))
        count += len(y)
    return MTM, MTy, count


def residual_accumulators_from_tile(geom, mask, lam_fit, beta_fit):
    dim = geom["dim"]
    if int(mask.sum()) == 0:
        return {}
    Q_fit = make_Q_HTR(geom, lam_fit, beta_fit)
    Q_action = make_Q_HTR(geom, lam_fit, -1.0)
    Qfit_mix = mixed_tensor(Q_fit, geom["gi"])
    Qaction_mix = mixed_tensor(Q_action, geom["gi"])
    C_fit = divergence_mixed_tensor(Qfit_mix, geom["Gamma"], geom["spacings"])
    C_action = divergence_mixed_tensor(Qaction_mix, geom["Gamma"], geom["spacings"])
    Dmix = Qaction_mix - Qfit_mix

    Cfit2, n = accum_vector_l2(C_fit, mask)
    Cact2, _ = accum_vector_l2(C_action, mask)
    Qfit2, _ = accum_tensor_l2(Qfit_mix, mask)
    Qact2, _ = accum_tensor_l2(Qaction_mix, mask)
    D2, _ = accum_tensor_l2(Dmix, mask)
    G2, _ = accum_tensor_l2(geom["Gmix"], mask)
    divG2, _ = accum_vector_l2(geom["divG"], mask)

    err = geom["rho_num"] - geom["rho_A"]
    peak_err = float(np.max(np.abs(err[mask])))
    peak_ref = float(np.max(np.abs(geom["rho_A"][mask])))

    pos_Q00 = np.maximum(Q_action[0,0][mask], 0.0)
    abs_rho = np.abs(geom["rho_A"][mask])
    # Use spatial volume element. Time dimension is a repeated sampling axis; this is
    # a consistent proxy with Stage 6A ratios for comparing across runs.
    dV = float(np.prod(geom["spacings"][1:]))
    qpos_sum = float(np.sum(pos_Q00) * dV)
    rho_abs_sum = float(np.sum(abs_rho) * dV)

    return {
        "n": n,
        "Cfit2": Cfit2, "Cact2": Cact2, "Qfit2": Qfit2, "Qact2": Qact2, "D2": D2,
        "G2": G2, "divG2": divG2,
        "rho_peak_err": peak_err, "rho_peak_ref": peak_ref,
        "qpos_sum": qpos_sum, "rho_abs_sum": rho_abs_sum,
    }


def combine_fit(parts):
    MTM = np.zeros((2,2)); MTy = np.zeros(2); count=0
    for p in parts:
        MTM += p["MTM"]; MTy += p["MTy"]; count += p["count"]
    if count == 0:
        raise RuntimeError("No points in fit mask")
    params = np.linalg.solve(MTM + 1e-30*np.eye(2), MTy)
    return float(params[0]), float(params[1]), count


def combine_scores(parts):
    totals = {k:0.0 for k in ["Cfit2","Cact2","Qfit2","Qact2","D2","G2","divG2","qpos_sum","rho_abs_sum"]}
    n=0; peak_err=0.0; peak_ref=0.0
    for p in parts:
        if not p: continue
        n += int(p.get("n",0))
        for k in totals: totals[k] += float(p.get(k,0.0))
        peak_err = max(peak_err, float(p.get("rho_peak_err",0.0)))
        peak_ref = max(peak_ref, float(p.get("rho_peak_ref",0.0)))
    return {
        "mask_points": n,
        "fit_residual": math.sqrt(totals["Cfit2"] / n) if n else np.nan,
        "action_residual": math.sqrt(totals["Cact2"] / n) if n else np.nan,
        "fit_Q_L2": math.sqrt(totals["Qfit2"] / n) if n else np.nan,
        "action_Q_L2": math.sqrt(totals["Qact2"] / n) if n else np.nan,
        "normalized_fit_residual": safe_ratio(math.sqrt(totals["Cfit2"]), math.sqrt(totals["Qfit2"])),
        "normalized_action_residual": safe_ratio(math.sqrt(totals["Cact2"]), math.sqrt(totals["Qact2"])),
        "action_over_fit": safe_ratio(math.sqrt(totals["Cact2"]), math.sqrt(totals["Cfit2"])),
        "relative_tensor_difference": safe_ratio(math.sqrt(totals["D2"]), math.sqrt(totals["Qfit2"])),
        "bianchi": safe_ratio(math.sqrt(totals["divG2"]), math.sqrt(totals["G2"])),
        "rho_peak_error": peak_err,
        "rho_relative_peak_error": safe_ratio(peak_err, peak_ref),
        "positive_Q00_over_abs_rho": safe_ratio(totals["qpos_sum"], totals["rho_abs_sum"]),
        "eta_needed": safe_ratio(totals["rho_abs_sum"], totals["qpos_sum"]),
    }


def run_case(args) -> int:
    dtype = dtype_from_name(args.dtype)
    output_dir = Path(args.output_dir).expanduser().resolve()
    label = make_case_label(args.n, args.v_s, args.sigma, args.R)
    case_dir = output_dir / label
    tile_dir = case_dir / "tiles"
    case_dir.mkdir(parents=True, exist_ok=True)
    tile_dir.mkdir(parents=True, exist_ok=True)

    status_path = case_dir / "status.json"
    done_path = case_dir / "case_summary.json"
    if done_path.exists() and not args.force:
        print(f"Skipping completed case {label}", flush=True)
        return 0

    write_json(status_path, {"status":"started", "time_utc":now_utc(), "label":label, "args":vars(args), "system_report":system_report(output_dir)})
    t0 = time.time()

    tiles = list(iter_tiles(args.n, args.tile_t, args.tile_x, args.tile_y, args.tile_z, args.halo))
    fit_parts = []
    tile_rows = []

    print(f"Stage 6B case {label}: {len(tiles)} tiles, scope={args.scope}", flush=True)
    for tile in tiles:
        tlabel = tile.label()
        tstatus = tile_dir / f"{tlabel}.fit.json"
        if tstatus.exists() and not args.force:
            data = json.loads(tstatus.read_text())
            fit_parts.append({"MTM":np.array(data["MTM"]), "MTy":np.array(data["MTy"]), "count":int(data["count"])})
            continue
        ts = time.time()
        geom = build_tile_geometry(args.n, tile, args.v_s, args.sigma, args.R, args.extent, args.t_extent, args.delta_tau, dtype)
        mask = wall_mask_for_tile(geom, tile, args.R, args.sigma, args.wall_k, args.interior_crop, args.scope)
        part = fit_accumulator_from_tile(geom, mask)
        record = {"tile":asdict(tile), "MTM":part[0].tolist(), "MTy":part[1].tolist(), "count":part[2], "elapsed":time.time()-ts}
        write_json(tstatus, record)
        fit_parts.append({"MTM":part[0], "MTy":part[1], "count":part[2]})
        del geom, mask
        gc.collect()
        if tile.tile_id % max(1,args.log_every) == 0:
            print(f"fit pass tile {tile.tile_id+1}/{len(tiles)} count={part[2]}", flush=True)

    lam_fit, beta_fit, fit_count = combine_fit(fit_parts)
    write_json(case_dir / "fit_parameters.json", {"lambda_fit":lam_fit, "beta_fit":beta_fit, "fit_count":fit_count, "time_utc":now_utc()})
    print(f"fit complete lambda={lam_fit:.8g} beta={beta_fit:.8g} count={fit_count}", flush=True)

    score_parts = []
    for tile in tiles:
        tlabel = tile.label()
        spath = tile_dir / f"{tlabel}.score.json"
        if spath.exists() and not args.force:
            score_parts.append(json.loads(spath.read_text()))
            continue
        ts = time.time()
        geom = build_tile_geometry(args.n, tile, args.v_s, args.sigma, args.R, args.extent, args.t_extent, args.delta_tau, dtype)
        mask = wall_mask_for_tile(geom, tile, args.R, args.sigma, args.wall_k, args.interior_crop, args.scope)
        score = residual_accumulators_from_tile(geom, mask, lam_fit, beta_fit)
        score["elapsed"] = time.time()-ts
        score["tile"] = asdict(tile)
        write_json(spath, score)
        score_parts.append(score)
        del geom, mask
        gc.collect()
        if tile.tile_id % max(1,args.log_every) == 0:
            print(f"score pass tile {tile.tile_id+1}/{len(tiles)} n={score.get('n',0)}", flush=True)

    scores = combine_scores(score_parts)
    elapsed = time.time()-t0
    row = {
        "stage": "6B_tiled_wall_focused",
        "N": args.n, "v_s": args.v_s, "sigma": args.sigma, "R": args.R,
        "dtype": args.dtype, "scope": args.scope,
        "tile_t": args.tile_t, "tile_x": args.tile_x, "tile_y": args.tile_y, "tile_z": args.tile_z, "halo": args.halo,
        "elapsed_seconds": elapsed,
        "lambda_fit": lam_fit, "beta_fit": beta_fit,
        **scores,
        "time_utc": now_utc(),
    }
    pd.DataFrame([row]).to_csv(case_dir / "case_summary.csv", index=False)
    write_json(done_path, row)
    write_json(status_path, {"status":"completed", "time_utc":now_utc(), "label":label, "elapsed_seconds":elapsed, "summary":row})
    print(f"Finished {label} in {elapsed/60:.2f} minutes", flush=True)
    return 0


def run_supervisor(args) -> int:
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "run_config.json", {"time_utc": now_utc(), "args": vars(args), "system_report": system_report(output_dir)})
    cases = get_cases(args.case_mode)
    rows = []
    for N in args.n:
        for case in cases:
            label = make_case_label(N, case["v_s"], case["sigma"], case["R"])
            summary_path = output_dir / label / "case_summary.json"
            if summary_path.exists() and not args.force:
                print(f"Skipping completed {label}", flush=True)
            else:
                cmd = [sys.executable, str(Path(__file__).resolve()), "case",
                       "--output-dir", str(output_dir), "--dtype", args.dtype,
                       "--n", str(N), "--v-s", str(case["v_s"]), "--sigma", str(case["sigma"]), "--R", str(case["R"]),
                       "--extent", str(args.extent), "--t-extent", str(args.t_extent), "--delta-tau", str(args.delta_tau),
                       "--interior-crop", str(args.interior_crop), "--wall-k", str(args.wall_k), "--scope", args.scope,
                       "--tile-t", str(args.tile_t), "--tile-x", str(args.tile_x), "--tile-y", str(args.tile_y), "--tile-z", str(args.tile_z),
                       "--halo", str(args.halo), "--log-every", str(args.log_every)]
                if args.force: cmd.append("--force")
                print("Launching", label, flush=True)
                rc = os.spawnv(os.P_WAIT, sys.executable, cmd)
                if rc != 0:
                    print(f"Worker failed for {label}, rc={rc}", flush=True)
                    return rc
            if summary_path.exists():
                rows.append(json.loads(summary_path.read_text()))
                atomic_write_csv(pd.DataFrame(rows), output_dir / "stage6B_results_incremental.csv")
    if rows:
        df = pd.DataFrame(rows)
        atomic_write_csv(df, output_dir / "stage6B_results.csv")
        summary = {
            "num_cases": int(len(df)),
            "N_values": sorted([int(x) for x in df["N"].unique()]),
            "median_bianchi": float(df["bianchi"].median()),
            "median_rho_error": float(df["rho_relative_peak_error"].median()),
            "median_beta_fit": float(df["beta_fit"].median()),
            "median_action_over_fit": float(df["action_over_fit"].median()),
            "median_tensor_difference": float(df["relative_tensor_difference"].median()),
            "time_utc": now_utc(),
        }
        write_json(output_dir / "stage6B_summary.json", summary)
        if args.make_zip:
            zpath = output_dir.with_suffix(".zip")
            with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_DEFLATED) as z:
                for p in output_dir.rglob("*"):
                    if p.is_file(): z.write(p, p.relative_to(output_dir.parent))
            print("ZIP created:", zpath, flush=True)
        print("Summary:", json.dumps(summary, indent=2), flush=True)
    return 0


def build_parser():
    p = argparse.ArgumentParser(description="Spinelli Stage 6B tiled / wall-focused solver")
    sub = p.add_subparsers(dest="command", required=True)
    def add_common(q):
        q.add_argument("--output-dir", required=True)
        q.add_argument("--dtype", choices=["float64","float32"], default="float64")
        q.add_argument("--extent", type=float, default=5.0)
        q.add_argument("--t-extent", type=float, default=0.4)
        q.add_argument("--delta-tau", type=float, default=0.04)
        q.add_argument("--interior-crop", type=int, default=3)
        q.add_argument("--wall-k", type=float, default=3.0)
        q.add_argument("--scope", choices=["wall","interior"], default="wall")
        q.add_argument("--tile-t", type=int, default=9)
        q.add_argument("--tile-x", type=int, default=41)
        q.add_argument("--tile-y", type=int, default=41)
        q.add_argument("--tile-z", type=int, default=9)
        q.add_argument("--halo", type=int, default=4)
        q.add_argument("--log-every", type=int, default=5)
        q.add_argument("--force", action="store_true")
    r = sub.add_parser("run")
    add_common(r)
    r.add_argument("--n", type=int, nargs="+", required=True)
    r.add_argument("--case-mode", choices=["sigma4_core","sigma4_full"], default="sigma4_core")
    r.add_argument("--make-zip", action=argparse.BooleanOptionalAction, default=True)
    c = sub.add_parser("case")
    add_common(c)
    c.add_argument("--n", type=int, required=True)
    c.add_argument("--v-s", dest="v_s", type=float, required=True)
    c.add_argument("--sigma", type=float, required=True)
    c.add_argument("--R", type=float, required=True)
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "case": return run_case(args)
    if args.command == "run": return run_supervisor(args)
    parser.error("unknown command")

if __name__ == "__main__":
    raise SystemExit(main())
