"""Non-operational regression checks: all mutable inputs live in temporary projects."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile


REPO = Path(__file__).resolve().parents[2]
POWERSHELL = shutil.which("powershell.exe") or shutil.which("pwsh")
GIT_BASH = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/bin/bash.exe"
BASH = str(GIT_BASH) if GIT_BASH.is_file() else shutil.which("bash")
ENTRY_POINTS = (
    "start", "startup", "update_zip", "install-print-agent", "run-print-agent",
    "uninstall-print-agent", "build-print-agent-installer",
)


def ps_literal(value: str | Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


class ScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="label-script-tests-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "project with spaces"
        self.root.mkdir()
        shutil.copytree(REPO / "scripts", self.root / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
        for entry in (REPO / "scripts/deploy-files.txt").read_text().splitlines():
            target = self.root / entry
            if target.exists():
                continue
            if "." in target.name or target.name.startswith("."):
                target.write_text("fixture\n", encoding="utf-8")
            else:
                target.mkdir(parents=True)
        (self.root / "conn/.env").write_text("TEST_PLACEHOLDER=not-a-secret\n", encoding="utf-8")
        (self.root / "storage/label-images").mkdir()
        (self.root / "storage/label-images/logo.png").write_bytes(b"test-logo")
        (self.root / "packaging/installer.iss").write_text("fixture", encoding="utf-8")
        for directory in ("node_modules", ".venv", "build", "dist", "__pycache__", "example.egg-info"):
            target = self.root / "app" / directory
            target.mkdir()
            (target / "excluded.txt").write_text("excluded", encoding="utf-8")

    def ps(self, code: str, success: bool = True) -> subprocess.CompletedProcess:
        if not POWERSHELL:
            self.skipTest("PowerShell is not installed")
        result = subprocess.run(
            [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", code],
            text=True, capture_output=True, timeout=45,
        )
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def bash(self, command: str, *arguments: str, success: bool = True, env: dict | None = None):
        if not BASH:
            self.skipTest("Bash is not installed")
        if os.name == "nt" and GIT_BASH.is_file():
            # Drive letters are accepted as command paths but not as PATH entries.
            arguments = tuple(
                f"/{value[0].lower()}{value[2:]}" if len(value) > 2 and value[1:3] == ":/" else value
                for value in arguments
            )
        result = subprocess.run(
            [BASH, "-c", command, "tests", *arguments],
            text=True, capture_output=True, timeout=30, env=env,
        )
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_platform_entry_points_and_shell_line_endings(self):
        for name in ENTRY_POINTS:
            self.assertTrue((REPO / f"scripts/powershell/{name}.ps1").is_file())
            shell_file = REPO / f"scripts/linux/{name}.sh"
            self.assertTrue(shell_file.is_file())
            self.assertNotIn(b"\r", shell_file.read_bytes())
        self.assertEqual(list((REPO / "scripts").glob("*.ps1")), [])
        self.assertEqual(list((REPO / "scripts").glob("*.sh")), [])

    def test_powershell_syntax(self):
        self.ps(
            "$ErrorActionPreference='Stop'; "
            f"Get-ChildItem -LiteralPath {ps_literal(REPO / 'scripts/powershell')} -Filter *.ps1 | ForEach-Object {{ "
            "$tokens=$null; $errors=$null; "
            "[void][System.Management.Automation.Language.Parser]::ParseFile($_.FullName, [ref]$tokens, [ref]$errors); "
            "if ($errors) { throw ($errors | Out-String) } }"
        )

    def test_bash_syntax(self):
        self.bash('for script in "$1"/*.sh; do bash -n "$script" || exit; done', (REPO / "scripts/linux").as_posix())

    def test_linux_help_and_invalid_tool_do_not_install(self):
        script = (self.root / "scripts/linux/startup.sh").as_posix()
        result = self.bash('bash "$1" --help', script)
        self.assertIn("Compose", result.stdout)
        self.bash('bash "$1" -t aws', script, success=False)
        self.bash('bash "$1" -t', script, success=False)

    def test_linux_start_without_env_fails(self):
        (self.root / "conn/.env").unlink()
        result = self.bash('bash "$1"', (self.root / "scripts/linux/start.sh").as_posix(), success=False)
        self.assertIn("conn/.env", result.stderr)

    def test_linux_start_with_mock_docker(self):
        mock_bin = self.root / "mock-bin"
        mock_bin.mkdir()
        mock = mock_bin / "docker"
        mock.write_text('#!/usr/bin/env bash\nprintf "%s\\n" "$*" >> "$TEST_LOG"\n', encoding="utf-8")
        mock.chmod(0o755)
        log = self.root / "docker-calls.txt"
        self.bash(
            'export PATH="$1:$PATH" TEST_LOG="$2"; bash "$3" --build --logs',
            mock_bin.as_posix(), log.as_posix(), (self.root / "scripts/linux/start.sh").as_posix(),
        )
        calls = log.read_text()
        self.assertIn("up -d --build", calls)
        self.assertIn("logs -f", calls)
        self.assertIn("conn/.env", calls)

    def test_powershell_start_with_mock_docker(self):
        log = self.root / "docker-calls.jsonl"
        self.ps(
            f"$env:TEST_LOG={ps_literal(log)}; "
            "function docker { $global:LASTEXITCODE=0; ConvertTo-Json -InputObject @($args) -Compress | Add-Content -LiteralPath $env:TEST_LOG }; "
            f"& {ps_literal(self.root / 'scripts/powershell/start.ps1')} -Build -Logs"
        )
        calls = [json.loads(line) for line in log.read_text(encoding="utf-8-sig").splitlines()]
        self.assertEqual(calls[0], ["info"])
        self.assertEqual(calls[1], ["compose", "version"])
        self.assertIn(["up", "-d", "--build"], [call[-3:] for call in calls])
        self.assertEqual(calls[-1][-2:], ["logs", "-f"])

    def test_powershell_docker_failure_is_reported(self):
        result = self.ps(
            "function docker { $global:LASTEXITCODE=42 }; "
            f"& {ps_literal(self.root / 'scripts/powershell/start.ps1')}", success=False,
        )
        self.assertIn("Docker is not running", result.stderr)

    def test_powershell_zip_includes_hidden_env_logos_and_packaging(self):
        script = self.root / "scripts/powershell/update_zip.ps1"
        self.ps(f"& {ps_literal(script)} -NoUpload")
        archive = self.root / "artifacts/deploy/deploy.zip"
        with zipfile.ZipFile(archive) as bundle:
            names = set(bundle.namelist())
            for name in ("conn/.env", "storage/label-images/logo.png", "packaging/installer.iss", "docker-compose.yml", ".gitignore"):
                self.assertIn(name, names)
            self.assertFalse(any(name.endswith("excluded.txt") for name in names))
        (self.root / "storage/label-images/logo.png").unlink()
        self.ps(f"& {ps_literal(script)} -NoUpload")
        with zipfile.ZipFile(archive) as bundle:
            self.assertNotIn("storage/label-images/logo.png", bundle.namelist())

    def test_powershell_zip_upload_failure_is_reported(self):
        self.ps(
            "function gsutil { $global:LASTEXITCODE=42 }; "
            f"& {ps_literal(self.root / 'scripts/powershell/update_zip.ps1')}", success=False,
        )

    def test_linux_zip_arguments_include_complete_manifest(self):
        mock_bin = self.root / "mock-bin"
        mock_bin.mkdir()
        zip_mock = mock_bin / "zip"
        zip_mock.write_text('#!/usr/bin/env bash\nprintf "%s\\n" "$@" > "$TEST_LOG"\n', encoding="utf-8")
        zip_mock.chmod(0o755)
        log = self.root / "zip-calls.txt"
        self.bash(
            'export PATH="$1:$PATH" TEST_LOG="$2"; bash "$3" --no-upload',
            mock_bin.as_posix(), log.as_posix(), (self.root / "scripts/linux/update_zip.sh").as_posix(),
        )
        calls = log.read_text().splitlines()
        for name in (REPO / "scripts/deploy-files.txt").read_text().splitlines():
            self.assertIn(name, calls)
        self.assertIn("*/node_modules/*", calls)

    def test_linux_zip_rejects_missing_required_directory(self):
        (self.root / "packaging/installer.iss").unlink()
        (self.root / "packaging").rmdir()
        self.bash(
            'zip() { :; }; export -f zip; bash "$1" --no-upload',
            (self.root / "scripts/linux/update_zip.sh").as_posix(), success=False,
        )

    def test_linux_agent_bridge_requires_windows_interop(self):
        self.bash(
            'source "$1"; command() { return 1; }; run_windows_agent_script run-print-agent',
            (self.root / "scripts/linux/windows-agent-common.sh").as_posix(), success=False,
        )

    def test_linux_agent_bridge_preserves_arguments(self):
        result = self.bash(
            'source "$1"; wslpath() { printf "%s\\n" "$2"; }; '
            'powershell.exe() { printf "[%s]\\n" "$@"; }; '
            'export -f wslpath powershell.exe; '
            'run_windows_agent_script install-print-agent -PrinterName "Printer with spaces" -ServerUrl "http://host:8080/api"',
            (self.root / "scripts/linux/windows-agent-common.sh").as_posix(),
        )
        self.assertIn("[Printer with spaces]", result.stdout)
        self.assertIn("[http://host:8080/api]", result.stdout)

    def test_agent_detection_uses_custom_installer_location(self):
        if os.name != "nt":
            self.skipTest("Registry/service mocks require Windows paths")
        installed = self.root / "custom-agent"
        (installed / "agent").mkdir(parents=True)
        (installed / "agent/ClinicLabelPrintAgent.exe").touch()
        result = self.ps(
            f". {ps_literal(REPO / 'scripts/powershell/windows-agent-common.ps1')}; "
            f"$script:mockLocation={ps_literal(installed)}; "
            "function Get-ItemProperty { param($LiteralPath, $ErrorAction); "
            "if ($LiteralPath -like '*Uninstall*') { [PSCustomObject]@{InstallLocation=$script:mockLocation} } }; "
            "Get-WindowsAgentInstallation | ConvertTo-Json -Compress"
        )
        actual = json.loads(result.stdout)
        self.assertEqual(actual["Kind"], "Installer")
        self.assertEqual(Path(actual["Root"]), installed)

    def test_agent_detection_falls_back_to_legacy(self):
        if os.name != "nt":
            self.skipTest("Registry/service mocks require Windows paths")
        result = self.ps(
            f". {ps_literal(REPO / 'scripts/powershell/windows-agent-common.ps1')}; "
            f"$env:ProgramData={ps_literal(self.root)}; "
            "$env:ProgramFiles=$env:ProgramW6432=${env:ProgramFiles(x86)}=$env:ProgramData; "
            "function Get-ItemProperty { param($LiteralPath, $ErrorAction) }; "
            "Get-WindowsAgentInstallation | ConvertTo-Json -Compress"
        )
        self.assertEqual(json.loads(result.stdout)["Kind"], "Legacy")

    def test_running_agent_is_rejected_without_starting_a_process(self):
        if os.name != "nt":
            self.skipTest("Service mocks require Windows")
        common = self.root / "scripts/powershell/windows-agent-common.ps1"
        common.write_text(
            "function Assert-WindowsAgentPlatform {}\n"
            "function Get-WindowsAgentInstallation { [PSCustomObject]@{Executable=$PSCommandPath; Kind='Installer'} }\n"
            "function Get-Service { param($Name, $ErrorAction); [PSCustomObject]@{Status='Running'} }\n",
            encoding="utf-8",
        )
        result = self.ps(f"& {ps_literal(self.root / 'scripts/powershell/run-print-agent.ps1')}", success=False)
        self.assertIn("dos consumidores", result.stderr)

    def test_installer_uninstall_uses_inno_and_preserves_data(self):
        if os.name != "nt":
            self.skipTest("Windows service mocks require Windows")
        uninstaller = self.root / "unins000.exe"
        uninstaller.touch()
        log = self.root / "uninstaller-calls.txt"
        common = self.root / "scripts/powershell/windows-agent-common.ps1"
        common.write_text(
            "function Assert-WindowsAgentPlatform {}\n"
            "function Assert-WindowsAgentAdministrator {}\n"
            f"function Get-WindowsAgentInstallation {{ [PSCustomObject]@{{Kind='Installer'; Root={ps_literal(self.root)}; Uninstaller={ps_literal(uninstaller)}}} }}\n"
            "function Get-Service { param($Name, $ErrorAction) }\n"
            "function Start-Process { param($FilePath, $ArgumentList, $WindowStyle, [switch]$Wait, [switch]$PassThru); "
            f"$FilePath | Set-Content -LiteralPath {ps_literal(log)}; [PSCustomObject]@{{ExitCode=0}} }}\n",
            encoding="utf-8",
        )
        self.ps(f"& {ps_literal(self.root / 'scripts/powershell/uninstall-print-agent.ps1')}")
        self.assertEqual(Path(log.read_text().strip()), uninstaller)
        self.assertTrue((self.root / "conn/.env").exists())

    def test_installer_console_runs_without_python_venv(self):
        if os.name != "nt":
            self.skipTest("Windows service mocks require Windows")
        executable = self.root / "fake-agent.ps1"
        log = self.root / "console-calls.txt"
        executable.write_text(
            f"'installer' | Set-Content -LiteralPath {ps_literal(log)}; $global:LASTEXITCODE=0\n",
            encoding="utf-8",
        )
        (self.root / "scripts/powershell/windows-agent-common.ps1").write_text(
            "function Assert-WindowsAgentPlatform {}\n"
            f"function Get-WindowsAgentInstallation {{ [PSCustomObject]@{{Kind='Installer'; Executable={ps_literal(executable)}}} }}\n"
            "function Get-Service { param($Name, $ErrorAction) }\n",
            encoding="utf-8",
        )
        self.ps(f"& {ps_literal(self.root / 'scripts/powershell/run-print-agent.ps1')}")
        self.assertEqual(log.read_text().strip(), "installer")


if __name__ == "__main__":
    unittest.main()
