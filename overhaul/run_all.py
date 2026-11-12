#!/usr/bin/env python3
"""Unattended driver: extract -> inventory -> gate -> analyses -> report.

Rerunning resumes: cached recordings and finished analysis conditions are reused.
Status: STATUS.json beside this file. Log: run.log (redirected by the launcher).
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cemhsey_overhaul as c  # noqa: E402

CACHE = HERE / "cache"
RESULTS = HERE / "results"
STATUS = HERE / "STATUS.json"
LOCAL_ROOTS = [Path(r"C:\work\CEMHSEY")]
DRIVE_RESULTS = Path(r"G:\My Drive\CEMHSEY_full_GRASP_2026\analysis")
MIN_FREE_GB = 30
DOWNLOADS = int(os.environ.get("CEMHSEY_DOWNLOADS", "8"))   # parallel Zenodo range streams
ANALYSES = [  # (folder, EMG variant, time base, role)
    ("primary_bandpass_physical", "bp", "physical", "primary"),
    ("sensitivity_unfiltered_physical", "raw", "physical", "sensitivity"),
    ("sensitivity_bandpass_normalized", "bp", "normalized", "sensitivity"),
]

state = {"started": time.strftime("%Y-%m-%d %H:%M:%S"), "stage": "starting", "subjects": {}}


def status(stage: str, **kw) -> None:
    state.update(stage=stage, updated=time.strftime("%Y-%m-%d %H:%M:%S"), **kw)
    c.atomic_json(STATUS, state)
    c.log(f"== {stage} {kw if kw else ''}")


def keep_awake(on: bool) -> None:
    if platform.system() == "Windows":
        import ctypes
        flags = 0x80000000 | (0x00000001 if on else 0)   # ES_CONTINUOUS | ES_SYSTEM_REQUIRED
        ctypes.windll.kernel32.SetThreadExecutionState(flags)


def available_ram_gb() -> float:
    try:
        if platform.system() == "Windows":
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            ms = MS(); ms.dwLength = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))
            return ms.ullAvailPhys / 1e9
        return os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / 1e9
    except Exception:
        return 4.0


def cpu_processes() -> int:
    """Leave one core free; budget ~0.6 GB per process plus 3 GB headroom."""
    if os.environ.get("CEMHSEY_CPU"):
        return max(1, int(os.environ["CEMHSEY_CPU"]))
    cores = os.cpu_count() or 2
    by_ram = int((available_ram_gb() - 3.0) / 0.6)
    return max(1, min(cores - 1, by_ram, 8))


def provenance() -> dict:
    import numpy, pandas, scipy, sklearn
    try:
        import remotezip
        rz = getattr(remotezip, "__version__", "installed")
    except ImportError:
        rz = None
    freeze = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True).stdout
    (HERE / "results").mkdir(exist_ok=True)
    (RESULTS / "pip_freeze.txt").write_text(freeze, encoding="utf-8")
    prov = {"python": sys.version, "platform": platform.platform(), "numpy": numpy.__version__,
            "pandas": pandas.__version__, "scipy": scipy.__version__, "sklearn": sklearn.__version__,
            "remotezip": rz, "pipeline": c.PIPELINE_VERSION,
            "pipeline_sha256": c.sha256_file(HERE / "cemhsey_overhaul.py"),
            "driver_sha256": c.sha256_file(HERE / "run_all.py"),
            "analysis_plan_sha256": c.sha256_file(HERE / "ANALYSIS_PLAN.md")}
    c.atomic_json(RESULTS / "provenance.json", prov)
    return prov


def write_report(gate: dict, inv: dict, metas: dict) -> None:
    import pandas as pd
    lines = ["# CEMHSEY overhaul run report", "", f"Finished {time.strftime('%Y-%m-%d %H:%M')}.", "",
             f"Recordings cached: {inv['observed']} of {inv['expected_usable']} "
             f"({inv['total_source_bytes'] / 1e9:.0f} GB streamed or read once).", "",
             f"Gate: timing ok = {gate['timing_ok']}, reproduction ok = {gate['reproduction_ok']} "
             f"(max |dR2| = {gate['reproduction_max_abs_diff']}), flagged recordings = "
             f"{gate['flagged_recordings']}/{gate['n_recordings']}, excluded grasp/force cells = "
             f"{gate['excluded_conditions']}.", ""]
    for folder, *_ in ANALYSES:
        p = RESULTS / folder / "cohort_model_summary.csv"
        if p.exists():
            df = pd.read_csv(p)
            lines += [f"## {folder}", "", df.head(12).to_markdown(index=False, floatfmt=".3f"), ""]
        fam = RESULTS / folder / "familiarization_summary.json"
        if fam.exists():
            lines += [f"Familiarization: {fam.read_text(encoding='utf-8')}", ""]
    (RESULTS / "RUN_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def copy_to_drive() -> str:
    if not DRIVE_RESULTS.parent.exists():
        return "Google Drive folder not available; results stay on C:."
    dest = DRIVE_RESULTS / f"overhaul_{time.strftime('%Y%m%d_%H%M')}"
    shutil.copytree(RESULTS, dest, ignore=shutil.ignore_patterns("checkpoints", "*.tmp"))
    return f"Results copied to {dest}"


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    for k in ("error", "traceback", "note"):
        state.pop(k, None)
    keep_awake(True)
    try:
        status("preflight")
        free = shutil.disk_usage(HERE).free / 1e9
        if free < MIN_FREE_GB:
            raise RuntimeError(f"Only {free:.0f} GB free on the drive holding {HERE}; need {MIN_FREE_GB} GB.")
        prov = provenance()
        c.log(f"Provenance: {json.dumps(prov)}")

        from concurrent.futures import ProcessPoolExecutor
        nproc = cpu_processes()
        state["parallel"] = {"downloads": DOWNLOADS, "cpu_processes": nproc, "cores": os.cpu_count(),
                             "available_ram_gb": round(available_ram_gb(), 1)}
        c.log(f"Parallelism: {state['parallel']}")
        for attempt in range(2):
            with ProcessPoolExecutor(max_workers=nproc) as cpu_pool:
                for s in c.SUBJECTS:
                    status("extract", current_subject=s)
                    try:
                        state["subjects"][str(s)] = c.extract_subject(
                            s, CACHE, local_roots=LOCAL_ROOTS, workers=DOWNLOADS, cpu_pool=cpu_pool)
                    except Exception as exc:
                        state["subjects"][str(s)] = {"error": repr(exc)}
                        c.log(f"S{s} extraction error (will retry later): {exc!r}")
            inv = c.build_inventory(CACHE, RESULTS / "inventory")
            status("inventory", inventory=inv)
            if inv["complete"]:
                break
            c.log("Inventory incomplete; one more pass after a 10-minute pause.")
            time.sleep(600)
        if not inv["complete"]:
            raise RuntimeError(f"Cache incomplete after two passes: {inv['missing']} recordings missing. "
                               "Rerun the launcher to resume.")

        import pandas as pd
        manifest = pd.read_csv(RESULTS / "inventory" / "recording_manifest.csv")
        status("gate")
        gate = c.run_gate(manifest, RESULTS / "gate")
        state["gate"] = gate
        if not gate["reproduction_ok"]:
            raise RuntimeError("Reproduction check failed: the pipeline does not recover the known "
                               "Session 1 / Task 2 protocol-prior error. Analysis not run. See results/gate.")
        if gate["excluded_conditions"]:
            c.log(f"Grasp/force cells off the nominal trapezoid, excluded per plan: {gate['excluded_conditions']}")

        extra = {"manifest_sha256": c.sha256_file(RESULTS / "inventory" / "recording_manifest.csv"),
                 "analysis_plan_sha256": prov["analysis_plan_sha256"]}
        metas = {}
        for folder, variant, timebase, role in ANALYSES:
            status("analysis", current=folder)
            metas[folder] = c.run_analysis(manifest, RESULTS / folder, variant, timebase, extra,
                                           excluded=gate["excluded_conditions"], processes=nproc)
        write_report(gate, inv, metas)
        msg = copy_to_drive()
        status("complete", note=msg)
        (HERE / "DONE.txt").write_text(time.strftime("%Y-%m-%d %H:%M:%S"), encoding="utf-8")
        return 0
    except Exception as exc:
        status("failed", error=repr(exc), traceback=traceback.format_exc())
        return 1
    finally:
        keep_awake(False)


if __name__ == "__main__":
    sys.exit(main())
