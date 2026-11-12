# CEMHSEY GRASP overhaul pipeline

This branch adds the completed full-GRASP analysis and its recorded outputs. **Read `RESULTS.md` and `CORRECTIONS_AND_LIMITATIONS.md` before interpreting the statistical results.** The original pipeline, plan files, SHA-256 fingerprints and all raw numerical CSV outputs are preserved; reporting corrections are documented separately.

## Source design and eligibility

The code inventoried and extracted features from 6,005 available MAT recordings for 13 CEMHSEY GRASP participants (7 sessions × 3 force tasks × 11 days × 2 trials, less one documented failed acquisition). The original 21-condition timing gate reports `passed=false` because the lumbrical/10%-MVC cell was excluded by its condition rule. The historical reference reproduction check passed. Model inference uses the 20 eligible grasp–force cells and independent participant N=13.

The original method train/validation/test split is Day-1 Trial 1 / Day-1 Trial 2 / held-out Days 2–11 Trial 2; unlabeled later-day Trial 1 supports optional affine alignment. The later **post hoc** protected-decoder analysis additionally trains a supervised within-day model on each current day's force-labelled Trial 1.

## Original computational pipeline

`cemhsey_overhaul.py` supports feature extraction, source inventory and timing QC. The driver `run_all.py` runs original model-fitting and generates primary and sensitivity outputs. Local `cache/` and checkpoints allow resumption. Original 320-channel MAT files are retrieved from the dataset author's Zenodo archives or read from local copies; the 23-GB feature cache and 251-GB raw dataset are not committed.

Python environment and dependencies: see `requirements.txt` and `results/pip_freeze.txt`. The original study's environment, pipeline source fingerprints and plan fingerprint are in `results/provenance.json`.

## Archived-result verification (no raw MAT files required)

From this repository checkout:

```powershell
python -m pip install -r .\overhaul\requirements.txt
python .\overhaul\verify_archived_results.py
python -m pytest -q .\overhaul\tests
```

The audit checks manifest cardinality, protocol gates, source fingerprints, scoring equations, reconstructed participant/cohort summaries, post hoc model comparisons and timing-QC count. It does not claim independent raw-data reexecution. A subset of tests requiring original MAT files will skip unless supplied through the documented `CEMHSEY_TEST_DIR` test fixture.

## Result products

- `results/inventory/` — manifest of 6,005 recordings with checksums
- `results/gate/` — 21 condition timing QC and restricted eligibility (one failure)
- `results/primary_bandpass_physical/` — original recorded model results and participant/cohort tables
- `results/sensitivity_unfiltered_physical/` and `results/sensitivity_bandpass_normalized/` — sensitivity variants
- `results/posthoc_robustness/` — exploratory protected decoders and within-day versus across-day contrasts
- `results/posthoc_timing_qc_sensitivity.csv` — additional flagged-recording sensitivity, performed **after** the original analysis

The complete three phase-metric CSVs are not in this GitHub branch; see `DATA_PRODUCTS.md` for their verified Drive locations and outstanding public-archive work. The previous `v1.0.3` release describes an earlier restricted analysis and must not be reused as the DOI for these data.
