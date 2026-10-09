#!/usr/bin/env python3
"""Locate exactly the CEMHSEY Part-I files used in this study.

Input examples: S1_Day1_Session1_Task2_Trial1.mat, ...
Only Subjects 1-10, Days 1-11, Session 1, Task 2, Trials 1-2 are included.
"""
import argparse
import re
from pathlib import Path
import pandas as pd

PAT = re.compile(r'^S(\d+)_Day(\d+)_Session(\d+)_Task(\d+)_Trial(\d+)\.mat$',re.I)


def build(root: Path) -> pd.DataFrame:
    wanted={(s,d,t) for s in range(1,11) for d in range(1,12) for t in (1,2)}
    found={}
    for path in root.rglob('*.mat'):
        m=PAT.fullmatch(path.name)
        if m is None:continue
        s,d,session,task,trial=map(int,m.groups())
        key=(s,d,trial)
        if (s,d,trial) not in wanted or session!=1 or task!=2:continue
        if key in found:raise ValueError(f'Duplicate for {key}: {found[key]} and {path}')
        found[key]=str(path.resolve())
    missing=sorted(wanted-set(found))
    if missing:raise ValueError(f'Missing {len(missing)} expected MAT files; first ten missing: {missing[:10]}')
    return pd.DataFrame([{'subject':s,'day':d,'trial':t,'mat_path':found[s,d,t]}
                         for s,d,t in sorted(wanted)])


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--data-root',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    df=build(a.data_root)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    df.to_csv(a.out,index=False)
    print(f'Wrote {len(df)} rows: {a.out}')


if __name__=='__main__':main()
