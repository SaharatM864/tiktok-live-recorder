import asyncio
import os
import time
from typing import Dict

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
        # ตั้งค่า client API ของ TikTok
        self.tiktok = TikTokAPI(proxy=proxy, cookies=cookies)

        # ข้อมูล TikTok
        self.url = url
        self.user = user
        self.room_id = room_id

        # การตั้งค่าเครื่องมือ
        self.mode = mode
        self.automatic_interval = automatic_interval
        self.duration = duration
        self.output = output

        # หากมีการระบุ proxy ให้ตั้งค่า HTTP client โดยไม่ใช้ proxy
        if proxy:
            self.tiktok = TikTokAPI(proxy=None, cookies=cookies)

    async def _initialize(self):
        """
        ดำเนินการ initialization tasks แบบ async
        """
        logger.info("กำลังตรวจสอบสถานะการบล็อกประเทศ...")
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

        if self.mode == Mode.FOLLOWERS:
            self.sec_uid = await self.tiktok.get_sec_uid()
            if self.sec_uid is None:
                raise TikTokRecorderError("ไม่สามารถดึงค่า sec_uid ได้")

            logger.info("โหมดผู้ติดตามเปิดใช้งาน\n")
        else:
            if self.url:
                logger.info(f"กำลังดึงข้อมูลผู้ใช้จาก URL: {self.url}")
                self.user, self.room_id = await self.tiktok.get_room_and_user_from_url(
                    self.url
                )

            if not self.user:
                logger.info(f"กำลังดึงข้อมูลผู้ใช้จาก Room ID: {self.room_id}")
                self.user = await self.tiktok.get_user_from_room_id(self.room_id)

            if not self.room_id:
                logger.info(f"กำลังดึง Room ID สำหรับผู้ใช้: {self.user}")
                self.room_id = await self.tiktok.get_room_id_from_user(self.user)

            logger.info(f"ชื่อผู้ใช้: {self.user}" + ("\n" if not self.room_id else ""))
            if self.room_id:
                logger.info(f"กำลังตรวจสอบว่าห้อง {self.room_id} ไลฟ์อยู่หรือไม่...")
                is_alive = await self.tiktok.is_room_alive(self.room_id)
                logger.info(
                    f"ROOM_ID:  {self.room_id}" + ("\n" if not is_alive else "")
                )

    async def run(self):
        """
        รันโปรแกรมในโหมดที่เลือก
        """
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
                logger.info(f"รอ {self.automatic_interval} นาทีก่อนตรวจสอบใหม่\n")
                await asyncio.sleep(self.automatic_interval * TimeOut.ONE_MINUTE)

            except LiveNotFound as ex:
                logger.error(f"ไม่พบไลฟ์: {ex}")
                logger.info(f"รอ {self.automatic_interval} นาทีก่อนตรวจสอบใหม่\n")
                await asyncio.sleep(self.automatic_interval * TimeOut.ONE_MINUTE)

            except ConnectionError:
                logger.error(Error.CONNECTION_CLOSED_AUTOMATIC)
                await asyncio.sleep(TimeOut.CONNECTION_CLOSED * TimeOut.ONE_MINUTE)

            except Exception as ex:
                logger.error(f"ข้อผิดพลาดที่ไม่คาดคิด: {ex}\n")
                await asyncio.sleep(5)

    async def followers_mode(self):
        active_recordings: Dict[str, asyncio.Task] = {}
        user_room_cache: Dict[str, str] = {}

        while not stop_event.is_set():
            try:
                followers = await self.tiktok.get_followers_list(self.sec_uid)
                if not followers:
                    logger.info("ไม่พบผู้ติดตาม หรือดึงข้อมูลล้มเหลว รอสักครู่...")
                    await asyncio.sleep(self.automatic_interval * TimeOut.ONE_MINUTE)
                    continue

                for user in list(active_recordings.keys()):
                    if active_recordings[user].done():
                        logger.info(f"การบันทึกของ @{user} เสร็จสิ้น")
                        del active_recordings[user]

                users_to_check = [u for u in followers if u not in active_recordings]

                if not users_to_check:
                    await asyncio.sleep(self.automatic_interval * TimeOut.ONE_MINUTE)
                    continue

                users_needing_resolution = [
                    u for u in users_to_check if u not in user_room_cache
                ]

                if users_needing_resolution:
                    logger.info(
                        f"กำลังค้นหา Room ID สำหรับ {len(users_needing_resolution)} ผู้ใช้ใหม่..."
                    )
                    tasks = [
                        self.tiktok.get_room_id_from_user(u)
                        for u in users_needing_resolution
                    ]
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    for user, result in zip(users_needing_resolution, results):
                        if isinstance(result, str) and result:
                            user_room_cache[user] = result
                        else:
                            if isinstance(result, Exception):
                                logger.debug(f"ไม่สามารถหา Room ID ของ {user}: {result}")

                batch_check_map = {}
                for user in users_to_check:
                    if user in user_room_cache:
                        batch_check_map[user] = user_room_cache[user]

                if batch_check_map:
                    room_ids_list = list(batch_check_map.values())
                    chunk_size = 50
                    for i in range(0, len(room_ids_list), chunk_size):
                        chunk = room_ids_list[i : i + chunk_size]
                        status_map = await self.tiktok.is_room_alive(chunk)

                        for user, room_id in batch_check_map.items():
                            if room_id in chunk and status_map.get(room_id):
                                logger.info(f"@{user} กำลังไลฟ์! เริ่มต้นการบันทึก...")
                                task = asyncio.create_task(
                                    self.start_recording(user, room_id)
                                )
                                active_recordings[user] = task

                logger.info(
                    f"ตรวจสอบผู้ติดตาม {len(users_to_check)} คนเรียบร้อยแล้ว รอ {self.automatic_interval} นาทีก่อนตรวจสอบรอบถัดไป..."
                )
                await asyncio.sleep(self.automatic_interval * TimeOut.ONE_MINUTE)

            except Exception as ex:
                logger.error(f"เกิดข้อผิดพลาดในลูป followers: {ex}")
                await asyncio.sleep(60)

    async def start_recording(self, user, room_id):
        """
        เริ่มบันทึกการไลฟ์
        """
        try:
            live_url = await self.tiktok.get_live_url(room_id)
            if not live_url:
                raise LiveNotFound(TikTokError.RETRIEVE_LIVE_URL)

            current_date = time.strftime("%Y.%m.%d_%H-%M-%S", time.localtime())
            output_path = self.output_dir_path(self.output)
            filename = f"{output_path}TK_{user}_{current_date}.mp4"

            recorder = FFmpegRecorder()

            if self.duration:
                logger.info(f"เริ่มบันทึกเป็นเวลา {self.duration} วินาที ")

                async def stop_after_duration():
                    await asyncio.sleep(self.duration)
                    await recorder.stop_recording()

                asyncio.create_task(stop_after_duration())
            else:
                logger.info("เริ่มบันทึก...")

            await recorder.start_recording(live_url, filename)

            logger.info(f"การบันทึกเสร็จสิ้น: {filename}\n")

        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการบันทึก {user}: {e}")

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
