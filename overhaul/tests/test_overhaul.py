import os
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cemhsey_overhaul as c  # noqa: E402

REAL = Path(os.environ.get("CEMHSEY_TEST_DIR", "/mnt/user-data/uploads/CEMHSEY_full_GRASP_2026/data/_selected"))
F_S1 = REAL / "S1/D1/S1_Day1_Session1_Task2_Trial1.mat"
F_S6 = REAL / "S6/D2/S6_Day2_Session1_Task2_Trial2.mat"
have_real = F_S1.exists() and F_S6.exists()


def test_filter_is_stable_and_passes_emg_band():
    from scipy.signal import sosfreqz
    w, h = sosfreqz(c.FILTER_SOS, worN=8192, fs=c.EMG_FS)
    g = np.abs(h)
    assert np.all(np.isfinite(g))
    assert g[np.argmin(abs(w - 120))] > 0.9 and g[np.argmin(abs(w - 5))] < 0.05
    assert g[np.argmin(abs(w - 50))] < 0.05 and g[np.argmin(abs(w - 800))] < 0.05


def test_nominal_target_levels():
    t = np.array([0, 7.5, 15, 22.5, 28.0])
    assert np.allclose(c.nominal_target(t, 3), [0, 0.25, 0.5, 0.25, 0])


def test_skill_definition():
    y = np.array([0, .1, .2, .1, 0.]); prior = np.zeros(5)
    assert c.metrics(y, y, prior)["skill_vs_prior"] == 1.0


def test_known_failed_and_counts():
    assert len(c.usable_keys()) == 6005


@pytest.mark.skipif(not have_real, reason="real files not staged")
def test_real_file_record_and_reference_reproduction(tmp_path):
    t0 = time.time()
    rec = c.mat_to_record(F_S6.read_bytes())
    print(f"mat_to_record {time.time() - t0:.1f}s")
    assert rec["feat_bp"].shape == (299, 320, 5) and rec["feat_raw"].shape == (299, 320, 5)
    p = tmp_path / "x.npz"
    c.write_cache(p, rec, {"sha256": "x"})
    assert c.cache_ok(p)
    y = c.load_force_only(p, "physical")
    target = c.nominal_target(c.WINDOW_CENTERS, 2)
    r2 = 1 - np.sum((y - target) ** 2) / np.sum((y - y.mean()) ** 2)
    assert abs(r2 - 0.988573) < 1e-4          # earlier per-recording value for S6 Day 2 Trial 2
    # Band-pass variant: ZC deadband reduces noise crossings; MAV broadly preserved.
    assert np.median(rec["feat_bp"][..., 3]) < np.median(rec["feat_raw"][..., 3])


@pytest.mark.skipif(not have_real, reason="real files not staged")
def test_end_to_end_reduced_design(tmp_path, monkeypatch):
    monkeypatch.setattr(c, "SUBJECTS", (1, 2, 3))
    monkeypatch.setattr(c, "DAYS", (1, 2, 3))
    monkeypatch.setattr(c, "SESSIONS", (1,))
    monkeypatch.setattr(c, "TASKS", (2,))
    monkeypatch.setattr(c, "KNOWN_FAILED_KEYS", set())
    src = {1: F_S1, 2: F_S6, 3: F_S1}
    cache = tmp_path / "cache"
    for s in c.SUBJECTS:
        zp = tmp_path / f"GRASP_S{s}.zip"
        with zipfile.ZipFile(zp, "w", compression=zipfile.ZIP_STORED) as z:
            for d in c.DAYS:
                for r in (1, 2):
                    f = src[s] if (d + r) % 2 else (F_S6 if src[s] == F_S1 else F_S1)
                    z.write(f, f"GRASP_S{s}/S{s}_Day{d}_Session1_Task2_Trial{r}.mat")
        info = c.extract_subject(s, cache, archive={"url": str(zp), "record_id": 0, "key": zp.name},
                                 workers=2)
        assert info["cached"] == 6
        # resume: second call does nothing
        assert c.extract_subject(s, cache, archive={"url": str(zp), "record_id": 0, "key": zp.name})["extracted"] == 0
    inv = c.build_inventory(cache, tmp_path / "inv")
    assert inv["complete"] and inv["observed"] == 18
    man = pd.read_csv(tmp_path / "inv" / "recording_manifest.csv")
    assert man.sha256.notna().all() and man.crc32.notna().all()
    gate = c.run_gate(man, tmp_path / "gate")
    assert gate["timing_ok"]
    assert gate["excluded_conditions"] == []
    for variant, tb in (("bp", "physical"), ("raw", "physical"), ("bp", "normalized")):
        meta = c.run_analysis(man, tmp_path / f"res_{variant}_{tb}", variant, tb, {"plan": "x"})
        assert meta["participants"] == 3
        cohort = pd.read_csv(tmp_path / f"res_{variant}_{tb}" / "cohort_model_summary.csv")
        assert {"protocol_prior", "ridge_all_residual", "pca_ols_raw", "pooled_day1_template_loso"} <= set(cohort.model)
        assert np.allclose(cohort.loc[cohort.model == "protocol_prior", "median_participant_skill"], 0)
    # resume from checkpoints gives identical tables
    out = tmp_path / "res_bp_physical"
    before = pd.read_csv(out / "heldout_model_metrics.csv")
    c.run_analysis(man, out, "bp", "physical", {"plan": "x"})
    pd.testing.assert_frame_equal(before, pd.read_csv(out / "heldout_model_metrics.csv"))
    # changed identity moves stale checkpoints aside instead of mixing
    c.run_analysis(man, out, "bp", "physical", {"plan": "y"})
    assert any(p.name.startswith("res_bp_physical_stale_") for p in tmp_path.iterdir())


def test_tampered_member_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(c, "SUBJECTS", (1,))
    monkeypatch.setattr(c, "DAYS", (1,))
    monkeypatch.setattr(c, "SESSIONS", (1,))
    monkeypatch.setattr(c, "TASKS", (2,))
    monkeypatch.setattr(c, "KNOWN_FAILED_KEYS", set())
    monkeypatch.setattr(c.time, "sleep", lambda s: None)
    zp = tmp_path / "GRASP_S1.zip"
    payload = b"\x00" * 4096
    with zipfile.ZipFile(zp, "w", compression=zipfile.ZIP_STORED) as z:
        for r in (1, 2):
            z.writestr(f"S1_Day1_Session1_Task2_Trial{r}.mat", payload)
    raw = bytearray(zp.read_bytes())
    i = raw.find(payload)
    raw[i + 10] = 1                                  # corrupt data; CRC no longer matches
    zp.write_bytes(bytes(raw))
    with pytest.raises(RuntimeError, match="failed after retries"):
        c.extract_subject(1, tmp_path / "cache", archive={"url": str(zp), "record_id": 0, "key": zp.name})
    assert not list((tmp_path / "cache").rglob("*.npz"))


@pytest.mark.skipif(not have_real, reason="real files not staged")
def test_fallback_full_download_with_md5(tmp_path, monkeypatch):
    import hashlib, http.server, threading, functools
    monkeypatch.setattr(c, "SUBJECTS", (1,))
    monkeypatch.setattr(c, "DAYS", (1,))
    monkeypatch.setattr(c, "SESSIONS", (1,))
    monkeypatch.setattr(c, "TASKS", (2,))
    monkeypatch.setattr(c, "KNOWN_FAILED_KEYS", set())
    monkeypatch.setattr(c.time, "sleep", lambda s: None)
    srv_dir = tmp_path / "srv"; srv_dir.mkdir()
    zp = srv_dir / "GRASP_S1.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.write(F_S1, "S1_Day1_Session1_Task2_Trial1.mat")
        z.write(F_S6, "S1_Day1_Session1_Task2_Trial2.mat")
    md5 = hashlib.md5(zp.read_bytes()).hexdigest()
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(srv_dir))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/GRASP_S1.zip"
    real_open = c.open_archive
    monkeypatch.setattr(c, "open_archive", lambda u: (_ for _ in ()).throw(IOError("no range support"))
                        if u.startswith("http") else real_open(u))
    monkeypatch.setenv("NO_PROXY", "127.0.0.1"); monkeypatch.setenv("no_proxy", "127.0.0.1")
    arch = {"url": url, "record_id": 0, "key": "GRASP_S1.zip", "checksum": f"md5:{md5}", "size": zp.stat().st_size}
    info = c.extract_subject(1, tmp_path / "cache", archive=arch)
    assert info["cached"] == 2 and len(list((tmp_path / "cache").rglob("*.npz"))) == 2
    assert not (tmp_path / "tmp_download" / "GRASP_S1.zip").exists()       # deleted after success
    # wrong checksum is refused
    for p in (tmp_path / "cache").rglob("*.npz"):
        p.unlink()
    arch["checksum"] = "md5:" + "0" * 32
    with pytest.raises(RuntimeError, match="MD5"):
        c.extract_subject(1, tmp_path / "cache", archive=arch)
    srv.shutdown()


@pytest.mark.skipif(not have_real, reason="real files not staged")
def test_parallel_extraction_spawn_and_parallel_analysis(tmp_path, monkeypatch):
    import multiprocessing as mp, pickle
    from concurrent.futures import ProcessPoolExecutor
    monkeypatch.setattr(c, "SUBJECTS", (1, 2))
    monkeypatch.setattr(c, "DAYS", (1, 2, 3))
    monkeypatch.setattr(c, "SESSIONS", (1,))
    monkeypatch.setattr(c, "TASKS", (2,))
    monkeypatch.setattr(c, "KNOWN_FAILED_KEYS", set())
    cache = tmp_path / "cache"
    serial = tmp_path / "serial"
    for s in c.SUBJECTS:
        zp = tmp_path / f"GRASP_S{s}.zip"
        with zipfile.ZipFile(zp, "w") as z:
            for d in c.DAYS:
                for r in (1, 2):
                    z.write(F_S1 if (s + d + r) % 2 else F_S6, f"S{s}_Day{d}_Session1_Task2_Trial{r}.mat")
        arch = {"url": str(zp), "record_id": 0, "key": zp.name}
        with ProcessPoolExecutor(max_workers=2, mp_context=mp.get_context("spawn")) as pool:   # Windows semantics
            assert c.extract_subject(s, cache, archive=arch, workers=4, cpu_pool=pool)["cached"] == 6
        c.extract_subject(s, serial, archive=arch, workers=1)
    for p in cache.rglob("*.npz"):                     # parallel cache == serial cache
        q = serial / p.relative_to(cache)
        with np.load(p) as a, np.load(q) as b:
            assert np.array_equal(a["feat_bp"], b["feat_bp"]) and np.array_equal(a["feat_raw"], b["feat_raw"])
    c.build_inventory(cache, tmp_path / "inv")
    man = pd.read_csv(tmp_path / "inv" / "recording_manifest.csv")
    lookup = {(r.subject, r.day, r.session, r.task, r.trial): Path(r.cache_path) for r in man.itertuples()}
    pickle.dumps((lookup, c.pooled_templates(man, "physical")))   # initargs must pickle for Windows spawn
    c.run_analysis(man, tmp_path / "par", "bp", "physical", {"p": 1}, processes=2)
    c.run_analysis(man, tmp_path / "ser", "bp", "physical", {"p": 1}, processes=1)
    a = pd.read_csv(tmp_path / "par" / "heldout_model_metrics.csv")
    b = pd.read_csv(tmp_path / "ser" / "heldout_model_metrics.csv")
    pd.testing.assert_frame_equal(a, b)
