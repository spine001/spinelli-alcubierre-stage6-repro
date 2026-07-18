# Stage 4 N111 Six-Grid Analysis

**Date:** 2026-07-18  
**Notebook SHA-256:** `1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe`  
**N111 result archive SHA-256:** `3ee2802b63b6cd430987a80f3f7301546444ef8ab1f3dbefbfe04939d4370d9a`

## Execution result

N111 completed successfully with all executable notebook cells passing.

- Grid: N111
- DELTA_TAU: 0.04
- Peak RSS: 238.242134 GiB
- Maximum sampled process swap: 75.525066 GiB
- Maximum sampled RSS plus process swap: 310.656925 GiB
- Maximum sampled system swap use: 122.655338 GiB
- Wall time: 1425.53 seconds
- Process major faults: 2576485
- Historical notebook modified on disk: no
- Resource sampler: PASS

## Six-grid numerical behavior

All principal diagnostics remain strictly monotonic over
N61/N71/N81/N91/N101/N111.

| Diagnostic | N101 | N111 | N101→N111 order |
|---|---:|---:|---:|
| Relative Bianchi residual | 0.002302252148 | 0.00191393522844 | 1.938160 |
| Classical rho error | 0.0185091495687 | 0.0153520916408 | 1.962156 |
| Hessian-Q residual | 0.0117091498471 | 0.011283480289 | 0.388530 |
| HTR residual | 0.00763775631249 | 0.00697435634695 | 0.953349 |

Bianchi and rho continue to approach second-order behavior. Hessian-Q and
HTR remain monotonic but show declining local order, making additional
high-resolution points scientifically useful.

## Recommendation

The N111 report authorizes N121. To use unattended processing time
efficiently, the next phase is a guarded sequential batch:

`N121 → N131 → N141 → N151`

Each case is analyzed before the next begins. The batch stops immediately
if execution fails or any principal residual loses monotonicity.
