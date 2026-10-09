# Reproducibility scope – v1.0.3

The original CEMHSEY Part-I 220 MAT source recordings (Subjects 1–10, Days 1–11, Trials 1–2, Session 1, Task 2) were used to independently execute the protocol prior, Day-1 force-template benchmarks, EMG/Ridge/Kalman decoder, and normalized-duration Figure-4 component audit.

The exact historical EMG executable was not recovered. Instead, the new `reproducibility/emg_reimplementation.py` specifies all relevant numerical safeguards and selection rules explicitly. Two uploaded run archives from that implementation are preserved byte-for-byte in `validation/`.

For physical-time results, all six fixed/adaptive EMG and adaptive-hybrid cohort median R² values are within 0.0005 of the frozen manuscript values. Residual-shape positive-correlation and positive-R² counts match all four reported configurations. Six of 80 three-decimal supplementary participant table entries differ beyond ±0.0005, notably Subject 7 with 16 electrodes; historical tables are preserved without rewriting.

For normalized-duration Figure 4, all six median paired effects agree within 0.00003 and Holm-adjusted tests agree at reported precision. One of 20 normalized-duration Day-1 parameter sets differs in alpha (Subject 5, 8 electrodes, 0.25 reconstructed vs 0.5 historical), and the eight-electrode adaptive-variance upper CI differs (0.007045 reconstructed vs 0.008986 frozen).

These independently obtained results validate the published substantive conclusions, but do not certify bitwise execution or every table entry. Detailed comparisons and full-data evidence are in `docs/FULL_DATA_VALIDATION_v1.0.3.md` and `validation/`.

The original public MAT files are available separately at https://doi.org/10.5281/zenodo.14224328 and are not redistributed here.
