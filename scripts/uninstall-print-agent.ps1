$ErrorActionPreference = "Stop"
$serviceName = "ClinicLabelPrintAgent"
$installRoot = Join-Path $env:ProgramData "ClinicLabelPrint"
$python = Join-Path $installRoot "venv\Scripts\python.exe"

if (Get-Service -Name $serviceName -ErrorAction SilentlyContinue) {
    Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue
    & $python -m agent.service remove
    Write-Host "Servicio $serviceName eliminado."
} else {
    Write-Host "El servicio $serviceName no esta instalado."
}
Write-Host "Los archivos de configuracion y logs se conservan en $installRoot."
