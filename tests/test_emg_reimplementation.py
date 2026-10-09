import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'reproducibility'))
from emg_reimplementation import (
    ReimplementationConfig, Trial, protocol_target, rank_electrodes,
    fit_electrodes, session_align, disagreement, kalman_fuse, fit_hybrid_weight,
    robust_consensus, tune_kalman,
)


def test_protocol_target_fixed_schedule():
    t=np.array([0.,5.,7.5,10.,20.,22.5,25.,30.])
    expected=np.array([0.,0.,.15,.30,.30,.15,0.,0.])
    np.testing.assert_allclose(protocol_target(t),expected,atol=1e-14)


def test_robust_trim_rejects_one_bad_channel():
    p=np.array([[.10,.10,.10,.10,9.], [.20,.20,.20,.20,10.]])
    np.testing.assert_allclose(robust_consensus(p),[.1,.2],atol=1e-14)


def test_session_alignment_rejects_calibration_scale_shift():
    cfg=ReimplementationConfig()
    x=np.linspace(-1,1,40)
    ref=np.column_stack([x, x+.01,x-.01,x+.015])
    cal=2.*ref+3.
    aligned,scale,c=session_align(ref,cal,cal,cfg)
    np.testing.assert_allclose(robust_consensus(aligned),robust_consensus(ref),atol=1e-12)
    assert scale==pytest.approx(.5)


def test_disagreement_has_defined_epsilon_for_identical_channels():
    cfg=ReimplementationConfig()
    z=np.full((4,8),.15)
    out=disagreement(z,cfg.epsilon)
    assert np.isfinite(out).all()
    assert not out.any()


def test_fused_filter_has_zero_initial_state_and_day1_covariance():
    cfg=ReimplementationConfig(x0=0.0)
    obs=np.array([[.1,.1],[.2,.2],[.3,.3]])
    rr=np.array([1.,1.])
    p0=.03
    fused=kalman_fuse(obs,rr,0.001,0.,p0,cfg)
    assert np.isfinite(fused).all()
    assert 0 < fused[0] < .1
    assert fused[-1] > fused[0]
    # Determinism and explicit x0/P0 effects
    np.testing.assert_array_equal(fused,kalman_fuse(obs,rr,.001,0.,p0,cfg))
    assert not np.array_equal(fused,kalman_fuse(obs,rr,.001,0.,p0+.5,cfg))


def test_day1_ridge_selection_and_no_later_day_target_in_fit():
    rng=np.random.default_rng(7)
    n=60
    force=np.linspace(0,.3,n)
    x=rng.normal(0,.01,(n,8,3))
    x[:,0,0]=force+rng.normal(0,.001,n)
    x[:,0,1]=force*2+rng.normal(0,.001,n)
    t=np.arange(n)*.1
    a=Trial(x,force,t)
    b=Trial(x+.0005,force+.0001,t)
    cfg=ReimplementationConfig()
    selected=rank_electrodes(x,force,4)
    assert 0 in selected
    models=fit_electrodes(a,b,4,cfg)
    z=models.predict(b)
    assert z.shape==(n,4)
    assert np.all(np.isfinite(models.r0))
    q,alpha,p0=tune_kalman(a,b,models,cfg)
    assert q in cfg.q_grid and alpha in cfg.alpha_grid and p0>0


def test_hybrid_parameter_constrained_to_unit_interval():
    y=np.array([0.,.3,.3,0.])
    template=np.array([0.,.1,.1,0.])
    emg=np.array([0.,.2,.2,0.])
    assert fit_hybrid_weight(y,template,emg)==pytest.approx(1.0)
