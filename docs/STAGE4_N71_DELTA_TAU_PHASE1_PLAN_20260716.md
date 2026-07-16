# Stage 4 N71 Proper-Time-Step Sensitivity — Phase 1

**Date:** 2026-07-16

## Purpose

Separate proper-time finite-difference sensitivity from the spatial-grid behavior already
measured at N61, N71, and N81.

## Matrix

- N=71, DELTA_TAU=0.02 — new run
- N=71, DELTA_TAU=0.04 — reuse verified baseline
- N=71, DELTA_TAU=0.08 — new run

The two new cases execute sequentially in separate Python processes so all dense arrays
are released between cases.

## Controlled constants

DIM=4, R_BUBBLE=3, SIGMA=1, V_S=0.5, EXTENT=5, T_EXTENT=0.4,
INTERIOR_CROP=3. The historical notebook remains unchanged on disk.

## Phase 2 decision

The postprocessor recommends either:

- `N81_DTAU_0P02_CONFIRMATION_ONLY`, when the fine-step changes are small; or
- `N81_FULL_DTAU_MATRIX`, when one or more sensitivity thresholds are exceeded.

No N81 or higher-resolution run is started automatically. Results are reviewed first.
