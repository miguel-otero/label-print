param(
    [ValidateSet("docker", "jq", "unzip", "zip", "gcloud")]
    [string[]]$Tools = @(),
    [switch]$Help
)

$ErrorActionPreference = "Stop"
$arguments = @()
if ($Help) { $arguments += "--help" }
elseif ($Tools.Count -eq 0) { throw "Indique -Tools docker,jq,zip,gcloud. Este preparador instala paquetes Linux (Ubuntu/Debian)." }
else { foreach ($tool in $Tools) { $arguments += @('-t', $tool) } }
$script = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "../linux/startup.sh"))
if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT) {
    if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
        throw "Este preparador instala paquetes Linux. Instale WSL/Ubuntu o ejecutelo con pwsh en Ubuntu. No instala Docker Desktop en Windows."
    }
    $linuxPath = & wsl.exe --exec wslpath -u $script
    if ($LASTEXITCODE -ne 0) { throw "No se pudo resolver la ruta en WSL. Instale una distribucion Ubuntu/Debian." }
    & wsl.exe --exec bash $linuxPath.Trim() @arguments
} else {
    & bash $script @arguments
}
if ($LASTEXITCODE -ne 0) { throw "La preparacion Linux fallo con codigo $LASTEXITCODE." }
