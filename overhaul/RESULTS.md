# Full-GRASP overhaul: verified findings and reporting scope

Completed-run snapshot dated 2026-11-12. The dataset was inventoried and reduced to windowed features for 6,005 CEMHSEY GRASP recordings spanning 13 participants, seven grasp sessions, three force levels and 11 days. The manifest records MAT source checksums. All findings below come from the archived CSV and JSON outputs, whose numeric data have not been changed in this corrective update.

**Scientific scope:** The model-performance analysis uses **20 of 21 grasp–force combinations**, excluding lumbrical grasp at 10% MVC after a predefined condition-level protocol-timing rule was applied. The original timing gate was **not fully passed** (`results/gate/gate_summary.json` has `passed: false`). The independent historic reference reproduction gate did pass (largest |ΔR²| = 4.67×10⁻⁷). Inference uses participants (N=13), not repeated trials as independent observations. One Subject-4 condition lacks Day-1 training data, leaving 2,590 model evaluations from 2,600 eligible later-day Trial-2 recordings.

## Original documented analysis plan

The original analysis plan, `ANALYSIS_PLAN.md`, states that it was written before the full run; its SHA-256 agrees with `results/provenance.json`. The plan and results were first committed publicly together. We therefore **cannot independently verify the plan's prospective timestamp or call it externally preregistered**. The original fixed all-channel residual Ridge model had median participant skill **−17.8685**, 95% participant-bootstrap CI [−65.0995, −1.8077], 0/13 positive, and two-sided Wilcoxon **p=0.000244**. Its exceptionally negative effect is driven by severe extrapolation under channel changes; it should not be interpreted as a biological information-loss magnitude.

Skill is `1 − SSE(model)/SSE(protocol prior)`, calculated per held-out recording and summarized by participant. Zero equals the prescribed trajectory; positive values improve upon it.

Among the original cross-day candidates, the best is **8-channel residual Ridge with unlabeled Trial-1 alignment**, median participant skill **−0.07816** (95% percentile-bootstrap CI [−0.33354, −0.04384], 3/13 participants positive; two-sided Wilcoxon **p=0.08032**). **Its bootstrap CI excludes zero while its Wilcoxon p does not meet p<0.05**. These are distinct small-sample inferential methods. Neither result warrants a universal claim that no EMG decoder could ever exceed the protocol prior. The best leave-one-subject-out pooled Day-1 template has skill −0.21911.

Across-day analyses support a performance gap relative to the nominal trajectory for the tested models and dataset conditions. The pattern persists in the unfiltered-EMG and normalized-time variants. Do not treat the current benchmark as demonstrating the performance of state-of-the-art decoders not evaluated here.

The nominal target's tracking error decreases across recorded days (original median slope −0.17734 percentage points of target force per day, 13/13 negative, Wilcoxon p=0.000244). This is a **day-associated tracking improvement** compatible with familiarization; causation cannot be isolated from feedback, fatigue or other factors. Exclusion of individually timing-flagged recordings leaves 11/13 negative slopes (median −0.11124, p=0.002441; post hoc sensitivity).

## Subsequent post hoc protected-decoder analysis

`ANALYSIS_PLAN_ADDENDUM.md` and `posthoc_robustness.py` document model protection after the original cross-day instability was observed. This is a **post hoc/exploratory** analysis, not independent confirmatory replication. In particular, "within-day" refers to **force-labelled Trial-1 calibration on the same day** followed by held-out Trial-2 evaluation; "across-day" uses Day-1 force labels. The affine-alignment variant uses unlabeled later-day Trial 1.

| Residual decoder | Within-day skill | Across-day fixed skill | Within-day participants positive |
| --- | ---: | ---: | ---: |
| Protected all-channel Ridge | +0.13033 | −0.20062 | 13/13 |
| Protected 8-channel Ridge | +0.11841 | −0.12010 | 13/13 |
| Protected PCA/OLS | +0.02402 | −0.85552 | 7/13 |
| Protected PLS | −0.02194 | −1.02988 | 5/13 |

Thus the positive incremental EMG finding is **specific to the tested protected Ridge residual decoders**; it does not generalize to every estimator. For all-channel residual Ridge, the median participant-wise within-minus-across fixed skill is +0.31645 (95% CI [0.20138, 0.79061], 13/13 positive, Wilcoxon p=0.000244). This paired contrast supports the role of current-day supervised calibration under the tested setup; it is not evidence that information itself disappears biologically.

EMG-only raw-force Ridge remains worse than the protocol prior even within day (median RMSE 2.86554% MVC versus prior 1.32049% MVC), so the improvement is a *residual correction* to a strong task-only predictor.

## Added timing-flag sensitivity (post hoc)

Among the 2,600 eligible later-day Trial-2 recordings, 206 were individually flagged for timing or force-hold deviations. Excluding these flags from the 2,590 model-evaluable recordings changes the cross-day aligned 8-channel model's median skill from −0.07816 to −0.10763; the protected within-day all-channel Ridge remains positive (+0.13033 to +0.12418) and protected within-day 8-channel Ridge remains positive (+0.11841 to +0.11618). Their latter positive-participant count remains 13/13. **The condition-level selection from the original plan is unchanged.** See `results/posthoc_timing_qc_sensitivity.csv` and `CORRECTIONS_AND_LIMITATIONS.md`.

## Reproducibility and public availability

The complete original-run summaries, numerical comparisons, source manifest and code are on this GitHub branch. The three ~54-MB phase-resolved CSV files exist in the associated Google Drive analysis folders, but **have not yet been deposited in a stable public DOI-backed archive**. Their availability must be resolved before submission. See `DATA_PRODUCTS.md` for paths and publication status.

This branch's numerical files and the original analysis-code fingerprints remain unchanged. A separate consistency checker, `verify_archived_results.py`, independently recomputes skill formulas, participant/cohort aggregations, exclusion checks, and the counts supported by the CSVs. It does not independently rerun source MAT processing; the corresponding four real-data unit tests were unavailable during the prior external audit.

## Navigation

- `ANALYSIS_PLAN.md` and `ANALYSIS_PLAN_ADDENDUM.md` — historical choices and stated temporal sequence, not independently timestamped preregistration
- `results/RUN_REPORT.md` — verbatim original pipeline report (unchanged, including original `timing_ok=false`)
- `results/inventory/` and `results/gate/` — complete source inventory and protocol QC
- `results/primary_bandpass_physical/` and `results/sensitivity_*/` — original primary and timing/filter sensitivities
- `results/posthoc_robustness/` — protected supervised within-day versus fixed/aligned across-day estimates
- `results/posthoc_timing_qc_sensitivity.csv` — added flagged-recording sensitivity
- `CORRECTIONS_AND_LIMITATIONS.md` and `DATA_PRODUCTS.md` — current interpretive qualification and missing phase archive
