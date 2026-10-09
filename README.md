# Prescribed Force Trajectories as Benchmarks for Longitudinal EMG Decoding

Reproducibility archive for a single-author manuscript by **Antonio Pereira**.

## Primary scientific result

Using ten CEMHSEY Part-I GRASP participants (Subjects 1–10), 100 held-out later-day participant-day recordings, and a fixed 30%-MVC trapezoidal grasp target, the protocol-defined prior achieved a historical cohort median participant R² of **0.9933**. The Day-1 average template yielded **0.9832**; adaptive EMG-only state-space decoders yielded **0.9388 (8 electrodes)** and **0.9370 (16 electrodes)**.

The independent biological sample is **N=10**, not 100.

## Full-data reproducibility verification (v1.0.3)

Two original, intact audit archives, executed against the 220 source MAT files, are preserved in `validation/`:

- `validation/physical_time/CONFORMANCE_REPORT.zip`: protocol-prior cohort summary, configuration, participant and recording metrics, Day-1 parameters, descriptive leave-one-day-out residuals, and six-way cohort-level conformance CSV.
- `validation/figure4_normalized/FIGURE4_AUDIT.zip`: independent normalized-duration Figure-4 reconstruction, six contrasts, bootstrap intervals, participant effects, selected hyperparameters, and Subject-6 checks.

The six fixed/adaptive EMG and adaptive-hybrid cohort R² summaries agree with the frozen historical summaries within **5×10⁻⁴**; maximum |difference| = **0.0000731**.

The six independently reconstructed Figure-4 paired median effects differ by at most **0.0000278**. All six Holm-adjusted tests reproduce the published inference to reported precision. Historical/recomputed differences are retained transparently in `docs/FULL_DATA_VALIDATION_v1.0.3.md`, including the adaptive-variance CI and one Day-1 alpha setting. Do not interpret agreement as proof that the historical and reconstructed source programs are identical.

## Run analyses on original public recordings

Dataset: https://doi.org/10.5281/zenodo.14224328

Create a dedicated Python virtual environment; on Windows use its explicit interpreter instead of MSYS2 Python. Then:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run_emg.ps1 -DataRoot "C:\work\CEMHSEY"
powershell -NoProfile -ExecutionPolicy Bypass -File .\run_figure4_audit.ps1 -DataRoot "C:\work\CEMHSEY"
```

The two runners create a 220-row manifest (Subjects 1–10, Days 1–11, Trials 1–2, Session 1, Task 2) and regenerate the outputs. The runtime-specific manifest is intentionally not tracked.

## Archive contents

- `manuscript/`: final pre-DOI LaTeX manuscript, supplement, bibliography and four original vector PDF figures.
- `reproducibility/protocol_prior_benchmark.py`: physical- and normalized-time protocol-prior and Day-1 template benchmarks.
- `reproducibility/emg_reimplementation.py`: independent executable EMG decoder with explicit numerical choices and leakage boundaries.
- `audit_figure4_normalized.py`, `run_figure4_audit.ps1`: independent normalized-time Figure-4 audit.
- `results/`: preserved frozen historical summary tables (unchanged).
- `validation/`: complete primary and Figure-4 empirical audit outputs.
- `tests/`: synthetic and integration tests.
- `docs/ANALYSIS_LOCK.md`, `docs/REIMPLEMENTATION_CONFORMANCE.md`, `docs/FULL_DATA_VALIDATION_v1.0.3.md`: locked specifications, independent choices, and audit interpretation.

## Versioning and DOI

This archive is version **v1.0.3**. Use its own Zenodo version DOI after Zenodo completes GitHub ingestion. The DOI `10.5281/zenodo.23249424` belongs specifically to the earlier **v1.0.1** release and should not identify these newer files. The archived manuscript is a pre-DOI snapshot; the journal submission's Data and Code Availability statement must be patched to the verified v1.0.3 DOI without changing the numerical analyses.

`v1.0.2` remains immutable. Do not overwrite historical tags or claim exact source-program identity.
