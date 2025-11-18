"""TikTok content downloader built on top of tikwm.com API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Iterator

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
        photo_sources: list[Any] = [
            images if images is not None else data.get("images"),
            data.get("image_list"),
            data.get("imageList"),
            data.get("image_urls"),
            data.get("imageUrls"),
        ]

        album_info = (
            data.get("image_post_info")
            or data.get("imagePostInfo")
            or data.get("image_post")
            or data.get("imagePost")
        )
        if isinstance(album_info, dict):
            photo_sources.extend(
                album_info.get(key)
                for key in ("images", "image_list", "imageList", "image_urls", "imageUrls")
            )
        elif album_info is not None:
            photo_sources.append(album_info)

        photos = self._collect_photo_urls(*photo_sources)
        if not photos:
            raise TikTokDownloadError("Bu bağlantıda fotoğraf albümü bulunamadı.")
        caption = self._build_caption(data)
        return TikTokPhotoAlbum(photos=list(photos), caption=caption, cover_url=data.get("cover"))

    async def _request(self, target_url: str) -> dict[str, Any]:
        payload = {"url": target_url}
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                headers=self._DEFAULT_HEADERS,
            ) as client:
                response = await client.post(self._base_url, data=payload)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status is not None and 500 <= status < 600:
                message = (
                    "TikTok servisinde geçici bir sorun oluştu. Lütfen birkaç dakika sonra tekrar deneyin."
                )
            else:
                message = "TikTok isteği reddedildi. Lütfen bağlantıyı kontrol edin."
            suffix = f" (HTTP {status})" if status is not None else ""
            raise TikTokDownloadError(f"{message}{suffix}") from exc
        except httpx.RequestError as exc:
            raise TikTokDownloadError("TikTok servisine bağlanırken ağ hatası oluştu.") from exc
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

    @classmethod
    def _collect_photo_urls(cls, *sources: Any) -> list[str]:
        collected: list[str] = []
        seen: set[str] = set()
        for source in sources:
            for url in cls._iter_photo_urls(source):
                normalized = cls._normalize_photo_url(url)
                if not normalized or normalized in seen:
                    continue
                seen.add(normalized)
                collected.append(normalized)
        return collected

    @classmethod
    def _iter_photo_urls(cls, value: Any) -> Iterator[str]:
        if not value:
            return
        if isinstance(value, str):
            yield value
            return
        if isinstance(value, dict):
            for key in ("url", "image_url", "imageUrl"):
                direct = value.get(key)
                if isinstance(direct, str):
                    yield direct
            for key in ("url_list", "urlList", "urls"):
                nested = value.get(key)
                if isinstance(nested, (list, tuple, set)):
                    for item in nested:
                        yield from cls._iter_photo_urls(item)
            for key in (
                "images",
                "image_list",
                "imageList",
                "image_urls",
                "imageUrls",
                "display_image",
                "origin_image",
                "webp_color_image",
                "download_addr",
                "cover",
                "cover_image",
                "image",
                "img",
            ):
                yield from cls._iter_photo_urls(value.get(key))
            return
        if isinstance(value, (list, tuple, set)):
            for item in value:
                yield from cls._iter_photo_urls(item)
            return

    @staticmethod
    def _normalize_photo_url(url: str) -> str | None:
        candidate = url.strip()
        if not candidate:
            return None
        if candidate.startswith("//"):
            candidate = f"https:{candidate}"
        if candidate.startswith(("http://", "https://")):
            return candidate
        return None
