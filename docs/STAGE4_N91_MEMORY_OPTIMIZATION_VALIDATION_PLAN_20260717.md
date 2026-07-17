# Stage 4 N91 Memory-Optimization Validation Plan

**Date:** 2026-07-17  
**Notebook SHA-256:** `1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe`

## Scope

This phase does not run N91. It validates a lower-memory implementation against the
existing N61 and N81 canonical evidence.

## Immutable source

The historical notebook is read and SHA-verified. It is never modified on disk.

The in-memory runner verifies the original source hashes:

- Configuration cell 3: `5a49221d2ba22d35ee05b94fa968dfc9e1628ccc5d228e08712264db8f5291a5`
- Export cell 23: `18dfd79cd2b9fe41b798714d1e2f80f6a53ffab7f0eb39a4abe3d98954326957`
- Action-comparison cell 24: `6528d7dedf482b7590ebf983c79e21ed9670673a570b319533a4f02367fbf1af`

## Optimization

Cell 23:

- Stream four direct candidates one at a time.
- Store only scalar scores.
- Recompute the winning candidate once for plots.
- Release all full candidate tensors before Stage 4D.

Cell 24:

- Score fitted, action-predicted, and difference tensors sequentially.
- Retain only scalar scores and 2-D central slices.
- Compute the relative tensor difference from the scored difference norm.

## Regression cases

- Optimized N61 versus verified N61 baseline.
- Optimized N81 versus verified N81 baseline.

Each case runs in a fresh Python process.

## Gate

`PHASE4_RECOMMENDATION=BUILD_N91_OPTIMIZED_RUNNER` requires:

- Both regressions PASS.
- No table differences outside `rtol=1e-8`, `atol=1e-10`.
- Both processes exit zero and use no swap.
- N81-based N91 projected peak RSS <= 190 GiB.

Otherwise:

`PHASE4_RECOMMENDATION=FURTHER_OPTIMIZE_BEFORE_N91`
