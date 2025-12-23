import re
import json
from typing import Optional


class TikTokUrlParser:
    """
    Shared logic for parsing TikTok URLs and HTML content.
    """

    @staticmethod
    def parse_room_id_from_html(html: str) -> Optional[str]:
        """
        Extracts room_id from the HTML content of a TikTok live page.
        """
        # Pattern 1: room_id=1234567890
        match = re.search(r"room_id=([0-9]+)", html)
        if match:
            return match.group(1)

        # Pattern 2: "roomId":"1234567890"
        match = re.search(r'"roomId":"([0-9]+)"', html)
        if match:
            return match.group(1)

        # Pattern 3: SIGI_STATE (JSON in script tag)
        match = re.search(
            r'<script id="SIGI_STATE" type="application/json">(.*?)</script>',
            html,
        )
        if match:
            try:
                data = json.loads(match.group(1))
                # Navigate json to find room id
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

        return None

    @staticmethod
    def parse_user_from_url(url: str) -> Optional[str]:
        """
        Extracts username from a TikTok live URL.
        """
        # https://www.tiktok.com/@<username>/live
        match = re.match(r"https?://(?:www\.)?tiktok\.com/@([^/]+)/live", url)
        if match:
            return match.group(1)
        return None
