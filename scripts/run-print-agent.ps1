$installRoot = Join-Path $env:ProgramData "ClinicLabelPrint"
$python = Join-Path $installRoot "venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "El agente no esta instalado. Ejecute scripts\install-print-agent.ps1 como administrador."
}
& $python -m agent.console
