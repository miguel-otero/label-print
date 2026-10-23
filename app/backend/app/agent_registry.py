"""Registered stations, scoped credentials and reproducible installer packages."""
import hashlib
import hmac
import json
import re
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import psycopg
from fastapi import HTTPException

from app.database import connect, queue_transaction
from app.schemas import AgentRegistration, AgentUpdate, PrinterAgentStatus
from app.settings import Settings


def clean_field(value: str, name: str) -> str:
    value = value.strip()
    if not value or len(value) > 160 or any(ord(char) < 32 for char in value):
        raise HTTPException(422, f"{name}: valor vacío, demasiado largo o con caracteres de control.")
    return value


class AgentRegistry:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _connect(self) -> psycopg.Connection:
        return connect(self.settings)

    def ensure_schema(self, conn: psycopg.Connection) -> None:
        conn.execute("""
            alter table print_agents alter column last_seen_at drop not null;
            alter table print_agents add column if not exists display_name text not null default '';
            alter table print_agents add column if not exists enabled boolean not null default true;
            alter table print_agents add column if not exists credential_version integer not null default 1;
            alter table print_agents add column if not exists installation_id text;
            alter table print_agents add column if not exists version text;
            alter table print_agents add column if not exists legacy_auth boolean not null default false;
            create table if not exists agent_admin_attempts (
                id integer primary key check(id = 1), failures integer not null,
                window_start timestamptz not null);
        """)
        conn.execute("""insert into print_agents(agent_id, printer_name, display_name, legacy_auth)
            values (%s, %s, %s, true) on conflict(agent_id) do nothing""",
            (self.settings.print_agent_id, self.settings.printer_name, self.settings.print_agent_id))
        # Existing rows predate registration. The empty display name marks only that migration.
        conn.execute("""update print_agents set display_name = agent_id,
            legacy_auth = (agent_id = %s) where display_name = ''""", (self.settings.print_agent_id,))

    def token(self, row: dict) -> str:
        secret = self.settings.agent_token_secret
        if len(secret) < 32 or secret == self.settings.print_agent_token:
            raise HTTPException(503, "Configure CLINIC_AGENT_TOKEN_SECRET con al menos 32 caracteres y distinto del token anterior.")
        message = f"clinic-agent-v1:{row['agent_id']}:{row['credential_version']}"
        return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()

    def authenticate(
        self, conn: psycopg.Connection, agent_id: str,
        installation_id: str | None, token: str | None,
    ) -> dict:
        row = conn.execute("select * from print_agents where agent_id = %s for update", (agent_id,)).fetchone()
        if row is None:
            raise HTTPException(401, "Agente no autorizado.")
        # None is reserved for trusted internal service calls, never supplied by routes.
        if token is None:
            return row
        legacy = (row["legacy_auth"] and agent_id == self.settings.print_agent_id
                  and bool(self.settings.print_agent_token)
                  and hmac.compare_digest(token.encode(), self.settings.print_agent_token.encode()))
        if legacy:
            return row
        if not hmac.compare_digest(token.encode(), self.token(row).encode()):
            raise HTTPException(401, "Credencial de agente inválida.")
        if not installation_id or not re.fullmatch(r"[0-9a-f-]{36}", installation_id):
            raise HTTPException(401, "Falta una identificación válida de instalación.")
        if row["installation_id"] and row["installation_id"] != installation_id:
            raise HTTPException(409, "Este agente está vinculado a otro equipo. Restablezca su instalación.")
        conn.execute("""update print_agents set installation_id = %s, legacy_auth = false
            where agent_id = %s""", (installation_id, agent_id))
        row.update(installation_id=installation_id, legacy_auth=False)
        return row

    def resolve(self, conn: psycopg.Connection, agent_id: str | None) -> dict:
        if not agent_id:
            rows = conn.execute("select * from print_agents where enabled order by agent_id for share").fetchall()
            if len(rows) != 1:
                raise HTTPException(400, "Seleccione el equipo y la impresora de destino.")
            return rows[0]
        row = conn.execute("select * from print_agents where agent_id = %s for share", (agent_id,)).fetchone()
        if not row or not row["enabled"]:
            raise HTTPException(400, "El agente seleccionado no existe o está deshabilitado.")
        return row

    def status(self, row: dict) -> PrinterAgentStatus:
        age = ((datetime.now(timezone.utc) - row["last_seen_at"]).total_seconds()
               if row["last_seen_at"] else float("inf"))
        return PrinterAgentStatus(
            agent_id=row["agent_id"], display_name=row["display_name"],
            printer_name=row["printer_name"], enabled=row["enabled"],
            online=age <= self.settings.print_agent_stale_seconds,
            printer_ok=row["printer_ok"], last_seen_at=row["last_seen_at"],
            message=row["message"], version=row["version"],
            paired=bool(row["installation_id"]), legacy_auth=row["legacy_auth"],
        )

    def list(self) -> list[PrinterAgentStatus]:
        if not self.settings.use_postgres:
            return []
        with self._connect() as conn:
            return [self.status(row) for row in conn.execute(
                "select * from print_agents order by display_name, agent_id").fetchall()]

    def check_admin(self, supplied: str) -> None:
        if not self.settings.agent_admin_key:
            raise HTTPException(503, "Configure CLINIC_AGENT_ADMIN_KEY con una clave no vacía.")
        denied = False
        with self._connect() as conn:
            conn.execute("""insert into agent_admin_attempts values (1, 0, now())
                on conflict(id) do nothing""")
            row = conn.execute("""select *, window_start > now() - interval '5 minutes' as recent
                from agent_admin_attempts where id = 1 for update""").fetchone()
            if row["recent"] and row["failures"] >= 10:
                raise HTTPException(429, "Demasiados intentos. Espere cinco minutos.")
            if not row["recent"]:
                conn.execute("update agent_admin_attempts set failures = 0, window_start = now() where id = 1")
            if not hmac.compare_digest(supplied.encode(), self.settings.agent_admin_key.encode()):
                conn.execute("update agent_admin_attempts set failures = failures + 1 where id = 1")
                denied = True
        if denied:
            raise HTTPException(401, "Clave de administrador incorrecta.")

    def save(self, payload: AgentRegistration | AgentUpdate, agent_id: str | None = None) -> PrinterAgentStatus:
        creating = agent_id is None
        with self._connect() as conn:
            queue_transaction(conn)
            # Serializes registration and enable/reset operations.
            conn.execute("select pg_advisory_xact_lock(749812003)")
            if agent_id is None:
                self.token({"agent_id": "validation", "credential_version": 1})
                agent_id = f"windows-{uuid4().hex[:16]}"
                conn.execute("""insert into print_agents(agent_id, display_name, printer_name, enabled)
                    values (%s, %s, %s, false)""",
                    (agent_id, clean_field(payload.display_name, "Nombre"), clean_field(payload.printer_name, "Impresora")))
            row = conn.execute("select * from print_agents where agent_id = %s for update", (agent_id,)).fetchone()
            if not row:
                raise HTTPException(404, "Agente no encontrado.")
            values = payload.model_dump(exclude_unset=True)
            if creating:
                values.setdefault("enabled", payload.enabled)
            if values.get("enabled", row["enabled"]):
                legacy = conn.execute("""select 1 from print_agents
                    where agent_id <> %s and enabled and legacy_auth limit 1""", (agent_id,)).fetchone()
                if legacy:
                    raise HTTPException(409, "Actualice el agente inicial con su nuevo ZIP antes de habilitar otra estación.")
            for field in ("display_name", "printer_name"):
                if field in values:
                    values[field] = clean_field(values[field], field)
            if "printer_name" in values and values["printer_name"] != row["printer_name"]:
                if conn.execute("""select 1 from print_jobs where target_agent_id = %s
                    and status in ('queued', 'processing') limit 1""", (agent_id,)).fetchone():
                    raise HTTPException(409, "Espere a terminar los trabajos antes de cambiar la impresora.")
            row.update(values)
            conn.execute("""update print_agents set display_name = %s, printer_name = %s,
                enabled = %s where agent_id = %s""",
                (row["display_name"], row["printer_name"], row["enabled"], agent_id))
            return self.status(row)

    def reset(self, agent_id: str) -> PrinterAgentStatus:
        with self._connect() as conn:
            queue_transaction(conn)
            conn.execute("select pg_advisory_xact_lock(749812003)")
            row = conn.execute("select * from print_agents where agent_id = %s for update", (agent_id,)).fetchone()
            if not row:
                raise HTTPException(404, "Agente no encontrado.")
            if conn.execute("""select 1 from print_jobs where target_agent_id = %s
                and status = 'processing' limit 1""", (agent_id,)).fetchone():
                raise HTTPException(409, "El agente tiene una impresión activa.")
            row = conn.execute("""update print_agents set installation_id = null, legacy_auth = false,
                credential_version = credential_version + 1, last_seen_at = null, printer_ok = false,
                message = null where agent_id = %s returning *""", (agent_id,)).fetchone()
            return self.status(row)

    def release(self) -> tuple[Path, dict]:
        root = Path(self.settings.agent_release_dir).resolve()
        try:
            manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
            filename = manifest["filename"]
            version = manifest["version"]
            if (not re.fullmatch(r"\d+\.\d+\.\d+", version)
                    or filename != f"ClinicLabelPrintAgent-Setup-{version}-x64.exe"):
                raise ValueError("filename")
            path = root / filename
            if path.is_symlink() or not 0 < path.stat().st_size <= 100 * 1024 * 1024:
                raise ValueError("size")
            with path.open("rb") as source:
                digest = hashlib.file_digest(source, "sha256").hexdigest()
            checksum = (root / f"{filename}.sha256").read_text().split()[0]
            if digest != manifest["sha256"] or digest != checksum:
                raise ValueError("checksum")
            return path, manifest
        except (OSError, ValueError, KeyError, IndexError, TypeError):
            raise HTTPException(503, "El instalador no está disponible o su checksum no coincide.") from None

    def package(self, agent_id: str) -> Path:
        path, manifest = self.release()
        parsed = urlsplit(self.settings.agent_public_api_url)
        if (parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.query
                or parsed.fragment or parsed.username or parsed.password):
            raise HTTPException(503, "Configure CLINIC_AGENT_PUBLIC_API_URL con la URL pública de la API.")
        with self._connect() as conn:
            row = conn.execute("select * from print_agents where agent_id = %s", (agent_id,)).fetchone()
            if not row:
                raise HTTPException(404, "Agente no encontrado.")
            values = {
                "CLINIC_AGENT_SERVER_URL": self.settings.agent_public_api_url.rstrip("/"),
                "CLINIC_PRINT_AGENT_TOKEN": self.token(row), "CLINIC_PRINT_AGENT_ID": row["agent_id"],
                "CLINIC_PRINTER_NAME": row["printer_name"],
                "CLINIC_AGENT_POLL_SECONDS": str(self.settings.agent_poll_seconds),
                "CLINIC_AGENT_HEARTBEAT_SECONDS": str(self.settings.agent_heartbeat_seconds),
                "CLINIC_AGENT_REQUEST_TIMEOUT_SECONDS": str(self.settings.agent_request_timeout_seconds),
            }
        configuration = "".join(f"{key}={clean_field(value, key)}\r\n" for key, value in values.items())
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temporary:
            package = Path(temporary.name)
        try:
            with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.write(path, path.name)
                archive.writestr(f"{path.name}.sha256", f"{manifest['sha256']}  {path.name}\n")
                archive.writestr("agent.env", configuration)
                archive.writestr("LEEME.txt",
                    f"Estación: {row['display_name']}\r\nImpresora: {row['printer_name']}\r\n\r\n"
                    "Extraiga todos los archivos en la misma carpeta y ejecute el instalador como administrador.\r\n"
                    "Importe el archivo agent.env incluido, también al actualizar una instalación existente.\r\n"
                    "Verifique que el nombre de la cola de Windows coincida exactamente con la impresora indicada.\r\n"
                    "Este paquete contiene una credencial privada: úselo solo en el equipo registrado.\r\n"
                    "No inicie la consola mientras el servicio esté funcionando.\r\n")
            return package
        except Exception:
            package.unlink(missing_ok=True)
            raise
