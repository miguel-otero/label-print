$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "windows-agent-common.ps1")
Assert-WindowsAgentPlatform
Assert-WindowsAgentAdministrator
$installation = Get-WindowsAgentInstallation
$serviceName = "ClinicLabelPrintAgent"

if ($installation.Kind -eq "Installer") {
    if (-not (Test-Path -LiteralPath $installation.Uninstaller)) {
        throw "Falta el desinstalador de $($installation.Root). Reinstale el .exe para reparar la instalacion antes de desinstalar."
    }
    # Inno Setup removes binaries and the Windows installed-program entry as well as the service.
    $process = Start-Process -FilePath $installation.Uninstaller -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART') -WindowStyle Hidden -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw "El desinstalador termino con codigo $($process.ExitCode)." }
} elseif (Get-Service -Name $serviceName -ErrorAction SilentlyContinue) {
    if (Test-Path -LiteralPath $installation.Wrapper) {
        & $installation.Wrapper stop | Out-Host
        if ($LASTEXITCODE -ne 0) { throw "No se pudo detener el servicio heredado." }
        & $installation.Wrapper uninstall | Out-Host
        if ($LASTEXITCODE -ne 0) { throw "No se pudo eliminar el servicio heredado." }
    } else {
        Stop-Service -Name $serviceName -ErrorAction Stop
        sc.exe delete $serviceName | Out-Host
        if ($LASTEXITCODE -ne 0) { throw "No se pudo eliminar el servicio heredado." }
    }
} else {
    Write-Host "El servicio $serviceName no esta instalado."
}
if (Get-Service -Name $serviceName -ErrorAction SilentlyContinue) {
    throw "El servicio sigue registrado (posiblemente pendiente de eliminacion). Cierre services.msc y revise antes de reinstalar."
}
Write-Host "Desinstalacion finalizada. Configuracion y logs conservados en $env:ProgramData\ClinicLabelPrint."
if ($installation.Kind -eq "Legacy") {
    Write-Host "Los binarios heredados tambien se conservan para permitir recuperacion."
}
