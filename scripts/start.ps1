param(
    [ValidateSet("Usb", "Docker")]
    [string]$Mode = "Usb",
    [switch]$Build,
    [switch]$InstallDeps,
    [switch]$Logs
)

# Uso normal:
#   .\scripts\start.ps1
#
# Impresion real por USB:
#   .\scripts\start.ps1 -Mode Usb
#
# Todo en Docker, con impresion simulada:
#   .\scripts\start.ps1 -Mode Docker
#
# Opcionales:
#   -Build        reconstruye imagenes Docker necesarias.
#   -InstallDeps reinstala dependencias Python del backend local.
#   -Logs        solo aplica en -Mode Docker.

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$backendDir = Join-Path $repoRoot "app\backend"
$venvDir = Join-Path $backendDir ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$envFile = Join-Path $repoRoot "conn\backend.env"
$secretsFile = Join-Path $repoRoot "conn\.env"

Set-Location $repoRoot

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Invoke-Docker {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    docker @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Docker command failed: docker $($Arguments -join ' ')"
    }
}

function Import-EnvFile {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        throw "Environment file not found: $Path"
    }

    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            return
        }

        $parts = $line.Split("=", 2)
        if ($parts.Length -ne 2) {
            return
        }

        [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
    }
}

function Get-PortOwner {
    param([int]$Port)

    $line = netstat -ano | Select-String "LISTENING" | Select-String ":$Port\s" | Select-Object -First 1
    if (-not $line) {
        return $null
    }

    $parts = ($line.Line.Trim() -split "\s+")
    return $parts[-1]
}

function Wait-Database {
    Write-Step "Waiting for PostgreSQL"
    for ($i = 1; $i -le 30; $i++) {
        docker compose exec -T clinic_db pg_isready -U $env:CLINIC_DATABASE_USER -d $env:CLINIC_DATABASE_NAME *> $null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "PostgreSQL is ready."
            return
        }
        Start-Sleep -Seconds 1
    }

    Write-Host "PostgreSQL logs:" -ForegroundColor Yellow
    docker compose logs clinic_db
    throw "PostgreSQL did not become ready in time."
}

function Test-BackendDatabaseConnection {
    Write-Step "Checking backend database connection"
    & $venvPython -c "import os, psycopg; psycopg.connect(host=os.environ['CLINIC_DATABASE_HOST'], port=os.environ['CLINIC_DATABASE_PORT'], dbname=os.environ['CLINIC_DATABASE_NAME'], user=os.environ['CLINIC_DATABASE_USER'], password=os.environ['CLINIC_DATABASE_PASSWORD']).execute('select 1'); print('Database connection OK')"
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "The backend cannot connect to PostgreSQL using the settings from conn\.env and conn\backend.env." -ForegroundColor Red
        Write-Host ""
        Write-Host "Verify that PostgreSQL publishes port 5432 and that conn\.env matches the credentials used to initialize the Docker volume."
        throw "Backend database connection failed."
    }
}

function Ensure-BackendVenv {
    if ((Test-Path $venvDir) -and (-not (Test-Path $venvPython))) {
        Write-Host "Backend virtual environment is incomplete; recreating it."
        Remove-Item -LiteralPath $venvDir -Recurse -Force
    }

    if (-not (Test-Path $venvPython)) {
        Write-Step "Creating backend virtual environment"
        python -m venv $venvDir
        $script:InstallDeps = $true
    }

    if (-not $InstallDeps) {
        & $venvPython -c "import fastapi, uvicorn, pydantic_settings, psycopg, pytds" 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Backend dependencies are missing; installing them."
            $script:InstallDeps = $true
        }
    }

    if ($InstallDeps) {
        Write-Step "Installing backend dependencies"
        & $venvPython -m pip install -r (Join-Path $backendDir "requirements.txt")
        if ($LASTEXITCODE -ne 0) {
            throw "Could not install backend dependencies."
        }
    }
}

Write-Host "clinic-label-print startup"
Write-Host "Mode: $Mode"

Import-EnvFile $envFile
Import-EnvFile $secretsFile

Write-Step "Checking Docker"
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker is not running or this terminal cannot access it."
}

if ($Mode -eq "Docker") {
    Write-Step "Starting everything in Docker"
    $composeArgs = @("compose", "up", "-d")
    if ($Build) {
        $composeArgs += "--build"
    }
    Invoke-Docker -Arguments $composeArgs

    Write-Step "Services"
    Invoke-Docker -Arguments @("compose", "ps")

    Write-Host ""
    Write-Host "Frontend: http://localhost:8083"
    Write-Host "Backend:  http://localhost:8080/api"
    Write-Host "Health:   http://localhost:8080/api/health"
    Write-Host ""
    Write-Host "Docker mode uses simulated printing."

    if ($Logs) {
        Write-Step "Following logs"
        Invoke-Docker -Arguments @("compose", "logs", "-f")
    }

    exit 0
}

if ($Logs) {
    Write-Host "Note: -Logs is only used with -Mode Docker. In USB mode the backend logs stay in this terminal."
}

Write-Step "Starting database in Docker"
Invoke-Docker -Arguments @("compose", "up", "-d", "clinic_db")
Wait-Database

Write-Step "Stopping Docker backend"
Invoke-Docker -Arguments @("compose", "stop", "clinic_backend")

Write-Step "Starting frontend in Docker"
$frontendArgs = @("compose", "up", "-d", "--no-deps")
if ($Build) {
    $frontendArgs += "--build"
}
$frontendArgs += "clinic_frontend"
Invoke-Docker -Arguments $frontendArgs

Ensure-BackendVenv
Test-BackendDatabaseConnection

$portOwner = Get-PortOwner -Port 8080
if ($portOwner) {
    Write-Host ""
    Write-Host "Port 8080 is already in use by process $portOwner." -ForegroundColor Red
    Write-Host "Stop that process before starting the local backend:"
    Write-Host "  Stop-Process -Id $portOwner"
    throw "Port 8080 is already in use."
}

Write-Host ""
Write-Host "Frontend: http://localhost:8083"
Write-Host "Backend:  http://localhost:8080/api"
Write-Host "Health:   http://localhost:8080/api/health"
Write-Host ""
Write-Host "USB mode keeps the backend in this terminal so it can use the Windows print queue."
Write-Host "Press Ctrl+C here to stop the local backend."

Write-Step "Starting local backend"
Set-Location $backendDir
& $venvPython -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
