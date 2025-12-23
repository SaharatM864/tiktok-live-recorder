import signal
import os
import threading
from utils.logger_manager import logger

# Global event to signal threads to stop
stop_event = threading.Event()


def setup_signal_handlers():
    """
    Sets up signal handlers for graceful shutdown and force exit.
    """

    def signal_handler(sig, frame):
        if stop_event.is_set():
            logger.warning("\n[!] Force exiting...")
            os._exit(1)
        else:
            logger.info(
                "\n[!] Stopping... Processing remaining file data. Press Ctrl+C again to force exit."
            )
            stop_event.set()
            # We don't raise KeyboardInterrupt here to avoid the "Exception ignored" spam
            # Instead, we rely on checking stop_event in loops

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
