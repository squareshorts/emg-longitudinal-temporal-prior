# v1.0.3 — Full-data EMG and Figure-4 conformance archive

This release adds the empirical verification that was not present in v1.0.2. It preserves the original submitted numerical tables and four vector figure PDFs without retrofitting code to published summary values.

**Original source data:** CEMHSEY Part-I GRASP Subjects 1–10, Days 1–11, Session 1, Task 2, Trials 1 and 2; 220 source MAT recordings and 100 later-day evaluation recordings; independent biological sample N=10.

**Physical-time benchmark:** protocol target cohort median R² ≈ 0.9933; all six fixed/adaptive EMG and adaptive-hybrid historical cohort medians independently agree within 0.0005 R² (largest difference 0.0000731). Descriptive residual-shape positive counts match historical results.

**Normalized-duration Figure 4:** six stage-by-electrode paired median effects agree within 0.00003, with matching Holm-adjusted test conclusions. The small eight-electrode adaptive-variance bootstrap CI difference and Subject-5 parameter alpha discrepancy are documented in the validation report.

**Archive contents:** `validation/physical_time/CONFORMANCE_REPORT.zip`, `validation/figure4_normalized/FIGURE4_AUDIT.zip`, original manuscript, supplement, bibliography, four original vector figures, frozen summaries, independent analysis code, synthetic tests, parameter specifications, and validation notes.

**Scope:** the historical exact executable was not recovered, and the independent implementation does not claim byte-for-byte historical code identity. Scientific results have independent full-data numerical support.

**Zenodo:** this GitHub release is intended for Zenodo ingestion and must receive its own version-specific DOI. The v1.0.1 DOI 10.5281/zenodo.23249424 identifies the older release, not v1.0.3.

**Manuscript snapshot:** intentionally unmodified pending the v1.0.3 version DOI; the final Overleaf package will receive the DOI-specific availability paragraph after DOI minting.
