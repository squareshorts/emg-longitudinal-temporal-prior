#!/usr/bin/env python3
"""Independent report-only comparison between new and frozen EMG cohort summaries.

It never tunes, adjusts, or overwrites a frozen manuscript statistic.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd


def compare(new_csv: Path, frozen_csv: Path) -> pd.DataFrame:
    new = pd.read_csv(new_csv)
    frozen = pd.read_csv(frozen_csv)
    expected = {'subject','method','electrodes','r2','rmse'}
    if not expected.issubset(new.columns):
        raise ValueError(f'New table missing {expected-set(new.columns)}')
    if not {'method','electrodes','median_participant_r2','median_rmse'}.issubset(frozen.columns):
        raise ValueError('Frozen table has unexpected schema')
    cohort = (new.groupby(['method','electrodes'],as_index=False)
                  .agg(recomputed_r2=('r2','median'),recomputed_rmse=('rmse','median'),n=('subject','nunique')))
    joined = frozen.merge(cohort,on=['method','electrodes'],how='left',validate='one_to_one')
    joined['delta_r2'] = joined['recomputed_r2'] - joined['median_participant_r2']
    joined['delta_rmse'] = joined['recomputed_rmse'] - joined['median_rmse']
    joined['status'] = np.where(joined['recomputed_r2'].isna(), 'not_available',
                        np.where(joined['delta_r2'].abs()<5e-4, 'within_summary_tolerance','discrepant'))
    return joined


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--new',type=Path,required=True)
    ap.add_argument('--frozen',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    df=compare(a.new,a.frozen)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    df.to_csv(a.out,index=False)
    print(df.to_string(index=False))
    if (df.status != 'within_summary_tolerance').any():
        raise SystemExit('Conformance incomplete; see table. Historical numbers remain unchanged.')


if __name__=='__main__': main()
