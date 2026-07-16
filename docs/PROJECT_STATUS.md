# Spinelli Framework / Alcubierre Validation — Project Status

**Status date:** 2026-07-16  
**Current published baseline before this update:** `1afef02806d804baf1f656e97adb96b2434fd4dc`  
**Authoritative Stage 4 notebook SHA-256:** `1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe`

## Publication state

Stage 4R N81 was published successfully in commit
`1afef02806d804baf1f656e97adb96b2434fd4dc`.

## Stage 4R N71

N71 completed successfully using the same physical parameters as N61 and N81.

- DIM=4, N=71
- Runtime: 151.29 seconds
- Peak RSS: 104.316132 GiB
- Swap: 0
- All notebook cells: PASS
- Historical notebook modified on disk: no

## Corrected three-grid interpretation

The principal residuals decrease monotonically from N61 to N71 to N81.

- Bianchi pairwise orders:
  1.845,
  1.882
- Classical rho error pairwise orders:
  1.901,
  1.939
- Hessian-Q pairwise orders:
  1.276,
  1.015
- HTR pairwise orders:
  1.740,
  1.614

The negative continuum values generated for Bianchi and rho by the original unconstrained
three-point fit are rejected as physically inadmissible for nonnegative quantities.
Original reports remain preserved for provenance.

## Resource model

The N^4 model predicted N71 peak RSS within 0.155% and runtime within
0.870%. It is the operative resource model for dense Stage 4 runs.

## Next numerical task

Proper-time-step sensitivity at fixed N71:

- DELTA_TAU = 0.02
- DELTA_TAU = 0.04
- DELTA_TAU = 0.08

The sensitivity matrix should run each case in a separate Python process and compare
Bianchi, rho error, Hessian-Q, HTR, lambda, beta, Action/Fit, and tensor difference.

## Preservation rule

Historical artifacts remain immutable. Raw N71 reports, including the original
three-point extrapolation, remain published beside this corrected interpretation.
