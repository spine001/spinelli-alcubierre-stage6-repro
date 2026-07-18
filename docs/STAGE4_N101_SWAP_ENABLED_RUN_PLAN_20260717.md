# Stage 4 N101 Swap-Enabled Run Plan

**Date:** 2026-07-17  
**Notebook SHA-256:** `1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe`

## Configuration

- DIM = 4
- N = 101
- DELTA_TAU = 0.04
- MANUAL_MEMORY_BUDGET_GIB = 220
- Existing physical and numerical parameters unchanged

## Resource expectation

- CPU-bound peak projection: 224.726 GiB
- CPU-bound runtime projection: 623.92 seconds
- Paging policy: ALLOWED
- Swap usage: measured, not a failure condition

## Preflight

The run requires:

- MemAvailable >= 160 GiB
- SwapFree >= 256 GiB
- result filesystem free >= 120 GiB
- no competing Stage 4/Stage 6 heavy Python calculation

These thresholds protect against concurrent workloads but do not require N101 to fit
entirely in physical RAM.

## Persistent resource sampling

While Python runs, the wrapper records a CSV sample every five seconds containing:

- Python PID and state
- VmRSS
- VmSwap
- system MemAvailable
- system swap used

## Completion

The run creates canonical exports, a production report, a memory profile, resource
samples, a full log, and a five-grid N61/N71/N81/N91/N101 analysis.

If the principal metrics remain monotonic, the report recommends an N111 runner. The
recommendation may explicitly require swap-enabled execution.
