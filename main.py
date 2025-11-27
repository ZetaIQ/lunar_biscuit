"""
Main entry point for Lunar Biscuit.
Runs the API server with self-ticking nodes in the background.
"""

import asyncio
import signal
import sys
import threading
from typing import Optional

import uvicorn

from radiant_chacha.api.json_rpc import app, set_factory
from radiant_chacha.core.factory import NeighborFactory
from radiant_chacha.utils.log_handler import get_logger

logger = get_logger(__name__, source_file=__file__)


class AsyncEventLoopThread:
    """Runs an asyncio event loop in a background thread."""

    def __init__(self):
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None
        self.running = False

    def start(self) -> asyncio.AbstractEventLoop:
        """Start the event loop in a background thread and return it."""
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        # Wait for the loop to be created
        while self.loop is None:
            pass
        logger.info("[*] Async event loop started")
        return self.loop

    def stop(self) -> None:
        """Stop the event loop."""
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("[*] Async event loop stopped")

    def _run_loop(self) -> None:
        """Run the event loop."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_forever()
        except Exception as e:
            logger.exception(f"[!!] Event loop error: {e}")
        finally:
            self.loop.close()


def run_api_server(host: str = "127.0.0.1", port: int = 8401) -> None:
    """Run the FastAPI server (blocks until interrupted)."""
    logger.info(f"[*] Starting API server on {host}:{port}")
    logger.info(f"[*] OpenAPI docs available at http://{host}:{port}/docs")
    uvicorn.run(app, host=host, port=port, log_level="info")


def main() -> None:
    """
    Main entry point.
    Starts:
      1. Asyncio event loop (background thread) for node self-ticking
      2. NeighborFactory with event loop reference
      3. REST API (FastAPI/Uvicorn, blocking)
    """
    logger.info("[*] Lunar Biscuit starting...")

    # Start asyncio event loop in background thread
    loop_thread = AsyncEventLoopThread()
    event_loop = loop_thread.start()

    # Create factory and register it with the event loop
    factory = NeighborFactory()
    factory.set_event_loop(event_loop)
    set_factory(factory)

    # Handle graceful shutdown
    def signal_handler(sig, frame):
        logger.info("[*] Shutdown signal received, cleaning up...")
        loop_thread.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start API server (blocking)
    try:
        run_api_server(host="0.0.0.0", port=8401)
    except KeyboardInterrupt:
        logger.info("[*] API server interrupted")
        loop_thread.stop()
        sys.exit(0)


if __name__ == "__main__":
    main()
