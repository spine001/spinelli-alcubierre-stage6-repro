# Stage 4D action-derived Q comparison

This package compares:

1. Best fitted HTR tensor:
   Q_fit = H - lambda_fit g S + beta_fit S G

2. Action-predicted tensor:
   Q_action = H - lambda_fit g S - S G

3. Difference:
   Q_action - Q_fit

Parameters:
DIM = 4
N = 61
lambda_fit = 0.015789560482987477
beta_fit = -1.0306645653775017
beta_action = -1.0

Key results:
Relative tensor difference action vs fit = 0.027417 %
Fitted normalized residual = 0.01661441080787219
Action normalized residual = 0.01661478737676192
Action residual / fitted residual = 1.000022665196743
Residual penalty percent = 0.002267 %

Interpretation:
If the action-predicted beta=-1 tensor has nearly the same residual and tensor shape as
the fitted HTR tensor, then the numerical Stage 4C result is supported by a minimal
effective action rather than being only a numerical fit.
