# Stage 8A PG-Horizon Near-Horizon Baseline Summary

Stage 8A introduced a dedicated near-horizon model using a Painleve-Gullstrand-like horizon-regular radial-flow metric.

Cases tested:

- geometry: pg_horizon
- N: 61
- mass: 1.25
- width: 0.75
- eps: 0.35
- masks: localized, schwarz_center, schwarz_edge, schwarz_exterior, schwarz_interior, all

Main findings:

1. The PG-horizon model substantially improved the exterior near-horizon signal compared with the Stage 7J smooth-lapse Schwarzschild-like surrogate.
2. The schwarz_exterior mask gave the best result: Action/Fit near 1.021 and relative tensor difference near 5.42%.
3. The schwarz_center mask was also promising, with Action/Fit near 1.083 and relative tensor difference near 6.00%.
4. Broad masks, interior masks, and edge masks remained poorly conditioned.
5. Absolute Bianchi values were small for the best exterior/center masks, while relative Bianchi remained elevated because the local Einstein-tensor norm is small.
6. beta_fit is strongly negative in the useful masks and is not yet established as stable.

Interpretation:

Stage 8A suggests that near-horizon behavior is highly coordinate/model dependent. A horizon-regular radial-flow metric produces a meaningful exterior-side signal, supporting continued dedicated near-horizon development. The next required step is a parameter stability sweep over width and core regularization using only the promising masks.
