# Spinelli Framework / Alcubierre Validation — Project Status

**Status date:** 2026-07-15  
**Public historical-recovery baseline:** `0f9dba3e1574cf4e25b0f9f8a9d8d65854ee71d4`

## Current validation state

Historical Stages 1–5 are preserved under `historical/stages1-5/` with article lineage,
three valid Jupyter notebooks, primary tables, export packages, checksums, and an explicit
retrospective-provenance disclosure.

Stage 6E has now completed the N301, `v_s=1.0`, `sigma=4`, `R=3` tiled run.

## N301 v_s=1.0 result

- Gate status: **PASS**
- Runtime: 67.098947 hours
- Tiles: 115,600 FIT + 115,600 SCORE
- `lambda_fit`: 1.025394848666301
- `beta_fit`: -1.763609007454936
- Robust Action/Fit: 0.9981612880562719
- Robust tensor difference: 1.143492551767036%
- Robust Bianchi: 0.03390250622778634
- Summed-peak rho relative error: 0.02433798003304372
- Excluded contributing fraction: 9.50422420426977e-05
- Corrupt contributing tiles quarantined: 2

## Interpretation

The run satisfies every predeclared rho-aware v2 gate. Relative to N261 at the same
velocity, the Bianchi residual and aggregate rho diagnostic improve materially, and
Action/Fit moves slightly toward unity. The fitted beta and tensor-difference metrics are
not monotonic with resolution, so the project must not claim monotonic convergence of
every fitted quantity.

The extreme-peak rho value remains a warning-only diagnostic. Its maximum is localized to:

`N301_v1_sigma4_R3/tiles/tile000864_t0-9_x62-93_y155-186_z126-135.score.json`

The next priority is a ring-neighborhood diagnostic of that tile, using the already
committed/local diagnostic method previously applied to the N301 `v_s=0.5` outlier.

## Next computation order

1. N301 `v_s=1.0` local rho-outlier diagnostic.
2. Terminal-only Stage 4 exact N61 regression.
3. Stage 4 N81 dense convergence run after the N61 regression passes.
4. Additional Stage 4 delta-tau/domain/crop sensitivity tests.
5. Stage 5 observer-projected magnitude reanalysis and adaptive parameter sweep.

## Required disclosures

- Two corrupt tiles were quarantined because of astronomical `Cact2` values.
- The excluded fraction is small and within the gate, but tile names/reasons must be published.
- The extreme rho peak is not a gate failure under v2; it requires local manual review.
- The result validates the defined numerical gate for this test geometry. It does not prove
  physical realizability of an Alcubierre drive.
