# Spinelli Stage 5 parameter sweep and magnitude test

This package contains the outputs of Spinelli_Stage5_parameter_sweep_and_magnitude_test.ipynb.

Configuration:
DIM = 4
N_SWEEP = 31
DTYPE = <class 'numpy.float64'>
V_VALUES = [0.25, 0.5, 0.75, 1.0]
SIGMA_VALUES = [0.5, 1.0, 2.0, 4.0]
R_VALUES = [2.0, 3.0, 4.0]
BETA_ACTION = -1.0

Core output files:
- stage5A_parameter_sweep_results.csv
- stage5_article_table.csv
- stage5_summary.csv
- stage5_summary.json

Core plots:
- stage5A_beta_fit_vs_sigma.png
- stage5A_action_over_fit_vs_sigma.png
- stage5A_relative_tensor_difference_vs_sigma.png
- stage5A_action_magnitude_fraction_vs_sigma.png
- stage5A_eta_needed_vs_sigma.png
- stage5A_Q00_absrho_correlation_vs_sigma.png

Interpretation targets:
- beta_fit close to -1 supports universality of the action-derived coupling.
- action_residual_over_fit_residual close to 1 means the beta=-1 action tensor performs nearly as well as the fitted HTR tensor.
- action_positive_fraction_of_abs_rho and eta_needed estimate whether the correction has physically meaningful magnitude.
