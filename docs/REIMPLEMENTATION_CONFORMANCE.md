# EMG reconstruction: implementation decisions and conformance gate

## Status

The **historical executable EMG/Kalman script has not been recovered**. The manuscript's existing EMG, hybrid, residual, and ablation numbers come from the historical interactive analysis, not from `reproducibility/emg_reimplementation.py`.

The new module is an independent, auditable reconstruction of the described algorithm. It is intentionally labelled as a **new reconstruction** until it has been run on the 220 source recordings and every manuscript quantity independently reconciled. Tests on synthetic data validate numerical behavior and leakage boundaries; they do not establish empirical agreement with the historical run.

## Newly fixed numerical choices (do not retroactively attribute these to the historical analysis)

| Parameter | New reconstruction choice | Scientific role |
| --- | --- | --- |
| `epsilon` | `1e-8` | Prevent zero scaled-MAD denominator for adaptive observation variance |
| Disagreement input | Affine-session-aligned electrode predictions | Variance adaptation acts on the actual Kalman observations |
| `x0` | `0.0` MVC | Protocol rest baseline, independent of later-day force |
| `P0` | `Var(force on Day-1 Trial-1) + 1e-10` | Day-1-only initialization uncertainty |
| `q_floor` | `1e-10` | Positive lower bound on process variance |
| `r_floor` | `1e-10` | Positive lower bound on baseline observation variance |
| `scale_floor` | `1e-8` | Reject session alignment if later-day prediction IQR is degenerate |
| Ridge grid | 17 values log-spaced from `1e-3` to `1e5` | Per-electrode Day-1-only selection |
| `q_s` grid | `0.01,0.03,0.1,0.3,1,3,10` | Day-1 Trial-2 error selection |
| Alpha grid | `0,0.1,0.25,0.5,1,2` | Day-1 Trial-2 error selection |
| Fusion | Scalar random-walk filter with simultaneous independent-channel precision update | Deterministic Kalman interpretation |

**Publication rule:** The numbers in the manuscript must remain labelled as historical results until this new implementation either reproduces them or a verified original execution script is recovered. Updating the archive alone cannot establish retrospective identity.

## Recommended full-data run

Generate `reproducibility/manifest.csv` from the original `.mat` tree using `reproducibility/build_manifest.py`; it selects precisely Subjects 1--10, Days 1--11, Trials 1--2, Session 1, Task 2 (220 MAT files).

On the machine holding the public CEMHSEY Part-I files, run:

```bash
python -m pip install -r requirements.txt
python -m pytest -q tests
python reproducibility/build_manifest.py --data-root PATH/TO/CEMHSEY_PART_I --out reproducibility/manifest.csv
python reproducibility/protocol_prior_benchmark.py --manifest reproducibility/manifest.csv --out results/new_protocol_prior
python reproducibility/emg_reimplementation.py --manifest reproducibility/manifest.csv --out results/new_emg_reimplementation
python reproducibility/compare_frozen_results.py --new results/new_emg_reimplementation/reimplemented_participant_metrics.csv --frozen results/longitudinal_performance_physical.csv --out results/new_emg_reimplementation/conformance.csv
```

`compare_frozen_results.py` is a check, never a parameter-tuning program. It reports differences in independently recomputed participant-median cohort summaries. The user should examine both summary and per-participant discrepancies, and must not alter the new implementation to reproduce the old manuscript by overfitting to published summary values.

## Evidence and remaining work

- The complete source package and original manuscript figure PDFs can be stored and compiled from this candidate release bundle.
- The force-only protocol benchmark has its own executable script.
- The EMG branch has a new explicitly specified implementation and deterministic tests.
- The original script `C:\work\CEMHSEY\build_feature_cache.py` and the old `analyze_force.py` were mentioned in the historical workflow, but their original file bytes are not available in this session. Neither the historical exact `epsilon` nor the historical `x0/P0` can be inferred from the published summary statistics.
- The complete source dataset is available from the external CEMHSEY Part-I Zenodo record. It is not included in this archive.
- A new empirical full-data run has not occurred in this environment. Until it has, the secondary EMG results cannot be certified as reproduced.
