"""
Main entry point for Lunar Biscuit.
Manages the simulation loop and REST API server.
"""

import signal
import sys
import threading
import time
from typing import Optional

import uvicorn

from radiant_chacha.api.json_rpc import app, set_factory
from radiant_chacha.core.factory import NeighborFactory
from radiant_chacha.methods.tick import tick
from radiant_chacha.utils.log_handler import get_logger

logger = get_logger(__name__, source_file=__file__)


class SimulationLoop:
    """Manages the background simulation loop."""

    def __init__(self, factory: NeighborFactory, tick_interval: float = 0.1):
        self.factory = factory
        self.tick_interval = tick_interval
        self.running = False
        self.thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the simulation loop in a background thread."""
        if self.running:
            logger.warning("[!] Simulation already running")
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("[*] Simulation loop started")

    def stop(self) -> None:
        """Stop the simulation loop."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("[*] Simulation loop stopped")

    def _run_loop(self) -> None:
        """Run the simulation loop (intended to run in a background thread)."""
        try:
            while self.running:
                # Tick all nodes
                for node in list(self.factory.nodes):
                    try:
                        tick(obj=node, dt=self.tick_interval, print_stats=False)
                    except Exception as e:
                        logger.exception(f"[!!] Error ticking node {node.id}: {e}")

                time.sleep(self.tick_interval)
        except Exception as e:
            logger.exception(f"[!!] Simulation loop error: {e}")


def run_api_server(host: str = "127.0.0.1", port: int = 8401) -> None:
    """Run the FastAPI server (blocks until interrupted)."""
    logger.info(f"[*] Starting API server on {host}:{port}")
    logger.info(f"[*] OpenAPI docs available at http://{host}:{port}/docs")
    uvicorn.run(app, host=host, port=port, log_level="info")


def main() -> None:
    """
    Main entry point.
    Starts:
      1. Simulation loop (background thread)
      2. JSON-RPC API (FastAPI/Uvicorn)
    """
    logger.info("[*] Lunar Biscuit starting...")

    # Create factory
    factory = NeighborFactory()
    set_factory(factory)

    # Start simulation loop
    sim_loop = SimulationLoop(factory, tick_interval=0.1)
    sim_loop.start()

    # Handle graceful shutdown
    def signal_handler(sig, frame):
        logger.info("[*] Shutdown signal received, cleaning up...")
        sim_loop.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start API server (blocking)
    try:
        run_api_server(host="127.0.0.1", port=8401)
    except KeyboardInterrupt:
        logger.info("[*] API server interrupted")
        sim_loop.stop()
        sys.exit(0)


if __name__ == "__main__":
    main()
