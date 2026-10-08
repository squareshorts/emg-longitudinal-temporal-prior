# Prescribed Force Trajectories as Benchmarks for Longitudinal EMG Decoding

Reproducibility archive for the manuscript by Antonio Pereira.

## Study question

This study asks how much apparent cross-day force-decoding accuracy in a highly structured surface-EMG experiment can be obtained from the prescribed task trajectory itself, before attributing performance to physiological information carried by EMG.

The primary dataset is the public CEMHSEY Part-I GRASP record. The analysis uses Subjects 1-10, Session 1 (cylindrical grasp), Task 2 (30% MVC), Trials 1-2, and Days 1-11.

Dataset DOI: https://doi.org/10.5281/zenodo.14224328

## Primary finding

The protocol-defined 30%-MVC trapezoidal trajectory, with no parameters fitted from participant data, reached a cohort median participant-level R2 of 0.9933 across Days 2-11. The average Day-1 force template reached 0.9832; adaptive EMG decoding reached 0.9388 with eight electrodes and 0.9370 with 16 electrodes.

## Repository contents

- `docs/ANALYSIS_LOCK.md` - fixed analysis choices used in the manuscript.
- `docs/REPRODUCIBILITY_SCOPE.md` - exact reproducibility scope and limitations.
- `results/` - frozen numerical summaries reported in the manuscript.
- `.zenodo.json` and `CITATION.cff` - release metadata.

A complete v1.0.0 source/reproducibility bundle, including manuscript source, scripts, and final figures, is prepared for the Zenodo version deposit.

## Version

v1.0.0 - presubmission reproducibility archive.
