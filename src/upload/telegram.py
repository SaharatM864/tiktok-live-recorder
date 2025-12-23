from pathlib import Path
from telethon import TelegramClient
from src.utils.logger_manager import logger
from src.config import config
from src.core.interfaces import IUploader


class TelegramUploader(IUploader):
    def __init__(self):
        self.api_id = config.telegram_api_id
        self.api_hash = config.telegram_api_hash
        self.chat_id = config.telegram_chat_id
        self.client = None

    async def _get_client(self):
        if not self.client:
            self.client = TelegramClient(
                "tiktok_live_recorder_session", self.api_id, self.api_hash
            )
            await self.client.start()
        return self.client

    async def upload(self, file_path: str) -> bool:
        if not config.telegram_enabled:
            return False

        if not (self.api_id and self.api_hash and self.chat_id):
            logger.warning("Telegram credentials missing. Skipping upload.")
            return False

        file = Path(file_path)
        if not file.exists():
            logger.error(f"File not found for upload: {file_path}")
            return False

        try:
            client = await self._get_client()

            logger.info(f"Uploading {file.name} to Telegram...")

            # Progress callback
            def callback(current, total):
                # Simple progress log, maybe improve later to avoid spam
                pass

            await client.send_file(
                self.chat_id,
                file_path,
                caption=f"🎥 **Recorded Live**: {file.name}",
                progress_callback=callback,
            )

            logger.info(f"Successfully uploaded {file.name} to Telegram.")
            return True

        except Exception as e:
            logger.error(f"Telegram upload failed: {e}")
            return False
        finally:
            if self.client:
                await self.client.disconnect()
                self.client = None
