"""TikTok content downloader built on top of tikwm.com API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

import httpx


class TikTokDownloadError(RuntimeError):
    """Raised when the TikTok asset cannot be fetched."""


@dataclass(slots=True)
class TikTokVideo:
    url: str
    caption: str
    cover_url: str | None


@dataclass(slots=True)
class TikTokPhotoAlbum:
    photos: list[str]
    caption: str
    cover_url: str | None


class TikTokDownloader:
    """Download TikTok assets via a public-friendly API."""

    _DEFAULT_HEADERS: Final[dict[str, str]] = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
        ),
    }

    def __init__(self, base_url: str, timeout: float = 30) -> None:
        self._base_url = base_url.rstrip("/") + "/"
        self._timeout = timeout

    async def fetch_video(self, target_url: str) -> TikTokVideo:
        data = await self._request(target_url)
        return self._build_video(data)

    async def fetch_story(self, target_url: str) -> TikTokVideo:
        """Stories teknik olarak videodur, ayrı komutla aynı akış kullanılır."""

        return await self.fetch_video(target_url)

    async def fetch_photos(self, target_url: str) -> TikTokPhotoAlbum:
        data = await self._request(target_url)
        return self._build_photo_album(data)

    async def fetch_asset(self, target_url: str) -> TikTokVideo | TikTokPhotoAlbum:
        """Tek bir uçtan gelen veriye göre uygun içerik tipini belirle."""

        data = await self._request(target_url)
        images = data.get("images") or []
        if images:
            return self._build_photo_album(data, images)
        return self._build_video(data)

    def _build_video(self, data: dict[str, Any]) -> TikTokVideo:
        video_url = data.get("play") or data.get("wmplay")
        if not video_url:
            raise TikTokDownloadError("Video akışı bulunamadı.")
        caption = self._build_caption(data)
        return TikTokVideo(url=video_url, caption=caption, cover_url=data.get("cover"))

    def _build_photo_album(
        self,
        data: dict[str, Any],
        images: list[str] | None = None,
    ) -> TikTokPhotoAlbum:
        photos = images if images is not None else (data.get("images") or [])
        if not photos:
            raise TikTokDownloadError("Bu bağlantıda fotoğraf albümü bulunamadı.")
        caption = self._build_caption(data)
        return TikTokPhotoAlbum(photos=list(photos), caption=caption, cover_url=data.get("cover"))

    async def _request(self, target_url: str) -> dict[str, Any]:
        payload = {"url": target_url}
        async with httpx.AsyncClient(timeout=self._timeout, headers=self._DEFAULT_HEADERS) as client:
            response = await client.post(self._base_url, data=payload)

        response.raise_for_status()
        body = response.json()
        if body.get("code") != 0 or not body.get("data"):
            raise TikTokDownloadError(body.get("msg") or "İçerik indirilemedi.")

        return body["data"]

    @staticmethod
    def _build_caption(data: dict[str, Any]) -> str:
        author_name = (data.get("author") or {}).get("nickname")
        title = data.get("title") or data.get("desc") or "TikTok"
        pieces = [title.strip()]
        if author_name:
            pieces.append(f"👤 {author_name}")
        return "\n".join(pieces)
