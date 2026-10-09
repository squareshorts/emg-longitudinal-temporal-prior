"""CEMHSEY-like MAT loader integration check (one small compressed synthetic MAT)."""
import sys
from pathlib import Path
import numpy as np
from scipy.io import savemat

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reproducibility'))
from emg_reimplementation import features_at_physical_times


def test_mat_shape_and_299_windows(tmp_path):
    emg=np.zeros((320,61500),dtype=np.float64)
    emg[0] = np.sin(np.arange(61500)*0.06)
    t=np.arange(6030)/200.
    force=np.interp(t,[0,5,10,20,25,30],[0,0,.3,.3,0,0])
    path=tmp_path/'S1_Day1_Session1_Task2_Trial1.mat'
    savemat(path,{'data_sEMG':emg,'data_force':force,'MVC':10.0},do_compression=True)
    trial=features_at_physical_times(path)
    assert trial.x.shape==(299,320,3)
    assert trial.y.shape==(299,)
    assert np.all(np.isfinite(trial.x))
    assert np.min(trial.x[:,:,0])>=0
