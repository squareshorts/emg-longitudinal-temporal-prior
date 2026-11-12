# Full-GRASP overhaul: findings

Run completed 2026-11-12 on all 6,005 usable CEMHSEY GRASP recordings (13 participants × 11 days × 7 grasps × 3 force levels × 2 trials; 251 GB read once from Zenodo, CRC-verified, SHA-256 recorded in `results/inventory/recording_manifest.csv`). Pipeline `overhaul-1.0`; code and plan hashes are in `results/provenance.json`.

## Quality gate
- **Reproduction.** The protocol-prior R² for Session 1 / Task 2 (participants 1–10) matches the earlier analysis to six decimals (`results/gate/reference_reproduction.csv`).
- **Protocol timing.** Twenty of 21 grasp × force cells follow the nominal 5–10–20–25 s trapezoid. Lumbrical grasp at 10 % MVC departs from it (median half-target crossings 0.9 s early and 0.8 s late; 172/286 recordings flagged) and is excluded by the pre-specified rule (`results/gate/protocol_timing_qc_by_condition.csv`).

## Pre-specified analysis (`ANALYSIS_PLAN.md`; `results/primary_bandpass_physical/`)
Skill is `1 − SSE(model)/SSE(protocol prior)`; 0 equals the prescribed trajectory, positive is better.

- Across days (train Day 1, test Days 2–11), no EMG decoder or empirical template beats the prescribed trajectory. The best decoder (8-channel ridge on the residual from the prior, Trial-1 label-free alignment) reaches median skill −0.08 (95 % CI −0.33 to −0.04; 3/13 participants positive; RMSE 1.49 vs 1.32 % MVC). The best template (leave-one-participant-out pooled Day-1 force) reaches −0.22.
- The pre-specified primary contrast (all-channel residual ridge, no alignment) gives −17.9 (CI −65.1 to −1.8; 0/13 positive; Wilcoxon p = 0.0002). Inspection showed this value is dominated by extreme outputs when a few of 320 channels change after electrode re-application; see the post hoc analysis below.
- At 30 % and 50 % MVC the best decoder approaches the prior (−0.02, −0.002); at 10 % MVC it is clearly worse (−0.40).
- Familiarization: protocol-tracking RMSE (as % of the target level) falls across days in all 13 participants (median slope −0.18 percentage points/day, CI −0.20 to −0.07, p = 0.0002), which explains why Day-1 force templates lose to the nominal trajectory.
- Conclusions are unchanged with unfiltered EMG (`results/sensitivity_unfiltered_physical/`) and with normalized force–EMG time alignment (`results/sensitivity_bandpass_normalized/`).

## Post hoc robustness analysis (`ANALYSIS_PLAN_ADDENDUM.md`; `results/posthoc_robustness/`)
Decided after the primary results and reported as post hoc. Decoders are protected against channels that change between sessions (label-free bad-channel rejection, median 7 of 320 per recording; standardized features clipped at ±5 SD), and each held-out recording (Day d Trial 2) is predicted by the same model trained either on Day 1 Trial 1 (across days) or on Day d Trial 1 (within day), with hyperparameters fixed on Day 1.

- **Within a session, EMG adds information beyond the prescribed trajectory in every participant.** All-channel residual ridge: skill +0.13 (CI 0.085–0.16), 13/13 positive, RMSE 1.21 vs 1.32 % MVC; 8-channel: +0.12 (CI 0.09–0.17), 13/13. The gain holds at 10, 30 and 50 % MVC and on every day.
- **Across sessions that information is lost.** The same protected models trained on Day 1 score −0.20 (all-channel) and −0.12 (8-channel), 2–3/13 positive; Trial-1 alignment does not recover it. Within-day exceeds across-days for every model in 13/13 participants (Wilcoxon p ≈ 0.0002; `within_vs_across_contrasts.csv`).
- Protection removes the extreme outputs (maximum across-day RMSE 15.6 % MVC, down from thousands).
- Decoders that predict total force from EMG alone remain far worse than the prior even within a day (RMSE 2.9 vs 1.3 % MVC): EMG is informative only as a correction to the prescribed trajectory.
- Caveats: within-day models need one force-labelled calibration trial per day; one within-day recording is an extreme outlier (RMSE 75 % MVC), absorbed by participant-median summaries.

## Files
| Path | Content |
|---|---|
| `results/RUN_REPORT.md` | Run summary written by the pipeline |
| `results/inventory/` | Manifest of all 6,005 recordings with source CRC-32, SHA-256, byte counts |
| `results/gate/` | Timing QC per recording and per condition; reproduction check |
| `results/primary_bandpass_physical/` | Pre-specified analysis: held-out metrics, participant and cohort summaries, exploratory per-condition summaries, familiarization, hyperparameters |
| `results/sensitivity_*` | Same outputs for unfiltered EMG and normalized time base |
| `results/posthoc_robustness/` | Protected decoders, within-day vs across-days contrasts, by force level and day |

Phase-resolved metrics (`heldout_phase_metrics.csv`, ~54 MB per analysis) are excluded from the repository for size and are kept with the full outputs on the analysis computer and in Google Drive.
