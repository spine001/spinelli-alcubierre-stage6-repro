# Stage 4 N101 Five-Grid Analysis and N111 Policy

**Date:** 2026-07-17  
**Notebook SHA-256:** `1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe`  
**N101 result:** PASS

## N101 execution

- Grid: N101
- DELTA_TAU: 0.04
- Peak RSS: 225.275547 GiB
- Wall time: 620.23 seconds
- Exit status: 0
- Swap used by the completed run: 0 GiB
- Historical notebook changed on disk: no

## Five-grid spatial behavior

All four principal diagnostics decreased monotonically over
N61/N71/N81/N91/N101.

| Diagnostic | N91 | N101 | N91→N101 order |
|---|---:|---:|---:|
| Relative Bianchi residual | 0.00281988028106 | 0.002302252148 | 1.924882 |
| Classical rho error | 0.0227403023102 | 0.0185091495687 | 1.953992 |
| Hessian-Q residual | 0.0124085733877 | 0.0117091498471 | 0.550653 |
| HTR residual | 0.0086606637656 | 0.00763775631249 | 1.192928 |

Bianchi and rho remain close to second order. Hessian-Q and HTR continue
to improve, with declining local effective order.

## N111 authorization

The measured N101 peak projects an N111 working-set scale of approximately
328.640 GiB.

N111 is authorized under the swap-enabled policy. Physical RAM is not a
hard gate. The CPU-bound runtime estimate is 15.08
minutes; paging may increase wall time substantially.

## Resource interpretation

For N111, process resource accounting will use:

- the actual Python PID, not the `/usr/bin/time` parent;
- VmRSS, VmSwap, VmSize, VmHWM, and VmPeak;
- process major page faults;
- system MemAvailable and swap occupancy;
- cumulative kernel `pswpin` and `pswpout` counters.

The six-grid analysis will use the sampled maximum of `VmRSS + VmSwap` as
an approximate instantaneous process working-set footprint when paging is
active.
