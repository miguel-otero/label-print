import logging
import threading

from agent.client import AgentClient
from agent.config import AgentConfig


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    stop_event = threading.Event()
    try:
        AgentClient(AgentConfig.load(), stop_event).run()
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    main()
