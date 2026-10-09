#!/usr/bin/env python3
"""Independent, explicitly specified CEMHSEY longitudinal EMG reconstruction.

WARNING: THIS IS NOT THE ORIGINAL HISTORICAL EXECUTION SCRIPT.
The original EMA/Kalman program and its exact numerical safeguards were not
recovered. This module provides a deterministic, inspectable reconstruction.
The frozen performance values in results/*.csv MUST NOT be represented as
outputs from this implementation until it has been run on the source dataset
and its outputs have been independently reconciled.

Use: python reproducibility/emg_reimplementation.py --manifest path/to/manifest.csv --out results/reimplemented

Manifest columns: subject,day,trial,mat_path. Subject/day/endpoint selection
follows docs/ANALYSIS_LOCK.md. The script never reads later-day Trial-1 force
for training, parameter selection or adaptation; later-day Trial-2 force is
used only for scoring and for a separate explicitly descriptive diagnostic.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.io import loadmat
from scipy.stats import pearsonr
from sklearn.linear_model import Ridge

EMG_FS = 2048.0
FORCE_FS = 200.0
WIN = 410
STEP = 205


@dataclass(frozen=True)
class ReimplementationConfig:
    """New reconstruction choices, not identified historical constants."""

    epsilon: float = 1e-8               # denominator safeguard in robust disagreement
    scale_floor: float = 1e-8          # zero-IQR guard for affine session alignment
    r_floor: float = 1e-10             # numerical guard on observation variance
    q_floor: float = 1e-10             # process variance floor
    p0_floor: float = 1e-10            # minimum initial covariance
    x0: float = 0.0                    # initial latent MVC-normalized force
    p0_source: str = 'day1_train_variance'  # P0=Var(Day1 Trial1 force) + floor
    alpha_grid: tuple = (0.0, 0.1, 0.25, 0.5, 1.0, 2.0)
    q_grid: tuple = (0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0)
    ridge_grid: tuple = tuple(np.logspace(-3, 5, 17))
    timebase: str = 'physical'
    feature_window: int = WIN
    feature_step: int = STEP


@dataclass
class Trial:
    x: np.ndarray        # windows x 320 x 3 [MAV, RMS, WL]
    y: np.ndarray        # force interpolated at window centers
    t: np.ndarray        # physical seconds


def _assert_dimensions(x: np.ndarray, y: np.ndarray) -> None:
    if x.ndim != 3 or x.shape[2] != 3 or x.shape[0] != y.size:
        raise ValueError(f'Expected features (T,channels,3) and force (T,), got {x.shape}, {y.shape}')


def features_at_physical_times(path: Path) -> Trial:
    """One trial; memory bounded by one raw 320-channel MAT file."""
    data = loadmat(path, squeeze_me=True, variable_names=['data_force', 'data_sEMG'])
    if 'data_force' not in data or 'data_sEMG' not in data:
        raise KeyError(f'Expected data_force and data_sEMG: {path}')
    emg = np.asarray(data['data_sEMG'], dtype=np.float64)
    if emg.ndim != 2:
        raise ValueError(f'{path}: data_sEMG must be two-dimensional')
    if emg.shape[0] != 320:
        if emg.shape[1] == 320:
            emg = emg.T
        else:
            raise ValueError(f'{path}: expected exactly 320 EMG channels; got {emg.shape}')
    force = np.asarray(data['data_force'], dtype=float).reshape(-1)
    if not np.isfinite(force).all():
        raise ValueError(f'{path}: nonfinite force samples')
    starts = np.arange(0, emg.shape[1] - WIN + 1, STEP, dtype=int)
    if len(starts) < 2:
        raise ValueError(f'{path}: too few samples')
    t = (starts + WIN / 2.0) / EMG_FS
    y = np.interp(t, np.arange(force.size) / FORCE_FS, force)
    x = np.empty((len(starts), 320, 3), dtype=np.float64)
    for channel in range(320):
        sig = emg[channel]
        # Create only the short window view, no 3-D copy of the whole acquisition.
        window = np.lib.stride_tricks.sliding_window_view(sig, WIN)[starts]
        x[:, channel, 0] = np.mean(np.abs(window), axis=-1)
        x[:, channel, 1] = np.sqrt(np.mean(window * window, axis=-1))
        x[:, channel, 2] = np.sum(np.abs(np.diff(window, axis=-1)), axis=-1)
    _assert_dimensions(x, y)
    return Trial(x, y, t)


def protocol_target(t: np.ndarray) -> np.ndarray:
    t = np.asarray(t)
    y = np.zeros_like(t, dtype=float)
    i = (t >= 5) & (t < 10)
    y[i] = .30 * (t[i] - 5.0) / 5.0
    i = (t >= 10) & (t < 20)
    y[i] = .30
    i = (t >= 20) & (t < 25)
    y[i] = .30 * (25.0 - t[i]) / 5.0
    return y


def metrics(y: np.ndarray, p: np.ndarray) -> dict:
    y = np.asarray(y, float)
    p = np.asarray(p, float)
    e = y - p
    denom = np.sum((y - np.mean(y))**2)
    out = {'r2': float(1 - np.sum(e**2) / denom) if denom > 0 else float('nan'),
           'rmse': float(np.sqrt(np.mean(e**2))),
           'mae': float(np.mean(np.abs(e))),
           'bias': float(np.mean(p-y))}
    return out


def rank_electrodes(x: np.ndarray, y: np.ndarray, k: int) -> np.ndarray:
    mav = x[:, :, 0]
    centered = mav - mav.mean(axis=0)
    yc = y - y.mean()
    num = yc @ centered
    den = np.sqrt((yc@yc) * np.sum(centered**2, axis=0))
    corr = np.divide(num, den, out=np.zeros_like(num), where=den>0)
    # Stable tie-breaking by physical electrode index.
    idx = np.lexsort((np.arange(len(corr)), -np.abs(corr)))
    return idx[:k]


class ElectrodeModels:
    def __init__(self, selected: np.ndarray, mean: np.ndarray, std: np.ndarray,
                 estimators: list[Ridge], ridge: np.ndarray, r0: np.ndarray):
        self.selected = selected
        self.mean = mean
        self.std = std
        self.estimators = estimators
        self.ridge = ridge
        self.r0 = r0

    def predict(self, trial: Trial) -> np.ndarray:
        x = trial.x[:, self.selected, :]
        xn = (x-self.mean) / self.std
        return np.column_stack([m.predict(xn[:, i, :]) for i,m in enumerate(self.estimators)])


def fit_electrodes(train: Trial, val: Trial, k: int,
                   cfg: ReimplementationConfig) -> ElectrodeModels:
    selected = rank_electrodes(train.x, train.y, k)
    tr = train.x[:, selected, :]
    va = val.x[:, selected, :]
    mean = np.mean(tr, axis=0)
    std = np.std(tr, axis=0, ddof=0)
    std = np.where(std > cfg.scale_floor, std, 1.0)
    trn = (tr-mean)/std
    van = (va-mean)/std
    models = []
    ridge = []
    r0 = []
    for i in range(k):
        best = None
        for lam in cfg.ridge_grid:
            model = Ridge(alpha=float(lam),fit_intercept=True,solver='cholesky')
            model.fit(trn[:,i,:],train.y)
            mse = float(np.mean((val.y-model.predict(van[:,i,:]))**2))
            if best is None or mse < best[0]:
                best = (mse,float(lam),model)
        models.append(best[2]); ridge.append(best[1]); r0.append(best[0])
    return ElectrodeModels(selected,mean,std,models,np.asarray(ridge),np.asarray(r0))


def robust_consensus(z: np.ndarray) -> np.ndarray:
    """Trim observations over 3 scaled-MAD, then mean; each row is a time."""
    if z.ndim != 2:
        raise ValueError('predictions need shape (time, electrodes)')
    med = np.median(z,axis=1,keepdims=True)
    s = 1.4826 * np.median(np.abs(z-med),axis=1,keepdims=True)
    keep = np.abs(z-med) <= 3.0*s
    # For exact-zero MAD, preserve observations at the median.
    keep = np.where(s == 0, z == med, keep)
    count = np.sum(keep, axis=1)
    return np.sum(z*keep,axis=1) / np.maximum(count,1)


def session_align(ref_z: np.ndarray, cal_z: np.ndarray, test_z: np.ndarray,
                  cfg: ReimplementationConfig) -> tuple[np.ndarray,float,float]:
    """All later-day alignment uses EMG predictions exclusively.

    Reference Day1 Trial2, later day Trial1 and later day Trial2 prediction
    arrays are passed in that order. Later-day force never enters the transform.
    """
    ref = robust_consensus(ref_z)
    cal = robust_consensus(cal_z)
    c_ref = float(np.median(ref))
    c_day = float(np.median(cal))
    s_ref = float(np.percentile(ref,75)-np.percentile(ref,25))
    s_day = float(np.percentile(cal,75)-np.percentile(cal,25))
    if s_day <= cfg.scale_floor:
        raise ValueError('Later-day unlabeled calibration prediction IQR is degenerate')
    scale = s_ref/s_day
    return c_ref + scale*(test_z-c_day), float(scale), float(c_day)


def disagreement(aligned_z: np.ndarray, epsilon: float) -> np.ndarray:
    """New reconstruction CHOICE: disagreement on aligned predictions.

    The original implementation's choice of aligned vs unaligned observations
    could not be recovered. A positive common affine transformation preserves
    MAD-standardized disagreement except for the additive safeguard.
    """
    med = np.median(aligned_z,axis=1,keepdims=True)
    s = 1.4826*np.median(np.abs(aligned_z-med),axis=1,keepdims=True)
    return np.abs(aligned_z-med)/(s+epsilon)


def kalman_fuse(z: np.ndarray, r0: np.ndarray, q: float, alpha: float,
                p0: float, cfg: ReimplementationConfig) -> np.ndarray:
    """Scalar random-walk Kalman; batch independent-channel update.

    x_0 = 0 MVC and P_0 = Var(force on Day1 Trial1)+p0_floor are choices
    made for this new deterministic reconstruction. They are NOT claimed to
    be the historical calibration implementation.
    """
    z = np.asarray(z,float)
    r0 = np.maximum(np.asarray(r0,float), cfg.r_floor)
    if z.ndim != 2 or z.shape[1] != len(r0):
        raise ValueError('Prediction array and variance vector incompatible')
    d = disagreement(z,cfg.epsilon)
    r = r0[None,:]*np.exp(np.minimum(float(alpha)*d*d,12.0))
    r = np.maximum(r,cfg.r_floor)
    q = max(float(q),cfg.q_floor)
    state = float(cfg.x0)
    cov = max(float(p0),cfg.p0_floor)
    out = np.empty(z.shape[0])
    for t in range(z.shape[0]):
        # F=1 random walk: predict then assimilate all k observations.
        prior_cov = cov + q
        prior_precision = 1.0/prior_cov
        precision = 1.0/r[t]
        denom = prior_precision+np.sum(precision)
        state = (prior_precision*state+np.sum(precision*z[t]))/denom
        cov = 1.0/denom
        out[t] = state
    return out


def tune_kalman(day1_train: Trial, day1_val: Trial, models: ElectrodeModels,
                cfg: ReimplementationConfig) -> tuple[float,float,float]:
    z = models.predict(day1_val)
    qbase = float(np.var(np.diff(day1_train.y), ddof=0))
    p0 = float(np.var(day1_train.y,ddof=0)+cfg.p0_floor)
    best = None
    for scale in cfg.q_grid:
        q = max(scale*qbase,cfg.q_floor)
        for alpha in cfg.alpha_grid:
            pred = kalman_fuse(z,models.r0,q,alpha,p0,cfg)
            mse = float(np.mean((day1_val.y-pred)**2))
            if best is None or mse < best[0]:
                best = (mse,float(scale),float(alpha))
    return best[1],best[2],p0


def fixed_q_scale(day1_train: Trial, day1_val: Trial,
                  models: ElectrodeModels,cfg: ReimplementationConfig) -> float:
    """Stage-matched fixed-variance process noise; tuned on Day 1 only."""
    z = models.predict(day1_val)
    qbase = float(np.var(np.diff(day1_train.y)))
    p0 = float(np.var(day1_train.y)+cfg.p0_floor)
    best = (np.inf,None)
    for scale in cfg.q_grid:
        q=max(scale*qbase,cfg.q_floor)
        p=kalman_fuse(z,models.r0,q,0.,p0,cfg)
        mse=float(np.mean((day1_val.y-p)**2))
        if mse<best[0]:best=(mse,float(scale))
    return best[1]


def fit_hybrid_weight(yval: np.ndarray, t1_template: np.ndarray, eval_emg: np.ndarray) -> float:
    v=eval_emg-t1_template
    denom=float(v@v)
    if denom==0:return 0.0
    return float(np.clip((v@(yval-t1_template))/denom,0,1))


def _read_manifest(path: Path) -> pd.DataFrame:
    df=pd.read_csv(path)
    req={'subject','day','trial','mat_path'}
    if not req.issubset(df.columns):raise ValueError(f'manifest missing {req-set(df.columns)}')
    df['subject']=df.subject.astype(int)
    df['day']=df.day.astype(int)
    df['trial']=df.trial.astype(int)
    wanted={(s,d,t) for s in range(1,11) for d in range(1,12) for t in [1,2]}
    got=set(zip(df.subject,df.day,df.trial))
    if got!=wanted or df.duplicated(['subject','day','trial']).any():
        raise ValueError(f'Expected 220 unique subject/day/trial rows: missing={len(wanted-got)}, extra={len(got-wanted)}')
    if df.mat_path.isna().any() or (df.mat_path.astype(str).str.strip()=='').any():
        raise ValueError('manifest contains blank mat_path; populate paths before execution')
    return df


def _residual_shape_diagnostics(traces: dict, out: Path) -> pd.DataFrame:
    """Descriptive LODO nuisance removal. Other days' force labels are used."""
    rows=[]
    for subject in range(1,11):
        days=sorted(d for s,d in traces if s==subject)
        if len(days)!=10:raise ValueError('Need 10 later days for LODO diagnostic')
        for k in (8,16):
            for method in ('fixed_kf','adaptive_kf'):
                for d in days:
                    rtrue=traces[(subject,d)]['force']-traces[(subject,d)]['day1_avg']
                    rpred=traces[(subject,d)][f'{method}_{k}']-traces[(subject,d)]['day1_avg']
                    held_axis=traces[(subject,d)]['t']
                    others_true=[];others_pred=[]
                    for other in days:
                        if other==d:continue
                        v=traces[(subject,other)]
                        a=np.interp(held_axis,v['t'],v['force']-v['day1_avg'])
                        b=np.interp(held_axis,v['t'],v[f'{method}_{k}']-v['day1_avg'])
                        others_true.append(a);others_pred.append(b)
                    y=rtrue-np.mean(others_true,axis=0)
                    p=rpred-np.mean(others_pred,axis=0)
                    if np.std(y)>0 and np.std(p)>0:
                        rr=float(pearsonr(y,p).statistic)
                    else:rr=np.nan
                    me=metrics(y,p)
                    rows.append({'subject':subject,'day':d,'electrodes':k,'method':method,
                                 'loo_pearson_r':rr,'loo_residual_r2':me['r2'],
                                 'positive_correlation': bool(rr>0),
                                 'positive_residual_r2': bool(me['r2']>0),
                                 'interpretation':'diagnostic_only_uses_other_days_force_labels'})
    df=pd.DataFrame(rows)
    df.to_csv(out/'reimplemented_descriptive_lodo.csv',index=False)
    return df


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    df=_read_manifest(args.manifest)
    files={(int(r.subject),int(r.day),int(r.trial)):Path(r.mat_path) for r in df.itertuples()}
    args.out.mkdir(parents=True,exist_ok=True)
    cfg=ReimplementationConfig()
    (args.out/'new_reimplementation_config.json').write_text(json.dumps(asdict(cfg),indent=2),encoding='utf-8')
    summary=[];parameters=[]; traces={}
    for s in range(1,11):
        train=features_at_physical_times(files[s,1,1])
        val=features_at_physical_times(files[s,1,2])
        models_by_k={}; knobs={}
        for k in [8,16]:
            model=fit_electrodes(train,val,k,cfg)
            best_q,alpha,p0=tune_kalman(train,val,model,cfg)
            fixed_q=fixed_q_scale(train,val,model,cfg)
            models_by_k[k]=model;knobs[k]=(best_q,alpha,p0,fixed_q)
            parameters.append({'subject':s,'electrodes':k,
                               'electrodes_0_indexed':json.dumps(model.selected.tolist()),
                               'ridge_penalties':json.dumps(model.ridge.tolist()),
                               'r0':json.dumps(model.r0.tolist()),
                               'q_scale':best_q,'alpha':alpha,'fixed_q_scale':fixed_q,
                               'initial_state_x0':cfg.x0,'initial_covariance_p0':p0,
                               'epsilon':cfg.epsilon,
                               'disagreement_input':'aligned_test_observations'})

        for d in range(2,12):
            # The later-day calibration force is loaded in the source MAT file
            # but never passed to model fitting, alignment or hyperparameter selection.
            cal=features_at_physical_times(files[s,d,1])
            test=features_at_physical_times(files[s,d,2])
            t1=np.interp(test.t,train.t,train.y)
            t2=np.interp(test.t,val.t,val.y)
            avg=(t1+t2)/2
            preds={'force':test.y,'t':test.t,'day1_avg':avg}
            for method,p in [('protocol_prior',protocol_target(test.t)),
                             ('day1_trial1_template',t1),('day1_average_template',avg)]:
                summary.append({'subject':s,'day':d,'method':method,'electrodes':0,**metrics(test.y,p)})
            for k in (8,16):
                model=models_by_k[k]
                val_z=model.predict(val)
                cal_z=model.predict(cal)
                test_z=model.predict(test)
                aligned,scale,_=session_align(val_z,cal_z,test_z,cfg)
                best_q,alpha,p0,fixed_q=knobs[k]
                qbase=float(np.var(np.diff(train.y)))
                fixed=kalman_fuse(aligned,model.r0,max(qbase*fixed_q,cfg.q_floor),0.,p0,cfg)
                adapt=kalman_fuse(aligned,model.r0,max(qbase*best_q,cfg.q_floor),alpha,p0,cfg)
                for method,p in [('unaligned_consensus',robust_consensus(test_z)),
                                 ('aligned_consensus',robust_consensus(aligned)),
                                 ('fixed_kf',fixed),('adaptive_kf',adapt)]:
                    summary.append({'subject':s,'day':d,'method':method,
                                    'electrodes':k,**metrics(test.y,p)})
                # Hybrid fitted to Day-1 Trial-2; NEVER tuned using later-day force.
                cal_template=np.interp(val.t,train.t,train.y)
                d1_emg=kalman_fuse(val_z,model.r0,max(qbase*best_q,cfg.q_floor),alpha,p0,cfg)
                beta=fit_hybrid_weight(val.y,cal_template,d1_emg)
                hybrid=t1+beta*(adapt-t1)
                summary.append({'subject':s,'day':d,'method':'hybrid_adaptive',
                                'electrodes':k,**metrics(test.y,hybrid)})
                preds[f'fixed_kf_{k}']=fixed;preds[f'adaptive_kf_{k}']=adapt
            traces[(s,d)]=preds
            print(f'Subject {s:02d}, Day {d:02d}/11 completed',flush=True)

    perf=pd.DataFrame(summary)
    perf.to_csv(args.out/'reimplemented_recording_metrics.csv',index=False)
    pars=pd.DataFrame(parameters)
    pars.to_csv(args.out/'reimplemented_day1_parameters.csv',index=False)
    med=perf.groupby(['subject','method','electrodes'],as_index=False).agg(r2=('r2','median'),rmse=('rmse','median'))
    med.to_csv(args.out/'reimplemented_participant_metrics.csv',index=False)
    _residual_shape_diagnostics(traces,args.out)
    print('Done. These new results are NOT the manuscript frozen numerical tables until independently reconciled.')


if __name__=='__main__':
    main()
