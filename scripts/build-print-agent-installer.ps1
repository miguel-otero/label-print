param(
    [string]$Version,
    [string]$InnoCompilerPath,
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$agentRoot = Join-Path $repoRoot "app\windows_agent"
$packagingRoot = Join-Path $repoRoot "packaging\windows-agent"
$buildRoot = Join-Path $repoRoot ".build\windows-agent"
$artifactRoot = Join-Path $repoRoot "artifacts\windows-agent"
$venvRoot = Join-Path $buildRoot "venv"
$python = Join-Path $venvRoot "Scripts\python.exe"
$winswVersion = "2.12.0"
$winswSha256 = "05B82D46AD331CC16BDC00DE5C6332C1EF818DF8CEEFCD49C726553209B3A0DA"
$winswCache = Join-Path $buildRoot "cache\WinSW-x64-$winswVersion.exe"
$payloadRoot = Join-Path $buildRoot "payload"
$distRoot = Join-Path $buildRoot "pyinstaller-dist"
$workRoot = Join-Path $buildRoot "pyinstaller-work"
$versionFile = Join-Path $buildRoot "version-info.txt"

if (-not $Version) {
    $match = Select-String -Path (Join-Path $agentRoot "pyproject.toml") -Pattern '^version\s*=\s*"([^"]+)"$'
    if (-not $match) { throw "No se pudo leer la version desde pyproject.toml." }
    $Version = $match.Matches[0].Groups[1].Value
}
if ($Version -notmatch '^\d+\.\d+\.\d+$') {
    throw "La version debe usar el formato SemVer X.Y.Z."
}

$versionParts = $Version.Split('.') | ForEach-Object { [int]$_ }
New-Item -ItemType Directory -Path $buildRoot, $artifactRoot, (Split-Path $winswCache) -Force | Out-Null

if (-not (Test-Path $python)) {
    py -3.12 -m venv $venvRoot
    if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el entorno de compilacion con Python 3.12." }
}
& $python -m pip install --disable-pip-version-check -r (Join-Path $agentRoot "requirements-build.txt")
if ($LASTEXITCODE -ne 0) { throw "No se pudieron instalar las dependencias de compilacion." }

if (-not (Test-Path $winswCache)) {
    Invoke-WebRequest -Uri "https://github.com/winsw/winsw/releases/download/v$winswVersion/WinSW-x64.exe" -OutFile $winswCache -UseBasicParsing
}
$actualWinSwHash = (Get-FileHash -Algorithm SHA256 $winswCache).Hash
if ($actualWinSwHash -ne $winswSha256) {
    throw "El checksum de WinSW no coincide. Esperado: $winswSha256. Recibido: $actualWinSwHash."
}

$versionInfo = @"
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=($($versionParts[0]), $($versionParts[1]), $($versionParts[2]), 0),
    prodvers=($($versionParts[0]), $($versionParts[1]), $($versionParts[2]), 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'Clinic Label Print'),
         StringStruct(u'FileDescription', u'Clinic Label Print Agent'),
         StringStruct(u'FileVersion', u'$Version'),
         StringStruct(u'InternalName', u'ClinicLabelPrintAgent'),
         StringStruct(u'OriginalFilename', u'ClinicLabelPrintAgent.exe'),
         StringStruct(u'ProductName', u'Clinic Label Print Agent'),
         StringStruct(u'ProductVersion', u'$Version')])
    ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"@
Set-Content -LiteralPath $versionFile -Value $versionInfo -Encoding UTF8

Remove-Item -LiteralPath $payloadRoot, $distRoot, $workRoot -Recurse -Force -ErrorAction SilentlyContinue
$env:CLINIC_AGENT_VERSION_FILE = $versionFile
try {
    & $python -m PyInstaller --noconfirm --clean --distpath $distRoot --workpath $workRoot (Join-Path $packagingRoot "agent.spec")
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller no pudo compilar el agente." }
} finally {
    Remove-Item Env:CLINIC_AGENT_VERSION_FILE -ErrorAction SilentlyContinue
}

New-Item -ItemType Directory -Path $payloadRoot -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $distRoot "ClinicLabelPrintAgent") -Destination (Join-Path $payloadRoot "agent") -Recurse
Copy-Item -LiteralPath $winswCache -Destination (Join-Path $payloadRoot "ClinicLabelPrintAgent.exe")
Copy-Item -LiteralPath (Join-Path $packagingRoot "ClinicLabelPrintAgent.xml") -Destination $payloadRoot

& (Join-Path $payloadRoot "agent\ClinicLabelPrintAgent.exe") --help
if ($LASTEXITCODE -ne 0) { throw "El ejecutable compilado no supera la prueba de arranque." }

if ($SkipInstaller) {
    Write-Host "Agente compilado en $payloadRoot"
    exit 0
}

if (-not $InnoCompilerPath) {
    $programFilesX86 = [Environment]::GetFolderPath([Environment+SpecialFolder]::ProgramFilesX86)
    $innoCandidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
        (Join-Path $programFilesX86 "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
    )
    $InnoCompilerPath = $innoCandidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
}
if (-not $InnoCompilerPath -or -not (Test-Path $InnoCompilerPath)) {
    throw "No se encontro ISCC.exe. Instale Inno Setup 6 o use -InnoCompilerPath."
}

& $InnoCompilerPath "/DAppVersion=$Version" "/DPayloadDir=$payloadRoot" "/DOutputDir=$artifactRoot" (Join-Path $packagingRoot "installer.iss")
if ($LASTEXITCODE -ne 0) { throw "Inno Setup no pudo generar el instalador." }

$installer = Join-Path $artifactRoot "ClinicLabelPrintAgent-Setup-$Version-x64.exe"
if (-not (Test-Path $installer)) { throw "No se encontro el instalador esperado: $installer" }
$hash = (Get-FileHash -Algorithm SHA256 $installer).Hash.ToLowerInvariant()
$checksumPath = "$installer.sha256"
Set-Content -LiteralPath $checksumPath -Value "$hash *$(Split-Path $installer -Leaf)" -Encoding ASCII

Write-Host "Instalador: $installer"
Write-Host "Checksum: $checksumPath"
