# Stage 8C PG-Horizon Resolution Ladder Summary

Stage 8C tested the best Stage 8B near-horizon exterior candidate across a resolution ladder.

Cases tested:

- geometry: pg_horizon
- model: Painleve-Gullstrand-like horizon-regular radial-flow metric
- mask: schwarz_exterior
- mass: 1.25
- eps: 0.35
- width: 1.00
- N: 61, 71, 81, 91

Main findings:

1. Action/Fit remained essentially pinned to unity across the full N61-N91 ladder.
2. Relative tensor difference improved from approximately 0.740% at N61 to approximately 0.457% at N91.
3. Absolute Bianchi decreased monotonically with resolution.
4. Relative Bianchi also decreased substantially with resolution.
5. beta_fit appears to stabilize around approximately -0.31 to -0.34 from N71 through N91.
6. The N61 beta value appears to be a coarse-grid artifact.

Interpretation:

Stage 8C establishes the PG-horizon exterior branch as a clean near-horizon validation case for the Spinelli Framework. The action-derived correction tensor remains strongly residual-predictive in a horizon-regular radial-flow chart, supporting the conclusion that near-horizon behavior depends strongly on using an appropriate coordinate/model structure.
