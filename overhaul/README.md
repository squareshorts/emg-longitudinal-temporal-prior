# CEMHSEY GRASP overhaul pipeline

Single-pass replacement for the earlier rclone/Google Drive workflow. Each of the 6,005 GRASP recordings is read once from Zenodo (HTTP range reads of `GRASP_S{n}.zip`; ZIP CRC-32 verified; SHA-256 recorded), reduced to window features for band-passed and unfiltered EMG plus the raw force trace, and stored in `cache/` (~23 GB). Raw MAT files are not kept: Zenodo is the archival copy. If range reads fail for a participant, the pipeline downloads that participant's whole archive, verifies Zenodo's MD5, processes it locally and deletes it.

Original local copies under `C:\work\CEMHSEY` are reused instead of downloaded.

## Run
The launcher waits for `READY.txt`, installs `requirements.txt` into the analysis venv and runs `run_all.py`, logging to `run.log`. To restart after an interruption, run `python run_all.py` again: cached recordings and finished analysis conditions are reused.

## Stages and outputs (`results/`)
1. `inventory/` — recording manifest with source CRC-32, SHA-256 and byte counts.
2. `gate/` — protocol-timing QC for every grasp × force level, and reproduction of the earlier Session 1 / Task 2 protocol-prior R² (participants 1–10, tolerance 0.002). A reproduction failure stops the run; grasp × force cells off the nominal trapezoid are excluded and listed.
3. `primary_bandpass_physical/`, `sensitivity_unfiltered_physical/`, `sensitivity_bandpass_normalized/` — held-out metrics, phase metrics, protocol tracking, hyperparameters, participant and cohort summaries, exploratory per-condition summaries, familiarization slopes, `run_metadata.json`.
4. `RUN_REPORT.md`, `provenance.json`, `pip_freeze.txt`.

Results (without checkpoints) are copied to `G:\My Drive\CEMHSEY_full_GRASP_2026\analysis\overhaul_<timestamp>` when Drive for desktop is available.

`STATUS.json` shows the current stage; `DONE.txt` appears on success.

The pre-specified analysis is in `ANALYSIS_PLAN.md`; its hash is stored with every result.

## Tests
`python -m pytest tests` (set `CEMHSEY_TEST_DIR` to a folder holding `S1/D1/S1_Day1_Session1_Task2_Trial1.mat` and `S6/D2/S6_Day2_Session1_Task2_Trial2.mat` for the real-data tests).
