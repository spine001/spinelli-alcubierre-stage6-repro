# Stage 4 N91 Four-Grid Result and N101 Execution Policy

**Date:** 2026-07-17  
**Notebook SHA-256:** `1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe`

## N91 result

N91 completed successfully with every executable cell passing, exit status zero, no
swap during this particular run, and the historical notebook unchanged.

- Measured peak RSS: 148.092434 GiB
- Measured runtime: 411.16 seconds
- Memory projection error: 0.2829%
- Runtime projection error: -0.6970%

All four principal residuals remain monotonic from N61 through N91.

## Scientific sequence

The N81-to-N91 effective orders are:

- Bianchi: 1.906921
- Classical rho error: 1.942577
- Hessian-Q: 0.762463
- HTR: 1.423748

Bianchi and rho remain near second order. Hessian-Q and HTR continue decreasing with
slower effective orders.

## Revised execution policy

Physical RAM is no longer a hard resolution gate.

Memory optimization remains desirable because it reduces wall time and disk traffic, but
a projected peak above physical RAM will not by itself stop the resolution sequence.
Swap/paging is allowed and will be measured.

Hard preflight conditions are now:

1. No competing heavy calculation.
2. Sufficient free swap/virtual-memory capacity.
3. Sufficient result filesystem space.
4. Verified runner, notebook, and baseline evidence.

## N101

The N91 measurement projects N101 at approximately 224.726 GiB. This is near
the available physical-memory ceiling, so N101 may use no swap, modest swap, or transient
paging depending on allocator behavior and system activity.

The CPU-bound runtime estimate is 10.40 minutes. Paging may make the
actual runtime substantially longer; that is acceptable under the revised policy.

## Beyond N101

The five-grid report will recalculate N111 from the measured N101 peak. If the principal
spatial trends remain valid, it will recommend an N111 runner even when swap is expected.
