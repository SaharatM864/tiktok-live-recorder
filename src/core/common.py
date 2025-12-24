import re
import orjson
from typing import Optional


class TikTokUrlParser:
    """
    ตรรกะที่ใช้ร่วมกันสำหรับการแยกวิเคราะห์ URL ของ TikTok และเนื้อหา HTML
    """

    # Pre-compile Regex เพื่อประสิทธิภาพที่ดีขึ้น (ไม่ต้อง compile ใหม่ทุกครั้งที่เรียกใช้)
    _ROOM_ID_PATTERN_1 = re.compile(r"room_id=([0-9]+)")
    _ROOM_ID_PATTERN_2 = re.compile(r'"roomId":"([0-9]+)"')
    _SIGI_STATE_PATTERN = re.compile(
        r'<script id="SIGI_STATE" type="application/json">(.*?)</script>'
    )
    _USER_URL_PATTERN = re.compile(r"https?://(?:www\.)?tiktok\.com/@([^/]+)/live")

    @classmethod
    def parse_room_id_from_html(cls, html: str) -> Optional[str]:
        """
        ดึง room_id จากเนื้อหา HTML ของหน้าไลฟ์ TikTok
        """
        # ลองค้นหาจาก SIGI_STATE ก่อน เพราะเป็นวิธีที่น่าเชื่อถือที่สุดสำหรับ TikTok เวอร์ชันใหม่
        match = cls._SIGI_STATE_PATTERN.search(html)
        if match:
            try:
                # ใช้ orjson.loads แทน json.loads เพื่อความเร็ว
                data = orjson.loads(match.group(1))
                # ท่องเข้าไปใน json เพื่อหา room id
                live_room = (
                    data.get("LiveRoom", {})
                    .get("liveRoomUserInfo", {})
                    .get("user", {})
                    .get("roomId")
                )
                if live_room:
                    return str(live_room)
            except Exception:
                pass

        # ถ้าไม่เจอ ให้ลองใช้ Pattern แบบง่าย
        match = cls._ROOM_ID_PATTERN_1.search(html)
        if match:
            return match.group(1)

        match = cls._ROOM_ID_PATTERN_2.search(html)
        if match:
            return match.group(1)

        return None

    @classmethod
    def parse_user_from_url(cls, url: str) -> Optional[str]:
        """
        ดึงชื่อผู้ใช้ (username) จาก URL ของ TikTok live
        """
        # https://www.tiktok.com/@<username>/live
        match = cls._USER_URL_PATTERN.match(url)
        if match:
            return match.group(1)
        return None
