# Spinelli Framework / Alcubierre Validation — Project Status

**Status date:** 2026-07-16  
**Current verified public baseline:** `a5465aa215af01d0eda8a23b0c12a91193ba3842`  
**Historical Stage 1–5 recovery:** `0f9dba3e1574cf4e25b0f9f8a9d8d65854ee71d4`

## Stage 6E

The N301 `v_s=1.0`, `sigma=4`, `R=3` case passed the rho-aware v2 gate. Its isolated
extreme-rho tile was classified as `LIKELY_BOUNDARY_OR_HALO_ARTIFACT` by the full local
ring-neighborhood diagnostic. The warning and detailed evidence remain preserved.

## Stage 4R exact N61 regression

The recovered authoritative notebook was executed directly from the terminal on the
256 GB server.

- Notebook SHA-256: `1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe`
- Configuration: DIM=4, N=61, R=3, sigma=1, `v_s=0.5`, delta-tau=0.04, crop=3
- Canonical tables checked: 6
- Tables passing: 6
- Differences outside tolerance: 0
- Maximum absolute difference: `7.3712147496962643e-12`
- Maximum relative difference: `1.0384524074045325e-09`
- Wall-clock runtime: 83.79 seconds
- Peak resident memory: 56.759686 GiB
- Swap events: 0

The first two tables matched exactly. Remaining tables differed only at floating-point
levels, with the largest absolute difference approximately `7.37e-12`.

This validates the historical computational lineage and establishes the verified N61
baseline for a new resolution series. It does not add an independent physical model or
prove physical realizability.

## Next run

The next priority is Stage 4 N81 using the same notebook and physics parameters.

The notebook's original requested cap is already N=81. The controlled runner leaves the
historical notebook unchanged on disk and modifies only its in-memory memory-budget line
from 28 GiB to 220 GiB so that N=81 is selected.

- Measured N61 peak RSS: 56.7597 GiB
- N^4-scaled N81 projection: 176.4659 GiB
- Required available physical RAM before start: 220 GiB
- Swap policy: emergency protection only

The N81 result will be compared with N61. Two resolutions can establish trends, but not a
formal observed convergence order.

## Later order

1. Stage 4 N81 resolution run.
2. Add a third resolution selected from the N81 result and measured memory behavior.
3. Stage 4 delta-tau, domain-size, crop, and derivative-order sensitivity tests.
4. Stage 5 observer-projected energy-density reanalysis.
5. Adaptive Stage 5 parameter revalidation.

## Preservation rule

`historical/stages1-5/` remains immutable. New outputs are stored under separate
`results/stage4_revalidation_*` and `results/published/stage4_revalidation_*` paths.
