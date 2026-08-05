from __future__ import annotations

import logging
import os
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path

import servicemanager
import win32event
import win32service
import win32serviceutil

from agent.client import AgentClient
from agent.config import AgentConfig


class ClinicPrintAgentService(win32serviceutil.ServiceFramework):
    _svc_name_ = "ClinicLabelPrintAgent"
    _svc_display_name_ = "Clinic Label Print Agent"
    _svc_description_ = "Recibe trabajos ZPL del servidor y los envia a la cola Zebra local."

    def __init__(self, args) -> None:
        super().__init__(args)
        self.stop_event = threading.Event()
        self.service_stop = win32event.CreateEvent(None, 0, 0, None)

    def SvcStop(self) -> None:
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.stop_event.set()
        win32event.SetEvent(self.service_stop)

    def SvcDoRun(self) -> None:
        self._configure_logging()
        servicemanager.LogInfoMsg("Clinic Label Print Agent iniciado")
        try:
            AgentClient(AgentConfig.load(), self.stop_event).run()
        except Exception:
            logging.exception("El servicio termino por un error")
            raise

    @staticmethod
    def _configure_logging() -> None:
        root = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "ClinicLabelPrint" / "logs"
        root.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(root / "agent.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8")
        logging.basicConfig(level=logging.INFO, handlers=[handler], format="%(asctime)s %(levelname)s %(message)s")


if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(ClinicPrintAgentService)
