# Reproducibility scope

This archive separates what is fully reconstructable from what is preserved only as a frozen numerical result.

## Fully reconstructable in this archive

The central protocol-defined temporal-prior benchmark and participant-specific Day-1 force-template comparison are implemented in `reproducibility/protocol_prior_benchmark.py`. They require only the public CEMHSEY Part-I `.mat` files and a local path manifest.

The script implements the physical sensor time base used for the primary result, the fixed 30%-MVC trapezoidal target, Day-1 Trial-1 and Day-1 average force templates, recording-level R2/RMSE/normalized-RMSE/MAE, participant-level medians, and the participant-level paired comparison of the protocol prior with the Day-1 average template.

## Preserved but not claimed as complete executable reproduction

The EMG-only state-space branch, hybrid analysis, leave-one-day-out residual-shape diagnostic, and component ablations were developed interactively during the project. The final manuscript methods and numerical summaries are preserved here, and the original Figure 3/4 plotting script was recovered. The exact frozen execution script plus every intermediate CSV was not preserved as a single artifact.

Accordingly, this release does not claim bit-for-bit reproduction of the complete EMG branch. It is a frozen presubmission archive of the central executable benchmark, analysis specification, final numerical results, figures, and manuscript source.

## Unresolved implementation details from the historical EMG branch

The historical record does not preserve a reliable numerical value for the small epsilon used as a division-by-zero safeguard in robust disagreement, nor a fully recoverable statement of the Kalman initial state/covariance implementation. These values are not invented in this archive.
