param(
    [ValidateSet("Docker")]
    [string]$Mode = "Docker",
    [switch]$Build,
    [switch]$Logs
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$envFile = Join-Path $repoRoot "conn\.env"
Set-Location $repoRoot

if (-not (Test-Path $envFile)) {
    throw "Environment file not found: $envFile"
}

Write-Host "clinic-label-print startup"
Write-Host "Mode: Docker (frontend, backend and PostgreSQL)"
Write-Host ""
Write-Host "==> Checking Docker" -ForegroundColor Cyan

$previousPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
docker info *> $null
$dockerExitCode = $LASTEXITCODE
$ErrorActionPreference = $previousPreference
if ($dockerExitCode -ne 0) {
    throw "Docker is not running or this terminal cannot access it."
}

$arguments = @("compose", "--env-file", $envFile, "up", "-d")
if ($Build) {
    $arguments += "--build"
}
docker @arguments
if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose could not start the application."
}

docker compose --env-file $envFile ps
Write-Host ""
Write-Host "Frontend: http://localhost:8083"
Write-Host "Backend:  http://localhost:8080/api"
Write-Host "Health:   http://localhost:8080/api/health"
Write-Host ""
Write-Host "Printing is handled by the ClinicLabelPrintAgent Windows service."

if ($Logs) {
    docker compose --env-file $envFile logs -f
}
