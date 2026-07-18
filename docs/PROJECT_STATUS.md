# Spinelli Framework / Alcubierre Validation — Project Status

**Status date:** 2026-07-17  
**Repository baseline before this update:** `709cd1a3c25816a3a90730db33ed35595600914f`  
**Notebook SHA-256:** `1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe`

## Completed

- N61, N71, N81, and N91 spatial runs: PASS
- N71 proper-time matrix: PASS
- N81 proper-time confirmation: PASS
- Streaming-memory N61/N81 regressions: PASS
- N91 optimized production run and four-grid analysis: PASS
- N91 evidence publication commit: `709cd1a3c25816a3a90730db33ed35595600914f`

## N91 measurements

- Peak RSS: 148.092434 GiB
- Runtime: 411.16 seconds
- Swap: 0
- Principal spatial monotonicity: PASS

## Current task

Publish the complete N91 evidence and execute N101 using the validated streaming
implementation.

The N101 workflow permits swap and records:

- maximum process RSS;
- maximum process VmSwap;
- minimum system MemAvailable;
- maximum system swap occupancy;
- paging activity;
- runtime and exit status.

## Resolution policy

Insufficient physical RAM alone no longer blocks a run. Optimization and swap-aware
execution proceed together.

N111 will be considered after N101 based primarily on numerical validity and available
virtual-memory/storage capacity, not on a physical-RAM-only threshold.
