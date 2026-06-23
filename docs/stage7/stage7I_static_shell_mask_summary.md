# Stage 7I Static-Shell Mask Redesign Summary

Stage 7I tested whether the static-shell fit degeneracy was caused by the original broad localized mask.

Cases tested:

- geometry: static_shell
- N: 61
- amplitude: 0.025
- width: 0.75
- radius: 2.5
- score masks: localized, shell_center, shell_core, shell_edge, all

Main findings:

1. The static-shell geometry remains fit-degenerate.
2. The shell_edge mask gives the best improvement in relative tensor difference.
3. Bianchi residuals remain small across all masks, indicating numerical stability.
4. beta_fit remains large and positive across all masks.
5. Static-shell behavior is not Alcubierre-like, Gaussian-like, or FRW-like under the current model.

Interpretation:

The static-shell result suggests that highly symmetric static geometries can make the fitted beta/lambda decomposition poorly conditioned. The shell-edge result indicates partial gradient-localized structure, but not enough to classify the static shell as a clean validation case.
