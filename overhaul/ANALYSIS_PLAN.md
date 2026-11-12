# Analysis plan (fixed before the full-corpus run)

Written 2026-11-11, before any data beyond Session 1 / Task 2 had been analysed. The SHA-256 of this file is recorded in `results/provenance.json` and in every analysis checkpoint.

## Data
CEMHSEY GRASP, 13 participants × 11 days × 7 grasps × 3 force levels (10/30/50 % MVC) × 2 trials; 6,005 usable recordings (S4 Day 1 Session 1 Task 1 Trial 1 is listed as failed by the dataset authors and is excluded). Force is MVC-normalized in the source files.

## Split
Day 1 Trial 1 trains every participant-specific model. Day 1 Trial 2 selects hyperparameters. On Days 2–11, Trial 1 is used only for label-free affine alignment of model outputs; Trial 2 is held out for scoring.

## Signals
Primary: EMG band-passed 20–450 Hz (4th-order Butterworth, zero-phase) with 50 Hz comb notches (50–400 Hz, Q = 30). Features per 200 ms window, 100 ms step: MAV, RMS, WL, ZC, SSC (ZC/SSC with a per-channel deadband equal to the 10th percentile of window RMS). Force is read at window centres on the physical time base (force at 200 Hz from the record start).

## Primary outcome and contrast
Skill relative to the nominal protocol trapezoid, `skill = 1 − SSE(model) / SSE(protocol prior)`, per held-out recording; participant median across days and conditions. Primary contrast: `ridge_all_residual`, fixed (no alignment), participant-median skill > 0, two-sided Wilcoxon signed-rank across 13 participants, with a participant-bootstrap 95 % CI for the median.

## Secondary (descriptive, with participant-bootstrap CIs)
All other decoders (ridge, PLS, PCA+OLS; raw-force and residual-on-prior targets; 8/16-channel residual ridge), each fixed and Trial-1-aligned; empirical templates (Day-1 Trial 1, Day-1 Trial 2, Day-1 average, previous-day Trial 2, leave-one-participant-out pooled Day-1 template); phase-resolved metrics; per grasp × force summaries (exploratory, no multiplicity correction); familiarization slope of protocol-tracking RMSE (% of target level) across days.

## Quality gate and exclusions (decided in advance)
1. Reproduction: the protocol-prior R² (median Days 2–11 Trial 2) for Session 1 / Task 2, participants 1–10, must match the earlier analysis within 0.002. Failure stops the run.
2. Protocol timing: for each grasp × force cell, the median 50 %-of-target up- and down-crossing must lie within 0.5 s of 7.5 s and 22.5 s, and the median hold force within 0.8–1.2 × target. Cells that fail are excluded from all analyses and reported.

## Sensitivity analyses
(a) Unfiltered EMG (physical time base). (b) Band-passed EMG with force mapped by normalized record duration.
