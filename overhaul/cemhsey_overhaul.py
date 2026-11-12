#!/usr/bin/env python3
"""CEMHSEY GRASP overhaul pipeline: single-pass extraction, QC gate and analysis.

Stages
  extract   Stream each GRASP MAT member once from Zenodo (HTTP range reads),
            verify its ZIP CRC-32, record its SHA-256, compute window features for
            two EMG variants ("bp": 20-450 Hz band-pass + 50 Hz comb notch,
            "raw": unfiltered) and store features + raw force in a compact NPZ
            cache. The raw MAT bytes are never written to disk.
  inventory Validate the cache against the 6,005-recording design.
  gate      Protocol-timing QC for every grasp/force level and a reproduction
            check of the protocol-prior error on the condition analysed earlier.
  analyze   Prior-referenced evaluation of templates and EMG decoders.

Design: Day-1 Trial 1 trains; Day-1 Trial 2 tunes; Days 2-11 Trial 1 is used
only for label-free affine alignment; Days 2-11 Trial 2 is held out. Force in the
source files is already MVC-normalized.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import time
import warnings
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import numpy as np
import pandas as pd
from scipy.io import loadmat
from scipy.signal import butter, iirnotch, sosfiltfilt, tf2sos
from scipy.stats import linregress, wilcoxon
from sklearn.cross_decomposition import PLSRegression
from sklearn.decomposition import PCA
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.preprocessing import StandardScaler

PIPELINE_VERSION = "overhaul-1.0"
SUBJECTS = tuple(range(1, 14))
DAYS = tuple(range(1, 12))
SESSIONS = tuple(range(1, 8))
TASKS = tuple(range(1, 4))
TRIALS = (1, 2)
KNOWN_FAILED_KEYS = {(4, 1, 1, 1, 1)}   # listed as failed in Yang et al. (2025)
GRASPS = {1: "Cyl", 2: "Lum", 3: "Obl", 4: "IntPP", 5: "2F_PpP", 6: "3F_PpP", 7: "LatP"}
TASK_PERCENT = {1: 10, 2: 30, 3: 50}
TASK_AMPLITUDE = {k: v / 100.0 for k, v in TASK_PERCENT.items()}
EMG_FS = 2048.0
FORCE_FS = 200.0
N_CH = 320
WINDOW = 410
STEP = 205
N_WINDOWS = 299
FEATURES = ("MAV", "RMS", "WL", "ZC", "SSC")
VARIANTS = ("bp", "raw")
BANDPASS_HZ = (20.0, 450.0)
NOTCH_HZ = (50.0, 100.0, 150.0, 200.0, 250.0, 300.0, 350.0, 400.0)
NOTCH_Q = 30.0
PHASES = {"rest_pre": (0.0, 5.0), "ramp_up": (5.0, 10.0), "hold": (10.0, 20.0),
          "ramp_down": (20.0, 25.0), "rest_post": (25.0, 30.1)}
RIDGE_ALPHAS = (0.01, 0.1, 1.0, 10.0, 100.0, 1000.0, 10000.0)
PLS_COMPONENTS = (2, 5, 10, 20, 40, 80)
PCA_COMPONENTS = (5, 10, 20, 50, 100, 150)
N_BOOT = 10000
SEED = 20261111
FILENAME_RE = re.compile(
    r"^S(?P<subject>\d+)_Day(?P<day>\d+)_Session(?P<session>\d+)_Task(?P<task>\d+)_Trial(?P<trial>\d+)\.mat$",
    re.IGNORECASE)
ZENODO_RECORDS = {"I": [14224328], "II": [15070187, 14272463]}

# Protocol-prior R2 (median over Days 2-11 Trial 2, physical time) from the earlier
# Session 1 / Task 2 analysis. Used only as a data-reading correctness check.
REFERENCE_PRIOR_R2_G1T2 = {1: 0.995723, 2: 0.995835, 3: 0.993159, 4: 0.995260, 5: 0.993918,
                           6: 0.990882, 7: 0.988888, 8: 0.993346, 9: 0.990523, 10: 0.985271}


def log(msg: str) -> None:
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}", flush=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    os.replace(tmp, path)


def parse_filename(name: str):
    m = FILENAME_RE.match(name)
    return None if m is None else tuple(int(m.group(k)) for k in ("subject", "day", "session", "task", "trial"))


def expected_keys() -> set:
    return {(s, d, g, t, r) for s in SUBJECTS for d in DAYS for g in SESSIONS for t in TASKS for r in TRIALS}


def usable_keys() -> set:
    return expected_keys() - KNOWN_FAILED_KEYS


def cache_path(cache_root: Path, key) -> Path:
    s, d, g, t, r = key
    return cache_root / f"S{s:02d}" / f"S{s:02d}_D{d:02d}_G{g}_T{t}_R{r}.npz"


# --------------------------------------------------------------------------- features

def _filter_sos():
    sos = [butter(4, BANDPASS_HZ, btype="bandpass", fs=EMG_FS, output="sos")]
    for f0 in NOTCH_HZ:
        b, a = iirnotch(f0, NOTCH_Q, fs=EMG_FS)
        sos.append(tf2sos(b, a))
    return np.vstack(sos)


FILTER_SOS = _filter_sos()


def window_features(emg: np.ndarray, thresholds: np.ndarray | None = None) -> np.ndarray:
    """emg: channels x samples. Returns windows x channels x 5 [MAV,RMS,WL,ZC,SSC] float32.

    ZC/SSC use an amplitude deadband (Hudgins et al.) when thresholds are given.
    """
    starts = np.arange(N_WINDOWS) * STEP
    if emg.shape[1] < starts[-1] + WINDOW:
        raise ValueError(f"EMG too short: {emg.shape[1]} samples")
    out = np.empty((N_WINDOWS, emg.shape[0], 5), dtype=np.float32)
    for ch in range(emg.shape[0]):
        w = np.lib.stride_tricks.sliding_window_view(emg[ch], WINDOW)[starts]
        dw = np.diff(w, axis=1)
        thr = 0.0 if thresholds is None else float(thresholds[ch])
        out[:, ch, 0] = np.mean(np.abs(w), axis=1)
        out[:, ch, 1] = np.sqrt(np.mean(w * w, axis=1))
        out[:, ch, 2] = np.sum(np.abs(dw), axis=1)
        zc = ((w[:, :-1] * w[:, 1:]) < 0) & (np.abs(dw) >= thr)
        out[:, ch, 3] = zc.sum(axis=1)
        ssc = ((dw[:, :-1] * dw[:, 1:]) < 0) & ((np.abs(dw[:, :-1]) >= thr) | (np.abs(dw[:, 1:]) >= thr))
        out[:, ch, 4] = ssc.sum(axis=1)
    if not np.isfinite(out).all():
        raise ValueError("non-finite features")
    return out


def noise_thresholds(emg: np.ndarray) -> np.ndarray:
    """Per-channel deadband: 10th percentile of window RMS (quietest windows).

    Label-free and protocol-free: uses neither force nor the task timing.
    """
    starts = np.arange(N_WINDOWS) * STEP
    thr = np.empty(emg.shape[0])
    for ch in range(emg.shape[0]):
        w = np.lib.stride_tricks.sliding_window_view(emg[ch], WINDOW)[starts]
        thr[ch] = np.percentile(np.sqrt(np.mean(w * w, axis=1)), 10)
    return thr


def mat_to_record(raw_bytes: bytes) -> dict:
    m = loadmat(io.BytesIO(raw_bytes), squeeze_me=True, variable_names=["data_force", "data_sEMG", "MVC"])
    for k in ("data_force", "data_sEMG", "MVC"):
        if k not in m:
            raise KeyError(f"missing {k}")
    force = np.asarray(m["data_force"], dtype=np.float64).reshape(-1)
    emg = np.asarray(m["data_sEMG"], dtype=np.float64)
    if emg.ndim != 2:
        raise ValueError(f"data_sEMG shape {emg.shape}")
    if emg.shape[0] != N_CH and emg.shape[1] == N_CH:
        emg = emg.T
    if emg.shape[0] != N_CH:
        raise ValueError(f"expected 320 channels, got {emg.shape}")
    if not (np.isfinite(force).all() and np.isfinite(emg).all()):
        raise ValueError("non-finite samples")
    mvc = float(np.ravel(m["MVC"])[0])
    feats_raw = window_features(emg)
    feats_bp = np.empty_like(feats_raw)
    for lo in range(0, N_CH, 32):          # chunked to bound memory; filtering is per channel
        bp = sosfiltfilt(FILTER_SOS, emg[lo:lo + 32], axis=1)
        feats_bp[:, lo:lo + 32] = window_features(bp, noise_thresholds(bp))
    return {"force": force.astype(np.float32), "mvc": mvc, "emg_n": int(emg.shape[1]),
            "force_n": int(force.size), "feat_raw": feats_raw, "feat_bp": feats_bp}


def write_cache(path: Path, rec: dict, meta: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as f:
        np.savez(f, force=rec["force"], feat_raw=rec["feat_raw"], feat_bp=rec["feat_bp"],
                 mvc=np.float64(rec["mvc"]), emg_n=np.int64(rec["emg_n"]), force_n=np.int64(rec["force_n"]),
                 meta=np.array(json.dumps(meta)))
    os.replace(tmp, path)


def cache_ok(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        with np.load(path, allow_pickle=False) as z:
            return z["feat_bp"].shape == (N_WINDOWS, N_CH, 5) and z["feat_raw"].shape == (N_WINDOWS, N_CH, 5)
    except Exception:
        return False


# --------------------------------------------------------------------------- extraction

def resolve_archive(subject: int) -> dict:
    """Return {'url', 'record_id', 'key', 'checksum'} for GRASP_S{subject}.zip on Zenodo."""
    import requests
    part = "I" if subject <= 10 else "II"
    label = f"part {part}".lower()
    records = []
    for rid in ZENODO_RECORDS[part]:
        for attempt in range(5):
            try:
                r = requests.get(f"https://zenodo.org/api/records/{rid}", timeout=60,
                                 headers={"User-Agent": "CEMHSEY-overhaul/1.0"})
                if r.status_code == 200:
                    rec = r.json()
                    title = rec.get("metadata", {}).get("title", "")
                    if "CEMHSEY" in title and label in title.lower():
                        records.append(rec)
                break
            except Exception as exc:  # network hiccup
                log(f"Zenodo record {rid} attempt {attempt + 1}: {exc}")
                time.sleep(30 * (attempt + 1))
    if not records:
        raise RuntimeError(f"Could not resolve CEMHSEY Part {part} on Zenodo")
    rec = sorted(records, key=lambda x: x.get("updated", ""), reverse=True)[0]
    want = f"GRASP_S{subject}.zip".casefold()
    for f in rec.get("files", []):
        if f.get("key", "").casefold() == want:
            links = f.get("links", {})
            url = links.get("content") or links.get("download")
            if not url:
                from urllib.parse import quote
                url = f"https://zenodo.org/api/records/{rec.get('id')}/files/{quote(f.get('key', ''), safe='')}/content"
            return {"url": url, "record_id": rec.get("id"), "key": f.get("key"),
                    "checksum": f.get("checksum"), "size": f.get("size")}
    raise RuntimeError(f"{want} not found in Zenodo record {rec.get('id')}")


def open_archive(url: str):
    if url.startswith("http"):
        from remotezip import RemoteZip
        return RemoteZip(url)
    return zipfile.ZipFile(url)


def _member_index(zf) -> dict:
    out = {}
    for name in zf.namelist():
        key = parse_filename(PurePosixPath(name).name)
        if key is not None and key not in KNOWN_FAILED_KEYS:
            if key in out:
                raise RuntimeError(f"duplicate member for {key}: {out[key]} and {name}")
            out[key] = name
    return out


def _compute(pool, raw: bytes) -> dict:
    return mat_to_record(raw) if pool is None else pool.submit(mat_to_record, raw).result()


def extract_subject(subject: int, cache_root: Path, archive: dict | None = None,
                    local_roots: list[Path] | None = None, workers: int = 3, cpu_pool=None) -> dict:
    """Populate the cache for one participant. Resumable; never stores raw MAT bytes."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    expected = {k for k in usable_keys() if k[0] == subject}
    todo = sorted(k for k in expected if not cache_ok(cache_path(cache_root, k)))
    if not todo:
        log(f"S{subject}: cache complete ({len(expected)} recordings)")
        return {"subject": subject, "extracted": 0, "cached": len(expected)}

    # Reuse any original local MAT copies first (no download needed).
    local = {}
    for root in local_roots or []:
        if root.exists():
            for p in root.rglob(f"S{subject}_Day*_Session*_Task*_Trial*.mat"):
                k = parse_filename(p.name)
                if k in expected and k[0] == subject:
                    local[k] = p
    n_done = 0
    def do_local(k):
        raw = local[k].read_bytes()
        rec = _compute(cpu_pool, raw)
        write_cache(cache_path(cache_root, k), rec, {
            "source": "local_copy", "path": str(local[k]), "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw), "pipeline": PIPELINE_VERSION})
    from concurrent.futures import ThreadPoolExecutor as _TPE
    with _TPE(max_workers=max(1, workers)) as tp:
        for _ in tp.map(do_local, [k for k in todo if k in local]):
            n_done += 1
    todo = [k for k in todo if k not in local]
    if not todo:
        log(f"S{subject}: completed from local copies ({n_done})")
        return {"subject": subject, "extracted": n_done, "cached": len(expected)}

    archive = archive or resolve_archive(subject)
    try:
        n_done += _process_archive(subject, archive, archive["url"], todo, expected, cache_root, workers,
                                   "zenodo_range" if str(archive["url"]).startswith("http") else "local_zip",
                                   cpu_pool)
    except Exception as exc:
        if not str(archive["url"]).startswith("http"):
            raise
        log(f"S{subject}: range streaming failed ({exc!r}); falling back to a full archive download")
        zpath = download_full(archive, cache_root.parent / "tmp_download")
        todo = sorted(k for k in expected if not cache_ok(cache_path(cache_root, k)))
        n_done += _process_archive(subject, archive, str(zpath), todo, expected, cache_root, workers,
                                   "zenodo_full_download", cpu_pool)
        zpath.unlink(missing_ok=True)          # kept only if processing failed, for resume
    return {"subject": subject, "extracted": n_done, "cached": len(expected)}


def _md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def download_full(archive: dict, tmp_dir: Path) -> Path:
    """Resumable whole-archive download verified against Zenodo's published MD5."""
    import requests
    tmp_dir.mkdir(parents=True, exist_ok=True)
    dest = tmp_dir / archive["key"]
    part = dest.with_name(dest.name + ".part")
    want = str(archive.get("checksum") or "").split(":")[-1].lower()
    size = int(archive.get("size") or 0)
    if dest.exists() and (not want or _md5(dest) == want):
        return dest
    for attempt in range(10):
        try:
            have = part.stat().st_size if part.exists() else 0
            if size and have > size:
                part.unlink(); have = 0
            headers = {"User-Agent": "CEMHSEY-overhaul/1.0"}
            if have:
                headers["Range"] = f"bytes={have}-"
            with requests.get(archive["url"], headers=headers, stream=True, timeout=120) as r:
                if r.status_code == 206 and have:
                    mode = "ab"
                elif r.status_code == 200:
                    mode = "wb"
                else:
                    raise IOError(f"HTTP {r.status_code}")
                with open(part, mode) as f:
                    for chunk in r.iter_content(chunk_size=8 << 20):
                        f.write(chunk)
            if size and part.stat().st_size != size:
                raise IOError(f"incomplete: {part.stat().st_size} of {size} bytes")
            break
        except Exception as exc:
            log(f"{archive['key']} download attempt {attempt + 1}: {exc!r}")
            time.sleep(min(900, 60 * 2 ** attempt))
    else:
        raise RuntimeError(f"{archive['key']}: full download failed")
    if want:
        got = _md5(part)
        if got != want:
            part.unlink()
            raise RuntimeError(f"{archive['key']}: MD5 {got} does not match Zenodo {want}")
    os.replace(part, dest)
    log(f"{archive['key']}: downloaded and MD5-verified ({dest.stat().st_size / 1e9:.1f} GB)")
    return dest


def _process_archive(subject, archive, url, todo, expected, cache_root, workers, source, cpu_pool=None) -> int:
    from concurrent.futures import ThreadPoolExecutor, as_completed
    log(f"S{subject}: {len(todo)} recordings via {source} from {archive['key']} (record {archive['record_id']})")
    n_done = 0
    with open_archive(url) as zf:
        index = _member_index(zf)
        crc = {k: zf.getinfo(n).CRC for k, n in index.items()}
        index_size = {k: zf.getinfo(n).file_size for k, n in index.items()}
    missing = [k for k in todo if k not in index]
    if missing:
        raise RuntimeError(f"S{subject}: {len(missing)} expected recordings absent from archive, e.g. {missing[:3]}")
    extra = sorted(k for k in index if k not in expected)
    if extra:
        raise RuntimeError(f"S{subject}: archive holds unexpected recordings, e.g. {extra[:3]}")

    import threading
    tls = threading.local()
    opened, lock = [], threading.Lock()

    def archive_handle():
        # One HTTP-range archive handle per worker thread: one request per member.
        if getattr(tls, "zf", None) is None:
            tls.zf = open_archive(url)
            with lock:
                opened.append(tls.zf)
        return tls.zf

    def work(k):
        last = None
        for attempt in range(6):
            try:
                raw = archive_handle().read(index[k])   # zipfile verifies CRC-32 on read
                if len(raw) != index_size[k]:
                    raise IOError(f"size mismatch for {index[k]}")
                rec = _compute(cpu_pool, raw)
                write_cache(cache_path(cache_root, k), rec, {
                    "source": source, "record_id": archive["record_id"], "archive": archive["key"],
                    "member": index[k], "crc32": crc[k], "sha256": hashlib.sha256(raw).hexdigest(),
                    "bytes": len(raw), "pipeline": PIPELINE_VERSION})
                return k
            except Exception as exc:
                last = exc
                log(f"{index[k]} attempt {attempt + 1} failed: {exc!r}")
                try:
                    tls.zf.close()
                except Exception:
                    pass
                tls.zf = None
                time.sleep(min(600, 20 * 2 ** attempt))
        raise RuntimeError(f"{index[k]} failed after retries: {last}")

    t0 = time.time()
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(work, k) for k in todo]
            for i, fut in enumerate(as_completed(futures), 1):
                fut.result()
                n_done += 1
                if i % 25 == 0 or i == len(todo):
                    rate = i / max(time.time() - t0, 1e-9) * 3600
                    log(f"S{subject}: {i}/{len(todo)} streamed ({rate:.0f} recordings/h)")
    finally:
        for z in opened:
            try:
                z.close()
            except Exception:
                pass
    return n_done


# --------------------------------------------------------------------------- inventory

def build_inventory(cache_root: Path, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for p in sorted(cache_root.rglob("S*_D*_G*_T*_R*.npz")):
        m = re.match(r"S(\d+)_D(\d+)_G(\d+)_T(\d+)_R(\d+)\.npz$", p.name)
        if not m:
            continue
        key = tuple(int(x) for x in m.groups())
        with np.load(p, allow_pickle=False) as z:
            meta = json.loads(str(z["meta"]))
            rows.append({"subject": key[0], "day": key[1], "session": key[2], "task": key[3], "trial": key[4],
                         "grasp": GRASPS.get(key[2]), "target_pct_mvc": TASK_PERCENT.get(key[3]),
                         "cache_path": str(p.resolve()), "mvc": float(z["mvc"]), "emg_n": int(z["emg_n"]),
                         "force_n": int(z["force_n"]), "source": meta.get("source"),
                         "record_id": meta.get("record_id"), "member": meta.get("member", meta.get("path")),
                         "crc32": meta.get("crc32"), "sha256": meta.get("sha256"), "bytes": meta.get("bytes")})
    man = pd.DataFrame(rows)
    keys = set(map(tuple, man[["subject", "day", "session", "task", "trial"]].to_numpy())) if len(man) else set()
    missing = sorted(usable_keys() - keys)
    extra = sorted(keys - usable_keys())
    dup = int(man.duplicated(["subject", "day", "session", "task", "trial"]).sum()) if len(man) else 0
    man.to_csv(out_dir / "recording_manifest.csv", index=False)
    summary = {"expected_usable": len(usable_keys()), "observed": len(keys), "missing": len(missing),
               "unexpected": len(extra), "duplicates": dup, "missing_examples": missing[:20],
               "complete": not missing and not extra and dup == 0,
               "total_source_bytes": int(man["bytes"].sum()) if len(man) else 0}
    atomic_json(out_dir / "inventory_summary.json", summary)
    return summary


# --------------------------------------------------------------------------- trials

def nominal_target(t: np.ndarray, task: int) -> np.ndarray:
    t = np.asarray(t, float)
    amp = TASK_AMPLITUDE[int(task)]
    y = np.zeros_like(t)
    up = (t >= 5.0) & (t < 10.0); hold = (t >= 10.0) & (t < 20.0); down = (t >= 20.0) & (t < 25.0)
    y[up] = amp * (t[up] - 5.0) / 5.0
    y[hold] = amp
    y[down] = amp * (25.0 - t[down]) / 5.0
    return y


WINDOW_CENTERS = (np.arange(N_WINDOWS) * STEP + WINDOW / 2.0) / EMG_FS


def force_at_windows(force: np.ndarray, emg_n: int, timebase: str) -> np.ndarray:
    if timebase == "physical":
        return np.interp(WINDOW_CENTERS, np.arange(force.size) / FORCE_FS, force)
    if timebase == "normalized":   # stretch force record onto the EMG record duration
        u = (np.arange(N_WINDOWS) * STEP + WINDOW / 2.0) / max(emg_n - 1, 1)
        return np.interp(u, np.linspace(0.0, 1.0, force.size), force)
    raise ValueError(timebase)


@dataclass
class Trial:
    x3: np.ndarray
    x4: np.ndarray
    y: np.ndarray
    target: np.ndarray
    t: np.ndarray
    mvc: float
    force_n: int
    emg_n: int


def load_trial(path: Path, task: int, variant: str, timebase: str) -> Trial:
    with np.load(path, allow_pickle=False) as z:
        f = z[f"feat_{variant}"].astype(np.float64)
        force = z["force"].astype(np.float64)
        emg_n = int(z["emg_n"]); force_n = int(z["force_n"]); mvc = float(z["mvc"])
    y = force_at_windows(force, emg_n, timebase)
    return Trial(x3=f[:, :, [0, 1, 2]], x4=f[:, :, [0, 3, 4, 2]], y=y,
                 target=nominal_target(WINDOW_CENTERS, task), t=WINDOW_CENTERS.copy(),
                 mvc=mvc, force_n=force_n, emg_n=emg_n)


def load_force_only(path: Path, timebase: str) -> np.ndarray:
    with np.load(path, allow_pickle=False) as z:
        return force_at_windows(z["force"].astype(np.float64), int(z["emg_n"]), timebase)


# --------------------------------------------------------------------------- gate

def crossing_times(y: np.ndarray, t: np.ndarray, level: float):
    above = np.where(y > level)[0]
    if above.size == 0:
        return np.nan, np.nan
    i, j = above[0], above[-1]
    up = t[i] if i == 0 else t[i - 1] + (level - y[i - 1]) * (t[i] - t[i - 1]) / (y[i] - y[i - 1])
    dn = t[j] if j == len(y) - 1 else t[j] + (y[j] - level) * (t[j + 1] - t[j]) / (y[j] - y[j + 1])
    return float(up), float(dn)


def run_gate(manifest: pd.DataFrame, out_dir: Path, tol_s: float = 0.5, ratio_band=(0.8, 1.2),
             r2_tol: float = 0.002) -> dict:
    """Fails if any grasp/force level departs from the nominal trapezoid, or the
    protocol-prior error on Session 1 / Task 2 does not reproduce the earlier values."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for r in manifest.itertuples():
        with np.load(r.cache_path, allow_pickle=False) as z:
            force = z["force"].astype(float)
        t = np.arange(force.size) / FORCE_FS
        amp = TASK_AMPLITUDE[int(r.task)]
        hold = float(np.mean(force[(t >= 10) & (t < 20)]))
        up, dn = crossing_times(force, t, 0.5 * amp)
        y = load_force_only(Path(r.cache_path), "physical")
        target = nominal_target(WINDOW_CENTERS, int(r.task))
        sst = np.sum((y - y.mean()) ** 2)
        rows.append({"subject": r.subject, "day": r.day, "session": r.session, "task": r.task, "trial": r.trial,
                     "hold_mean": hold, "hold_ratio": hold / amp, "up50_s": up, "down50_s": dn,
                     "force_duration_s": force.size / FORCE_FS, "emg_duration_s": r.emg_n / EMG_FS,
                     "prior_r2": float(1 - np.sum((y - target) ** 2) / sst) if sst > 0 else np.nan,
                     "prior_rmse": float(np.sqrt(np.mean((y - target) ** 2)))})
    qc = pd.DataFrame(rows)
    qc["flag"] = ((qc.up50_s - 7.5).abs() > 1.0) | ((qc.down50_s - 22.5).abs() > 1.0) | \
                 (qc.hold_ratio < 0.5) | (qc.hold_ratio > 1.5) | qc.up50_s.isna()
    qc.to_csv(out_dir / "protocol_timing_qc_by_recording.csv", index=False)
    cond = qc.groupby(["session", "task"], as_index=False).agg(
        up50_median=("up50_s", "median"), down50_median=("down50_s", "median"),
        hold_ratio_median=("hold_ratio", "median"), prior_rmse_median=("prior_rmse", "median"),
        flagged=("flag", "sum"), n=("flag", "size"))
    cond["ok"] = ((cond.up50_median - 7.5).abs() <= tol_s) & ((cond.down50_median - 22.5).abs() <= tol_s) & \
                 cond.hold_ratio_median.between(*ratio_band)
    cond.to_csv(out_dir / "protocol_timing_qc_by_condition.csv", index=False)
    ref = qc[(qc.session == 1) & (qc.task == 2) & (qc.trial == 2) & (qc.day >= 2)]
    rep = ref.groupby("subject").prior_r2.median()
    repro = [{"subject": int(s), "reference_r2": v, "recomputed_r2": float(rep.get(s, np.nan)),
              "abs_diff": abs(float(rep.get(s, np.nan)) - v)} for s, v in REFERENCE_PRIOR_R2_G1T2.items()
             if s in rep.index]
    rep_df = pd.DataFrame(repro)
    rep_df.to_csv(out_dir / "reference_reproduction.csv", index=False)
    repro_ok = len(rep_df) > 0 and bool((rep_df.abs_diff <= r2_tol).all())
    summary = {"timing_ok": bool(cond.ok.all()), "failing_conditions": cond[~cond.ok].to_dict("records"),
               "flagged_recordings": int(qc.flag.sum()), "n_recordings": int(len(qc)),
               "reproduction_ok": repro_ok, "reproduction_max_abs_diff": float(rep_df.abs_diff.max()) if len(rep_df) else None,
               "force_minus_emg_duration_s_median": float((qc.force_duration_s - qc.emg_duration_s).median()),
               "passed": bool(cond.ok.all()) and repro_ok,
               "excluded_conditions": [[int(a), int(b)] for a, b in cond.loc[~cond.ok, ["session", "task"]].to_numpy()]}
    atomic_json(out_dir / "gate_summary.json", summary)
    return summary


# --------------------------------------------------------------------------- models

def flat_x(trial: Trial, fs: str, channels=None) -> np.ndarray:
    x = trial.x3 if fs == "x3" else trial.x4
    if channels is not None:
        x = x[:, channels, :]
    return x.reshape(x.shape[0], -1)


def _targets(train, val, mode):
    if mode == "raw":
        return train.y, val.y
    return train.y - train.target, val.y - val.target


def fit_ridge(train, val, mode, channels=None):
    ytr, yval = _targets(train, val, mode)
    sc = StandardScaler().fit(flat_x(train, "x3", channels))
    a = sc.transform(flat_x(train, "x3", channels)); b = sc.transform(flat_x(val, "x3", channels))
    best = None
    for alpha in RIDGE_ALPHAS:
        m = Ridge(alpha=alpha).fit(a, ytr)
        mse = float(np.mean((yval - m.predict(b)) ** 2))
        if best is None or mse < best[0]:
            best = (mse, alpha, m)
    _, alpha, m = best
    return (lambda tr: m.predict(sc.transform(flat_x(tr, "x3", channels)))), alpha


def fit_pls(train, val, mode):
    ytr, yval = _targets(train, val, mode)
    xtr, xval = flat_x(train, "x3"), flat_x(val, "x3")
    best = None
    for nc in PLS_COMPONENTS:
        if nc >= min(xtr.shape):
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m = PLSRegression(n_components=nc, scale=True, max_iter=1000).fit(xtr, ytr)
            mse = float(np.mean((yval - m.predict(xval).ravel()) ** 2))
        if best is None or mse < best[0]:
            best = (mse, nc, m)
    _, nc, m = best
    return (lambda tr: m.predict(flat_x(tr, "x3")).ravel()), nc


def fit_pca_ols(train, val, mode):
    """PCA + OLS with the component count tuned on Day-1 Trial 2."""
    ytr, yval = _targets(train, val, mode)
    sc = StandardScaler().fit(flat_x(train, "x4"))
    a = sc.transform(flat_x(train, "x4")); b = sc.transform(flat_x(val, "x4"))
    pca = PCA(n_components=max(PCA_COMPONENTS), svd_solver="randomized", random_state=SEED).fit(a)
    za, zb = pca.transform(a), pca.transform(b)
    best = None
    for k in PCA_COMPONENTS:
        m = LinearRegression().fit(za[:, :k], ytr)
        mse = float(np.mean((yval - m.predict(zb[:, :k])) ** 2))
        if best is None or mse < best[0]:
            best = (mse, k, m)
    _, k, m = best
    return (lambda tr: m.predict(pca.transform(sc.transform(flat_x(tr, "x4")))[:, :k])), k


def select_channels(train: Trial, target: np.ndarray, k: int) -> np.ndarray:
    mav = train.x3[:, :, 0]
    yc = target - target.mean(); xc = mav - mav.mean(0, keepdims=True)
    den = np.sqrt((xc * xc).sum(0) * (yc * yc).sum())
    corr = np.divide(yc @ xc, den, out=np.zeros(mav.shape[1]), where=den > 0)
    return np.lexsort((np.arange(mav.shape[1]), -np.abs(corr)))[:k]


def fit_models(train: Trial, val: Trial) -> dict:
    models = {}
    for mode in ("raw", "residual"):
        for name, fn in (("ridge_all", fit_ridge), ("pls_all", fit_pls), ("pca_ols", fit_pca_ols)):
            pred, hp = fn(train, val, mode)
            models[f"{name}_{mode}"] = {"predict": pred, "mode": mode, "hyperparameter": hp}
    resid = train.y - train.target
    for k in (8, 16):
        ch = select_channels(train, resid, k)
        pred, hp = fit_ridge(train, val, "residual", channels=ch)
        models[f"ridge_{k}_residual"] = {"predict": pred, "mode": "residual", "hyperparameter": hp,
                                         "selected_channels": ch.tolist()}
    return models


def robust_affine(reference, calibration, test):
    rm, cm = np.median(reference), np.median(calibration)
    ri = np.subtract(*np.percentile(reference, [75, 25])); ci = np.subtract(*np.percentile(calibration, [75, 25]))
    scale = ri / ci if ci > 1e-8 and np.isfinite(ci) and ri > 0 else 1.0
    return rm + scale * (np.asarray(test, float) - cm)


def metrics(y, pred, prior) -> dict:
    e = y - pred; e0 = y - prior; res = y - prior
    sst = np.sum((y - y.mean()) ** 2); sse = np.sum(e ** 2); sse0 = np.sum(e0 ** 2)
    rsst = np.sum((res - res.mean()) ** 2)
    return {"r2": float(1 - sse / sst) if sst > 0 else np.nan,
            "rmse_pct_mvc": float(100 * np.sqrt(np.mean(e ** 2))),
            "mae_pct_mvc": float(100 * np.mean(np.abs(e))),
            "bias_pct_mvc": float(100 * np.mean(pred - y)),
            "prior_rmse_pct_mvc": float(100 * np.sqrt(np.mean(e0 ** 2))),
            "skill_vs_prior": float(1 - sse / sse0) if sse0 > 0 else np.nan,
            "residual_r2": float(1 - sse / rsst) if rsst > 0 else np.nan}


def phase_mask(t, phase):
    lo, hi = PHASES[phase]
    return (t >= lo) & (t < hi)


def bootstrap_median_ci(values, seed=SEED, n_boot=N_BOOT):
    v = np.asarray(values, float); v = v[np.isfinite(v)]
    if v.size == 0:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    meds = np.median(v[rng.integers(0, v.size, (n_boot, v.size))], axis=1)
    return float(np.percentile(meds, 2.5)), float(np.percentile(meds, 97.5))


def safe_wilcoxon(v):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    if v.size < 2 or not np.any(np.abs(v) > 1e-12):
        return np.nan
    try:
        return float(wilcoxon(v).pvalue)
    except ValueError:
        return np.nan


# --------------------------------------------------------------------------- analysis

def pooled_templates(manifest: pd.DataFrame, timebase: str) -> dict:
    d1 = manifest[manifest.day == 1]
    per = {}
    for r in d1.itertuples():
        per.setdefault((r.subject, r.session, r.task), []).append(load_force_only(Path(r.cache_path), timebase))
    per = {k: np.mean(v, axis=0) for k, v in per.items()}
    out = {}
    for s in SUBJECTS:
        for g in SESSIONS:
            for t in TASKS:
                others = [per[(o, g, t)] for o in SUBJECTS if o != s and (o, g, t) in per]
                out[(s, g, t)] = np.mean(others, axis=0)
    return out


def analyze_condition(key, lookup, pooled, variant, timebase):
    s, g, task = key
    L = lambda d, r: load_trial(lookup[(s, d, g, task, r)], task, variant, timebase)
    d1t1 = L(1, 1) if (s, 1, g, task, 1) in lookup else None
    d1t2 = L(1, 2)
    models = fit_models(d1t1, d1t2) if d1t1 is not None else {}
    val_pred = {n: np.asarray(m["predict"](d1t2), float).ravel() for n, m in models.items()}
    hp = [{"subject": s, "session": g, "task": task, "model": n, "hyperparameter": m["hyperparameter"],
           "selected_channels": json.dumps(m.get("selected_channels", []))} for n, m in models.items()]
    rows, phase_rows, track = [], [], []

    def add(model, align, day, y, pred, prior):
        base = {"subject": s, "session": g, "grasp": GRASPS[g], "task": task, "target_pct_mvc": TASK_PERCENT[task],
                "day": day, "model": model, "alignment": align}
        m = metrics(y, pred, prior)
        if model == "protocol_prior":
            m["skill_vs_prior"] = 0.0
        rows.append({**base, **m})
        for ph in PHASES:
            mk = phase_mask(WINDOW_CENTERS, ph)
            phase_rows.append({**base, "phase": ph, **metrics(y[mk], pred[mk], prior[mk])})

    for day, tr_no, tr in ([(1, 1, d1t1)] if d1t1 is not None else []) + [(1, 2, d1t2)]:
        track.append({"subject": s, "session": g, "task": task, "day": day, "trial": tr_no, "mvc": tr.mvc,
                      **{f"{k}": v for k, v in metrics(tr.y, tr.target, tr.target).items()
                         if k in ("r2", "rmse_pct_mvc", "mae_pct_mvc", "bias_pct_mvc")}})
    prev = d1t2.y.copy()
    for day in DAYS[1:]:
        cal, test = L(day, 1), L(day, 2)
        for tr_no, tr in ((1, cal), (2, test)):
            track.append({"subject": s, "session": g, "task": task, "day": day, "trial": tr_no, "mvc": tr.mvc,
                          **{f"{k}": v for k, v in metrics(tr.y, tr.target, tr.target).items()
                             if k in ("r2", "rmse_pct_mvc", "mae_pct_mvc", "bias_pct_mvc")}})
        base = {"protocol_prior": test.target, "day1_trial2_template": d1t2.y,
                "pooled_day1_template_loso": pooled[key], "previous_day_trial2_template": prev}
        if d1t1 is not None:
            base["day1_trial1_template"] = d1t1.y
            base["day1_average_template"] = (d1t1.y + d1t2.y) / 2
        for n, p in base.items():
            add(n, "none", day, test.y, p, test.target)
        for n, m in models.items():
            tc = np.asarray(m["predict"](test), float).ravel()
            cc = np.asarray(m["predict"](cal), float).ravel()
            aligned = robust_affine(val_pred[n], cc, tc)
            off = test.target if m["mode"] == "residual" else 0.0
            add(n, "fixed", day, test.y, off + tc, test.target)
            add(n, "trial1_unlabelled_affine", day, test.y, off + aligned, test.target)
        prev = test.y.copy()
    return rows, phase_rows, track, hp


_W = {}


def _init_analysis_worker(lookup, pooled, variant, timebase, ckdir):
    try:
        from threadpoolctl import threadpool_limits
        _W["limits"] = threadpool_limits(1)
    except Exception:
        pass
    _W.update(lookup=lookup, pooled=pooled, variant=variant, timebase=timebase, ckdir=ckdir)


def _analysis_worker(key):
    r, ph, tr, hp = analyze_condition(key, _W["lookup"], _W["pooled"], _W["variant"], _W["timebase"])
    res = {"model": r, "phase": ph, "tracking": tr, "hyper": hp}
    atomic_json(Path(_W["ckdir"]) / f"S{key[0]:02d}_G{key[1]}_T{key[2]}.json", res)
    return key


def run_analysis(manifest: pd.DataFrame, out_dir: Path, variant: str, timebase: str,
                 identity_extra: dict, limit: int | None = None,
                 excluded: list | None = None, processes: int = 1) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    ckdir = out_dir / "checkpoints"; ckdir.mkdir(exist_ok=True)
    identity = {"pipeline": PIPELINE_VERSION, "variant": variant, "timebase": timebase,
                "excluded_grasp_task": sorted([list(x) for x in (excluded or [])]),
                "script_sha256": sha256_file(Path(__file__)), **identity_extra}
    idp = ckdir / "identity.json"
    if idp.exists():
        old = json.loads(idp.read_text(encoding="utf-8"))
        if old != identity:
            stale = out_dir.parent / f"{out_dir.name}_stale_{time.strftime('%Y%m%d_%H%M%S')}"
            log(f"Analysis identity changed; moving old checkpoints to {stale}")
            os.replace(out_dir, stale)
            out_dir.mkdir(parents=True); ckdir.mkdir()
    atomic_json(idp, identity)
    lookup = {(r.subject, r.day, r.session, r.task, r.trial): Path(r.cache_path) for r in manifest.itertuples()}
    pooled = pooled_templates(manifest, timebase)
    excluded = {tuple(x) for x in (excluded or [])}
    conditions = [(s, g, t) for s in SUBJECTS for g in SESSIONS for t in TASKS if (g, t) not in excluded]
    if limit:
        conditions = conditions[:limit]
    tables = {"model": [], "phase": [], "tracking": [], "hyper": []}
    t0 = time.time()
    pending = [k for k in conditions if not (ckdir / f"S{k[0]:02d}_G{k[1]}_T{k[2]}.json").exists()]
    if processes > 1 and len(pending) > 1:
        from concurrent.futures import ProcessPoolExecutor, as_completed
        with ProcessPoolExecutor(max_workers=processes, initializer=_init_analysis_worker,
                                 initargs=(lookup, pooled, variant, timebase, str(ckdir))) as pool:
            futs = [pool.submit(_analysis_worker, k) for k in pending]
            for j, f in enumerate(as_completed(futs), 1):
                f.result()
                if j % 21 == 0 or j == len(futs):
                    log(f"[{variant}/{timebase}] {j}/{len(futs)} conditions computed "
                        f"({(time.time() - t0) / 60:.1f} min, {processes} processes)")
    for i, key in enumerate(conditions, 1):
        cp = ckdir / f"S{key[0]:02d}_G{key[1]}_T{key[2]}.json"
        if cp.exists():
            res = json.loads(cp.read_text(encoding="utf-8"))
        else:
            r, ph, tr, hp = analyze_condition(key, lookup, pooled, variant, timebase)
            res = {"model": r, "phase": ph, "tracking": tr, "hyper": hp}
            atomic_json(cp, res)
        for k in tables:
            tables[k].extend(res[k])
        if i % 21 == 0 or i == len(conditions):
            log(f"[{variant}/{timebase}] {i}/{len(conditions)} conditions ({(time.time() - t0) / 60:.1f} min)")
    model = pd.DataFrame(tables["model"]); phase = pd.DataFrame(tables["phase"])
    track = pd.DataFrame(tables["tracking"]); hyper = pd.DataFrame(tables["hyper"])
    model.to_csv(out_dir / "heldout_model_metrics.csv", index=False)
    phase.to_csv(out_dir / "heldout_phase_metrics.csv", index=False)
    track.to_csv(out_dir / "protocol_tracking_all_trials.csv", index=False)
    hyper.to_csv(out_dir / "day1_selected_hyperparameters.csv", index=False)
    return summarize(model, track, out_dir, identity, len(conditions))


def summarize(model, track, out_dir, identity, n_conditions):
    part = model.groupby(["subject", "model", "alignment"], as_index=False).agg(
        median_skill=("skill_vs_prior", "median"), median_rmse_pct_mvc=("rmse_pct_mvc", "median"),
        median_r2=("r2", "median"))
    part.to_csv(out_dir / "participant_model_summary.csv", index=False)
    rows = []
    for (m, a), grp in part.groupby(["model", "alignment"]):
        v = grp.median_skill.to_numpy(float); lo, hi = bootstrap_median_ci(v)
        rows.append({"model": m, "alignment": a, "median_participant_skill": float(np.nanmedian(v)),
                     "ci95_low": lo, "ci95_high": hi, "participants_positive": int((v > 0).sum()),
                     "n_participants": int(len(v)), "wilcoxon_p": safe_wilcoxon(v),
                     "median_rmse_pct_mvc": float(grp.median_rmse_pct_mvc.median())})
    cohort = pd.DataFrame(rows).sort_values("median_participant_skill", ascending=False)
    cohort.to_csv(out_dir / "cohort_model_summary.csv", index=False)
    pc = model.groupby(["subject", "session", "grasp", "task", "target_pct_mvc", "model", "alignment"],
                       as_index=False).agg(median_skill=("skill_vs_prior", "median"),
                                           median_rmse_pct_mvc=("rmse_pct_mvc", "median"))
    crow = []
    for (g, t, m, a), grp in pc.groupby(["session", "task", "model", "alignment"]):
        v = grp.median_skill.to_numpy(float); lo, hi = bootstrap_median_ci(v, seed=SEED + 10 * int(g) + int(t))
        crow.append({"session": g, "grasp": GRASPS[int(g)], "task": t, "target_pct_mvc": TASK_PERCENT[int(t)],
                     "model": m, "alignment": a, "median_participant_skill": float(np.nanmedian(v)),
                     "ci95_low": lo, "ci95_high": hi, "participants_positive": int((v > 0).sum()),
                     "n_participants": int(len(v))})
    pd.DataFrame(crow).to_csv(out_dir / "condition_model_summary_exploratory.csv", index=False)
    # Familiarization: prior-tracking error across days, normalized by target level so
    # 10/30/50% MVC conditions contribute comparably.
    tr = track.copy()
    tr["rmse_pct_of_target"] = tr.rmse_pct_mvc / tr.task.map(TASK_PERCENT) * 100
    pdays = tr.groupby(["subject", "day"], as_index=False).rmse_pct_of_target.median()
    slopes = []
    for s, grp in pdays.groupby("subject"):
        if grp.day.nunique() > 2:
            lr = linregress(grp.day, grp.rmse_pct_of_target)
            slopes.append({"subject": s, "slope_per_day": lr.slope, "r": lr.rvalue})
    sl = pd.DataFrame(slopes); sl.to_csv(out_dir / "familiarization_slopes.csv", index=False)
    lo, hi = bootstrap_median_ci(sl.slope_per_day.to_numpy(float), seed=SEED + 99) if len(sl) else (np.nan, np.nan)
    fam = {"unit": "participant", "outcome": "median protocol-tracking RMSE (% of target level) per day",
           "median_slope_per_day": float(sl.slope_per_day.median()) if len(sl) else None,
           "ci95": [lo, hi], "decreasing": int((sl.slope_per_day < 0).sum()) if len(sl) else 0,
           "n": int(len(sl)), "wilcoxon_p": safe_wilcoxon(sl.slope_per_day) if len(sl) else None}
    atomic_json(out_dir / "familiarization_summary.json", fam)
    primary = cohort[(cohort.model == "ridge_all_residual") & (cohort.alignment == "fixed")]
    meta = {**identity, "conditions": n_conditions, "participants": int(model.subject.nunique()),
            "primary_contrast": "ridge_all_residual / fixed: participant-median skill_vs_prior > 0",
            "primary_result": primary.to_dict("records")}
    atomic_json(out_dir / "run_metadata.json", meta)
    return meta
