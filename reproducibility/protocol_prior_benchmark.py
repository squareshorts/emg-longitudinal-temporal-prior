#!/usr/bin/env python3
"""Reconstruct the force-only temporal-prior benchmark from CEMHSEY Part I.

This script intentionally reproduces only the force-only benchmark and Day-1
force-template comparisons that define the central result of the manuscript.
It does not reconstruct the complete EMG/Kalman branch.

Expected manifest columns:
    subject, day, trial, mat_path

The manifest should contain 10 subjects x 11 days x 2 trials = 220 rows for
Subjects 1-10, Session 1 cylindrical grasp, Task 2 (30% MVC).
"""
from __future__ import annotations

import argparse
from pathlib import Path
import json

import numpy as np
import pandas as pd
from scipy.io import loadmat
from scipy.stats import wilcoxon

EMG_FS = 2048.0
FORCE_FS = 200.0
WINDOW_SAMPLES = 410
STEP_SAMPLES = 205
N_BOOT = 100_000
BOOT_SEED = 20260918


def protocol_target_seconds(t: np.ndarray) -> np.ndarray:
    """Nominal 30%-MVC trapezoid at physical time t (seconds)."""
    t = np.asarray(t, dtype=float)
    y = np.zeros_like(t)
    ramp_up = (t >= 5.0) & (t < 10.0)
    hold = (t >= 10.0) & (t < 20.0)
    ramp_down = (t >= 20.0) & (t < 25.0)
    y[ramp_up] = 0.30 * (t[ramp_up] - 5.0) / 5.0
    y[hold] = 0.30
    y[ramp_down] = 0.30 * (25.0 - t[ramp_down]) / 5.0
    return y


def metrics(y: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    y = np.asarray(y, dtype=float)
    pred = np.asarray(pred, dtype=float)
    ok = np.isfinite(y) & np.isfinite(pred)
    y = y[ok]
    pred = pred[ok]
    if y.size < 2:
        return {"r2": np.nan, "rmse": np.nan, "nrmse_sd": np.nan, "mae": np.nan}
    err = y - pred
    sse = float(np.sum(err ** 2))
    sst = float(np.sum((y - np.mean(y)) ** 2))
    r2 = np.nan if sst <= 0 else 1.0 - sse / sst
    rmse = float(np.sqrt(np.mean(err ** 2)))
    sd = float(np.std(y, ddof=0))
    return {
        "r2": r2,
        "rmse": rmse,
        "nrmse_sd": np.nan if sd <= 0 else rmse / sd,
        "mae": float(np.mean(np.abs(err))),
    }


def semg_sample_count(x: np.ndarray) -> int:
    x = np.asarray(x)
    if x.ndim != 2:
        raise ValueError(f"data_sEMG must be 2-D; got shape {x.shape}")
    if x.shape[0] == 320:
        return int(x.shape[1])
    if x.shape[1] == 320:
        return int(x.shape[0])
    return int(max(x.shape))


def load_trial(path: Path) -> dict[str, np.ndarray]:
    m = loadmat(path, squeeze_me=True)
    if "data_force" not in m or "data_sEMG" not in m:
        raise KeyError(f"{path}: expected data_force and data_sEMG")
    force = np.asarray(m["data_force"], dtype=float).squeeze()
    if force.ndim != 1:
        force = force.reshape(-1)
    n_emg = semg_sample_count(np.asarray(m["data_sEMG"]))
    starts = np.arange(0, n_emg - WINDOW_SAMPLES + 1, STEP_SAMPLES, dtype=int)
    centers = starts.astype(float) + WINDOW_SAMPLES / 2.0
    t_physical = centers / EMG_FS
    force_t = np.arange(force.size, dtype=float) / FORCE_FS
    force_physical = np.interp(t_physical, force_t, force)

    denom_emg = max(n_emg - 1, 1)
    u = centers / denom_emg
    u_force = np.linspace(0.0, 1.0, force.size)
    force_normalized = np.interp(u, u_force, force)

    return {
        "t_physical": t_physical,
        "u": u,
        "force_physical": force_physical,
        "force_normalized": force_normalized,
    }


def interpolate_template(src_axis: np.ndarray, src_y: np.ndarray,
                         dst_axis: np.ndarray) -> np.ndarray:
    return np.interp(dst_axis, src_axis, src_y)


def percentile_bootstrap_median(delta: np.ndarray, n_boot: int = N_BOOT,
                                seed: int = BOOT_SEED) -> tuple[float, float]:
    delta = np.asarray(delta, dtype=float)
    delta = delta[np.isfinite(delta)]
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, delta.size, size=(n_boot, delta.size))
    vals = np.median(delta[idx], axis=1)
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return float(lo), float(hi)


def evaluate_mode(trials: dict[tuple[int, int, int], dict[str, np.ndarray]],
                  mode: str) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    if mode == "physical":
        axis_key = "t_physical"
        force_key = "force_physical"
    elif mode == "normalized":
        axis_key = "u"
        force_key = "force_normalized"
    else:
        raise ValueError(mode)

    rows = []
    for subject in range(1, 11):
        d1t1 = trials[(subject, 1, 1)]
        d1t2 = trials[(subject, 1, 2)]
        for day in range(2, 12):
            test = trials[(subject, day, 2)]
            axis = test[axis_key]
            y = test[force_key]

            p_t1 = interpolate_template(d1t1[axis_key], d1t1[force_key], axis)
            p_t2 = interpolate_template(d1t2[axis_key], d1t2[force_key], axis)
            p_avg = 0.5 * (p_t1 + p_t2)
            if mode == "physical":
                p_nom = protocol_target_seconds(axis)
            else:
                p_nom = protocol_target_seconds(30.0 * axis)

            for method, pred in [
                ("protocol_prior", p_nom),
                ("day1_trial1_template", p_t1),
                ("day1_average_template", p_avg),
            ]:
                rec = metrics(y, pred)
                rows.append({
                    "mode": mode,
                    "subject": subject,
                    "day": day,
                    "trial": 2,
                    "method": method,
                    **rec,
                })

    recording = pd.DataFrame(rows)
    participant = (
        recording.groupby(["mode", "subject", "method"], as_index=False)
        .agg(r2=("r2", "median"), rmse=("rmse", "median"),
             nrmse_sd=("nrmse_sd", "median"), mae=("mae", "median"))
    )

    cohort = {}
    for method in participant["method"].unique():
        x = participant[participant["method"] == method]
        cohort[method] = {
            "median_participant_r2": float(x["r2"].median()),
            "median_participant_rmse": float(x["rmse"].median()),
            "median_participant_nrmse_sd": float(x["nrmse_sd"].median()),
            "median_participant_mae": float(x["mae"].median()),
            "min_participant_r2": float(x["r2"].min()),
            "max_participant_r2": float(x["r2"].max()),
        }

    wide = participant.pivot(index="subject", columns="method", values="r2")
    delta = (wide["protocol_prior"] - wide["day1_average_template"]).to_numpy()
    ci_lo, ci_hi = percentile_bootstrap_median(delta)
    stat, p = wilcoxon(delta, alternative="two-sided", method="auto")
    recording_wide = recording.pivot_table(index=["subject", "day"], columns="method", values="r2")
    rec_delta = recording_wide["protocol_prior"] - recording_wide["day1_average_template"]
    cohort["protocol_prior_vs_day1_average"] = {
        "median_paired_delta_r2": float(np.median(delta)),
        "bootstrap95_low": ci_lo,
        "bootstrap95_high": ci_hi,
        "participants_improved": int(np.sum(delta > 0)),
        "participants_total": int(delta.size),
        "recordings_improved": int(np.sum(rec_delta > 0)),
        "recordings_total": int(rec_delta.size),
        "wilcoxon_statistic": float(stat),
        "wilcoxon_p_unadjusted": float(p),
    }
    return recording, participant, cohort


def validate_manifest(df: pd.DataFrame) -> None:
    required = {"subject", "day", "trial", "mat_path"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Manifest missing columns: {sorted(missing)}")
    df["subject"] = df["subject"].astype(int)
    df["day"] = df["day"].astype(int)
    df["trial"] = df["trial"].astype(int)
    wanted = {(s, d, t) for s in range(1, 11) for d in range(1, 12) for t in (1, 2)}
    got = set(zip(df.subject, df.day, df.trial))
    if got != wanted:
        miss = sorted(wanted - got)
        extra = sorted(got - wanted)
        raise ValueError(f"Manifest must contain exactly 220 target rows. Missing={miss[:10]}, extra={extra[:10]}")
    if df.duplicated(["subject", "day", "trial"]).any():
        raise ValueError("Duplicate subject/day/trial rows in manifest")
    blank = df["mat_path"].astype(str).str.strip().eq("")
    if blank.any():
        raise ValueError(f"Manifest has {int(blank.sum())} blank mat_path entries")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    manifest = pd.read_csv(args.manifest)
    validate_manifest(manifest)

    trials = {}
    for row in manifest.itertuples(index=False):
        p = Path(row.mat_path)
        if not p.exists():
            raise FileNotFoundError(p)
        trials[(int(row.subject), int(row.day), int(row.trial))] = load_trial(p)

    all_cohort = {}
    for mode in ("physical", "normalized"):
        recording, participant, cohort = evaluate_mode(trials, mode)
        recording.to_csv(args.out / f"recording_metrics_{mode}.csv", index=False)
        participant.to_csv(args.out / f"participant_metrics_{mode}.csv", index=False)
        all_cohort[mode] = cohort

    with open(args.out / "cohort_summary.json", "w", encoding="utf-8") as f:
        json.dump(all_cohort, f, indent=2)

    print(json.dumps(all_cohort, indent=2))


if __name__ == "__main__":
    main()
