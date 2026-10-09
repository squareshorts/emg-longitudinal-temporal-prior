from pathlib import Path
import sys
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reproducibility'))
from compare_frozen_results import compare


def test_frozen_matching_only_emg_and_hybrid(tmp_path):
    rows=[]
    for s in range(1,11):
        for k in [8,16]:
            for method,r2 in [('fixed_kf',.93),('adaptive_kf',.94),('hybrid_adaptive',.98),('protocol_prior',.99)]:
                rows.append({'subject':s,'method':method,'electrodes':k,'r2':r2,'rmse':.02})
    new=tmp_path/'new.csv'
    pd.DataFrame(rows).to_csv(new,index=False)
    historical=tmp_path/'old.csv'
    pd.DataFrame([
        {'method':method,'electrodes':k,'median_participant_r2':r2,'median_rmse':.02}
        for k in [8,16] for method,r2 in [('emg_fixed_kf',.93),('emg_adaptive_kf',.94),('hybrid_adaptive',.98),('protocol_prior',.99)]
    ]).to_csv(historical,index=False)
    df=compare(new,historical)
    assert len(df)==6
    assert set(df.status)=={'within_summary_tolerance'}
