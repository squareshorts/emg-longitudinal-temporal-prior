# Presubmission reproducibility repair audit

- Restored final single-author LaTeX manuscript, supplement, bibliography and four original vector PDF figures to the GitHub repository and ZIP. The original PDF bytes were verified by hash.
- Added an independently specified EMG model implementation with explicit numerical safeguards and Kalman initial values. The implementation is new; published historical numerical results have **not** been recomputed using it.
- Added MAT-file manifest auto-discovery and a report-only conformance comparison tool.
- Added integration and synthetic tests covering 61,500-sample source-like MAT trial layout and 299 windows.
- Historical fixed results retained without alteration.
- No original MATLAB data redistributed.
- The tagged GitHub source tree contains the manuscript text, synthetic tests, and all four bitwise-verified original figure PDFs.
- The old versioned DOI 10.5281/zenodo.23249424 describes v1.0.1. This v1.0.2 source tag will receive its own DOI when Zenodo completes the automatic GitHub import.

**Required for scientific closure:** execute the full new EMG reimplementation on CEMHSEY Part-I recordings, compare participant-level and cohort-level outputs, and correct either the implementation or manuscript statements where disagreement is found. The exact original historical epsilon / x0 / P0 cannot be retrieved from the files presently accessible.
