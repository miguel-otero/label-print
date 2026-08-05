param(
    [Parameter(Mandatory = $true)][string]$ServerUrl,
    [Parameter(Mandatory = $true)][string]$Token,
    [string]$PrinterName = "ZDesigner ZD230-203dpi ZPL",
    [string]$AgentId = "windows-primary"
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$source = Join-Path $repoRoot "app\windows_agent"
$installRoot = Join-Path $env:ProgramData "ClinicLabelPrint"
$venv = Join-Path $installRoot "venv"
$python = Join-Path $venv "Scripts\python.exe"
$serviceName = "ClinicLabelPrintAgent"
$wrapper = Join-Path $installRoot "$serviceName.exe"
$wrapperConfig = Join-Path $installRoot "$serviceName.xml"
$logsPath = Join-Path $installRoot "logs"

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Ejecute este script desde PowerShell como administrador."
}

if (Get-Service -Name $serviceName -ErrorAction SilentlyContinue) {
    Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue
    if (Test-Path $wrapper) { & $wrapper uninstall | Out-Host }
    if (Get-Service -Name $serviceName -ErrorAction SilentlyContinue) {
        sc.exe delete $serviceName | Out-Host
        Start-Sleep -Seconds 2
    }
}

New-Item -ItemType Directory -Path $installRoot, $logsPath -Force | Out-Null
if (-not (Test-Path $python)) {
    py -3.12 -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw "Python 3.12 es requerido." }
}
& $python -m pip install --upgrade pip
& $python -m pip install $source
if ($LASTEXITCODE -ne 0) { throw "No se pudo instalar el agente." }

$configPath = Join-Path $installRoot "agent.env"
Set-Content -LiteralPath $configPath -Encoding UTF8 -Value @(
    "CLINIC_AGENT_SERVER_URL=$($ServerUrl.TrimEnd('/'))"
    "CLINIC_PRINT_AGENT_TOKEN=$Token"
    "CLINIC_PRINT_AGENT_ID=$AgentId"
    "CLINIC_PRINTER_NAME=$PrinterName"
    "CLINIC_AGENT_POLL_SECONDS=1"
    "CLINIC_AGENT_HEARTBEAT_SECONDS=10"
    "CLINIC_AGENT_REQUEST_TIMEOUT_SECONDS=15"
)

if (-not (Test-Path $wrapper)) {
    $winswUrl = "https://github.com/winsw/winsw/releases/download/v2.12.0/WinSW-x64.exe"
    Write-Host "Descargando WinSW 2.12.0 desde el repositorio oficial..."
    Invoke-WebRequest -Uri $winswUrl -OutFile $wrapper -UseBasicParsing
}

$xml = @"
<service>
  <id>$serviceName</id>
  <name>Clinic Label Print Agent</name>
  <description>Recibe trabajos ZPL del servidor y los envia a la cola Zebra local.</description>
  <executable>$python</executable>
  <arguments>-m agent.console</arguments>
  <workingdirectory>$installRoot</workingdirectory>
  <startmode>Automatic</startmode>
  <onfailure action="restart" delay="10 sec" />
  <logpath>$logsPath</logpath>
  <log mode="roll" />
</service>
"@
Set-Content -LiteralPath $wrapperConfig -Value $xml -Encoding UTF8

icacls $configPath /inheritance:r /grant:r "*S-1-5-18:F" "*S-1-5-32-544:F" | Out-Null
& $wrapper install | Out-Host
if ($LASTEXITCODE -ne 0 -or -not (Get-Service $serviceName -ErrorAction SilentlyContinue)) {
    throw "WinSW no pudo registrar el servicio."
}
& $wrapper start | Out-Host
Start-Sleep -Seconds 2
$service = Get-Service $serviceName
if ($service.Status -ne "Running") { throw "El servicio fue registrado pero no permanece en ejecucion. Revise $logsPath." }

Write-Host "Servicio $serviceName instalado e iniciado como LocalSystem."
Write-Host "Configuracion: $configPath"
Write-Host "Logs: $logsPath"
