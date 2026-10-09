# CEMHSEY presubmission independent conformance runner.
# Usage: powershell -ExecutionPolicy Bypass -File .\scripts\run_full_conformance.ps1 -DataRoot "C:\work\CEMHSEY"
# This is a NEW pipeline; it must not be described as rerunning the missing historical script.
param(
    [string] $DataRoot = 'C:\work\CEMHSEY',
    [string] $Python = 'python'
)

$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)

function Invoke-Step {
    param([string[]] $Arguments)
    & $Python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Failed: python $($Arguments -join ' ') (exit code $LASTEXITCODE)"
    }
}

Invoke-Step @('-m','pip','install','-r','requirements.txt')
$projectTemp = Join-Path (Get-Location).Path '.emg_temp'
New-Item -ItemType Directory -Force -Path $projectTemp | Out-Null
$env:TEMP = $projectTemp
$env:TMP = $projectTemp
Invoke-Step @('-m','pytest','-q','tests','--basetemp',(Join-Path $projectTemp 'pytest'))
Invoke-Step @('reproducibility/build_manifest.py','--data-root',$DataRoot,'--out','reproducibility/manifest.csv')
Invoke-Step @('reproducibility/protocol_prior_benchmark.py','--manifest','reproducibility/manifest.csv','--out','results/new_protocol_prior')
Invoke-Step @('reproducibility/emg_reimplementation.py','--manifest','reproducibility/manifest.csv','--out','results/new_emg_reimplementation')

# Intentionally capture failed conformance without discarding the report.
& $Python 'reproducibility/compare_frozen_results.py' `
    '--new' 'results/new_emg_reimplementation/reimplemented_participant_metrics.csv' `
    '--frozen' 'results/longitudinal_performance_physical.csv' `
    '--out' 'results/new_emg_reimplementation/conformance.csv'
$conformanceCode = $LASTEXITCODE

$package = 'results/new_emg_reimplementation/CONFORMANCE_REPORT.zip'
$items = @(
    'results/new_protocol_prior/cohort_summary.json',
    'results/new_emg_reimplementation/new_reimplementation_config.json',
    'results/new_emg_reimplementation/reimplemented_recording_metrics.csv',
    'results/new_emg_reimplementation/reimplemented_participant_metrics.csv',
    'results/new_emg_reimplementation/reimplemented_day1_parameters.csv',
    'results/new_emg_reimplementation/reimplemented_descriptive_lodo.csv',
    'results/new_emg_reimplementation/conformance.csv'
)
Compress-Archive -Path $items -DestinationPath $package -Force
Write-Host "Conformance report package: $package"
if ($conformanceCode -ne 0) {
    Write-Warning 'Empirical conformance is NOT established. Frozen manuscript values were not changed.'
    exit 3
}
Write-Host 'Summary-level EMG model comparison passed; inspect participant-level outputs before publishing.'
