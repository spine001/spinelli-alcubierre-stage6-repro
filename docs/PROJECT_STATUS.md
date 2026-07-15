# Spinelli Framework / Alcubierre Validation — Current Project Status

**Status date:** 2026-07-15  
**Current public baseline:** `1ea683db30bbe9d9c303205fa613bb9d50c9a96a`  
**Historical Stage 1–5 recovery:** `0f9dba3e1574cf4e25b0f9f8a9d8d65854ee71d4`

## Completed work

- Historical Stages 1–5 are preserved with article lineage, notebooks, result tables,
  export packages, checksums, and explicit retrospective-provenance disclosure.
- Stage 6E rho-aware v2 PASS results are complete at N261 and N301 for
  `v_s=0.5` and `v_s=1.0`.
- The N301 `v_s=1.0`, `sigma=4`, `R=3` summary and self-contained master were published
  in commit `1ea683db30bbe9d9c303205fa613bb9d50c9a96a`.
- The remaining N301 `v_s=1.0` extreme-rho warning was examined with the established
  local ring-neighborhood diagnostic.

## N301 v_s=1.0 outlier closure

Target:

`N301_v1_sigma4_R3/tiles/tile000864_t0-9_x62-93_y155-186_z126-135.score.json`

Classification:

`LIKELY_BOUNDARY_OR_HALO_ARTIFACT`

Runner result:

`DIAGNOSTIC_RUN_RESULT=PASS`

The diagnostic loaded all 115,600 score files. The classification indicates that the
isolated maximum-ratio tile is more consistent with a boundary/halo effect than with a
spatially coherent physical failure. The detailed TXT, CSV, and JSON diagnostic records
remain part of the auditable evidence and must be published.

## Current scientific interpretation

The N301 `v_s=1.0` case remains a rho-aware v2 PASS. The aggregate rho metric passes,
the corrupt-tile exclusion fraction remains below the predeclared limit, and the isolated
extreme warning has been locally classified.

This validates the defined numerical gate for the tested geometry. It does not establish
physical realizability, engineering feasibility, chronology safety, or a general proof
of the Spinelli Framework.

## Next run order

1. **Stage 4 exact N61 terminal regression.**
   - Execute the original committed notebook code without Jupyter.
   - Confirm that the new server reproduces the recovered Stage 4A–4D canonical tables.
   - Treat this as a regression test, not as new evidence.

2. **Stage 4 N81 dense convergence run**, only after N61 passes.
3. Stage 4 delta-tau, domain-size, crop, and derivative-order sensitivity tests.
4. Stage 5 observer-projected energy-density reanalysis.
5. Adaptive Stage 5 parameter revalidation.

## Preservation rule

The historical files under `historical/stages1-5/` are immutable evidence. New
revalidation outputs belong under separate `results/stage4_revalidation_*` paths.
