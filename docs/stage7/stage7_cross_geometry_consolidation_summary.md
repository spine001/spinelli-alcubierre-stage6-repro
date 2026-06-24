# Stage 7 Cross-Geometry Consolidation

This package consolidates Stage 7A-J results for the Spinelli Framework cross-geometry validation branch.

Core conclusion: the action-derived correction tensor remains residual-predictive across several geometry classes, but the fitted beta coefficient is geometry dependent. The Alcubierre beta≈-1 result is best interpreted as a steep-wall limit, not a universal coefficient.

Key branches:

- Alcubierre Stage 6B: steep-wall behavior organizes around beta=-1 with high-resolution overshoot.
- Gaussian Stage 7E-F: Action/Fit approaches unity with increasing width; beta moves toward zero.
- FRW Stage 7G: Action/Fit remains near unity across amplitude/omega sweeps; beta is positive and mode-dependent.
- Weak-GW Stage 7H: mask choice does not explain behavior; amplitude sensitivity dominates.
- Static shell Stage 7I: stable but fit-degenerate; shell-edge mask helps but does not rescue it.
- Schwarzschild-like Stage 7J: smooth-lapse redesign gives a partial exterior-side near-horizon signal.

Generated article:

- `article/alcubierre_drive_within_reach_with_stage7_cross_geometry_consolidated.html`

Generated consolidated result tables:

- `results/stage7_consolidated_all_results.csv`
- individual Stage 7 summary CSVs under `results/stage7/`

Generated figures:

- `plots/stage7_action_fit_resolution_ladder.png`
- `plots/stage7_beta_geometry_dependence.png`
- `plots/stage7_gaussian_width_confirmation.png`
- `plots/stage7_frw_sweep_heatmap.png`
- `plots/stage7_weakgw_amplitude_mask.png`
- `plots/stage7_static_schwarz_mask_diagnostics.png`
