"""Verify that the four original vector PDF figures are present and bitwise unchanged."""
from pathlib import Path
import hashlib

ROOT=Path(__file__).resolve().parents[1]
EXPECTED={
    'fig1_temporal_prior_vs_emg.pdf':'6b9ba49fd2922dd6f3b56ef86ccd7a730dff221c6b961124d52403dc6d9f7cc2',
    'fig2_incremental_emg.pdf':'2746f66da3233d10655a0a693c9811fb9e2e253776c8e3c9f8bddcac87934289',
    'fig3_residual_information_final.pdf':'2000cc99d91574a4aa1aa82ddb0f4a4e6df534fc84c0003b17777c58d2c665c7',
    'fig4_emg_component_ablation_final.pdf':'77dd9a8d090928cb1a8818e3d07847209917e0d8a53fbc82972130e6550c6380',
}

def test_original_figure_pdfs_sha256():
    for name,expected in EXPECTED.items():
        p=ROOT/'manuscript'/'figures'/name
        assert p.is_file(), f'Missing original figure PDF: {name}'
        assert hashlib.sha256(p.read_bytes()).hexdigest()==expected, f'PDF bytes changed: {name}'
