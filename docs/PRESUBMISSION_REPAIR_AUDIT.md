# Presubmission reproducibility repair audit

- Restored final single-author LaTeX manuscript, supplement, bibliography and four original figure PDFs to the **downloadable candidate ZIP**.
- Added an independently specified EMG model implementation with explicit numerical safeguards and Kalman initial values. The implementation is new; published historical numerical results have **not** been recomputed using it.
- Added MAT-file manifest auto-discovery and a report-only conformance comparison tool.
- Added integration and synthetic tests covering 61,500-sample source-like MAT trial layout and 299 windows.
- Historical fixed results retained without alteration.
- No original MATLAB data redistributed.
- The GitHub repository contains text source and tests; binary figure PDFs are included in this candidate ZIP and remain pending remote upload.
- Current versioned DOI 10.5281/zenodo.23249424 continues to describe v1.0.1, not this candidate.

**Required for scientific closure:** execute the full new EMG reimplementation on CEMHSEY Part-I recordings, compare participant-level and cohort-level outputs, and correct either the implementation or manuscript statements where disagreement is found. The exact original historical epsilon / x0 / P0 cannot be retrieved from the files presently accessible.
