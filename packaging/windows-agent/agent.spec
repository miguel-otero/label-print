import os
from pathlib import Path


repo_root = Path(SPECPATH).parents[1]
agent_root = repo_root / "app" / "windows_agent"

analysis = Analysis(
    [str(agent_root / "agent" / "console.py")],
    pathex=[str(agent_root)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(analysis.pure)

executable = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="ClinicLabelPrintAgent",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    version=os.environ.get("CLINIC_AGENT_VERSION_FILE"),
)

bundle = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ClinicLabelPrintAgent",
)
