# Shared helpers; dot-source this file, do not execute it as an entry point.
function Assert-WindowsAgentPlatform {
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
        throw "El agente usa el spooler de Windows. Ejecute este script en Windows, o scripts/linux desde WSL con interoperabilidad Windows."
    }
}

function Assert-WindowsAgentAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Ejecute la terminal como administrador."
    }
}

function Get-WindowsAgentInstallation {
    $roots = @()
    $uninstallKeys = @(
        'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{C5B71EA9-B977-4BD8-B458-A7A73333AE42}_is1',
        'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\{C5B71EA9-B977-4BD8-B458-A7A73333AE42}_is1'
    )
    foreach ($key in $uninstallKeys) {
        $entry = Get-ItemProperty -LiteralPath $key -ErrorAction SilentlyContinue
        if ($entry -and $entry.InstallLocation) { $roots += $entry.InstallLocation }
    }
    # ImagePath also locates custom installations when the uninstall key is absent.
    $service = Get-ItemProperty -LiteralPath 'HKLM:\SYSTEM\CurrentControlSet\Services\ClinicLabelPrintAgent' -ErrorAction SilentlyContinue
    if ($service -and $service.ImagePath) {
        $servicePath = [Environment]::ExpandEnvironmentVariables($service.ImagePath)
        if ($servicePath -match '^"([^"]+\.exe)"' -or $servicePath -match '^(.+?\.exe)(?:\s|$)') {
            $roots += Split-Path -Parent $Matches[1]
        }
    }
    foreach ($programRoot in @($env:ProgramW6432, $env:ProgramFiles, ${env:ProgramFiles(x86)})) {
        if ($programRoot) { $roots += Join-Path $programRoot "ClinicLabelPrintAgent" }
    }
    foreach ($root in ($roots | Select-Object -Unique)) {
        $executable = Join-Path $root "agent\ClinicLabelPrintAgent.exe"
        $uninstaller = Join-Path $root "unins000.exe"
        if ((Test-Path -LiteralPath $executable) -or (Test-Path -LiteralPath $uninstaller)) {
            return [PSCustomObject]@{
                Kind = "Installer"; Root = $root; Executable = $executable
                Wrapper = Join-Path $root "ClinicLabelPrintAgent.exe"
                Uninstaller = $uninstaller
            }
        }
    }
    $legacyRoot = Join-Path $env:ProgramData "ClinicLabelPrint"
    return [PSCustomObject]@{
        Kind = "Legacy"; Root = $legacyRoot
        Executable = Join-Path $legacyRoot "venv\Scripts\python.exe"
        Wrapper = Join-Path $legacyRoot "ClinicLabelPrintAgent.exe"
        Uninstaller = $null
    }
}
