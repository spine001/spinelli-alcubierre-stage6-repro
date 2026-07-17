# Spinelli Framework / Alcubierre Validation — Project Status

**Status date:** 2026-07-17  
**Current repository baseline before this update:** `5bd579b6e2324fb535ca322be3bf74f90a194768`  
**Authoritative Stage 4 notebook SHA-256:** `1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe`

## Completed Stage 4R evidence

- N61 exact terminal regression: PASS
- N71 intermediate resolution: PASS
- N81 dense resolution: PASS
- N61/N71/N81 corrected three-grid analysis: published
- N71 DELTA_TAU=0.02/0.04/0.08 matrix: PASS

## Proper-time sensitivity conclusion

At N71, the maximum fine-step effect on the principal diagnostics was only
0.0185483%. Fitted coefficients changed by at most 0.0104432%,
the tensor comparison changed by 0.01533%, and Action/Fit moved by only
0.0686332 ppm.

The changing quantities show approximately second-order DELTA_TAU behavior. Bianchi and
the classical rho benchmark are invariant under this parameter in the current notebook
implementation.

## Current next run

Execute one controlled N81/DELTA_TAU=0.02 confirmation.

The post-run report compares:

1. N71: DELTA_TAU=0.02 versus 0.04
2. N81: DELTA_TAU=0.02 versus 0.04
3. Spatial N71→N81 changes at both DELTA_TAU values
4. Proper-time sensitivity relative to the spatial-resolution effect

## Decision after N81 confirmation

- Small sensitivity: begin measured-memory optimization for N91.
- Unexpected sensitivity: run N81/DELTA_TAU=0.08 before optimization.

N91 and N101 are roadmap targets, but are not started by this package.
