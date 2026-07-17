# Stage 4 Optimized N91 Run Plan

**Date:** 2026-07-17  
**Notebook SHA-256:** `1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe`

## Controlled configuration

- DIM = 4
- N = 91
- DELTA_TAU = 0.04
- MANUAL_MEMORY_BUDGET_GIB = 220
- R_BUBBLE = 3
- SIGMA = 1
- V_S = 0.5
- EXTENT = 5
- T_EXTENT = 0.4
- INTERIOR_CROP = 3

The historical notebook is never changed on disk.

## Validated implementation

The production runner uses the same streaming cells that reproduced the N61 and N81
canonical outputs.

Original source hashes:

- Cell 3: `5a49221d2ba22d35ee05b94fa968dfc9e1628ccc5d228e08712264db8f5291a5`
- Cell 23: `18dfd79cd2b9fe41b798714d1e2f80f6a53ffab7f0eb39a4abe3d98954326957`
- Cell 24: `6528d7dedf482b7590ebf983c79e21ed9670673a570b319533a4f02367fbf1af`

## Expected resources

- Projected peak RSS: 147.675 GiB
- Projected runtime: 6.90 minutes
- Required MemAvailable before start: 210 GiB
- Swap: emergency protection only; the run must complete with zero process swaps

## N91 reporting

The run produces canonical exports, a metric summary, a per-cell memory profile, the full
log, and a four-grid N61/N71/N81/N91 analysis.

## Phase 5 decision

The report emits one of:

- `PHASE5_RECOMMENDATION=BUILD_N101_OPTIMIZED_RUNNER`
- `PHASE5_RECOMMENDATION=FURTHER_OPTIMIZE_BEFORE_N101`
- `PHASE5_RECOMMENDATION=INVESTIGATE_N91_SPATIAL_TREND_BEFORE_N101`

N101 is never started automatically.
