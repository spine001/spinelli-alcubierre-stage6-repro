# Stage 4 N121/N131 Eight-Grid Analysis and N141 Failure Closure

**Date:** 2026-07-18  
**Notebook SHA-256:** `1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe`  
**Recovery archive SHA-256:** `1d3cf9136c92d3b5b476b4679f51a785d08c7f866f74ad0e3e62dea645461d42`

## Reused completed cases

N121 and N131 are accepted as completed production cases and will not be
rerun.

| Quantity | N121 | N131 |
|---|---:|---:|
| Peak RSS | 238.115608 GiB | 238.245651 GiB |
| Peak process VmSwap | 161.242283 GiB | 310.103741 GiB |
| Peak RSS + process swap | 397.267956 GiB | 543.005581 GiB |
| Peak system swap use | 264.141914 GiB | 470.475838 GiB |
| Wall time | 52.08 min | 148.90 min |
| Principal monotonicity | PASS | PASS |

## Numerical sequence through N131

| Diagnostic | N121 | N131 | N121→N131 order |
|---|---:|---:|---:|
| Relative Bianchi residual | 0.00161549684425 | 0.00138136773611 | 1.956061 |
| Classical rho error | 0.0129326220748 | 0.0110424096016 | 1.974067 |
| Hessian-Q residual | 0.0110207822042 | 0.0108567477701 | 0.187350 |
| HTR residual | 0.00654394297146 | 0.00626480863812 | 0.544607 |

All four principal diagnostics remain strictly decreasing through the
eight-grid N61/N71/N81/N91/N101/N111/N121/N131 sequence.

## N141 failure closure

The failed N141 attempt did not begin the numerical geometry calculation.
Cell 3 selected N131 because the historical notebook contains
`MAX_N_CAP = 131`. The runner then rejected the selected/requested mismatch.

The attempt ended in 0.88 seconds with approximately 0.13 GiB peak RSS,
zero process swap, and no OOM, kernel-memory event, or storage failure.

The continuation runner corrects this only in memory by replacing
`MAX_N_CAP = 131` with the requested authorized grid. The historical
notebook remains unchanged on disk.
