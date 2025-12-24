import re
import orjson  # ใช้ orjson เพื่อประสิทธิภาพในการ parse JSON
from typing import Union, List, Dict

from http_utils.async_http_client import AsyncHttpClient
from utils.enums import StatusCode, TikTokError
from utils.logger_manager import logger
from utils.custom_exceptions import (
    UserLiveError,
    TikTokRecorderError,
    LiveNotFound,
)

from core.common import TikTokUrlParser


class TikTokAPI:
    def __init__(self, proxy, cookies):
        self.BASE_URL = "https://www.tiktok.com"
        self.WEBCAST_URL = "https://webcast.tiktok.com"
        self.API_URL = "https://www.tiktok.com/api-live/user/room/"
        self.EULER_API = "https://tiktok.eulerstream.com"
        self.TIKREC_API = "https://tikrec.com"

        self.http_client = AsyncHttpClient(proxy, cookies)

    async def close(self):
        await self.http_client.close()

    async def is_country_blacklisted(self) -> bool:
        """
        ตรวจสอบว่าผู้ใช้อยู่ในประเทศที่ถูกบล็อกซึ่งต้องเข้าสู่ระบบหรือไม่
        """
        try:
            response = await self.http_client.get(
                f"{self.BASE_URL}/live", allow_redirects=False
            )
            return response.status_code == StatusCode.REDIRECT
        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการตรวจสอบ country blacklist: {e}")
            return False

    async def is_room_alive(
        self, room_id: Union[str, List[str]]
    ) -> Union[bool, Dict[str, bool]]:
        """
        ตรวจสอบว่าผู้ใช้กำลังไลฟ์อยู่หรือไม่
        รองรับทั้งแบบ room_id เดียว (str) และหลาย room_id (List[str]) เพื่อทำ Batch request
        """
        if not room_id:
            if isinstance(room_id, list):
                return {}
            return False

        # แปลง room_id เป็น string สำหรับส่งใน URL
        is_batch = isinstance(room_id, list)
        room_ids_str = ",".join(room_id) if is_batch else room_id

        try:
            response = await self.http_client.get(
                f"{self.WEBCAST_URL}/webcast/room/check_alive/"
                f"?aid=1988&region=CH&room_ids={room_ids_str}&user_is_login=true"
            )

            data = orjson.loads(response.content)

            if "data" not in data:
                return {} if is_batch else False

            data_list = data["data"]

            if is_batch:
                result = {}
                for item in data_list:
                    r_id = str(item.get("room_id", ""))
                    is_alive = item.get("alive", False)
                    result[r_id] = is_alive
                return result
            else:
                if len(data_list) == 0:
                    return False
                return data_list[0].get("alive", False)

        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการตรวจสอบสถานะห้อง (is_room_alive): {e}")
            return {} if is_batch else False

    async def get_sec_uid(self):
        """
        คืนค่า sec_uid ของผู้ใช้ที่ยืนยันตัวตนแล้ว
        """
        try:
            response = await self.http_client.get(f"{self.BASE_URL}/foryou")
            text = response.text

            sec_uid = re.search('"secUid":"(.*?)",', text)
            if sec_uid:
                return sec_uid.group(1)
            return None
        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการดึง sec_uid: {e}")
            return None

    async def get_user_from_room_id(self, room_id) -> str:
        """
        รับ room_id แล้วคืนค่า username
        """
        try:
            response = await self.http_client.get(
                f"{self.WEBCAST_URL}/webcast/room/info/?aid=1988&room_id={room_id}"
            )
            data = orjson.loads(response.content)
            data_str = str(data)

            if "Follow the creator to watch their LIVE" in data_str:
                raise UserLiveError(TikTokError.ACCOUNT_PRIVATE_FOLLOW)

            if "This account is private" in data_str:
                raise UserLiveError(TikTokError.ACCOUNT_PRIVATE)

            display_id = data.get("data", {}).get("owner", {}).get("display_id")
            if display_id is None:
                raise TikTokRecorderError(TikTokError.USERNAME_ERROR)

            return display_id
        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการดึง user จาก room_id: {e}")
            raise TikTokRecorderError(TikTokError.USERNAME_ERROR)

    async def get_room_and_user_from_url(self, live_url: str):
        """
        รับ url แล้วคืนค่า user และ room_id
        """
        try:
            response = await self.http_client.get(live_url, allow_redirects=False)
            content = response.text

            if response.status_code == StatusCode.REDIRECT:
                raise UserLiveError(TikTokError.COUNTRY_BLACKLISTED)

            if response.status_code == StatusCode.MOVED:
                matches = re.findall("com/@(.*?)/live", content)
                if len(matches) < 1:
                    raise LiveNotFound(TikTokError.INVALID_TIKTOK_LIVE_URL)

                user = matches[0]
            else:
                user = TikTokUrlParser.parse_user_from_url(live_url)
                if not user:
                    raise LiveNotFound(TikTokError.INVALID_TIKTOK_LIVE_URL)

            room_id = await self.get_room_id_from_user(user)

            return user, room_id
        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการดึง room และ user จาก url: {e}")
            raise e

    async def _tikrec_get_room_id_signed_url(self, user: str) -> str:
        response = await self.http_client.get(
            f"{self.TIKREC_API}/tiktok/room/api/sign",
            params={"unique_id": user},
        )
        data = orjson.loads(response.content)
        signed_path = data.get("signed_path")
        return f"{self.BASE_URL}{signed_path}"

    async def get_room_id_from_user(self, user: str) -> str | None:
        """รับ username แล้วคืนค่า room_id"""
        try:
            try:
                response = await self.http_client.get(
                    f"{self.BASE_URL}/@{user}/live", allow_redirects=False
                )
                if response.status_code == 200:
                    room_id = TikTokUrlParser.parse_room_id_from_html(response.text)
                    if room_id:
                        return room_id
            except Exception as e:
                logger.warning(f"วิธีการ Scrape ล้มเหล้ว (Fallback ไปใช้ API): {e}")

            signed_url = await self._tikrec_get_room_id_signed_url(user)
            response = await self.http_client.get(signed_url)
            content = response.text

            if not content or "Please wait" in content:
                raise UserLiveError(TikTokError.WAF_BLOCKED)

            data = orjson.loads(response.content)
            return (data.get("data") or {}).get("user", {}).get("roomId")
        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการดึง room_id จาก user: {e}")
            return None

    async def get_followers_list(self, sec_uid) -> list:
        """
        คืนค่ารายชื่อผู้ติดตามทั้งหมดสำหรับผู้ใช้ที่ยืนยันตัวตนแล้วโดยการแบ่งหน้า
        """
        followers = []
        cursor = 0
        has_more = True

        try:
            response = await self.http_client.get(
                f"{self.BASE_URL}/api/user/list/?"
                "WebIdLastTime=1747672102&aid=1988&app_language=it-IT&app_name=tiktok_web&"
                "browser_language=it-IT&browser_name=Mozilla&browser_online=true&"
                "browser_platform=Linux%20x86_64&"
                "browser_version=5.0%20%28X11%3B%20Linux%20x86_64%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F140.0.0.0%20Safari%2F537.36&"
                "channel=tiktok_web&cookie_enabled=true&count=5&data_collection_enabled=true&"
                "device_id=7506194516308166166&device_platform=web_pc&focus_state=true&"
                "from_page=user&history_len=3&is_fullscreen=false&is_page_visible=true&"
                "maxCursor=0&minCursor=0&odinId=7246312836442604570&os=linux&priority_region=IT&"
                "referer=&region=IT&root_referer=https%3A%2F%2Fwww.tiktok.com%2Flive&scene=21&"
                "screen_height=1080&screen_width=1920&tz_name=Europe%2FRome&user_is_login=true&"
                "verifyFp=verify_mh4yf0uq_rdjp1Xwt_OoTk_4Jrf_AS8H_sp31opbnJFre&webcast_language=it-IT&"
                "msToken=GphHoLvRR4QxA5AWVwDkrs3AbumoK5H8toE8LVHtj6cce3ToGdXhMfvDWzOXG-0GXUWoaGVHrwGNA4k_NnjuFFnHgv2S5eMjsvtkAhwMPa13xLmvP7tumx0KreFjPwTNnOj-BvAkPdO5Zrev3hoFBD9lHVo=&X-Bogus=&X-Gnarly="
            )

            while has_more:
                url = (
                    "https://www.tiktok.com/api/user/list/?"
                    "WebIdLastTime=1747672102&aid=1988&app_language=it-IT&app_name=tiktok_web"
                    "&browser_language=it-IT&browser_name=Mozilla&browser_online=true"
                    "&browser_platform=Linux%20x86_64&browser_version=5.0%20%28X11%3B%20Linux%20x86_64%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F140.0.0.0%20Safari%2F537.36&channel=tiktok_web&"
                    "cookie_enabled=true&count=5&data_collection_enabled=true&device_id=7506194516308166166"
                    "&device_platform=web_pc&focus_state=true&from_page=user&history_len=3&"
                    f"is_fullscreen=false&is_page_visible=true&maxCursor={cursor}&minCursor={cursor}&"
                    "odinId=7246312836442604570&os=linux&priority_region=IT&referer=&"
                    "region=IT&scene=21&screen_height=1080&screen_width=1920"
                    "&tz_name=Europe%2FRome&user_is_login=true&"
                    f"secUid={sec_uid}&verifyFp=verify_mh4yf0uq_rdjp1Xwt_OoTk_4Jrf_AS8H_sp31opbnJFre&"
                    f"webcast_language=it-IT&X-Bogus=&X-Gnarly="
                )

                if cursor != 0:
                    response = await self.http_client.get(url)

                if response.status_code != StatusCode.OK:
                    raise TikTokRecorderError("ไม่สามารถดึงรายชื่อผู้ติดตามได้")

                data = orjson.loads(response.content)
                user_list = data.get("userList", [])

                for user in user_list:
                    username = user.get("user", {}).get("uniqueId")
                    if username:
                        followers.append(username)

                has_more = data.get("hasMore", False)
                new_cursor = data.get("minCursor", 0)

                if new_cursor == cursor:
                    break

                cursor = new_cursor

            if not followers:
                raise TikTokRecorderError("รายชื่อผู้ติดตามว่างเปล่า")

            return followers
        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการดึงรายชื่อผู้ติดตาม: {e}")
            return []

    async def get_live_url(self, room_id: str) -> str | None:
        """
        คืนค่า cdn (flv หรือ m3u8) ของการสตรีม
        """
        response = await self.http_client.get(
            f"{self.WEBCAST_URL}/webcast/room/info/?aid=1988&room_id={room_id}"
        )
        data = orjson.loads(response.content)

        if "This account is private" in str(data):
            raise UserLiveError(TikTokError.ACCOUNT_PRIVATE)

        stream_url = data.get("data", {}).get("stream_url", {})

        flv_url = (
            stream_url.get("flv_pull_url", {}).get("FULL_HD1")
            or stream_url.get("flv_pull_url", {}).get("HD1")
            or stream_url.get("flv_pull_url", {}).get("SD2")
            or stream_url.get("flv_pull_url", {}).get("SD1")
            or stream_url.get("rtmp_pull_url", "")
        )

        if flv_url:
            return flv_url

        sdk_data_str = (
            stream_url.get("live_core_sdk_data", {})
            .get("pull_data", {})
            .get("stream_data")
        )
        if not sdk_data_str:
            return None

        try:
            sdk_data = orjson.loads(sdk_data_str).get("data", {})
            qualities = (
                stream_url.get("live_core_sdk_data", {})
                .get("pull_data", {})
                .get("options", {})
                .get("qualities", [])
            )
            if not qualities:
                return None

            level_map = {q["sdk_key"]: q["level"] for q in qualities}

            best_level = -1
            best_flv = None
            for sdk_key, entry in sdk_data.items():
                level = level_map.get(sdk_key, -1)
                stream_main = entry.get("main", {})
                if level > best_level:
                    best_level = level
                    best_flv = stream_main.get("flv")

            return best_flv
        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการ parse SDK data: {e}")
            return None
