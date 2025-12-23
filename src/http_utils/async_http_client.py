import aiohttp
import asyncio
from typing import Optional, Dict, Any


class AsyncHttpClient:
    def __init__(
        self, proxy: Optional[str] = None, cookies: Optional[Dict[str, str]] = None
    ):
        self.proxy = proxy
        self.cookies = cookies
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.tiktok.com/",
        }
        self.session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers=self.headers, cookies=self.cookies, trust_env=True
            )

    async def get(
        self, url: str, params: Optional[Dict[str, Any]] = None, **kwargs
    ) -> aiohttp.ClientResponse:
        await self._ensure_session()
        return await self.session.get(url, params=params, proxy=self.proxy, **kwargs)

    async def post(
        self, url: str, data: Any = None, json: Any = None, **kwargs
    ) -> aiohttp.ClientResponse:
        await self._ensure_session()
        return await self.session.post(
            url, data=data, json=json, proxy=self.proxy, **kwargs
        )

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
