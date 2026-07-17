# Spinelli Framework / Alcubierre Validation — Project Status

**Status date:** 2026-07-17  
**Current repository baseline before this update:** `5ec5b066adaa77b4da117ab8122e74b51a7f7f9b`  
**Authoritative notebook SHA-256:** `1e605096b1334c1998331c4fefdc1017b2d783120f8079e4d836f40af4680afe`

## Completed evidence

- N61 exact regression: PASS
- N71 intermediate grid: PASS
- N81 dense grid: PASS
- N61/N71/N81 spatial analysis: published
- N71 proper-time matrix: PASS
- N81 proper-time confirmation: PASS
- Streaming-memory N61 regression: PASS
- Streaming-memory N81 regression: PASS

## Memory result

The streaming implementation reduces peak RSS by approximately 47.7% while preserving
all six canonical tables.

- Optimized N61 peak: 29.643742 GiB
- Optimized N81 peak: 92.700161 GiB
- Projected N91 peak: 147.674661 GiB
- Projected N101 peak: 224.091771 GiB

## Current task

Run the authorized optimized N91 calculation at DELTA_TAU=0.04.

The N91 postprocessor will:

1. Create the N61/N71/N81/N91 metric sequence.
2. Compute adjacent-grid effective orders.
3. Verify that the four principal residuals continue decreasing.
4. Compare measured N91 memory and runtime with their projections.
5. Recalculate N101 memory from the measured N91 peak.
6. Emit the Phase 5 recommendation.

## N101 gate

N101 is built only when:

- N91 completes without swap;
- the principal spatial trends remain valid; and
- the measured N91 peak projects N101 at no more than 205 GiB.

Otherwise the next step is another focused memory optimization.
