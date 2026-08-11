from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


DEFAULT_CONFIG = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "ClinicLabelPrint" / "agent.env"


def load_env_file(path: Path) -> None:
    if not path.exists():
        raise RuntimeError(f"No se encontro la configuracion del agente: {path}")
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass(frozen=True)
class AgentConfig:
    server_url: str
    token: str
    agent_id: str
    printer_name: str
    poll_seconds: float
    heartbeat_seconds: float
    request_timeout_seconds: float

    @classmethod
    def load(cls, path: Path | None = None) -> "AgentConfig":
        load_env_file(path or DEFAULT_CONFIG)
        server_url = os.environ.get("CLINIC_AGENT_SERVER_URL", "").rstrip("/")
        token = os.environ.get("CLINIC_PRINT_AGENT_TOKEN", "")
        printer_name = os.environ.get("CLINIC_PRINTER_NAME", "")
        if not server_url or not token or not printer_name:
            raise RuntimeError(
                "CLINIC_AGENT_SERVER_URL, CLINIC_PRINT_AGENT_TOKEN y CLINIC_PRINTER_NAME son obligatorios."
            )
        parsed_url = urlparse(server_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise RuntimeError("CLINIC_AGENT_SERVER_URL debe ser una URL HTTP o HTTPS valida.")

        poll_seconds = _positive_float("CLINIC_AGENT_POLL_SECONDS", "1")
        heartbeat_seconds = _positive_float("CLINIC_AGENT_HEARTBEAT_SECONDS", "10")
        request_timeout_seconds = _positive_float("CLINIC_AGENT_REQUEST_TIMEOUT_SECONDS", "15")
        return cls(
            server_url=server_url,
            token=token,
            agent_id=os.environ.get("CLINIC_PRINT_AGENT_ID", "windows-primary"),
            printer_name=printer_name,
            poll_seconds=poll_seconds,
            heartbeat_seconds=heartbeat_seconds,
            request_timeout_seconds=request_timeout_seconds,
        )


def _positive_float(name: str, default: str) -> float:
    raw_value = os.environ.get(name, default)
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} debe ser un numero valido.") from exc
    if value <= 0:
        raise RuntimeError(f"{name} debe ser mayor que cero.")
    return value
