$ErrorActionPreference = 'Stop'

if (-not (Test-Path .venv)) {
  py -3.11 -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

Write-Host "Environment ready. Activate with: .\.venv\Scripts\Activate.ps1"
