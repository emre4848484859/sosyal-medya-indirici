"""TikTok content downloader powered by yt-dlp's native extractor."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from functools import partial
from typing import Any, Final, Iterator

from yt_dlp import YoutubeDL
from yt_dlp.extractor.tiktok import TikTokIE
from yt_dlp.utils import DownloadError, ExtractorError


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


class _RawTikTokIE(TikTokIE):
    """Expose raw aweme payloads so we can inspect image posts."""

    def _parse_aweme_video_app(self, aweme_detail: dict[str, Any]) -> dict[str, Any]:
        info = super()._parse_aweme_video_app(aweme_detail)
        info["_aweme_detail"] = aweme_detail
        return info

    def _parse_aweme_video_web(
        self,
        aweme_detail: dict[str, Any],
        webpage_url: str,
        video_id: str,
        extract_flat: bool = False,
    ) -> dict[str, Any]:
        info = super()._parse_aweme_video_web(aweme_detail, webpage_url, video_id, extract_flat)
        info["_aweme_detail"] = aweme_detail
        return info


class TikTokDownloader:
    """Download TikTok assets without relying on third-party scraper APIs."""

    _YTDLP_BASE_OPTS: Final[dict[str, Any]] = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }

    def __init__(self, timeout: float = 30) -> None:
        self._timeout = timeout

    async def fetch_video(self, target_url: str) -> TikTokVideo:
        info = await self._extract_info(target_url)
        detail = self._aweme(info)
        return self._build_video(info, detail)

    async def fetch_story(self, target_url: str) -> TikTokVideo:
        """Stories teknik olarak videodur, ayrı komutla aynı akış kullanılır."""

        return await self.fetch_video(target_url)

    async def fetch_photos(self, target_url: str) -> TikTokPhotoAlbum:
        info = await self._extract_info(target_url)
        detail = self._aweme(info)
        images = self._extract_photo_sources(detail)
        return self._build_photo_album(detail, images)

    async def fetch_asset(self, target_url: str) -> TikTokVideo | TikTokPhotoAlbum:
        """Tek bir uçtan gelen veriye göre uygun içerik tipini belirle."""

        info = await self._extract_info(target_url)
        detail = self._aweme(info)
        images = self._extract_photo_sources(detail)
        if images:
            return self._build_photo_album(detail, images)
        return self._build_video(info, detail)

    def _build_video(self, info: dict[str, Any], detail: dict[str, Any]) -> TikTokVideo:
        video_url = info.get("url")
        if not video_url:
            raise TikTokDownloadError("Video akışı bulunamadı.")
        caption = self._build_caption(detail, info)
        cover_url = self._pick_cover(detail)
        return TikTokVideo(url=video_url, caption=caption, cover_url=cover_url)

    def _build_photo_album(
        self,
        detail: dict[str, Any],
        images: list[str],
    ) -> TikTokPhotoAlbum:
        if not images:
            raise TikTokDownloadError("Bu bağlantıda fotoğraf albümü bulunamadı.")
        caption = self._build_caption(detail, {})
        cover_url = self._pick_cover(detail)
        return TikTokPhotoAlbum(photos=images, caption=caption, cover_url=cover_url)

    async def _extract_info(self, target_url: str) -> dict[str, Any]:
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(None, partial(self._extract_sync, target_url))
        except DownloadError as exc:
            raise TikTokDownloadError(self._translate_download_error(exc)) from exc
        except ExtractorError as exc:
            message = exc.msg or "TikTok içeriği indirilemedi."
            raise TikTokDownloadError(message) from exc

    def _extract_sync(self, target_url: str) -> dict[str, Any]:
        opts = dict(self._YTDLP_BASE_OPTS)
        opts["socket_timeout"] = self._timeout
        with YoutubeDL(opts) as ydl:
            extractor = _RawTikTokIE(ydl)
            return extractor.extract(target_url)

    @staticmethod
    def _aweme(info: dict[str, Any]) -> dict[str, Any]:
        detail = info.get("_aweme_detail")
        if not isinstance(detail, dict):
            raise TikTokDownloadError("TikTok cevabı beklenen formatta değil.")
        return detail

    def _build_caption(self, detail: dict[str, Any], info: dict[str, Any]) -> str:
        author = (detail.get("author") or {}).get("nickname") or info.get("channel") or info.get("uploader")
        title = detail.get("desc") or info.get("title") or "TikTok"
        pieces = [title.strip() or "TikTok"]
        if author:
            pieces.append(f"👤 {author}")
        return "\n".join(pieces)

    def _extract_photo_sources(self, detail: dict[str, Any]) -> list[str]:
        photo_sources: list[Any] = []
        image_post = detail.get("imagePost") or detail.get("image_post") or {}
        if isinstance(image_post, dict):
            photo_sources.extend(
                image_post.get(key)
                for key in ("images", "cover", "shareCover", "coverImage", "cover_image")
            )
        image_info = detail.get("image_post_info") or detail.get("imagePostInfo")
        if isinstance(image_info, dict):
            photo_sources.extend(
                image_info.get(key) for key in ("images", "image_list", "imageList", "image_urls")
            )
        photo_sources.extend(
            detail.get(key)
            for key in ("images", "image_list", "imageList", "image_urls", "imageUrls")
        )
        collected = self._collect_photo_urls(*photo_sources)
        return collected

    @staticmethod
    def _pick_cover(detail: dict[str, Any]) -> str | None:
        video = detail.get("video") or {}
        covers = [
            video.get("cover"),
            video.get("originCover"),
            video.get("dynamicCover"),
        ]
        image_post = detail.get("imagePost") or {}
        if isinstance(image_post, dict):
            cover_dict = image_post.get("cover") or {}
            covers.append(cover_dict.get("imageURL"))
        photo_urls = TikTokDownloader._collect_photo_urls(*(covers or []))
        return photo_urls[0] if photo_urls else None

    @staticmethod
    def _translate_download_error(exc: DownloadError) -> str:
        message = str(exc)
        lower = message.lower()
        if "timed out" in lower or "timeout" in lower or "temporarily unavailable" in lower:
            return "TikTok servisine bağlanırken zaman aşımı oluştu, lütfen tekrar deneyin."
        if "404" in lower or "not found" in lower:
            return "TikTok bağlantısı bulunamadı. Lütfen linki kontrol edin."
        if "private" in lower or "login" in lower:
            return "Bu TikTok içeriği özel olduğu için indirilemiyor."
        return "TikTok isteği reddedildi. Lütfen bağlantıyı kontrol edin."

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
                "imageURL",
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
