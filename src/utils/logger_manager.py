import logging
from rich.logging import RichHandler
from rich.console import Console

# Create a global console instance
console = Console()


class LoggerManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LoggerManager, cls).__new__(cls)
            cls._instance.setup_logger()
        return cls._instance

    def setup_logger(self):
        # Configure the root logger to use RichHandler
        logging.basicConfig(
            level="INFO",
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(console=console, rich_tracebacks=True)],
        )
        self.logger = logging.getLogger("tiktok_recorder")

    def info(self, message):
        self.logger.info(message)

    def error(self, message):
        self.logger.error(message)

    def warning(self, message):
        self.logger.warning(message)

    def debug(self, message):
        self.logger.debug(message)

    def critical(self, message, exc_info=False):
        self.logger.critical(message, exc_info=exc_info)


# Global logger instance
logger = LoggerManager().logger
