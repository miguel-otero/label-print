param(
    [Parameter(Mandatory = $true)][string]$ServerUrl,
    [Parameter(Mandatory = $true)][string]$Token,
    [string]$PrinterName = "ZDesigner ZD230-203dpi ZPL",
    [string]$AgentId = "windows-primary",
    [PSCredential]$ServiceCredential
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$source = Join-Path $repoRoot "app\windows_agent"
$installRoot = Join-Path $env:ProgramData "ClinicLabelPrint"
$venv = Join-Path $installRoot "venv"
$python = Join-Path $venv "Scripts\python.exe"
$serviceName = "ClinicLabelPrintAgent"

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Ejecute este script desde PowerShell como administrador."
}
if (-not $ServiceCredential) {
    $ServiceCredential = Get-Credential -Message "Cuenta dedicada que ejecutara el agente y puede acceder a la impresora"
}

if (Get-Service -Name $serviceName -ErrorAction SilentlyContinue) {
    Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue
    & $python -m agent.service remove
}

New-Item -ItemType Directory -Path $installRoot -Force | Out-Null
$logsPath = Join-Path $installRoot "logs"
New-Item -ItemType Directory -Path $logsPath -Force | Out-Null
if (-not (Test-Path $python)) {
    python -m venv $venv
}
& $python -m pip install --upgrade pip
& $python -m pip install $source
$postInstall = Join-Path $venv "Scripts\pywin32_postinstall.py"
if (Test-Path $postInstall) {
    & $python $postInstall -install
}

$config = @(
    "CLINIC_AGENT_SERVER_URL=$($ServerUrl.TrimEnd('/'))"
    "CLINIC_PRINT_AGENT_TOKEN=$Token"
    "CLINIC_PRINT_AGENT_ID=$AgentId"
    "CLINIC_PRINTER_NAME=$PrinterName"
    "CLINIC_AGENT_POLL_SECONDS=1"
    "CLINIC_AGENT_HEARTBEAT_SECONDS=10"
    "CLINIC_AGENT_REQUEST_TIMEOUT_SECONDS=15"
)
$configPath = Join-Path $installRoot "agent.env"
Set-Content -LiteralPath $configPath -Value $config -Encoding UTF8

$networkCredential = $ServiceCredential.GetNetworkCredential()
& $python -m agent.service --startup auto --username $ServiceCredential.UserName --password $networkCredential.Password install
if ($LASTEXITCODE -ne 0) { throw "No se pudo instalar el servicio." }

icacls $configPath /inheritance:r /grant:r "*S-1-5-18:F" "*S-1-5-32-544:F" "$($ServiceCredential.UserName):R" | Out-Null
icacls $logsPath /grant "$($ServiceCredential.UserName):(OI)(CI)M" | Out-Null
Start-Service -Name $serviceName
Write-Host "Servicio $serviceName instalado e iniciado."
Write-Host "Configuracion: $configPath"
Write-Host "Logs: $(Join-Path $installRoot 'logs\agent.log')"
