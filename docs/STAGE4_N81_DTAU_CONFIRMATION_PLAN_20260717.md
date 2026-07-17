# Stage 4 N81 DELTA_TAU=0.02 Confirmation Plan

**Date:** 2026-07-17

## Inputs

- Verified N71 DELTA_TAU matrix: 0.02, 0.04, 0.08
- Verified N81 baseline: DELTA_TAU=0.04
- Historical notebook SHA-256:
  `1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe`

## New calculation

- DIM=4
- N=81
- DELTA_TAU=0.02
- MANUAL_MEMORY_BUDGET_GIB=220
- All other physical and numerical parameters unchanged

## Resource expectation

- Peak RSS: approximately 177 GiB
- Runtime: approximately 4 minutes 15 seconds
- Required MemAvailable before start: 220 GiB
- Swap is emergency protection only

## Reporting decision

The postprocessor compares N71 and N81 fine-step effects. It emits:

- `PHASE3_RECOMMENDATION=BEGIN_MEMORY_OPTIMIZATION_FOR_N91`, or
- `PHASE3_RECOMMENDATION=RUN_N81_DTAU_0P08_BEFORE_MEMORY_OPTIMIZATION`

No N91 run starts automatically.
