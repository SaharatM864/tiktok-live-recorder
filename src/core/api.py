import aiohttp
import re
import json
from typing import Optional
from src.utils.logger_manager import logger
from src.config import config


class AsyncTikTokAPI:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.tiktok.com/",
        }
        self.proxy = config.proxy

    async def get_room_id_from_user(self, user: str) -> Optional[str]:
        """
        Get room_id from username using aiohttp.
        """
        url = f"https://www.tiktok.com/@{user}/live"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, headers=self.headers, proxy=self.proxy
                ) as response:
                    if response.status == 200:
                        html = await response.text()

                        # Try to find room_id in HTML
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
                            data = json.loads(match.group(1))
                            # Navigate json to find room id... implementation varies as tiktok changes structure
                            # This is a fallback attempt
                            try:
                                live_room = (
                                    data.get("LiveRoom", {})
                                    .get("liveRoomUserInfo", {})
                                    .get("user", {})
                                    .get("roomId")
                                )
                                if live_room:
                                    return live_room
                            except Exception:
                                pass

                    elif response.status == 404:
                        logger.error(f"User {user} not found (404)")
                        return None
                    else:
                        logger.warning(
                            f"Failed to get room id for {user}. Status: {response.status}"
                        )
                        return None
        except Exception as e:
            logger.error(f"Error getting room ID for {user}: {e}")
            return None

        return None

    async def is_live(self, room_id: str) -> bool:
        """
        Check if a room is live.
        """
        if not room_id:
            return False

        url = f"https://webcast.tiktok.com/webcast/room/check_alive/?aid=1988&room_ids={room_id}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, headers=self.headers, proxy=self.proxy
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        data_list = data.get("data", [])
                        if data_list:
                            return data_list[0].get("alive", False)
        except Exception as e:
            logger.error(f"Error checking live status for {room_id}: {e}")

        return False
