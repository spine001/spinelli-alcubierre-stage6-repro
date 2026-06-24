# Stage 7J Schwarzschild-Like Redesign Summary

Stage 7J replaced the original clipped Schwarzschild-like pilot with a smooth bounded lapse-wall surrogate.

Cases tested:

- geometry: schwarzschild_like
- N: 61
- mass: 1.25
- width: 0.75
- eps/lapse floor: 0.35
- score masks: localized, schwarz_center, schwarz_edge, schwarz_exterior, schwarz_interior, all

Main findings:

1. The smooth bounded redesign substantially improves numerical behavior relative to the original clipped surrogate.
2. Bianchi residuals are small enough to treat the run as numerically meaningful.
3. The best signal appears in the schwarz_exterior mask.
4. The horizon center and interior masks remain poorly conditioned.
5. The Schwarzschild-like case is not yet a clean validation case like Gaussian or FRW.
6. The result suggests that near-horizon radial geometries need specialized exterior/interior treatment.

Interpretation:

The previous Schwarzschild-like failure was partly due to the clipped coordinate surrogate. The redesigned bounded lapse-wall model produces a partial exterior-side signal, but near-horizon geometries remain more difficult than Alcubierre, Gaussian, FRW, or low-amplitude weak-GW tests.
