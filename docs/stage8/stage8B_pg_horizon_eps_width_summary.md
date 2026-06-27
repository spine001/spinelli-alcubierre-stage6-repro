# Stage 8B PG-Horizon Eps/Width Parameter Sweep Summary

Stage 8B tested the dedicated PG-horizon near-horizon model over core regularization and horizon-wall width.

Cases tested:

- geometry: pg_horizon
- N: 61
- mass: 1.25
- eps: 0.15, 0.25, 0.35, 0.50
- width: 0.50, 0.75, 1.00, 1.25
- masks: schwarz_exterior, schwarz_center
- total cases: 32

Main findings:

1. The exterior near-horizon branch is stable across the eps/width sweep.
2. The best candidate is eps=0.35, width=1.00, schwarz_exterior.
3. The best candidate has Action/Fit near 1.001, tensor difference near 0.740%, and small absolute Bianchi.
4. Width near 1.00 is the cleanest region for the exterior mask.
5. The center mask is less attractive because its Bianchi absolute values are larger.
6. The near-horizon PG model is now ready for a resolution ladder.

Interpretation:

Stage 8B confirms that the Stage 8A exterior near-horizon signal is not a one-off parameter artifact. The PG-horizon exterior branch appears stable, especially near eps=0.25–0.35 and width=1.00. The next step is a resolution ladder on the best exterior candidate.
