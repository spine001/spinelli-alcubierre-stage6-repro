# Spinelli Framework / Alcubierre Validation — Project Status

**Status date:** 2026-07-16  
**Run baseline commit:** `0ebf492f3800cf108e735ec59e5ea85358b19e66`  
**Authoritative Stage 4 notebook SHA-256:** `1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe`

## Stage 4R N61

The exact terminal regression reproduced all six recovered Stage 4A–4D canonical tables
within the declared floating-point tolerances.

## Stage 4R N81

The controlled N81 resolution run completed successfully.

- Historical notebook modified on disk: no
- Selected grid: DIM=4, N=81
- Runtime: 254.07 seconds
- Peak RSS: 176.983734 GiB
- Swap: 0
- Exit status: 0

### N61 → N81 trends

- Relative Bianchi residual: -41.478%
- Classical rho peak error: -42.419%
- Hessian-Q residual: -28.267%
- Best HTR residual: -38.355%

Geometry and conservation diagnostics therefore improve strongly with resolution.

`lambda_fit` increased by 2.773%. `beta_fit`
moved from -1.03066456537 to -1.03651301313. Action/Fit
remained extremely close to unity at 1.00002445109283,
but the tiny action-fit tensor difference increased to
0.030532789%.

The proper conclusion is strong two-grid numerical improvement, not complete coefficient
convergence.

## Resource model

The N61-based N^4 prediction for N81 was 176.466 GiB. The measured peak was
176.984 GiB, an error of only 0.293%.

The notebook's internal estimate of 83.388 GiB was low by a factor of
2.122. Future dense-grid safety checks must use measured
peak scaling rather than the notebook estimate alone.

## Next run

Run N71 as the intermediate third grid.

- Projected peak RSS: 104.48 GiB
- Projected runtime: 150.0 seconds
- Purpose: generalized three-grid observed-order and continuum-estimate analysis

N91 and N101 are not selected because measured N^4 scaling projects approximately
281.9 GiB and 427.8 GiB respectively.

## Later order

1. N71 three-grid resolution analysis.
2. Stage 4 delta-tau sensitivity.
3. Domain-size and interior-crop sensitivity.
4. Derivative-order sensitivity.
5. Stage 5 observer-projected energy-density reanalysis.
6. Adaptive Stage 5 parameter revalidation.

## Preservation rule

Historical sources remain immutable under `historical/stages1-5/`. New computations are
stored under separate `results/stage4_revalidation_*` paths.
