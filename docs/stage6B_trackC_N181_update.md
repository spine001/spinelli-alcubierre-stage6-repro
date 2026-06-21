# Stage 6B Track C and N181 Update

This update adds the final Stage 6B post-N161 validation files to the reproducibility repository.

Included:

- `results/stage6B_tiled_convergence_through_N181.csv`
- `results/stage6B_N181_single_v1_results.csv`
- `results/stage6B_N181_single_v1_summary.json`
- `results/trackC_crosscheck_summary.csv`
- `results/trackC_crosscheck_summary.json`
- `plots/*.png`
- `packages/N181_stage6B_single_v1_wall_float64_outputs.zip`
- `packages/trackC_after_N161_outputs.zip`
- `article/alcubierre_drive_within_reach_with_stage6B_trackC_N181_update.html`

Key interpretation:

- Track C confirms that the N=141, v_s=1.0 result is stable under tile-size, halo, and wall-shell variations.
- The N=181 single-case v_s=1.0 probe shows continued beta overshoot: beta_fit = -1.347998.
- Action/Fit remains residual-equivalent to the fitted tensor: Action/Fit = 0.998927.
- The N=181 probe should be described as a single-case overshoot diagnostic, not as a two-case median replacement.

Repository citation:

https://github.com/spine001/spinelli-alcubierre-stage6-repro
