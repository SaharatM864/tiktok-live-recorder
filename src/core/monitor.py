import asyncio
from pathlib import Path
from datetime import datetime
from src.utils.logger_manager import logger
from src.config import config
from src.core.tiktok_api_async import AsyncTikTokAPI
from src.core.streamlink_recorder import StreamlinkRecorder
from src.core.events import event_bus, Events


class Monitor:
    def __init__(self, user: str):
        self.user = user
        self.api = AsyncTikTokAPI()
        self.recorder = StreamlinkRecorder()
        self.running = False

    async def start(self):
        self.running = True
        logger.info(f"Started monitoring for user: {self.user}")

        while self.running:
            try:
                # 1. Get Room ID (if not cached/known, though API handles it?
                # The API I wrote takes room_id for is_live, so we need to resolve it first)
                room_id = await self.api.get_room_id_from_user(self.user)

                if not room_id:
                    logger.warning(
                        f"Could not resolve room ID for {self.user}. Retrying in {config.check_interval} min."
                    )
                    await asyncio.sleep(config.check_interval * 60)
                    continue

                # 2. Check if Live
                is_live = await self.api.is_live(room_id)

                if is_live:
                    logger.info(f"User {self.user} is LIVE! Starting recording...")

                    # Prepare output path
                    timestamp = datetime.now().strftime("%Y.%m.%d_%H-%M-%S")
                    filename = f"TK_{self.user}_{timestamp}.mp4"
                    output_path = str(Path(config.output_dir) / filename)

                    # Notify Start
                    await event_bus.publish(
                        Events.RECORDING_STARTED,
                        {"user": self.user, "filename": filename},
                    )

                    # Start Recording (waits until finished)
                    await self.recorder.start_recording(self.user, room_id, output_path)

                    # Notify Finish
                    await event_bus.publish(
                        Events.RECORDING_FINISHED,
                        {"user": self.user, "output_path": output_path},
                    )

                    # Wait a bit before checking again to avoid spam if stream just ended
                    await asyncio.sleep(60)
                else:
                    logger.info(
                        f"User {self.user} is offline. Checking again in {config.check_interval} min."
                    )
                    await asyncio.sleep(config.check_interval * 60)

            except Exception as e:
                logger.error(f"Error in monitor loop for {self.user}: {e}")
                await asyncio.sleep(60)  # Wait a bit on error

    def stop(self):
        self.running = False
        self.recorder.stop_recording()
