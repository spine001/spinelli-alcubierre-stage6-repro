# Stage 4R N61 → N81 Resolution Analysis

**Analysis date:** 2026-07-16  
**Authoritative notebook SHA-256:** `1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe`  
**N81 result:** `STAGE4_N81_RUN_RESULT=PASS`

## Executive result

The controlled N81 execution is valid. All notebook cells completed, the historical
notebook remained unchanged on disk, and the run used the same physical and numerical
parameters as the verified N61 baseline except for spatial/temporal grid resolution.

The four principal error or conservation indicators all improved:

| Metric | N61 | N81 | Change |
|---|---:|---:|---:|
| Relative Bianchi residual | 0.00603191210189 | 0.00352999838332 | -41.478% |
| Classical rho peak error | 0.0496463826384 | 0.0285866953681 | -42.419% |
| Hessian-Q residual | 0.0189236083292 | 0.0135744981064 | -28.267% |
| Best HTR residual | 0.0166144108079 | 0.0102418757555 | -38.355% |

The two-grid zero-limit decay exponents are approximately:

- Bianchi residual: 1.862
- rho peak error: 1.919
- Hessian-Q residual: 1.155
- HTR residual: 1.682

These are descriptive two-grid exponents, not formal observed convergence orders.

## Fitted coefficients and action comparison

- `lambda_fit` changed by 2.773%.
- `beta_fit` changed from -1.03066456537 to -1.03651301313.
- The distance of `beta_fit` from the action value -1 increased from
  0.030664565 to 0.036513013, a 19.072% increase.
- HTR improvement over H increased from 42.622% to
  43.278%.
- Action/Fit remained extremely close to unity:
  1.00002445109283.
- The action residual penalty at N81 was only
  0.0024451093%.
- Tensor difference increased to
  0.030532789%, still a very small absolute mismatch.

The coefficient drift and the slight worsening of the action-fit mismatch mean that
coefficient convergence should not yet be declared.

## Resource validation

- N61 measured peak RSS: 56.759686 GiB.
- N81 measured peak RSS: 176.983734 GiB.
- N^4 prediction from N61: 176.465868 GiB.
- Prediction error: 0.2935%.
- Notebook internal estimate: 83.387997 GiB.
- Actual/notebook-estimate factor: 2.1224.
- N81 wall time: 254.07 seconds.
- Swap used by the run: 0.

The empirical N^4 scaling model was excellent. The notebook's internal footprint estimate
should not be used as the sole safety limit because it was about a factor of 2.12 below
the measured process peak at both N61 and N81.

## Next resolution

N71 is recommended as the third level:

- Projected peak RSS: 104.48 GiB.
- Projected runtime: 150.0 seconds.
- It lies between N61 and N81 and permits generalized three-grid observed-order analysis.

N91 and N101 are not appropriate in-memory next runs on this server:

- N91 projected RSS: 281.9 GiB.
- N101 projected RSS: 427.8 GiB.

A large swap allocation protects against abrupt out-of-memory termination but should not
be treated as equivalent to physical RAM for this dense four-dimensional workload.
