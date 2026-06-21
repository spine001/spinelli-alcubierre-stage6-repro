# Stage 7 Cross-Geometry Validation Summary

Stage 7 tested the Spinelli correction framework outside the Alcubierre geometry using five pilot geometries:

1. static_shell
2. gaussian_pulse
3. weak_gw_packet
4. schwarzschild_like
5. frw

Resolution ladder completed:

- N31, N41, N51: all five geometries
- N61: all five geometries
- N71: gaussian_pulse and frw

Preliminary interpretation:

- gaussian_pulse gives the cleanest convergence signal.
- frw gives a very stable Action/Fit residual near 1, but beta has a cosmology-specific behavior.
- weak_gw_packet has very small tensor differences but beta drifts with resolution.
- static_shell appears fit-degenerate under the current mask.
- schwarzschild_like is not reliable in the current coordinate/mask design.

The complete uploaded bundle is stored in packages/stage7.
