# Reproducibility scope

## Executable reconstructed analyses

The central force-only protocol prior and participant-specific Day-1 force-template comparisons are implemented in `reproducibility/protocol_prior_benchmark.py`, using the public CEMHSEY Part-I `.mat` files and a manifest with their paths.

The complete source archive includes `reproducibility/emg_reimplementation.py`, a newly specified independent EMG/Ridge/Kalman reconstruction. It contains explicit numerical settings, Day-1-only model selection, force-label-free session alignment, a bounded hybrid weight, and a separate descriptive leave-one-day-out residual diagnostic. It has unit tests, but it has **not** been empirically reconciled against the historical EMG results.

## Preserved historical outputs

The `results/` CSV files preserve the final reported numerical summaries. The downloadable candidate ZIP contains the LaTeX manuscript, supplement, bibliography, and four original figure PDFs in `manuscript/`. The GitHub repository currently includes text-based manuscript source; the vector figure PDFs must be uploaded before any corresponding new version is released. The recovered Figure 3/4 script preserves plotting provenance; its original intermediate CSV inputs are unavailable. The full historical EMG execution script is also unavailable.

`docs/REIMPLEMENTATION_CONFORMANCE.md` lists the new reconstruction's explicit numerical assumptions, how to run the full-data check, and why those values must not be passed off as the original frozen implementation settings.

The source dataset is maintained by the original CEMHSEY investigators at DOI 10.5281/zenodo.14224328 and is not redistributed here.
