import sys
from pathlib import Path
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reproducibility'))
from build_manifest import build


def test_manifest_selects_exact_220_files(tmp_path):
    for s in range(1,11):
        for d in range(1,12):
            p=tmp_path/f'S{s}'/f'Day{d}'
            p.mkdir(parents=True,exist_ok=True)
            for trial in (1,2):
                (p/f'S{s}_Day{d}_Session1_Task2_Trial{trial}.mat').touch()
            (p/f'S{s}_Day{d}_Session2_Task2_Trial1.mat').touch()
    df=build(tmp_path)
    assert len(df)==220
    assert df[['subject','day','trial']].drop_duplicates().shape[0]==220


def test_manifest_missing_source_fails(tmp_path):
    with pytest.raises(ValueError,match='Missing 220'):
        build(tmp_path)
