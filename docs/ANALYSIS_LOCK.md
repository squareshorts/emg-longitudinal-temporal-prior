# Fixed analysis choices

## Biological sample and recordings

- Independent biological sample: N = 10 participants (CEMHSEY Part-I GRASP Subjects 1-10).
- Session: Session 1, cylindrical grasp.
- Task: Task 2, 30% MVC.
- Days: 1-11.
- Trials per day used here: 1 and 2.
- Later-day evaluation recordings: Days 2-11 Trial 2, giving 100 participant-day evaluations nested within N=10 participants.

## Sampling and feature timing

- HD-sEMG sampling rate: 2048 Hz.
- Force sampling rate: 200 Hz.
- sEMG features: MAV, RMS, waveform length.
- Feature window: 200 ms = 410 samples.
- Step: 100 ms = 205 samples.
- Typical trial: 299 feature windows.
- Primary timing: physical sensor time bases with common t=0; no optimized lag.
- Sensitivity analysis: normalized-duration mapping.

## Protocol-defined temporal prior

Nominal 30-s target:

- 0-5 s: 0 MVC
- 5-10 s: linear ramp 0 to 0.30 MVC
- 10-20 s: 0.30 MVC
- 20-25 s: linear ramp 0.30 to 0 MVC
- 25-30 s: 0 MVC

No amplitude, offset, lag, or timing parameter is fitted from participant data.

## Day-1 force templates

- Day-1 Trial-1 template: measured Day-1 Trial-1 force trajectory.
- Day-1 average template: pointwise average of measured Day-1 Trials 1 and 2 after mapping to the evaluation time base.

## EMG-only decoder

- Electrode ranking: absolute Pearson correlation between Day-1 Trial-1 MAV and force.
- Electrode counts: k = 8 and 16.
- Per-electrode features: MAV, RMS, waveform length.
- Feature standardization: Day-1 Trial-1 mean and population SD.
- Observation model: independent ridge regression per selected electrode.
- Ridge grid: 17 logarithmically spaced penalties from 1e-3 to 1e5; selected by Day-1 Trial-2 MSE.
- Day-1 Trial 1: ranking, standardization, regression fitting, process-noise estimation.
- Day-1 Trial 2: ridge/Kalman hyperparameter selection, baseline observation-noise estimation, reference prediction distribution, hybrid calibration.
- Later Days 2-11 Trial 1: EMG-derived predictions only for force-label-free session alignment.
- Later Days 2-11 Trial 2: held-out evaluation.
- Session alignment: robust 3-MAD consensus followed by median/IQR affine alignment to Day-1 Trial 2.
- Kalman process-noise scale grid q_s: {0.01, 0.03, 0.1, 0.3, 1, 3, 10}.
- Adaptive-variance alpha grid: {0, 0.1, 0.25, 0.5, 1, 2}.
- Baseline observation variance: Day-1 Trial-2 residual mean square for each electrode model.

## Hybrid and residual controls

- Hybrid form: T_1(t) + beta [E(t) - T_1(t)].
- beta fitted on Day-1 Trial 2, then frozen for later days.
- Residual-shape diagnostic: leave one evaluation day out; remove the mean true-residual and prediction-residual trajectories estimated from the other nine evaluation days of that participant.
- This residual-shape procedure uses force labels from other evaluation days and is descriptive, not deployable.

## Inference

- Participant is the inferential unit (N=10).
- 100,000 participant-level bootstrap resamples for reported percentile CIs.
- Two-sided Wilcoxon signed-rank tests used as exploratory participant-level paired tests.
- Holm adjustment for the nominal-target comparison family and the prespecified EMG-component comparison family reported in the manuscript.
