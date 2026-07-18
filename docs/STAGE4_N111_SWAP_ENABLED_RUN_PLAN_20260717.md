# Stage 4 N111 Swap-Enabled Run Plan

**Date:** 2026-07-17  
**Notebook SHA-256:** `1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe`

## Controlled configuration

- DIM = 4
- N = 111
- DELTA_TAU = 0.04
- MANUAL_MEMORY_BUDGET_GIB = 512
- All physical and numerical parameters otherwise unchanged
- Historical notebook remains unchanged on disk

## Expected resources

- Working-set projection: 328.640 GiB
- CPU-bound runtime projection: 904.81 seconds
- Paging: allowed
- Swap use: allowed and measured
- Wall time: potentially much longer than the CPU-bound estimate

## Preflight requirements

- MemAvailable >= 128 GiB
- SwapFree >= 512 GiB
- Result filesystem free >= 120 GiB
- No competing heavy Stage 4 or Stage 6 Python calculation
- Verified N101 PASS evidence
- Verified notebook and installed-script hashes

## Corrected sampling

The wrapper samples the actual Python process every five seconds and stores:

`stage4_n111_resource_samples.csv`

The sampler includes process RSS, process swap, virtual-memory high-water
values, major faults, system memory, system swap, and kernel paging
counters.

## Completion

The wrapper creates one result ZIP and a six-grid
N61/N71/N81/N91/N101/N111 report. N121 is recommended when N111 exits
cleanly and all principal diagnostics remain monotonic.
