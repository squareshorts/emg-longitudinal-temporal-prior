# Re-run the six Figure 4 contrasts on the original CEMHSEY recordings.
# Save this file AND audit_figure4_normalized.py in C:\work\EMG_reproducibility.
# It uses the existing project virtual environment and does not edit the manuscript.
param(
    [string] $DataRoot = 'C:\work\CEMHSEY'
)
$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $project
$python = Join-Path $project '.venv\Scripts\python.exe'
$auditor = Join-Path $project 'audit_figure4_normalized.py'
$manifest = Join-Path $project 'reproducibility\manifest.csv'
$builder = Join-Path $project 'reproducibility\build_manifest.py'
$out = Join-Path $project 'results\figure4_normalized_audit'
if (-not (Test-Path $python)) { throw "Missing dedicated Python: $python" }
if (-not (Test-Path $auditor)) { throw "Missing audit program: $auditor" }
if (-not (Test-Path (Join-Path $project 'reproducibility\emg_reimplementation.py'))) { throw 'Missing existing EMG reconstruction module.' }
if (-not (Test-Path $manifest)) {
    if (-not (Test-Path $builder)) { throw "Missing manifest builder: $builder" }
    & $python $builder '--data-root' $DataRoot '--out' $manifest
    if ($LASTEXITCODE -ne 0) { throw 'Manifest generation failed.' }
}
& $python $auditor '--manifest' $manifest '--out' $out
if ($LASTEXITCODE -ne 0) { throw "Figure 4 independent reconstruction failed (exit $LASTEXITCODE)" }
$archive = Join-Path $out 'FIGURE4_AUDIT.zip'
if (-not (Test-Path $archive)) { throw "Missing expected report: $archive" }
Write-Host "Figure 4 audit ready: $archive"
