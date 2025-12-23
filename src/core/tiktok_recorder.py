import asyncio
import os
import time
from asyncio import AbstractEventLoop
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from core.tiktok_api import TikTokAPI
from core.recorders.ffmpeg_recorder import FFmpegRecorder
from utils.logger_manager import logger
from utils.custom_exceptions import LiveNotFound, UserLiveError, TikTokRecorderError
from utils.enums import Mode, Error, TimeOut, TikTokError
from utils.signals import stop_event


class TikTokRecorder:
    def __init__(
        self,
        url,
        user,
        room_id,
        mode,
        automatic_interval,
        cookies,
        proxy,
        output,
        duration,
    ):
        # Setup TikTok API client
        self.tiktok = TikTokAPI(proxy=proxy, cookies=cookies)

        # TikTok Data
        self.url = url
        self.user = user
        self.room_id = room_id

        # Tool Settings
        self.mode = mode
        self.automatic_interval = automatic_interval
        self.duration = duration
        self.output = output

        # Async helpers
        self.loop: Optional[AbstractEventLoop] = None
        self.executor = ThreadPoolExecutor(max_workers=5)

        # If proxy is provided, set up the HTTP client without the proxy
        if proxy:
            self.tiktok = TikTokAPI(proxy=None, cookies=cookies)

    async def _initialize(self):
        """
        Perform async initialization tasks.
        """
        # Check if the user's country is blacklisted
        logger.info("Checking country blacklist status...")
        is_blacklisted = await self.tiktok.is_country_blacklisted()
        if is_blacklisted:
            if self.room_id is None:
                raise TikTokRecorderError(TikTokError.COUNTRY_BLACKLISTED)
            if self.mode == Mode.AUTOMATIC:
                raise TikTokRecorderError(TikTokError.COUNTRY_BLACKLISTED_AUTO_MODE)
            elif self.mode == Mode.FOLLOWERS:
                raise TikTokRecorderError(
                    TikTokError.COUNTRY_BLACKLISTED_FOLLOWERS_MODE
                )

        # Retrieve sec_uid if the mode is FOLLOWERS
        if self.mode == Mode.FOLLOWERS:
            self.sec_uid = await self.tiktok.get_sec_uid()
            if self.sec_uid is None:
                raise TikTokRecorderError("Failed to retrieve sec_uid.")

            logger.info("Followers mode activated\n")
        else:
            # Get live information based on the provided user data
            if self.url:
                logger.info(f"Fetching user info from URL: {self.url}")
                self.user, self.room_id = await self.tiktok.get_room_and_user_from_url(
                    self.url
                )

            if not self.user:
                logger.info(f"Fetching user info from Room ID: {self.room_id}")
                self.user = await self.tiktok.get_user_from_room_id(self.room_id)

            if not self.room_id:
                logger.info(f"Fetching Room ID for user: {self.user}")
                self.room_id = await self.tiktok.get_room_id_from_user(self.user)

            logger.info(f"USERNAME: {self.user}" + ("\n" if not self.room_id else ""))
            if self.room_id:
                logger.info(f"Checking if room {self.room_id} is alive...")
                is_alive = await self.tiktok.is_room_alive(self.room_id)
                logger.info(
                    f"ROOM_ID:  {self.room_id}" + ("\n" if not is_alive else "")
                )

    async def run(self):
        """
        runs the program in the selected mode.
        """
        self.loop = asyncio.get_running_loop()
        try:
            await self._initialize()

            if self.mode == Mode.MANUAL:
                await self.manual_mode()

            elif self.mode == Mode.AUTOMATIC:
                await self.automatic_mode()

            elif self.mode == Mode.FOLLOWERS:
                await self.followers_mode()
        finally:
            await self.tiktok.close()

    async def manual_mode(self):
        is_alive = await self.tiktok.is_room_alive(self.room_id)
        if not is_alive:
            raise UserLiveError(f"@{self.user}: {TikTokError.USER_NOT_CURRENTLY_LIVE}")

        await self.start_recording(self.user, self.room_id)

    async def automatic_mode(self):
        while not stop_event.is_set():
            try:
                self.room_id = await self.tiktok.get_room_id_from_user(self.user)

                is_alive = await self.tiktok.is_room_alive(self.room_id)
                if not is_alive:
                    raise UserLiveError(
                        f"@{self.user}: {TikTokError.USER_NOT_CURRENTLY_LIVE}"
                    )

                await self.start_recording(self.user, self.room_id)

            except UserLiveError as ex:
                logger.info(ex)
                logger.info(
                    f"Waiting {self.automatic_interval} minutes before recheck\n"
                )
                await asyncio.sleep(self.automatic_interval * TimeOut.ONE_MINUTE)

            except LiveNotFound as ex:
                logger.error(f"Live not found: {ex}")
                logger.info(
                    f"Waiting {self.automatic_interval} minutes before recheck\n"
                )
                await asyncio.sleep(self.automatic_interval * TimeOut.ONE_MINUTE)

            except ConnectionError:
                logger.error(Error.CONNECTION_CLOSED_AUTOMATIC)
                await asyncio.sleep(TimeOut.CONNECTION_CLOSED * TimeOut.ONE_MINUTE)

            except Exception as ex:
                logger.error(f"Unexpected error: {ex}\n")
                await asyncio.sleep(5)  # Prevent tight loop on error

    async def followers_mode(self):
        active_recordings = {}  # follower -> Task

        while not stop_event.is_set():
            try:
                followers = await self.tiktok.get_followers_list(self.sec_uid)

                for follower in followers:
                    if follower in active_recordings:
                        if active_recordings[follower].done():
                            logger.info(f"Recording of @{follower} finished.")
                            del active_recordings[follower]
                        else:
                            continue

                    try:
                        room_id = await self.tiktok.get_room_id_from_user(follower)

                        if not room_id:
                            continue

                        is_alive = await self.tiktok.is_room_alive(room_id)
                        if not is_alive:
                            continue

                        logger.info(f"@{follower} is live. Starting recording...")

                        task = asyncio.create_task(
                            self.start_recording(follower, room_id)
                        )
                        active_recordings[follower] = task

                        await asyncio.sleep(2.5)

                    except Exception as e:
                        logger.error(f"Error while processing @{follower}: {e}")
                        continue

                print()
                delay = self.automatic_interval * TimeOut.ONE_MINUTE
                logger.info(f"Waiting {delay} minutes for the next check...")
                await asyncio.sleep(delay)

            except UserLiveError as ex:
                logger.info(ex)
                logger.info(
                    f"Waiting {self.automatic_interval} minutes before recheck\n"
                )
                await asyncio.sleep(self.automatic_interval * TimeOut.ONE_MINUTE)

            except ConnectionError:
                logger.error(Error.CONNECTION_CLOSED_AUTOMATIC)
                await asyncio.sleep(TimeOut.CONNECTION_CLOSED * TimeOut.ONE_MINUTE)

            except Exception as ex:
                logger.error(f"Unexpected error: {ex}\n")
                await asyncio.sleep(5)

    async def start_recording(self, user, room_id):
        """
        Start recording live
        """
        try:
            live_url = await self.tiktok.get_live_url(room_id)
            if not live_url:
                raise LiveNotFound(TikTokError.RETRIEVE_LIVE_URL)

            current_date = time.strftime("%Y.%m.%d_%H-%M-%S", time.localtime())

            # Handle output directory path
            output_path = self.output_dir_path(self.output)

            filename = f"{output_path}TK_{user}_{current_date}.mp4"

            recorder = FFmpegRecorder()

            if self.duration:
                logger.info(f"Started recording for {self.duration} seconds ")

                # Create a task to stop recording after duration
                async def stop_after_duration():
                    await asyncio.sleep(self.duration)
                    await recorder.stop_recording()

                asyncio.create_task(stop_after_duration())
            else:
                logger.info("Started recording...")

            await recorder.start_recording(live_url, filename)

            logger.info(f"Recording finished: {filename}\n")

        except Exception as e:
            logger.error(f"Error recording {user}: {e}")

    def output_dir_path(self, output_path):
        if isinstance(output_path, str) and output_path != "":
            if not (output_path.endswith("/") or output_path.endswith("\\")):
                if os.name == "nt":
                    output_path = output_path + "\\"
                else:
                    output_path = output_path + "/"
        else:
            output_path = ""
        return output_path
