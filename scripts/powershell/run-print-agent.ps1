param([switch]$StopService)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "windows-agent-common.ps1")
Assert-WindowsAgentPlatform
$installation = Get-WindowsAgentInstallation
if (-not (Test-Path -LiteralPath $installation.Executable)) {
    throw "No se encontro el agente instalado. Instale el .exe o use install-print-agent.ps1 para la instalacion heredada."
}
$service = Get-Service -Name ClinicLabelPrintAgent -ErrorAction SilentlyContinue
if ($service -and $service.Status -ne "Stopped") {
    if (-not $StopService) {
        throw "El servicio esta activo. Detengalo o use -StopService como administrador para evitar dos consumidores."
    }
    Assert-WindowsAgentAdministrator
    Stop-Service -Name ClinicLabelPrintAgent -ErrorAction Stop
    (Get-Service -Name ClinicLabelPrintAgent).WaitForStatus('Stopped', [TimeSpan]::FromSeconds(30))
    Write-Host "Servicio detenido. Reinicielo al terminar con Start-Service ClinicLabelPrintAgent."
}
Write-Host "Diagnostico en consola ($($installation.Kind)). Ctrl+C para terminar."
if ($installation.Kind -eq "Installer") {
    & $installation.Executable
} else {
    & $installation.Executable -m agent.console
}
if ($LASTEXITCODE -ne 0) { throw "El agente termino con codigo $LASTEXITCODE." }
