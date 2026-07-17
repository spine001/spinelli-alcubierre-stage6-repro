# Stage 4R N81 Proper-Time Confirmation

**Date:** 2026-07-17  
**Notebook SHA-256:** `1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe`  
**Confirmation status:** PASS

## Controlled result

The N81/DELTA_TAU=0.02 confirmation completed every notebook cell, preserved the
historical notebook on disk, exited with status zero, used no swap, and reproduced the
expected approximately 177 GiB dense-process peak.

- Peak RSS: 176.975353 GiB
- Principal fine-step maximum change: 0.0161359048%
- Coefficient fine-step maximum change: 0.0108151937%
- Tensor-difference fine-step change: 0.0151303004%
- Action/Fit absolute change: 0.135289194 ppm
- Maximum principal DELTA_TAU/spatial-effect ratio: 0.000670811861

The proper-time-step effect remains far below the N71-to-N81 spatial-resolution effect.

## Decision

`PHASE3_RECOMMENDATION=BEGIN_MEMORY_OPTIMIZATION_FOR_N91`

A full N81 DELTA_TAU=0.08 run is not needed.

## Memory-optimization target

The historical notebook's two largest late-run memory accumulations are documentary
export operations, not the geometry itself:

1. Cell 23 retained full Q, mixed-Q, and divergence tensors for every direct candidate.
2. Cell 24 retained fitted, action, and difference tensors and their scored derivatives
   simultaneously.

The new validation runner changes only those two cells in memory:

- Candidate scores are computed sequentially and discarded.
- The best candidate is recomputed once for plots and immediately released.
- Stage 4D fitted, action, and difference tensors are scored sequentially.
- Only two-dimensional central slices and scalar scores are retained for plotting.
- All canonical CSV/JSON values and filenames are preserved.

Before N91 is built, the implementation must reproduce the verified N61 and N81
canonical tables within `rtol=1e-8`, `atol=1e-10` and demonstrate a measured N91
projection below the physical-memory safety threshold.
