# Stage 7J Schwarzschild-Like Redesign Summary

Stage 7J replaced the original clipped Schwarzschild-like pilot geometry with a bounded smooth-lapse horizon-wall surrogate.

Cases tested:

- geometry: schwarzschild_like
- N: 71
- redesign: smooth_bounded_lapse_wall
- masks: all, localized, schwarz_center, schwarz_edge, schwarz_exterior, schwarz_interior

Main findings:

1. The original Schwarzschild-like failure was partly caused by the clipped near-singular surrogate.
2. The smooth bounded-lapse redesign produced a meaningful partial signal on the exterior side of the horizon-like wall.
3. The schwarz_exterior mask gave the best result: lowest tensor difference, closest Action/Fit ratio, and small Bianchi residual.
4. The center and interior masks remain poor.
5. Near-horizon geometries require physically meaningful exterior/interior treatment and should not be interpreted with a single broad mask.

Interpretation:

The Schwarzschild-like geometry is not a clean validation case yet, but it is no longer simply unreliable. The exterior-side smooth-lapse result suggests that the action-derived correction tensor may capture part of the near-horizon radial-gradient structure, while the interior and center regions remain poorly conditioned under the current pilot model.
