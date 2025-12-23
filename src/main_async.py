import asyncio
import sys
import os

# Add project root to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import config
from src.utils.logger_manager import logger
from src.core.monitor import Monitor
from src.core.events import event_bus, Events
from src.upload.telegram import TelegramUploader


async def upload_handler(data):
    """Handler for recording finished event."""
    output_path = data.get("output_path")
    if output_path:
        uploader = TelegramUploader()
        await uploader.upload(output_path)


async def main():
    logger.info("TikTok Live Recorder (Async Version) Started")
    logger.info(f"Loaded configuration. Monitoring {len(config.users)} users.")

    # 1. Setup Event Handlers
    if config.telegram_enabled:
        event_bus.subscribe(Events.RECORDING_FINISHED, upload_handler)
        logger.info("Telegram Upload Enabled")

    # 2. Create Monitors
    monitors = []
    tasks = []

    # If users provided in config
    users = config.users

    # If no users in config, check args (simple fallback or just rely on config for now)
    if not users:
        logger.warning(
            "No users specified in config. Please set 'users' in .env or config.py"
        )
        return

    for user in users:
        monitor = Monitor(user)
        monitors.append(monitor)
        tasks.append(asyncio.create_task(monitor.start()))

    # 3. Run forever
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        logger.info("Stopping...")
    finally:
        for monitor in monitors:
            monitor.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
