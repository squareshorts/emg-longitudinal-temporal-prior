# Data product inventory and publication status

## Public GitHub branch artifacts

`overhaul-full-grasp` contains the following result products:

- `results/inventory/recording_manifest.csv` (6,005 source-record keys, source checksums and byte counts)
- `results/gate/` (21 condition timing audit, individual timing flags, historical reproduction check)
- `results/primary_bandpass_physical/` (full recording-level model metrics, participant/cohort tables and run metadata)
- `results/sensitivity_unfiltered_physical/` and `results/sensitivity_bandpass_normalized/` (the corresponding sensitivity outputs)
- `results/posthoc_robustness/` (protected within-day/across-day analysis)
- `results/posthoc_timing_qc_sensitivity.csv` (additional **post hoc** excluded-recording sensitivity)
- `verify_archived_results.py` (internal archive consistency tests)
- The original `cemhsey_overhaul.py`, `run_all.py`, `posthoc_robustness.py`, and both analysis plans with SHA-256 fingerprints in `results/provenance.json` and `results/posthoc_robustness/summary.json`

## Three phase-resolved outputs not in the GitHub source tree

The full results were saved by the original pipeline to the user's connected Google Drive folder (not a stable public repository):

`https://drive.google.com/drive/folders/1SpQrUryn0fq0tE4JRGtZgiqlPbzJtLhT`

Under the three analysis variant subfolders:

| Analysis | Filename | Approx. size |
| --- | --- | ---: |
| `primary_bandpass_physical` | `heldout_phase_metrics.csv` | 54,113,368 bytes |
| `sensitivity_unfiltered_physical` | `heldout_phase_metrics.csv` | 54,105,708 bytes |
| `sensitivity_bandpass_normalized` | `heldout_phase_metrics.csv` | 54,108,589 bytes |

These Google Drive files were confirmed to exist and to have the indicated file sizes. Their complete contents and byte-level hashes were **not** independently verified during this audit. This folder link may require the account's permissions; it must not be described as permanent public access.

**Required before publication:** publish immutable, versioned copies of all three phase CSVs (e.g. in a DOI-backed archive), verify SHA-256 hashes and checksums against the local originals, and place the verified DOI and per-file hashes here. Do not attach unsupported DOI claims to this branch.

## Original CEMHSEY raw data

The actual MAT files are distributed by the CEMHSEY authors on Zenodo. This GitHub source archive does not redistribute 251 GB of raw MAT data and does not contain the approximately 23-GB local feature cache. The manifest's checksums identify what the run claims to have processed; independent reexecution against those original bytes is a separate validation task.
