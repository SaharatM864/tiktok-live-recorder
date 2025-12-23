from typing import Optional, Dict, Any
from curl_cffi.requests import AsyncSession


class AsyncHttpClient:
    def __init__(
        self, proxy: Optional[str] = None, cookies: Optional[Dict[str, str]] = None
    ):
        self.proxy = proxy
        self.cookies = cookies
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.tiktok.com/",
        }
        self.session: Optional[AsyncSession] = None

    async def _ensure_session(self):
        if self.session is None:
            self.session = AsyncSession(
                headers=self.headers,
                cookies=self.cookies,
                impersonate="chrome120",
                proxies={"http": self.proxy, "https": self.proxy}
                if self.proxy
                else None,
            )

    async def get(self, url: str, params: Optional[Dict[str, Any]] = None, **kwargs):
        await self._ensure_session()
        kwargs.setdefault("timeout", 10)
        return await self.session.get(url, params=params, **kwargs)

    async def post(self, url: str, data: Any = None, json: Any = None, **kwargs):
        await self._ensure_session()
        kwargs.setdefault("timeout", 10)
        return await self.session.post(url, data=data, json=json, **kwargs)

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None
