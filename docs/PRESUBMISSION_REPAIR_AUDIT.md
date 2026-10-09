# Presubmission reproducibility repair audit

- Restored final single-author LaTeX manuscript, supplement, bibliography and four original vector PDF figures to the GitHub repository and ZIP. The original PDF bytes were verified by hash.
- Added an independently specified EMG model implementation with explicit numerical safeguards and Kalman initial values. The implementation is new; published historical numerical results have now been independently checked against full-data recomputations (v1.0.3); original historical execution bytes remain unavailable.
- Added MAT-file manifest auto-discovery and a report-only conformance comparison tool.
- Added integration and synthetic tests covering 61,500-sample source-like MAT trial layout and 299 windows.
- Historical fixed results retained without alteration.
- No original MATLAB data redistributed.
- The tagged GitHub source tree contains the manuscript text, synthetic tests, and all four bitwise-verified original figure PDFs.
- The old versioned DOI 10.5281/zenodo.23249424 describes v1.0.1. v1.0.3 contains full-data physical-time and normalized-time validation archives and will receive its own DOI upon Zenodo ingestion.

**Completed in v1.0.3:** full-data EMG reconstruction, participant/cohort comparisons, and normalized-duration Figure-4 ablation validation. The remaining small numerical differences are documented in `docs/FULL_DATA_VALIDATION_v1.0.3.md`. The journal manuscript's availability statement must cite the new version DOI once minted. The exact original historical epsilon / x0 / P0 cannot be retrieved from the files presently accessible.
