# Stage 4R N71 Proper-Time-Step Sensitivity

**Analysis date:** 2026-07-17  
**Notebook SHA-256:** `1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe`  
**Matrix status:** PASS

## Controlled matrix

The verified N71/DELTA_TAU=0.04 result was reused. New DELTA_TAU=0.02 and 0.08
cases were executed sequentially in separate Python processes.

All code cells passed in both new cases. The historical notebook remained unchanged on
disk, both processes exited with status zero, and neither process used swap.

## Main result

The proper-time-step effect is much smaller than the previously measured spatial-grid
effect.

| Metric | DELTA_TAU 0.02 | 0.04 | 0.08 | Fine vs baseline |
|---|---:|---:|---:|---:|
| Bianchi residual | 0.00453843762693 | 0.00453843762693 | 0.00453843762693 | 0% |
| Classical rho error | 0.0370338509084 | 0.0370338509084 | 0.0370338509084 | 0% |
| Hessian-Q residual | 0.0155467752562 | 0.0155450475606 | 0.0155381467744 | 0.0111141% |
| HTR residual | 0.0127078431621 | 0.0127054865137 | 0.0126960704211 | 0.0185483% |

The maximum fine-step changes were:

- Principal diagnostics: 0.0185482734%
- Fitted coefficients: 0.0104432375%
- Action-fit tensor difference: 0.0153299767%
- Action/Fit absolute change: 0.0686332204 ppm

## Observed DELTA_TAU order

For the quantities that changed, the 0.02/0.04/0.08 sequence produced effective orders
very close to two:

- Hessian-Q: 1.997912
- HTR: 1.998392
- lambda_fit: 1.999055
- beta_fit: 1.998714
- Action/Fit: 2.002668
- Tensor difference: 1.999882

Bianchi and the classical rho benchmark were exactly unchanged because their current
notebook computation path is independent of DELTA_TAU. They should be described as
invariant in this sweep, not as a failed convergence sequence.

## Phase 2 decision

`PHASE2_RECOMMENDATION=N81_DTAU_0P02_CONFIRMATION_ONLY`

A full N81 three-step matrix is not justified. One N81/DELTA_TAU=0.02 confirmation is
sufficient to test whether the very small fine-step sensitivity persists at the finest
currently verified spatial grid.

After that confirmation, the reporting script will either recommend beginning the
memory-optimization phase for N91 or request the missing N81/DELTA_TAU=0.08 case if the
fine-grid sensitivity unexpectedly exceeds the declared thresholds.
