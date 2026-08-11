import argparse
import logging
import threading
from pathlib import Path

from agent.client import AgentClient
from agent.config import AgentConfig
from agent.spooler import WindowsSpooler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clinic Label Print Agent")
    parser.add_argument(
        "--check-config",
        type=Path,
        metavar="PATH",
        help="Valida la configuracion y el acceso a la impresora sin iniciar el agente.",
    )
    return parser.parse_args()


def check_config(path: Path) -> None:
    config = AgentConfig.load(path)
    WindowsSpooler(config.printer_name).check_exists()
    print(f"Configuracion valida. Impresora registrada: {config.printer_name}")


def main() -> None:
    args = parse_args()
    if args.check_config:
        check_config(args.check_config)
        return
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    stop_event = threading.Event()
    try:
        AgentClient(AgentConfig.load(), stop_event).run()
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    main()
