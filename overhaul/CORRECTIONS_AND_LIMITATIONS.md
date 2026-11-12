# Reporting corrections and scientific limitations — 12 November 2026

This addendum corrects the description of the already completed CEMHSEY full-GRASP analysis. **It does not replace, retune, or retrospectively modify any original model, numerical result, analysis plan, code hash, or raw-data-derived output.** The original run and its documented later robustness analysis are preserved unchanged. The additional timing-flag sensitivity is explicitly post hoc.

## 1. Recordings processed versus recordings eligible for inference

All 6,005 available source MAT records were inventoried and feature-extracted (13 participants; 11 days; 7 grasps; 3 force levels; two trials). The complete 21-cell protocol timing gate did **not** pass. Its JSON retains `timing_ok=false` and `passed=false`. Only 20 of 21 grasp–force combinations satisfied the documented timing rule. Lumbrical grasp at 10% MVC (Session 2, Task 1) was excluded from the *performance analysis*, not removed from the source inventory. The historical reproduction check independently passed (largest absolute R² difference 4.67×10⁻⁷). The implementation proceeds with eligible cells; do not reinterpret the full timing gate as having passed. The primary evaluation pool is 260 participant–grasp–force combinations and 2,600 held-out later-day Trial-2 recordings. A missing Day-1 Trial-1 training recording in one Subject-4 condition means a subset of EMG model outcomes has 2,590 evaluation records. These repeated recordings are not 2,600 independent biological samples; inferential N is 13 participants.

Out of 6,005 source recordings, 653 are individually flagged for timing/holding deviations. Of those, 481 occur within eligible conditions. Among the 2,600 eligible held-out Trial-2 evaluations, 206 are individually flagged. The original condition-level exclusion remains unchanged; individual flag filtering is a later exploratory sensitivity analysis.

## 2. Main preregistration and temporal provenance

The file `ANALYSIS_PLAN.md` identifies choices described as fixed before the full-corpus run. Its SHA-256 is recorded and verified against `results/provenance.json`; the `ANALYSIS_PLAN_ADDENDUM.md` and post hoc script similarly match their recorded fingerprints. Because the documents were first made public together with the results, the available Git history cannot establish independent prospective registration. Do **not** describe this work as preregistered or externally timestamp-confirmed. Use “original analysis plan recorded with the run” and “subsequent post hoc analysis,” preserving the original plan file and hashes for audit.

## 3. Primary model instability

The original primary comparison was a fixed, all-channel residual Ridge model calibrated on Day 1. Its median participant-level skill was −17.8685 (95% percentile bootstrap CI −65.0995 to −1.8077; two-sided Wilcoxon p=0.000244). Very large across-day prediction excursions cause extreme squared errors (one recorded model-recording RMSE exceeds 12,000% MVC). This establishes a failure of that *particular unconstrained implementation* under channel nonstationarity, not an interpretable estimate of neural-information loss or an effect size that can be generalized to other decoders. The model and result must remain visible; the protected models were developed **after** inspecting this instability.

## 4. Strongest original cross-day decoder and small-sample inference

For the original analysis, the best 8-electrode residual Ridge with unlabeled Trial-1 alignment has median participant skill −0.07816, percentile bootstrap CI [−0.33354, −0.04384], 3/13 participants positive, and two-sided Wilcoxon p=0.08032. The percentile CI excludes zero, while the Wilcoxon p exceeds 0.05. These procedures have different finite-sample behavior; report both without claiming that the Wilcoxon test establishes a difference at the 5% threshold. The negative median is descriptive evidence that the tested decoder did not consistently exceed the protocol-only baseline; it is not evidence that no possible EMG decoder can do so.

## 5. Post hoc residual-decoder analysis; labeled within-day calibration

The protected Ridge, PLS and PCA comparisons were designed after the original results were examined. Protection uses recording-level unlabeled channel screening and feature clipping, described exactly in `ANALYSIS_PLAN_ADDENDUM.md` and `posthoc_robustness.py`. The **within-day** model is supervised: it fits to force labels from the same day's Trial 1, and predicts that day's Trial 2. It is **not** unsupervised transfer and should not be described as an evaluation of fixed Day-1 calibration. Across-day variants fit using Day-1 labels; one aligns with unlabeled later-day Trial 1. Hyperparameter grids are fixed from Day-1 calibration.

Protected within-day *residual Ridge* improves over the protocol prior in 13/13 participant summaries: 8-channel median skill +0.11841, all-channel +0.13033. The analogous across-day fixed models remain negative (−0.12010 and −0.20062 respectively). For the all-channel model, within-minus-across participant median difference is +0.31645 (CI [0.20138, 0.79061]); all 13 participants show a positive contrast (p=0.000244). This statement is model-specific: within-day PCA/OLS residual has median skill +0.02402 (7/13 positive) and within-day PLS residual has −0.02194 (5/13 positive), with nonsignificant signed-rank tests. Raw-force Ridge remains worse than the protocol prior even within day.

## 6. Timing-QC sensitivity and day-associated tracking improvements

The subsequent exploratory sensitivity drops **206** individually flagged held-out Trial-2 observations from the 2,600 eligible evaluations; it must not replace the original condition-level analysis. The best original aligned 8-channel residual Ridge changes from −0.07816 to −0.10763 median skill. Protected within-day all-channel residual Ridge changes from +0.13033 to +0.12418; protected within-day 8-channel Ridge changes from +0.11841 to +0.11618. Its 13/13 positive participant count remains unchanged. See `results/posthoc_timing_qc_sensitivity.csv`.

The original tracking-error day slope was negative for 13/13 participants (median −0.17734 percentage points/day). With individually flagged recordings removed from the tracking analysis, 11/13 slopes remain negative (median −0.11124 percentage points/day, Wilcoxon p=0.002441). These are **day-associated changes** consistent with familiarization, but do not independently establish learning as the causal mechanism. Feedback, fatigue, motivation or recording factors may also matter.

## 7. Data products and execution claims

The GitHub branch contains the code, analysis plans, full 6,005-key source manifest, model-level recording results, main/sensitivity cohort outputs, QC metadata and post hoc robustness outputs. Three ~54 MB phase-metric CSVs were omitted from GitHub and remain in the user's Google Drive analysis folders. Those Drive files are not a public DOI-backed archival deposit. See `DATA_PRODUCTS.md` for exact locations and the outstanding publication step.

Five synthetic/unit tests passed in the previous independent review; four tests requiring actual MAT source files were skipped. Original MAT files and the 23-GB feature cache were **not independently reprocessed** during the review. The script `verify_archived_results.py` checks internal consistency of the *archived* CSVs, code hashes and recorded statistical summaries; it is not raw-data reproduction.

## 8. Manuscript and release boundary

The prior version v1.0.3 describes an earlier restricted 10-participant analysis. This branch reports a new 13-participant, multi-condition study. Do not overwrite the old Zenodo DOI, merge the branch as a finalized publication, or generate a journal manuscript before resolving outstanding public phase-output archiving and reviewing the model-specific claims. The original scientific numerical outputs remain immutable.
