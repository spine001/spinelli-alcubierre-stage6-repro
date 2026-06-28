# Stage 8D PG-Horizon High-Resolution Summary

Stage 8D extended the PG-horizon exterior near-horizon branch to higher resolution.

Cases tested:

- geometry: pg_horizon
- model: Painleve-Gullstrand-like horizon-regular radial-flow metric
- mask: schwarz_exterior
- mass: 1.25
- eps: 0.35
- width: 1.00
- N: 101, 111, 121

Main findings:

1. Action/Fit remained essentially pinned to unity through N121.
2. Relative tensor difference remained below 0.5% across N101, N111, and N121.
3. Absolute Bianchi decreased monotonically with increasing resolution.
4. Relative Bianchi also decreased with increasing resolution.
5. beta_fit remained negative and bounded, approximately in the -0.3 to -0.45 range.
6. lambda_fit and lambda_action remained nearly identical.

Interpretation:

Stage 8D strengthens the PG-horizon exterior branch as a high-resolution near-horizon validation case for the Spinelli Framework. The action-derived correction tensor remains strongly predictive in a horizon-regular radial-flow chart, while the fitted beta coefficient behaves as a geometry-dependent effective parameter rather than a universal constant.
