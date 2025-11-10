from typing import Any, Dict

import httpx


class EveryPixelService:
    def __init__(
        self,
        base_url: str,
        client_id: str,
        client_secret: str,
        timeout: float = 15.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout

    async def keywords_by_url(
        self,
        image_url: str,
        *,
        num_keywords: int = 10,
        colors: bool = False,
        num_colors: int = 5,
        lang: str = "en",
    ) -> Dict[str, Any]:
        params = {
            "url": image_url,
            "num_keywords": num_keywords,
            "colors": str(colors),
            "num_colors": num_colors,
            "lang": lang,
        }

        async with httpx.AsyncClient(
            auth=(self.client_id, self.client_secret),
            timeout=self.timeout,
        ) as client:
            r = await client.get(f"{self.base_url}/keywords", params=params)
            r.raise_for_status()
            return r.json()

    async def captions_by_url(
        self,
        image_url: str,
    ) -> Dict[str, Any]:
        params = {
            "url": image_url,
        }

        async with httpx.AsyncClient(
            auth=(self.client_id, self.client_secret),
            timeout=self.timeout,
        ) as client:
            r = await client.get(f"{self.base_url}/image_captioning", params=params)
            r.raise_for_status()
            return r.json()
