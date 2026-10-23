"""Stage/verify exactly one versioned installer for offline server distribution."""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(directory: Path) -> dict:
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    filename = manifest["filename"]
    version = manifest["version"]
    if not re.fullmatch(r"\d+\.\d+\.\d+", version) or filename != f"ClinicLabelPrintAgent-Setup-{version}-x64.exe":
        raise ValueError("Nombre o versión de instalador inválidos.")
    allowed = {filename, f"{filename}.sha256", "manifest.json", ".gitkeep"}
    if any(path.name not in allowed or path.is_symlink() or not path.is_file() for path in directory.iterdir()):
        raise ValueError("La carpeta de distribución contiene archivos ajenos al manifiesto.")
    digest = checksum(directory / filename)
    if digest != manifest["sha256"] or digest != (directory / f"{filename}.sha256").read_text().split()[0]:
        raise ValueError("Checksum de instalador incorrecto.")
    return manifest


def stage(installer: Path, directory: Path) -> None:
    match = re.fullmatch(r"ClinicLabelPrintAgent-Setup-(\d+\.\d+\.\d+)-x64\.exe", installer.name)
    if not match or installer.is_symlink():
        raise ValueError("Instalador inválido.")
    digest = checksum(installer)
    if digest != Path(f"{installer}.sha256").read_text().split()[0]:
        raise ValueError("El checksum del artefacto no coincide.")
    directory.mkdir(parents=True, exist_ok=True)
    # Reject unexpected files; never delete unknown user content or secret packages.
    if (directory / "manifest.json").exists():
        previous = verify(directory)
        for name in (previous["filename"], f"{previous['filename']}.sha256", "manifest.json"):
            (directory / name).unlink()
    elif any(path.name != ".gitkeep" for path in directory.iterdir()):
        raise ValueError("La carpeta de destino debe estar vacía o contener una versión válida.")
    shutil.copy2(installer, directory / installer.name)
    shutil.copy2(Path(f"{installer}.sha256"), directory / f"{installer.name}.sha256")
    manifest = {"version": match[1], "filename": installer.name, "sha256": digest}
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    verify(directory)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installer", type=Path)
    parser.add_argument("--directory", type=Path, default=Path(__file__).resolve().parents[1] / "storage/agent-release")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        result = verify(args.directory)
        print(f"Instalador {result['version']} verificado.")
    elif args.installer:
        stage(args.installer, args.directory)
        print("Instalador preparado.")
    else:
        parser.error("Indique --installer o --verify.")
