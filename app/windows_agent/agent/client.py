from __future__ import annotations

import json
import logging
import threading
import time
import urllib.error
import urllib.request

from agent.config import AgentConfig
from agent.spooler import WindowsSpooler


class AgentClient:
    def __init__(self, config: AgentConfig, stop_event: threading.Event) -> None:
        self.config = config
        self.stop_event = stop_event
        self.spooler = WindowsSpooler(config.printer_name)
        self.last_heartbeat = 0.0

    def run(self) -> None:
        logging.info("Agente iniciado: %s -> %s", self.config.agent_id, self.config.server_url)
        while not self.stop_event.is_set():
            try:
                self._heartbeat_if_due()
                job = self._request("POST", "/agente/trabajos/reclamar", {"agent_id": self.config.agent_id})
                if job:
                    self._process(job)
                    continue
            except Exception:
                logging.exception("Error en el ciclo del agente")
            self.stop_event.wait(self.config.poll_seconds)

    def _heartbeat_if_due(self) -> None:
        now = time.monotonic()
        if now - self.last_heartbeat < self.config.heartbeat_seconds:
            return
        printer_ok = True
        message = None
        try:
            self.spooler.test()
        except Exception as exc:
            printer_ok = False
            message = str(exc)
        self._request(
            "POST",
            "/agente/heartbeat",
            {
                "agent_id": self.config.agent_id,
                "printer_name": self.config.printer_name,
                "printer_ok": printer_ok,
                "message": message,
            },
        )
        self.last_heartbeat = now

    def _process(self, job: dict) -> None:
        logging.info("Procesando trabajo %s (%s)", job["id"], job["kind"])
        results = []
        for document in job["documents"]:
            try:
                if job["kind"] == "printer_test":
                    self.spooler.test()
                else:
                    self.spooler.send(document["zpl"])
                results.append({"document_id": document["id"], "ok": True})
            except Exception as exc:
                logging.exception("Fallo documento %s", document["id"])
                results.append({"document_id": document["id"], "ok": False, "message": str(exc)})
        self._request(
            "POST",
            f"/agente/trabajos/{job['id']}/resultado",
            {"agent_id": self.config.agent_id, "documents": results},
        )

    def _request(self, method: str, path: str, payload: dict | None = None):
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            f"{self.config.server_url}{path}",
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.config.token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.request_timeout_seconds) as response:
                if response.status == 204:
                    return None
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"API {exc.code}: {body}") from exc
