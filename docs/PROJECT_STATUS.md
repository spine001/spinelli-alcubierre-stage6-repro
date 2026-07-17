# Spinelli Framework / Alcubierre Validation — Project Status

**Status date:** 2026-07-17  
**Current repository baseline before this update:** `b8f364464b94ffb3eaf89decff45331f662fbd0b`  
**Authoritative Stage 4 notebook SHA-256:** `1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe`

## Completed

- Stage 4R N61 exact regression: PASS
- Stage 4R N71: PASS
- Stage 4R N81: PASS
- Corrected N61/N71/N81 spatial analysis: published
- N71 DELTA_TAU=0.02/0.04/0.08 matrix: PASS
- N81 DELTA_TAU=0.02 confirmation: PASS

## Proper-time conclusion

At N81, the largest principal-metric change from DELTA_TAU=0.04 to 0.02 was
0.0161359%. The largest proper-time effect was only
0.0670812% of its corresponding N71-to-N81 spatial effect.

The next task is therefore memory optimization for N91, not another DELTA_TAU case.

## Current validation gate

Run a streaming late-cell implementation at N61 and N81 in separate Python processes.

The gate requires:

1. All executable cells PASS.
2. Six canonical tables reproduce within `rtol=1e-8`, `atol=1e-10`.
3. No swap.
4. Measured N81 peak projects N91 below 190 GiB.
5. Historical notebook remains unchanged.

Only a passing gate authorizes construction of the N91 production runner.

## N101

N101 remains a later target. Its feasibility will be recalculated from the optimized N81
peak and then checked again after the measured N91 run.
