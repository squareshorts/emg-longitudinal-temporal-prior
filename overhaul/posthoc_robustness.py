#!/usr/bin/env python3
"""Post hoc robustness analysis (decided after the primary results; see ANALYSIS_PLAN_ADDENDUM.md).

Two questions on the cached features (band-passed EMG, physical time base):
  A. Do all-channel decoders still lose to the protocol prior across days once
     they are protected against channels that change between sessions?
     Protection is label-free and fitted only on training data: per-recording
     bad-channel rejection (channel median MAV outside 1/10-10x the recording's
     median channel, or flat) and clipping of standardized features at +/-5 SD.
  B. How much of the EMG information about deviations from the prior survives
     across days? For every held-out recording (Day d Trial 2, d = 2..11) the
     same model is trained either on Day 1 Trial 1 (across days) or on Day d
     Trial 1 (within day). Hyperparameters are selected once on Day 1
     (Trial 1 -> Trial 2) and reused, so no within-day test trial informs any
     choice.
"""
from __future__ import annotations

import json
import os
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cross_decomposition import PLSRegression
from sklearn.decomposition import PCA
from sklearn.linear_model import LinearRegression, Ridge

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cemhsey_overhaul as c  # noqa: E402

CLIP_SD = 5.0
BAD_FACTOR = 10.0
MODELS = ("ridge_all_residual", "ridge_8_residual", "pls_all_residual", "pca_ols_residual", "ridge_all_raw")


def bad_channels(trial: c.Trial) -> np.ndarray:
    mav = trial.x3[:, :, 0]
    m = np.median(mav, axis=0)
    ref = np.median(m)
    return (m < ref / BAD_FACTOR) | (m > ref * BAD_FACTOR) | (mav.std(axis=0) <= 1e-12) | ~np.isfinite(m)


class Prep:
    """Standardize on the training trial, zero bad channels, clip at +/-CLIP_SD."""

    def __init__(self, train: c.Trial, fs: str, channels=None):
        self.fs, self.ch = fs, channels
        x = self._raw(train)
        bad = self._bad(train)
        good = x[:, ~bad, :]
        self.mean = np.zeros(x.shape[1:]); self.sd = np.ones(x.shape[1:])
        self.mean[~bad] = good.mean(axis=0)
        sd = good.std(axis=0); sd[sd <= 1e-12] = 1.0
        self.sd[~bad] = sd

    def _raw(self, t):
        x = t.x3 if self.fs == "x3" else t.x4
        return x if self.ch is None else x[:, self.ch, :]

    def _bad(self, t):
        b = bad_channels(t)
        return b if self.ch is None else b[self.ch]

    def __call__(self, t: c.Trial) -> np.ndarray:
        z = (self._raw(t) - self.mean) / self.sd
        z[:, self._bad(t), :] = 0.0
        return np.clip(z, -CLIP_SD, CLIP_SD).reshape(z.shape[0], -1)


def _target(t: c.Trial, mode: str) -> np.ndarray:
    return t.y if mode == "raw" else t.y - t.target


def _channels_for(train: c.Trial, k: int | None):
    if k is None:
        return None
    ch_bad = bad_channels(train)
    order = c.select_channels(train, train.y - train.target, c.N_CH)
    return np.array([ch for ch in order if not ch_bad[ch]][:k])


SPEC = {  # name -> (family, feature set, target mode, n channels)
    "ridge_all_residual": ("ridge", "x3", "residual", None),
    "ridge_8_residual": ("ridge", "x3", "residual", 8),
    "pls_all_residual": ("pls", "x3", "residual", None),
    "pca_ols_residual": ("pca", "x4", "residual", None),
    "ridge_all_raw": ("ridge", "x3", "raw", None),
}


def fit(name: str, train: c.Trial, hp=None, val: c.Trial | None = None):
    """Fit on `train`; if hp is None, select it on `val`. Returns (predict, hp)."""
    family, fs, mode, k = SPEC[name]
    prep = Prep(train, fs, _channels_for(train, k))
    ztr, ytr = prep(train), _target(train, mode)
    if family == "ridge":
        grid = c.RIDGE_ALPHAS
        make = lambda a: Ridge(alpha=a).fit(ztr, ytr)
        pred_of = lambda m, z: m.predict(z)
    elif family == "pls":
        grid = [n for n in c.PLS_COMPONENTS if n < min(ztr.shape)]
        def make(n):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                return PLSRegression(n_components=n, scale=False, max_iter=1000).fit(ztr, ytr)
        pred_of = lambda m, z: m.predict(z).ravel()
    else:
        pca = PCA(n_components=max(c.PCA_COMPONENTS), svd_solver="randomized", random_state=c.SEED).fit(ztr)
        ptr = pca.transform(ztr)
        grid = c.PCA_COMPONENTS
        make = lambda n: (n, LinearRegression().fit(ptr[:, :n], ytr))
        pred_of = lambda m, z: m[1].predict(pca.transform(z)[:, :m[0]])
    if hp is None:
        zval, yval = prep(val), _target(val, mode)
        best = None
        for h in grid:
            m = make(h)
            mse = float(np.mean((yval - pred_of(m, zval)) ** 2))
            if best is None or mse < best[0]:
                best = (mse, h)
        hp = best[1]
    model = make(hp)
    offset = (lambda t: t.target) if mode == "residual" else (lambda t: 0.0)
    return (lambda t: offset(t) + pred_of(model, prep(t))), hp


def analyze(key, lookup):
    s, g, task = key
    if (s, 1, g, task, 1) not in lookup:
        return []
    L = lambda d, r: c.load_trial(lookup[(s, d, g, task, r)], task, "bp", "physical")
    d1t1, d1t2 = L(1, 1), L(1, 2)
    across, hps, rows = {}, {}, []
    for name in MODELS:
        across[name], hps[name] = fit(name, d1t1, None, d1t2)
    val_out = {n: across[n](d1t2) for n in MODELS}
    for day in c.DAYS[1:]:
        cal, test = L(day, 1), L(day, 2)
        nbad = int(bad_channels(test).sum())
        base = {"subject": s, "session": g, "grasp": c.GRASPS[g], "task": task,
                "target_pct_mvc": c.TASK_PERCENT[task], "day": day, "bad_channels_test": nbad}
        for name in MODELS:
            p_fix = across[name](test)
            p_al = c.robust_affine(val_out[name], across[name](cal), p_fix)
            within, _ = fit(name, cal, hps[name])
            for scheme, p in (("across_fixed", p_fix), ("across_trial1_aligned", p_al), ("within_day", within(test))):
                rows.append({**base, "model": name, "scheme": scheme, "hyperparameter": hps[name],
                             **c.metrics(test.y, p, test.target)})
    return rows


_W = {}


def _init(lookup, ckdir):
    try:
        from threadpoolctl import threadpool_limits
        _W["lim"] = threadpool_limits(1)
    except Exception:
        pass
    _W.update(lookup=lookup, ckdir=ckdir)


def _work(key):
    rows = analyze(key, _W["lookup"])
    c.atomic_json(Path(_W["ckdir"]) / f"S{key[0]:02d}_G{key[1]}_T{key[2]}.json", rows)
    return key


def summarize(df: pd.DataFrame, out: Path) -> dict:
    part = df.groupby(["subject", "model", "scheme"], as_index=False).agg(
        median_skill=("skill_vs_prior", "median"), median_rmse=("rmse_pct_mvc", "median"),
        median_prior_rmse=("prior_rmse_pct_mvc", "median"))
    part.to_csv(out / "participant_summary.csv", index=False)
    rows = []
    for (m, sch), g in part.groupby(["model", "scheme"]):
        v = g.median_skill.to_numpy(float); lo, hi = c.bootstrap_median_ci(v)
        rows.append({"model": m, "scheme": sch, "median_participant_skill": float(np.median(v)), "ci95_low": lo,
                     "ci95_high": hi, "participants_positive": int((v > 0).sum()), "n": len(v),
                     "wilcoxon_p_vs_prior": c.safe_wilcoxon(v), "median_rmse_pct_mvc": float(g.median_rmse.median()),
                     "median_prior_rmse_pct_mvc": float(g.median_prior_rmse.median())})
    cohort = pd.DataFrame(rows).sort_values(["model", "scheme"])
    cohort.to_csv(out / "cohort_summary.csv", index=False)
    # Within-day minus across-days skill, paired on identical held-out recordings.
    w = part.pivot_table(index=["subject", "model"], columns="scheme", values="median_skill").reset_index()
    crow = []
    for m, g in w.groupby("model"):
        for other in ("across_fixed", "across_trial1_aligned"):
            d = (g["within_day"] - g[other]).to_numpy(float); lo, hi = c.bootstrap_median_ci(d)
            crow.append({"model": m, "contrast": f"within_day - {other}", "median_difference": float(np.median(d)),
                         "ci95_low": lo, "ci95_high": hi, "participants_within_better": int((d > 0).sum()),
                         "n": len(d), "wilcoxon_p": c.safe_wilcoxon(d)})
    contrasts = pd.DataFrame(crow)
    contrasts.to_csv(out / "within_vs_across_contrasts.csv", index=False)
    lvl = df.groupby(["subject", "target_pct_mvc", "model", "scheme"], as_index=False).skill_vs_prior.median()
    lvl.groupby(["target_pct_mvc", "model", "scheme"], as_index=False).agg(
        median_participant_skill=("skill_vs_prior", "median"),
        participants_positive=("skill_vs_prior", lambda v: int((v > 0).sum()))).to_csv(
        out / "by_force_level.csv", index=False)
    dy = df.groupby(["subject", "day", "model", "scheme"], as_index=False).skill_vs_prior.median()
    dy.groupby(["day", "model", "scheme"], as_index=False).skill_vs_prior.median().to_csv(out / "by_day.csv", index=False)
    return {"cohort": cohort.to_dict("records"), "contrasts": contrasts.to_dict("records"),
            "bad_channels_per_test_recording_median": float(df.drop_duplicates(
                ["subject", "session", "task", "day"]).bad_channels_test.median())}


def main(processes: int | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    res = HERE / "results"
    out = res / "posthoc_robustness"; ck = out / "checkpoints"; ck.mkdir(parents=True, exist_ok=True)
    manifest = pd.read_csv(res / "inventory" / "recording_manifest.csv")
    gate = json.loads((res / "gate" / "gate_summary.json").read_text(encoding="utf-8"))
    excluded = {tuple(x) for x in gate["excluded_conditions"]}
    identity = {"script_sha256": c.sha256_file(Path(__file__)), "pipeline_sha256": c.sha256_file(HERE / "cemhsey_overhaul.py"),
                "addendum_sha256": c.sha256_file(HERE / "ANALYSIS_PLAN_ADDENDUM.md"),
                "manifest_sha256": c.sha256_file(res / "inventory" / "recording_manifest.csv"),
                "excluded": sorted(map(list, excluded)), "clip_sd": CLIP_SD, "bad_factor": BAD_FACTOR}
    idp = ck / "identity.json"
    if idp.exists() and json.loads(idp.read_text(encoding="utf-8")) != identity:
        for p in ck.glob("S*.json"):
            p.unlink()
    c.atomic_json(idp, identity)
    lookup = {(r.subject, r.day, r.session, r.task, r.trial): Path(r.cache_path) for r in manifest.itertuples()}
    conds = [(s, g, t) for s in c.SUBJECTS for g in c.SESSIONS for t in c.TASKS if (g, t) not in excluded]
    todo = [k for k in conds if not (ck / f"S{k[0]:02d}_G{k[1]}_T{k[2]}.json").exists()]
    nproc = processes or max(1, min((os.cpu_count() or 2) - 1, 8))
    c.log(f"Post hoc robustness: {len(conds)} conditions, {len(todo)} to compute, {nproc} processes")
    t0 = time.time()
    if todo:
        from concurrent.futures import ProcessPoolExecutor, as_completed
        with ProcessPoolExecutor(max_workers=nproc, initializer=_init, initargs=(lookup, str(ck))) as pool:
            for i, f in enumerate(as_completed([pool.submit(_work, k) for k in todo]), 1):
                f.result()
                if i % 21 == 0 or i == len(todo):
                    c.log(f"{i}/{len(todo)} conditions ({(time.time() - t0) / 60:.1f} min)")
    rows = []
    for k in conds:
        rows.extend(json.loads((ck / f"S{k[0]:02d}_G{k[1]}_T{k[2]}.json").read_text(encoding="utf-8")))
    df = pd.DataFrame(rows); df.to_csv(out / "heldout_metrics.csv", index=False)
    summary = {**identity, **summarize(df, out)}
    c.atomic_json(out / "summary.json", summary)
    drive = Path(r"G:\My Drive\CEMHSEY_full_GRASP_2026\analysis")
    if drive.exists():
        import shutil
        dest = drive / f"posthoc_robustness_{time.strftime('%Y%m%d_%H%M')}"
        shutil.copytree(out, dest, ignore=shutil.ignore_patterns("checkpoints"))
        c.log(f"Copied to {dest}")
    (out / "DONE.txt").write_text(time.strftime("%Y-%m-%d %H:%M:%S"), encoding="utf-8")
    c.log("Post hoc robustness complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
