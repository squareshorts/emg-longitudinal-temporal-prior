# Full-data independent reproducibility verification – v1.0.3

Date: 2026-10-09

Source: CEMHSEY Part-I GRASP, 10 participants, 11 days, two trials/day, Task 2, Session 1 (220 source MAT recordings). Biological inferential unit: N=10; later-day held-out participant-day evaluations: 100.

## Byte-preserved uploaded audit archives

| Path | Original archive SHA-256 | Purpose |
| --- | --- | --- |
| `validation/physical_time/CONFORMANCE_REPORT.zip` | `fd17f3c0d94d3e5d445cad305d5883cd8d804710e5609ea7fa82911d5a974818` | Physical-time benchmark, six-model conformance, Day-1 fitted parameters and residual diagnostic |
| `validation/figure4_normalized/FIGURE4_AUDIT.zip` | `0dc9bb673960b3a4c421021ebe705d37e2f041f77f13064bdd1d917b44380190` | Normalized-duration paired component contrasts and auxiliary audit |

The original archive bytes were checked for ZIP corruption and preserved as blobs in the GitHub source tree. Neither ZIP includes source CEMHSEY MAT recordings.

## Physical-time cohort audit

| Model | k | Frozen median R² | Independent median R² | Delta |
| --- | ---: | ---: | ---: | ---: |
| Fixed Kalman | 8 | 0.933500 | 0.933573 | +0.000073 |
| Fixed Kalman | 16 | 0.935600 | 0.935563 | -0.000037 |
| Adaptive Kalman | 8 | 0.938800 | 0.938856 | +0.000056 |
| Adaptive Kalman | 16 | 0.937000 | 0.937028 | +0.000028 |
| Adaptive hybrid | 8 | 0.979600 | 0.979615 | +0.000015 |
| Adaptive hybrid | 16 | 0.978500 | 0.978523 | +0.000023 |

All 6/6 within preselected absolute median R² tolerance 0.0005. Maximum |delta R²| approximately 0.0000731. Cohort median RMSE differs by at most approximately 0.0000516.

Physical-time protocol-prior cohort median R²: 0.9932526 (historical rounded 0.9933). Day-1 average template: 0.9832265 (rounded 0.9832). LODO residual diagnostic matches historical positive-correlation counts 87,88,89,89 and positive residual-R² counts 0,0,1,1 for fixed/adaptive 8/16.

Participant-level rounding check: 74/80 historical values agree within ±0.0005; six differences exceed this strict bound, three only marginally. Subject 7, k=16 has frozen/recomputed R² values 0.811/0.812453 (fixed), 0.883/0.886969 (adaptive) and 0.954/0.955618 (hybrid). Do not claim exact per-participant equality.

## Normalized-duration Figure 4 audit

| Contrast | k | Historical paired median delta R² | Independent | Holm adjusted p |
| --- | ---: | ---: | ---: | ---: |
| Session alignment | 8 | 0.081697 | 0.081675 | 0.0390625 |
| Session alignment | 16 | 0.068871 | 0.068899 | 0.0390625 |
| Temporal filtering | 8 | 0.009632 | 0.009618 | 0.01171875 |
| Temporal filtering | 16 | 0.011658 | 0.011659 | 0.01171875 |
| Adaptive observation variance | 8 | 0.000000 | 0.000000 | 0.250000 |
| Adaptive observation variance | 16 | 0.000000 | 0.000000 | 0.250000 |

Six of six cohort effects within 0.00003. All six Holm adjusted tests reproduce the reported values to journal precision. Reported CI values are closely reproduced; largest upper-limit difference is adaptive variance, k=8 (historical 0.008986 vs new 0.007045), without a change of inferential conclusion.

Subject 6 confirms large alignment effects: reconstructed +3.3451 (k=8) and +3.9499 (k=16); both track historical values +3.344 and +3.951.

Normalized-duration fitted Day-1 alpha/q parameter rows agree in 19/20 configurations. The sole difference is Subject 5, 8 electrodes: newly selected alpha=0.25 versus frozen manuscript alpha=0.5; process-noise scales agree. Alpha=0 was selected in 12/20 in both.

## Scientific interpretation

The central finding survives independent reexecution on all original source recordings. Explicitly specified independent code is available for both the main cohort analysis and the Figure-4 secondary analysis. This is strong numerical conformance to published conclusions; it is **not a claim of bitwise identity** to an unrecovered historical implementation. Historical manuscript numbers remain frozen pending any deliberate editorial adjustment.

The Figure-4 normalized-duration analysis is implemented in `audit_figure4_normalized.py`, and the Windows runner in `run_figure4_audit.ps1`. The physical-time pipeline is in `reproducibility/emg_reimplementation.py` and `scripts/run_full_conformance.ps1`.

## Manuscript handling

Do not silently overwrite historical tables, confidence intervals or figures with reconstructed ones. Once v1.0.3 receives a version DOI, update *only* the manuscript's Data and Code Availability statement and any agreed scope clarifications. Compile and verify a separate final Overleaf ZIP for journal submission. The v1.0.3 GitHub snapshot intentionally precedes DOI minting.
