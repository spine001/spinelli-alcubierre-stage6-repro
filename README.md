# Spinelli Alcubierre Stage 6 Reproducibility Package

This repository contains numerical scripts, run commands, and convergence outputs for the Stage 6A dense-grid and Stage 6B tiled/wall-focused Alcubierre tests in the Spinelli discrete proper-time framework.

## Purpose

The repository is intended to make the Stage 6 numerical evidence reproducible and inspectable.

The main tested claim is not that an Alcubierre drive has been proven physically realizable. The narrower numerical claim is:

> In the steep-wall sigma = 4 Alcubierre test, the fitted correction tensor converges toward the action-predicted value beta = -1 as resolution increases, while the action-derived tensor becomes numerically indistinguishable from the locally fitted tensor under residual testing.

## Included results

Dense Stage 6A:

- N = 61 through N = 101
- Core sigma = 4 cases
- Convergence table and full core-case CSV

Tiled Stage 6B:

- N = 101
- N = 121
- N = 141
- N = 161 will be added after the current run completes

## Key diagnostics

- Bianchi residual
- Alcubierre rho_A relative peak error
- Fitted beta coefficient
- Action/Fit residual ratio
- Relative tensor difference
- Eta needed
- Runtime and memory behavior

## Main convergence pattern

The important pattern is:

1. Geometry diagnostics improve with resolution.
2. beta_fit moves toward beta_action = -1.
3. Action/Fit approaches 1.
4. Relative tensor difference approaches 0.
5. Stage 6B keeps memory nearly flat compared with dense Stage 6A.

## How to run

Create a Python environment with:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Then use the scripts in run_scripts/, or call the Python scripts directly.

## Repository link for article

https://github.com/spine001/spinelli-alcubierre-stage6-repro

<!-- N301_V1_STATUS_START -->
## Current validation status — 2026-07-17

N101 completed successfully with 225.28 GiB peak RSS, zero swap, and
monotonic principal diagnostics across N61/N71/N81/N91/N101.

N111 is the next authorized resolution. Its projected working set is
approximately 328.64 GiB. Paging is allowed and is measured with a corrected
sampler that tracks the actual Python process, process swap, virtual memory,
major faults, and system paging counters.

See `docs/PROJECT_STATUS.md`, the N101 five-grid analysis, the resource
sampler correction, the N111 run plan, and the latest integrated HTML under
`article/`.
<!-- N301_V1_STATUS_END -->
