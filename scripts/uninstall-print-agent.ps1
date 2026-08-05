$ErrorActionPreference = "Stop"
$serviceName = "ClinicLabelPrintAgent"
$installRoot = Join-Path $env:ProgramData "ClinicLabelPrint"
$wrapper = Join-Path $installRoot "$serviceName.exe"

if (Get-Service -Name $serviceName -ErrorAction SilentlyContinue) {
    if (Test-Path $wrapper) {
        & $wrapper stop | Out-Host
        & $wrapper uninstall | Out-Host
    } else {
        Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue
        sc.exe delete $serviceName | Out-Host
    }
    Write-Host "Servicio $serviceName eliminado."
} else {
    Write-Host "El servicio $serviceName no esta instalado."
}
Write-Host "Los archivos de configuracion y logs se conservan en $installRoot."
