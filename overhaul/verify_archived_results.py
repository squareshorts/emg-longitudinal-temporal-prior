#!/usr/bin/env python3
"""Verify the published CEMHSEY overhaul CSVs without accessing source MAT files.

This is a post-run integrity audit; it does NOT regenerate EMG features or certify
that the original raw recordings match the source checksums in the manifest.
It reads the unchanged completed-run outputs in overhaul/results/ and exits
nonzero on a contract mismatch. It does not modify any historical result file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / 'results'
RAW_KEY = ['subject', 'day', 'session', 'task', 'trial']
EVAL_KEY = ['subject', 'session', 'task', 'day']
EXPECTED_EXCLUSION = [[2, 1]]


def check(ok: bool, message: str) -> None:
    if not bool(ok):
        raise AssertionError(message)
    print('PASS', message)


def close(a, b, msg: str, atol=1e-10) -> None:
    x = np.asarray(a, dtype=float)
    y = np.asarray(b, dtype=float)
    check(x.shape == y.shape and np.allclose(x, y, atol=atol, rtol=1e-12, equal_nan=True), msg)


def check_model_rows(d: pd.DataFrame, method_cols: list[str], context: str) -> None:
    check(not d.duplicated(EVAL_KEY + method_cols).any(), context + ': unique evaluation and model keys')
    check(set(d.subject) == set(range(1, 14)), context + ': 13 participants')
    check(set(zip(d.session, d.task)) == {(s, t) for s in range(1, 8) for t in range(1, 4)} - {(2, 1)}, context + ': only 20 eligible grasp-force cells')
    check(np.isfinite(d['skill_vs_prior']).all(), context + ': finite skill scores')
    y = 1 - (d.rmse_pct_mvc.to_numpy(float) / d.prior_rmse_pct_mvc.to_numpy(float))**2
    close(y, d.skill_vs_prior.to_numpy(float), context + ': skill follows 1 - SSE_model/SSE_prior', 1e-7)


def audit(base: Path, extra_qc: Path | None = None) -> dict:
    prov = json.loads((base / 'provenance.json').read_text(encoding='utf-8'))
    for file, key in [('cemhsey_overhaul.py', 'pipeline_sha256'),
                      ('run_all.py', 'driver_sha256'),
                      ('ANALYSIS_PLAN.md', 'analysis_plan_sha256')]:
        digest = hashlib.sha256((ROOT / file).read_bytes()).hexdigest()
        check(digest == prov[key], f'Original {file} fingerprint matches completed-run provenance')

    manifest = pd.read_csv(base / 'inventory/recording_manifest.csv')
    inventory = json.loads((base / 'inventory/inventory_summary.json').read_text(encoding='utf-8'))
    check(len(manifest) == 6005 and inventory['observed'] == 6005 and inventory['complete'], '6005 source-record manifest entries and reported inventory complete')
    check(not manifest.duplicated(RAW_KEY).any(), 'Source recording keys unique')
    check(set(manifest.subject) == set(range(1, 14)), 'All 13 biological participants represented')
    check(manifest.sha256.astype(str).str.fullmatch('[0-9a-f]{64}').all(), 'Source manifest contains SHA-256 fingerprints (raw bytes not independently checked)')

    gate = json.loads((base / 'gate/gate_summary.json').read_text(encoding='utf-8'))
    check(gate['reproduction_ok'] and gate['reproduction_max_abs_diff'] < 0.002, 'Historical protocol reference reproduction gate passed')
    check(not gate['timing_ok'] and not gate['passed'] and gate['excluded_conditions'] == EXPECTED_EXCLUSION, 'Global timing gate failed exactly one grasp-force cell; exclusion applied')
    check(gate['flagged_recordings'] == 653, '653 individually QC-flagged recordings recorded')

    ret = {'inventory': len(manifest), 'excluded_conditions': gate['excluded_conditions'], 'analysis': {}}
    for variant in ('primary_bandpass_physical', 'sensitivity_unfiltered_physical', 'sensitivity_bandpass_normalized'):
        directory = base / variant
        d = pd.read_csv(directory / 'heldout_model_metrics.csv')
        check(len(d) == 57020, variant + ': expected model-record rows')
        check_model_rows(d, ['model', 'alignment'], variant)
        part = pd.read_csv(directory / 'participant_model_summary.csv')
        p = d.groupby(['subject','model','alignment'], as_index=False).skill_vs_prior.median()
        joined = p.merge(part, on=['subject','model','alignment'], validate='one_to_one')
        check(len(joined) == len(part), variant + ': participant rows match grouping')
        close(joined.skill_vs_prior, joined.median_skill, variant + ': participant median skill reconciled')
        cohort = pd.read_csv(directory / 'cohort_model_summary.csv')
        g = part.groupby(['model','alignment'], as_index=False).agg(median_skill=('median_skill','median'), positive=('median_skill',lambda z:int((z>0).sum())))
        merged = g.merge(cohort,on=['model','alignment'],validate='one_to_one')
        check(len(merged)==len(cohort),variant + ': every cohort method represented')
        close(merged.median_skill,merged.median_participant_skill,variant + ': cohort medians reconciled')
        check((merged.positive == merged.participants_positive).all(),variant + ': positive participant counts reconciled')
        ret['analysis'][variant] = {'rows': len(d), 'methods':len(cohort), 'participants':13}

    post = pd.read_csv(base / 'posthoc_robustness/heldout_metrics.csv')
    check(len(post)==38850,'Post hoc model rows: 38850')
    check_model_rows(post,['model','scheme'],'Post hoc')
    ph_part=pd.read_csv(base / 'posthoc_robustness/participant_summary.csv')
    pg=post.groupby(['subject','model','scheme'],as_index=False).skill_vs_prior.median()
    pp=pg.merge(ph_part,on=['subject','model','scheme'],validate='one_to_one')
    check(len(pp)==len(ph_part),'Post hoc: all participant summary rows accounted for')
    close(pp.skill_vs_prior,pp.median_skill,'Post hoc: participant skill medians reconciled')
    ph_cohort=pd.read_csv(base / 'posthoc_robustness/cohort_summary.csv')
    cg=ph_part.groupby(['model','scheme'],as_index=False).agg(median_skill=('median_skill','median'),positive=('median_skill',lambda z:int((z>0).sum())))
    cc=cg.merge(ph_cohort,on=['model','scheme'],validate='one_to_one')
    check(len(cc)==len(ph_cohort),'Post hoc: every cohort model and scheme accounted for')
    close(cc.median_skill,cc.median_participant_skill,'Post hoc: cohort skill medians reconciled')
    check((cc.positive==cc.participants_positive).all(),'Post hoc: participant sign counts reconciled')
    within=ph_cohort[(ph_cohort.model=='ridge_all_residual')&(ph_cohort.scheme=='within_day')].iloc[0]
    check(within.participants_positive==13 and 0.12 < within.median_participant_skill <0.14,'Protected within-day Ridge: 13/13 positive and ~0.13 median skill')
    pca=ph_cohort[(ph_cohort.model=='pca_ols_residual')&(ph_cohort.scheme=='within_day')].iloc[0]
    pls=ph_cohort[(ph_cohort.model=='pls_all_residual')&(ph_cohort.scheme=='within_day')].iloc[0]
    check(pca.participants_positive==7 and pls.participants_positive==5,'Within-day benefit is method specific (PCA 7/13, PLS 5/13)')
    contrast=pd.read_csv(base/'posthoc_robustness/within_vs_across_contrasts.csv')
    check(len(contrast)==10 and (contrast.participants_within_better==13).all(),'Ten exploratory paired contrasts favor within-day calibration in 13/13')
    ret['analysis']['posthoc_robustness']={'rows':len(post),'methods_schemes':len(ph_cohort),'participants':13}

    if extra_qc is not None:
        qc=pd.read_csv(extra_qc)
        check(len(qc)==10,'Added post hoc timing-QC sensitivity has ten result rows')
        check(set(qc.sensitivity)=={'all_eligible','exclude_timing_flagged_test_records'},'QC sensitivity labels specify original vs post hoc exclusion')
        flagged=pd.read_csv(base/'gate/protocol_timing_qc_by_recording.csv')
        flagged=flagged[(flagged.trial==2) & (flagged.day>=2) & ((flagged.session!=2) | (flagged.task!=1))]
        nflag=int(flagged['flag'].sum())
        check(nflag==206,'QC flags among eligible held-out Trial-2 evaluation recordings: 206')
        ret['additional_qc_sensitivity']={'rows':len(qc),'flagged_heldout':nflag}

    return ret


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--results-root',type=Path,default=RESULTS)
    ap.add_argument('--additional-qc',type=Path,default=ROOT/'results/posthoc_timing_qc_sensitivity.csv')
    args=ap.parse_args()
    result=audit(args.results_root,args.additional_qc if args.additional_qc.exists() else None)
    print(json.dumps({'status':'PASS','checks':result},indent=2))


if __name__=='__main__':
    main()
