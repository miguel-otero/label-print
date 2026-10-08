param(
    [switch]$NoUpload,
    [string]$Bucket = "gs://label-print-cv/deploy.zip"
)

$ErrorActionPreference = "Stop"
if (-not $Bucket.StartsWith('gs://')) { throw "El destino debe comenzar por gs://." }
if (-not $NoUpload -and -not (Get-Command gsutil -ErrorAction SilentlyContinue)) {
    throw "Falta gsutil. Instale Google Cloud CLI y autentiquese, o use -NoUpload."
}
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "../.."))
$paths = Get-Content -LiteralPath (Join-Path $repoRoot "scripts/deploy-files.txt") | Where-Object { $_.Trim() }
foreach ($entry in $paths) {
    if (-not (Test-Path -LiteralPath (Join-Path $repoRoot $entry))) { throw "Falta un archivo/directorio requerido: $entry" }
}
$artifactRoot = Join-Path $repoRoot "artifacts/deploy"
New-Item -ItemType Directory -Path $artifactRoot -Force | Out-Null
$archivePath = Join-Path $artifactRoot "deploy.zip"
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$stream = [IO.File]::Open($archivePath, [IO.FileMode]::Create)
$archive = [IO.Compression.ZipArchive]::new($stream, [IO.Compression.ZipArchiveMode]::Create)
$excludedDirectories = @('node_modules', '__pycache__', '.venv', 'venv', 'build', 'dist', '.vite', '.nitro', '.output', '.git', '.build', 'artifacts', 'logs')
function Add-DeploymentEntry([string]$Path) {
    $item = Get-Item -LiteralPath $Path -Force
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw "No se empaquetan enlaces simbolicos/junctions: $Path"
    }
    $relative = $item.FullName.Substring($repoRoot.Length + 1).Replace('\', '/')
    if ($item.PSIsContainer) {
        if ($item.Name -in $excludedDirectories -or $item.Name -like '*.egg-info') { return }
        [void]$archive.CreateEntry("$relative/")
        foreach ($child in (Get-ChildItem -LiteralPath $Path -Force)) { Add-DeploymentEntry $child.FullName }
    } elseif ($item.Extension -notin @('.pyc', '.pyo', '.log')) {
        [void][IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $item.FullName, $relative)
    }
}
try {
    foreach ($entry in $paths) { Add-DeploymentEntry (Join-Path $repoRoot $entry) }
} finally {
    $archive.Dispose()
    $stream.Dispose()
}
Write-Host "ZIP creado: $archivePath"
Write-Host "Incluye conn/ deliberadamente. No es un respaldo del volumen PostgreSQL."
if (-not $NoUpload) {
    & gsutil cp $archivePath $Bucket
    if ($LASTEXITCODE -ne 0) { throw "No se pudo subir el ZIP a $Bucket." }
}
