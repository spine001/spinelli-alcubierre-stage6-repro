# Stage 4 Swap Authorization: N141 through N201

**Date:** 2026-07-18  
**Maximum authorized process swap:** 2990 GiB  
**Maximum authorized ladder point:** N201

## Authorization model

The measured N131 maximum instantaneous process footprint was
543.005581 GiB, with 238.245651 GiB peak RSS.
Scaling that footprint as N⁴ gives:

| Case | Notebook 260-field estimate | Measured-footprint projection | Projected process swap | Descriptive runtime projection |
|---|---:|---:|---:|---:|
| N141 | 765.7 GiB | 728.8 GiB | 490.5 GiB | 6.6 h |
| N151 | 1007.1 GiB | 958.6 GiB | 720.3 GiB | 16.3 h |
| N161 | 1301.6 GiB | 1238.9 GiB | 1000.6 GiB | 38.0 h |
| N171 | 1656.3 GiB | 1576.5 GiB | 1338.3 GiB | 84.3 h |
| N181 | 2079.1 GiB | 1978.9 GiB | 1740.7 GiB | 178.8 h |
| N191 | 2578.1 GiB | 2453.9 GiB | 2215.6 GiB | 364.2 h |
| N201 | 3161.9 GiB | 3009.6 GiB | 2771.3 GiB | 715.4 h |

The runtime column is a descriptive extrapolation from the measured
N121-to-N131 paging slowdown. It is not an execution gate and becomes
increasingly uncertain at higher swap occupancy.

## Why the ceiling is N201

- N201 projected total process footprint:
  3009.562 GiB.
- N201 projected process swap:
  2771.317 GiB.
- N211 projected process swap:
  3416.431 GiB.

N201 is therefore the highest +10 grid point below the authorized
2990 GiB process-swap ceiling. N211 is not authorized.

## Notebook selector correction

For authorized continuation cases, cell 3 is patched in memory to use:

- requested target as `MAX_N_CAP`;
- `MANUAL_MEMORY_BUDGET_GIB = 4096`;
- unchanged DIM=4 and DELTA_TAU=0.04.

The 4096 GiB value is a selector allowance, not a claim
of physical RAM. Actual execution remains constrained by measured RAM,
swap, and the hard 2990 GiB swap ceiling.

## Runtime gates

The workflow stops and packages all available evidence when:

- a case exits nonzero;
- principal monotonicity is lost;
- the projected next-case process swap exceeds 2990 GiB;
- sampled process swap reaches 2990 GiB; or
- sampled system swap use reaches 2990 GiB.

Every exit path creates a recoverable aggregate ZIP.
