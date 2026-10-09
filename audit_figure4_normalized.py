#!/usr/bin/env python3
"""Independent full-data reconstruction and audit of manuscript Figure 4.

Run at the ROOT of the EMG repository with its dedicated .venv Python:
  .\\.venv\\Scripts\\python.exe .\\audit_figure4_normalized.py \
      --manifest .\\reproducibility\\manifest.csv \
      --out .\\results\\figure4_normalized_audit

Uses the CEMHSEY original MAT recordings referenced in the 220-row manifest;
never changes manuscript files, historical tables, or the frozen release.
This is a separately specified check, not the missing historical program.
"""
from __future__ import annotations

import argparse
import json
import sys
import hashlib
import zipfile
import platform
import importlib.metadata as metadata
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.io import loadmat
from scipy.stats import wilcoxon

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'reproducibility'))
import emg_reimplementation as emg

# Historical targets extracted from original Figure 4 plotting validations.
EXPECTED = {
    ('stage_alignment',8): (0.081697, 0.011109, 0.230108, 0.039),
    ('stage_alignment',16): (0.068871, 0.016384, 0.199991, 0.039),
    ('stage_temporal_fixed_weights',8): (0.009632, 0.007770, 0.022737, 0.0117),
    ('stage_temporal_fixed_weights',16): (0.011658, 0.006221, 0.019429, 0.0117),
    ('stage_adaptive_variance_matched_q',8): (0.0, 0.0, 0.008986, 0.25),
    ('stage_adaptive_variance_matched_q',16): (0.0, 0.0, 0.006460, 0.25),
}
STAGES = {
    'stage_alignment': ('aligned_consensus','unaligned_consensus'),
    'stage_temporal_fixed_weights': ('fixed_kf','inverse_variance_instantaneous'),
    'stage_adaptive_variance_matched_q': ('adaptive_kf','fixed_kf_matched_q'),
}
# Supplementary table of Day-1 hyperparameters: (alpha, adaptive_q, fixed_q)
SUPPLEMENTARY_PARAMS = {
    (1,8):(.1,.3,.3), (1,16):(.5,.3,.3),
    (2,8):(0,.3,.3), (2,16):(0,.3,.3),
    (3,8):(0,.3,.3), (3,16):(0,.1,.1),
    (4,8):(0,1,1), (4,16):(0,.3,.3),
    (5,8):(.5,1,.3), (5,16):(1,1,.3),
    (6,8):(0,3,3), (6,16):(0,1,1),
    (7,8):(2,.1,.1), (7,16):(.1,.03,.03),
    (8,8):(0,.3,.3), (8,16):(0,.1,.1),
    (9,8):(0,1,1), (9,16):(0,.3,.3),
    (10,8):(1,3,3), (10,16):(.1,3,3),
}
N_BOOT = 100_000
BOOT_SEED = 20260918


def normalized_trial(path: Path) -> emg.Trial:
    """Preserve the original feature extraction; change force mapping only.

    Uses the same normalized-duration convention as the published
    reproducibility/protocol_prior_benchmark.py: EMG center/(N_EMG-1),
    interpolated onto force sample indices normalized to [0,1].
    """
    m = loadmat(path, squeeze_me=True, variable_names=['data_force', 'data_sEMG'])
    if 'data_force' not in m or 'data_sEMG' not in m:
        raise KeyError(f'{path}: data_force/data_sEMG not found')
    signal = np.asarray(m['data_sEMG'], dtype=np.float64)
    if signal.ndim != 2:
        raise ValueError(f'{path}: expected 2D EMG')
    if signal.shape[0] != 320:
        if signal.shape[1] != 320:
            raise ValueError(f'{path}: expected 320 electrodes, got {signal.shape}')
        signal = signal.T
    force = np.asarray(m['data_force'], dtype=float).ravel()
    if len(force)<2 or not np.isfinite(force).all():
        raise ValueError(f'{path}: invalid force vector')
    starts = np.arange(0, signal.shape[1]-emg.WIN+1, emg.STEP, dtype=int)
    if len(starts)<2:
        raise ValueError(f'{path}: too few EMG windows')
    centers = starts + emg.WIN/2.0
    u = centers/(signal.shape[1]-1)
    y = np.interp(u, np.linspace(0,1,len(force)), force)
    x = np.empty((len(starts),320,3), dtype=np.float64)
    for k in range(320):
        signal_k = signal[k]
        window = np.lib.stride_tricks.sliding_window_view(signal_k,emg.WIN)[starts]
        x[:,k,0] = np.mean(np.abs(window), axis=-1)
        x[:,k,1] = np.sqrt(np.mean(window**2,axis=-1))
        x[:,k,2] = np.sum(np.abs(np.diff(window,axis=-1)),axis=-1)
    del signal
    return emg.Trial(x=x,y=y,t=u)


def fast_instantaneous(z: np.ndarray, r0: np.ndarray, r_floor: float) -> np.ndarray:
    # Same fixed observation variances as the fixed Kalman decoder.
    weights = 1.0/np.maximum(r0,r_floor)
    return (z@weights)/weights.sum()


def bootstrap_ci(values: np.ndarray, seed: int = BOOT_SEED) -> tuple[float,float]:
    rng = np.random.default_rng(seed)
    idx = rng.integers(len(values),size=(N_BOOT,len(values)))
    meds = np.median(values[idx],axis=1)
    a,b = np.percentile(meds,[2.5,97.5])
    return float(a), float(b)


def holm_adjust(p: np.ndarray) -> np.ndarray:
    # Family of six stage-by-electrode signed-rank tests.
    order = np.argsort(p)
    out=np.empty(len(p))
    out[order] = np.minimum(1,np.maximum.accumulate((len(p)-np.arange(len(p)))*p[order]))
    return out


def summarize(record: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    groups=['subject','electrodes','method']
    part = record.groupby(groups,as_index=False).agg(r2=('r2','median'))
    piv=part.pivot(index=['subject','electrodes'],columns='method',values='r2')
    contrasts=[]; diffs=[]
    for contrast,(a,b) in STAGES.items():
        for k in (8,16):
            p=piv.xs(k,level='electrodes')
            delta=(p[a]-p[b]).sort_index()
            if len(delta)!=10 or delta.isna().any():
                raise ValueError(f'{contrast} {k}: expected ten complete participants')
            for subject,val in delta.items():
                diffs.append({'contrast':contrast,'k':k,'subject':int(subject),'delta':float(val)})
            values=delta.to_numpy()
            lo,hi=bootstrap_ci(values)
            if np.allclose(values,0,atol=1e-13):
                raw_p=1.0
            else:
                raw_p=float(wilcoxon(values,alternative='two-sided').pvalue)
            contrasts.append({'contrast':contrast,'k':k,'median_paired_delta':float(np.median(values)),
                              'ci95_low':lo,'ci95_high':hi,'p_unadjusted':raw_p,
                              'n_positive':int(sum(values>1e-12)),'n_unchanged':int(sum(np.abs(values)<=1e-12))})
    inf=pd.DataFrame(contrasts)
    inf['p_holm']=holm_adjust(inf.p_unadjusted.to_numpy())
    return part,pd.DataFrame(diffs),inf


def audit(inf: pd.DataFrame, out: Path, params: pd.DataFrame, part: pd.DataFrame) -> None:
    rows=[]
    for _,v in inf.iterrows():
        key=(v.contrast,int(v.k))
        target=EXPECTED[key]
        rows.append({'contrast':key[0],'k':key[1],
                     'expected_delta':target[0],'observed_delta':v.median_paired_delta,
                     'abs_delta_error':abs(v.median_paired_delta-target[0]),
                     'expected_ci_low':target[1],'observed_ci_low':v.ci95_low,
                     'expected_ci_high':target[2],'observed_ci_high':v.ci95_high,
                     'expected_p_holm':target[3],'observed_p_holm':v.p_holm,
                     'median_within_0.001':abs(v.median_paired_delta-target[0])<=.001,
                     'both_ci_bounds_within_0.01':abs(v.ci95_low-target[1])<=.01 and abs(v.ci95_high-target[2])<=.01})
    ad=pd.DataFrame(rows)
    ad.to_csv(out/'figure4_comparison_with_manuscript.csv',index=False)
    checks=[]
    for _,p in params.iterrows():
        k=(int(p.subject),int(p.electrodes))
        expected=SUPPLEMENTARY_PARAMS[k]
        actual=(float(p.alpha),float(p.q_scale),float(p.fixed_q_scale))
        checks.append({'subject':k[0],'electrodes':k[1],
                       'expected_alpha':expected[0], 'actual_alpha':actual[0],
                       'expected_q':expected[1], 'actual_q':actual[1],
                       'expected_fixed_q':expected[2], 'actual_fixed_q':actual[2],
                       'all_match':bool(np.allclose(expected,actual,atol=1e-12,rtol=0))})
    param_check=pd.DataFrame(checks)
    param_check.to_csv(out/'supplementary_parameters_comparison.csv',index=False)
    np0=int((params.alpha==0).sum())
    # Manuscript subsection lists this exact Subject 6 normalized result.
    sub6=[]
    pv=part.pivot(index=['subject','electrodes'],columns='method',values='r2')
    for k,exp1,exp2 in [(8,-2.440,0.905),(16,-3.041,0.910)]:
        a=float(pv.loc[(6,k),'unaligned_consensus'])
        b=float(pv.loc[(6,k),'aligned_consensus'])
        sub6.append({'k':k,'unaligned':a,'aligned':b,'delta':b-a,
                     'reported_unaligned':exp1,'reported_aligned':exp2,
                     'within_0.02':abs(a-exp1)<.02 and abs(b-exp2)<.02})
    pd.DataFrame(sub6).to_csv(out/'subject6_alignment_check.csv',index=False)
    report = [
       '# Figure 4 independent normalized-duration audit',
       '',
       'This run independently reconstructs the Figure 4 component analysis from CEMHSEY MAT recordings.',
       'Each of the ten participants contributes a median over Days 2-11; inference uses N=10, not 100 independent observations.',
       'The pipeline does not modify any manuscript numbers.',
       '',
       f'- Alpha=0 count: {np0}/20; manuscript reports 12/20.',
       f'- Supplementary parameter sets matching individually: {int(param_check.all_match.sum())}/20.',
       f'- Cohort contrast medians within 0.001: {int(ad["median_within_0.001"].sum())}/6.',
       f'- CI bounds within 0.01: {int(ad["both_ci_bounds_within_0.01"].sum())}/6.',
       '- Historical code was not used; any small mismatch reflects a separately specified analysis and should be investigated.',
       '- Check supplementary_parameters_comparison.csv for alpha and process-noise-scale discrepancies.',
       '',
       '## Comparison with the manuscript',
       '',
       ad.to_string(index=False),
       '',
       '## Subject 6',
       '',
       pd.DataFrame(sub6).to_string(index=False),
       '',
       '## Next decision',
       '',
       'If any comparisons fail, inspect the per-participant deltas and report discrepancies explicitly; do not tune the implementation to published summaries.',
       'If all pass, Figure 4 has independent empirical support and its archive can be updated with these outputs.',
    ]
    (out/'FIGURE4_AUDIT.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    print('\n'.join(report))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    df=emg._read_manifest(args.manifest)
    files={(int(r.subject),int(r.day),int(r.trial)):Path(r.mat_path) for r in df.itertuples()}
    for path in files.values():
        if not path.is_file():
            raise FileNotFoundError(path)
    cfg=replace(emg.ReimplementationConfig(),timebase='normalized')
    manifest_hash=hashlib.sha256(args.manifest.read_bytes()).hexdigest()
    run_details={'config':asdict(cfg),'manifest_sha256':manifest_hash,
                 'python':platform.python_version(),
                 'libraries':{x:metadata.version(x) for x in ('numpy','pandas','scipy','scikit-learn')},
                 'method':'independent normalized-time reimplementation; not historical executable'}
    (args.out/'normalized_audit_config.json').write_text(json.dumps(run_details,indent=2),encoding='utf-8')
    records=[];pars=[]
    for s in range(1,11):
        train=normalized_trial(files[s,1,1]);val=normalized_trial(files[s,1,2])
        models={};tune={}
        qbase=float(np.var(np.diff(train.y)))
        for k in [8,16]:
            model=emg.fit_electrodes(train,val,k,cfg)
            best_q,alpha,p0=emg.tune_kalman(train,val,model,cfg)
            fixed_q=emg.fixed_q_scale(train,val,model,cfg)
            models[k]=model;tune[k]=(best_q,alpha,p0,fixed_q)
            pars.append({'subject':s,'electrodes':k,'alpha':alpha,'q_scale':best_q,'fixed_q_scale':fixed_q,
                         'electrodes_0_indexed':json.dumps(model.selected.tolist()),
                         'ridge_penalties':json.dumps(model.ridge.tolist())})
        for day in range(2,12):
            cal=normalized_trial(files[s,day,1]); test=normalized_trial(files[s,day,2])
            for k in [8,16]:
                model=models[k]
                qscale,alpha,p0,fixed_q=tune[k]
                test_z=model.predict(test)
                aligned,_,_=emg.session_align(model.predict(val),model.predict(cal),test_z,cfg)
                q=max(qscale*qbase,cfg.q_floor)
                q_fixed=max(fixed_q*qbase,cfg.q_floor)
                preds={
                  'unaligned_consensus':emg.robust_consensus(test_z),
                  'aligned_consensus':emg.robust_consensus(aligned),
                  'inverse_variance_instantaneous':fast_instantaneous(aligned,model.r0,cfg.r_floor),
                  'fixed_kf':emg.kalman_fuse(aligned,model.r0,q_fixed,0.,p0,cfg),
                  'fixed_kf_matched_q':emg.kalman_fuse(aligned,model.r0,q,0.,p0,cfg),
                  'adaptive_kf':emg.kalman_fuse(aligned,model.r0,q,alpha,p0,cfg),
                }
                for method,p in preds.items():
                    records.append({'subject':s,'day':day,'electrodes':k,'method':method,
                                   'r2':emg.metrics(test.y,p)['r2']})
            print(f'Figure 4 normalized: Subject {s:02d}, Day {day:02d}/11 completed',flush=True)
    records=pd.DataFrame(records)
    pars=pd.DataFrame(pars)
    records.to_csv(args.out/'normalized_recording_metrics.csv',index=False)
    pars.to_csv(args.out/'normalized_day1_parameters.csv',index=False)
    part,diff,inf=summarize(records)
    part.to_csv(args.out/'normalized_participant_metrics.csv',index=False)
    diff.to_csv(args.out/'figure4_paired_participant_differences.csv',index=False)
    inf.to_csv(args.out/'figure4_paired_inference.csv',index=False)
    audit(inf,args.out,pars,part)
    package=args.out/'FIGURE4_AUDIT.zip'
    with zipfile.ZipFile(package,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for path in sorted(args.out.iterdir()):
            if path.is_file() and path != package:
                z.write(path,arcname=path.name)
    print(f'\nUpload this file for independent review: {package.resolve()}')

if __name__=='__main__':
    main()
