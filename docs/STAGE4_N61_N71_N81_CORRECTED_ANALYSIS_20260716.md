# Stage 4R N61/N71/N81 — Corrected Three-Grid Analysis

**Date:** 2026-07-16  
**Notebook SHA-256:** `1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe`  
**N71 run status:** PASS

## Why this corrected analysis is necessary

The original N71 postprocessor fitted each monotonic sequence exactly to

`q(h) = q_infinity + C h^p`

using only three values. That is mathematically solvable, but an exact three-point fit has
no degrees of freedom for checking model adequacy.

For the nonnegative Bianchi and classical rho error metrics, the unconstrained fit produced
negative continuum values. Those limits are not physically admissible for norms or error
magnitudes. They are therefore rejected, while the original values remain preserved as
raw provenance.

## Robust resolution result

All four principal diagnostics decrease monotonically:

| Metric | N61 | N71 | N81 |
|---|---:|---:|---:|
| Relative Bianchi residual | 0.00603191210189 | 0.00453843762693 | 0.00352999838332 |
| Classical rho peak error | 0.0496463826384 | 0.0370338509084 | 0.0285866953681 |
| Hessian-Q normalized residual | 0.0189236083292 | 0.0155450475606 | 0.0135744981064 |
| Best HTR normalized residual | 0.0166144108079 | 0.0127054865137 | 0.0102418757555 |

### Pairwise effective zero-limit orders

| Metric | N61→N71 | N71→N81 | Interpretation |
|---|---:|---:|---|
| Bianchi | 1.845 | 1.882 | Stable, close to second order |
| rho peak error | 1.901 | 1.939 | Stable, close to second order |
| Hessian-Q | 1.276 | 1.015 | Fine-grid behavior near first order |
| HTR | 1.740 | 1.614 | Stable decrease around order 1.6–1.7 |

The strongest defensible conclusion is that Bianchi and the classical rho error show
stable near-second-order decay across both adjacent grid intervals. Hessian-Q and HTR also
improve monotonically, but at different effective rates.

## Coefficient behavior

- `lambda_fit`: 0.015789560483 → 0.0160469927834 → 0.0162274185811
- `beta_fit`: -1.03066456537 → -1.03429601867 → -1.03651301313

Both coefficients move monotonically. The exact three-point nonzero-limit fits
(`lambda≈0.01706`, `beta≈-1.04232`) are provisional, not validated continuum values.
Notably, beta moves farther from the action coefficient `-1`.

## Action comparison

- Action/Fit: 1.0000226652, 1.00000401927, 1.00002445109
- Tensor difference: 0.027417084%, 0.029452344%, 0.030532789%

Action/Fit is nonmonotonic but remains within about 25 parts per million of unity.
The tensor mismatch rises monotonically but remains only about 0.03%. Its nonzero-limit
fit is provisional.

## Resource validation

- Measured N71 peak RSS: 104.316132 GiB
- N^4 prediction: 104.478439 GiB
- Memory prediction error: -0.155%
- Measured runtime: 151.29 s
- Runtime prediction: 149.98 s
- Runtime prediction error: 0.870%
- Swap: 0

The empirical N^4 resource model remains validated to well below 1%.

## Scientific conclusion

The three-grid sequence provides strong evidence that the principal Stage 4 geometry and
conservation residuals decrease with resolution. Bianchi and the classical rho benchmark
are especially convincing because their adjacent-grid effective orders are stable and
near two.

It does not yet justify literal continuum values for every metric. Negative extrapolated
limits are rejected, and all remaining three-point continuum estimates are labeled
provisional.

## Next priority

The next independent numerical question is proper-time-step sensitivity at a fixed grid,
preferably N71, testing `DELTA_TAU = 0.02, 0.04, 0.08` sequentially. This separates
proper-time finite-difference sensitivity from spatial-grid convergence.
