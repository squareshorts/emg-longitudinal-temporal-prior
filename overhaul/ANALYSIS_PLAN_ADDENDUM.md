# Addendum: post hoc robustness analysis (decided after the primary results)

Written 2026-11-12 15:35 (UTC-3), after the pre-specified run completed (`results/`, plan hash 0d4cb9c0…). Everything below is post hoc and is reported as such; the pre-specified primary contrast and its result are unchanged.

## What prompted it
The pre-specified primary contrast (`ridge_all_residual`, fixed) produced a participant-median skill of −17.9. Inspection of cached features showed that the all-channel models, trained on Day 1, generalize within Day 1 (R² 0.96–0.998) but occasionally produce extreme outputs on later days (RMSE up to thousands of % MVC), consistent with a few of 320 channels changing after electrode re-application. The 8-channel model did not show this.

## Analysis A — protected all-channel decoders across days
Per held-out recording, channels whose median MAV lies outside 1/10–10× the recording's median channel, or that are flat, are zeroed after standardization; standardized features are clipped at ±5 SD of the Day-1 Trial-1 training distribution. Both steps are label-free and use no information from the test labels. Models: ridge (all channels, residual and raw targets), ridge (8 channels, residual), PLS (all channels, residual), PCA+OLS (residual). Schemes: fixed, and Trial-1 label-free affine alignment, as in the primary analysis.

## Analysis B — within-day versus across-days
For each held-out recording (Day d Trial 2, d = 2…11) the same model specification is trained on Day 1 Trial 1 (across days) and on Day d Trial 1 (within day). Hyperparameters are selected once, on Day 1 (Trial 1 → Trial 2), and reused for both, so no held-out trial informs any choice. Contrast: participant-median skill (within day − across days), Wilcoxon signed-rank and participant-bootstrap 95 % CI.

Data, exclusions (Session 2 / Task 1), EMG variant (band-passed) and time base (physical) are those of the primary analysis.
