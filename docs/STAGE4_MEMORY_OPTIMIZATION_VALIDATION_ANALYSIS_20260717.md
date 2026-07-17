# Stage 4 Memory-Optimization Validation

**Date:** 2026-07-17  
**Notebook SHA-256:** `1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe`  
**Validation status:** PASS

## Canonical regression

The streaming implementation reproduced all six canonical tables at both N61 and N81.

- Stage 4A: exact
- Stage 4B: exact
- Stage 4C fit: exact
- Stage 4C ranking: exact
- Stage 4D comparison: agreement to floating-point roundoff
- Stage 4D summary: exact

The historical notebook remained unchanged. Both processes exited with status zero and
used no swap.

## Measured memory reduction

| Grid | Original peak RSS | Optimized peak RSS | Reduction |
|---|---:|---:|---:|
| N61 | 56.759686 GiB | 29.643742 GiB | 47.773% |
| N81 | 176.983734 GiB | 92.700161 GiB | 47.622% |

The optimized N61-to-N81 memory exponent is `4.0205`, confirming
that the remaining dominant storage still follows the expected N^4 dense-grid scaling.

## What changed

The numerical geometry, Hessian calculation, fit, and canonical formulas were not
changed. Only late documentary/export behavior was streamed:

1. Direct candidates are scored one at a time and discarded.
2. The winning candidate is recomputed once for plots and released.
3. Fitted, action, and difference tensors are scored sequentially.
4. Only scalar results and two-dimensional central slices survive for plotting.

## N91 authorization

The measured optimized N81 peak projects:

- N91: 147.674661 GiB
- N101: 224.091771 GiB

N91 is safely below the 190 GiB gate and is authorized.

The expected no-swap N91 runtime is approximately
6.90 minutes.

## N101 status

N101 is not authorized yet. The current projection of 224.092 GiB
leaves too little physical-memory margin on the 245 GiB server. Its feasibility will be
recomputed from the measured N91 peak. A production N101 run requires a projected peak
of at most 205 GiB or another optimization cycle.
