# Stage 7H Weak-GW Amplitude and Mask Summary

Stage 7H tested the Spinelli correction framework on the weak gravitational wave packet geometry.

Cases tested:

- geometry: weak_gw_packet
- N: 61
- amplitudes: 0.005, 0.010, 0.025, 0.050
- score masks: all, localized

Main findings:

1. The all-mask and localized-mask results are almost identical.
2. Therefore, the weak-GW behavior is not primarily a masking artifact.
3. At low amplitudes, the relative tensor difference is very small.
4. As amplitude increases, Bianchi residual and Action/Fit deviation both increase.
5. beta_fit remains negative but moves toward zero as amplitude increases.
6. The weak-GW result supports cross-geometry relevance of the action-derived tensor, but does not support beta=-1 universality.

Interpretation:

Weak-GW behavior is amplitude-sensitive rather than mask-sensitive. The action-derived correction tensor remains close to the fitted correction in tensor difference, especially at low amplitude, but beta is geometry- and amplitude-dependent.
