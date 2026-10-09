# Dedicated Windows Python venv entry point, independent of PATH/MSYS2.
param([string]$DataRoot = 'C:\work\CEMHSEY')
$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $project '.venv\Scripts\python.exe'
$runner = Join-Path $project 'scripts\run_full_conformance.ps1'
if (-not (Test-Path $python)) { throw "Missing Python venv: $python" }
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $runner -DataRoot $DataRoot -Python $python
exit $LASTEXITCODE
