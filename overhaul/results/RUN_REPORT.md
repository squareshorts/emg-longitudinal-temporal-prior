# CEMHSEY overhaul run report

Finished 2026-11-12 15:21.

Recordings cached: 6005 of 6005 (251 GB streamed or read once).

Gate: timing ok = False, reproduction ok = True (max |dR2| = 4.669571380677695e-07), flagged recordings = 653/6005, excluded grasp/force cells = [[2, 1]].

## primary_bandpass_physical

| model                        | alignment                |   median_participant_skill |   ci95_low |   ci95_high |   participants_positive |   n_participants |   wilcoxon_p |   median_rmse_pct_mvc |
|:-----------------------------|:-------------------------|---------------------------:|-----------:|------------:|------------------------:|-----------------:|-------------:|----------------------:|
| protocol_prior               | none                     |                      0.000 |      0.000 |       0.000 |                       0 |               13 |      nan     |                 1.320 |
| ridge_8_residual             | trial1_unlabelled_affine |                     -0.078 |     -0.334 |      -0.044 |                       3 |               13 |        0.080 |                 1.486 |
| ridge_16_residual            | trial1_unlabelled_affine |                     -0.097 |     -0.274 |      -0.048 |                       3 |               13 |        0.057 |                 1.518 |
| pooled_day1_template_loso    | none                     |                     -0.219 |     -0.340 |       0.000 |                       4 |               13 |        0.010 |                 1.471 |
| ridge_8_residual             | fixed                    |                     -0.224 |     -0.495 |      -0.080 |                       2 |               13 |        0.006 |                 1.527 |
| ridge_16_residual            | fixed                    |                     -0.252 |     -0.555 |      -0.091 |                       2 |               13 |        0.003 |                 1.570 |
| previous_day_trial2_template | none                     |                     -0.361 |     -0.523 |      -0.301 |                       0 |               13 |        0.000 |                 1.578 |
| ridge_all_residual           | trial1_unlabelled_affine |                     -0.394 |     -0.894 |      -0.297 |                       0 |               13 |        0.000 |                 1.688 |
| day1_average_template        | none                     |                     -0.579 |     -1.185 |      -0.312 |                       1 |               13 |        0.000 |                 1.672 |
| pca_ols_residual             | trial1_unlabelled_affine |                     -0.691 |     -1.249 |      -0.379 |                       0 |               13 |        0.000 |                 1.746 |
| pls_all_residual             | trial1_unlabelled_affine |                     -0.937 |     -1.708 |      -0.650 |                       0 |               13 |        0.000 |                 1.793 |
| day1_trial2_template         | none                     |                     -1.063 |     -1.462 |      -0.786 |                       0 |               13 |        0.000 |                 1.956 |

Familiarization: {
  "unit": "participant",
  "outcome": "median protocol-tracking RMSE (% of target level) per day",
  "median_slope_per_day": -0.1773397347225484,
  "ci95": [
    -0.19750745188143623,
    -0.066640241257888
  ],
  "decreasing": 13,
  "n": 13,
  "wilcoxon_p": 0.000244140625
}

## sensitivity_unfiltered_physical

| model                        | alignment                |   median_participant_skill |   ci95_low |   ci95_high |   participants_positive |   n_participants |   wilcoxon_p |   median_rmse_pct_mvc |
|:-----------------------------|:-------------------------|---------------------------:|-----------:|------------:|------------------------:|-----------------:|-------------:|----------------------:|
| protocol_prior               | none                     |                      0.000 |      0.000 |       0.000 |                       0 |               13 |      nan     |                 1.320 |
| ridge_8_residual             | trial1_unlabelled_affine |                     -0.103 |     -0.365 |      -0.060 |                       3 |               13 |        0.033 |                 1.381 |
| ridge_16_residual            | trial1_unlabelled_affine |                     -0.120 |     -0.350 |      -0.047 |                       3 |               13 |        0.008 |                 1.428 |
| pooled_day1_template_loso    | none                     |                     -0.219 |     -0.340 |       0.000 |                       4 |               13 |        0.010 |                 1.471 |
| ridge_8_residual             | fixed                    |                     -0.304 |     -0.488 |      -0.085 |                       2 |               13 |        0.002 |                 1.524 |
| ridge_16_residual            | fixed                    |                     -0.318 |     -0.649 |      -0.061 |                       2 |               13 |        0.005 |                 1.628 |
| previous_day_trial2_template | none                     |                     -0.361 |     -0.523 |      -0.301 |                       0 |               13 |        0.000 |                 1.578 |
| ridge_all_residual           | trial1_unlabelled_affine |                     -0.406 |     -0.871 |      -0.306 |                       0 |               13 |        0.000 |                 1.693 |
| day1_average_template        | none                     |                     -0.579 |     -1.185 |      -0.312 |                       1 |               13 |        0.000 |                 1.672 |
| pca_ols_residual             | trial1_unlabelled_affine |                     -0.790 |     -1.034 |      -0.582 |                       0 |               13 |        0.000 |                 1.848 |
| pls_all_residual             | trial1_unlabelled_affine |                     -1.022 |     -2.415 |      -0.833 |                       0 |               13 |        0.000 |                 2.020 |
| day1_trial2_template         | none                     |                     -1.063 |     -1.462 |      -0.786 |                       0 |               13 |        0.000 |                 1.956 |

Familiarization: {
  "unit": "participant",
  "outcome": "median protocol-tracking RMSE (% of target level) per day",
  "median_slope_per_day": -0.1773397347225484,
  "ci95": [
    -0.19750745188143623,
    -0.066640241257888
  ],
  "decreasing": 13,
  "n": 13,
  "wilcoxon_p": 0.000244140625
}

## sensitivity_bandpass_normalized

| model                        | alignment                |   median_participant_skill |   ci95_low |   ci95_high |   participants_positive |   n_participants |   wilcoxon_p |   median_rmse_pct_mvc |
|:-----------------------------|:-------------------------|---------------------------:|-----------:|------------:|------------------------:|-----------------:|-------------:|----------------------:|
| protocol_prior               | none                     |                      0.000 |      0.000 |       0.000 |                       0 |               13 |      nan     |                 1.355 |
| ridge_8_residual             | trial1_unlabelled_affine |                     -0.082 |     -0.170 |      -0.039 |                       3 |               13 |        0.033 |                 1.510 |
| ridge_16_residual            | trial1_unlabelled_affine |                     -0.102 |     -0.280 |      -0.047 |                       3 |               13 |        0.021 |                 1.515 |
| ridge_8_residual             | fixed                    |                     -0.152 |     -0.308 |      -0.105 |                       2 |               13 |        0.003 |                 1.554 |
| pooled_day1_template_loso    | none                     |                     -0.184 |     -0.345 |       0.067 |                       4 |               13 |        0.013 |                 1.499 |
| ridge_16_residual            | fixed                    |                     -0.203 |     -0.449 |      -0.102 |                       2 |               13 |        0.002 |                 1.623 |
| previous_day_trial2_template | none                     |                     -0.283 |     -0.474 |      -0.185 |                       0 |               13 |        0.000 |                 1.607 |
| ridge_all_residual           | trial1_unlabelled_affine |                     -0.401 |     -0.922 |      -0.302 |                       0 |               13 |        0.000 |                 1.747 |
| day1_average_template        | none                     |                     -0.556 |     -1.036 |      -0.291 |                       1 |               13 |        0.000 |                 1.693 |
| pca_ols_residual             | trial1_unlabelled_affine |                     -0.625 |     -1.246 |      -0.408 |                       0 |               13 |        0.000 |                 1.834 |
| pls_all_residual             | trial1_unlabelled_affine |                     -0.853 |     -1.721 |      -0.643 |                       0 |               13 |        0.000 |                 1.873 |
| day1_trial2_template         | none                     |                     -0.903 |     -1.313 |      -0.706 |                       0 |               13 |        0.000 |                 2.040 |

Familiarization: {
  "unit": "participant",
  "outcome": "median protocol-tracking RMSE (% of target level) per day",
  "median_slope_per_day": -0.14319204280328876,
  "ci95": [
    -0.20256953035981456,
    -0.058590227654229554
  ],
  "decreasing": 12,
  "n": 13,
  "wilcoxon_p": 0.00048828125
}
