"""Handlers responsible for Twitter/X downloads."""

from __future__ import annotations

import logging
import mimetypes
import re
from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse

import httpx
from aiogram import Router
from aiogram.filters import BaseFilter
from aiogram.types import BufferedInputFile, Message

from ..config import settings
from ..services.twitter import TwitterDownloadError, TwitterDownloader
from ..utils.telegram_media import send_photo_album

router = Router(name="twitter")
logger = logging.getLogger(__name__)

downloader = TwitterDownloader(
    base_url=str(settings.twitter_api_base_url),
    timeout=settings.http_timeout_seconds,
)

TWITTER_URL_RE = re.compile(
    r"(?P<url>(?:https?://)?(?:www\.)?(?:twitter|x)\.com/[^\s]+)",
    re.IGNORECASE,
)

PHOTO_DOWNLOAD_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    ),
    "Referer": "https://x.com/",
}
VIDEO_DOWNLOAD_HEADERS = {
    **PHOTO_DOWNLOAD_HEADERS,
    "Accept": "video/mp4,video/*;q=0.9,*/*;q=0.8",
}


class TwitterLinkFilter(BaseFilter):
    """Detect Twitter/X links in any incoming message."""

    async def __call__(self, message: Message) -> bool | dict[str, str]:
        url = _extract_twitter_url(message)
        if not url:
            return False
        return {"tweet_url": url}


@router.message(TwitterLinkFilter())
async def handle_twitter_link(message: Message, tweet_url: str) -> None:
    """Automatically download any Twitter/X link shared in chat."""

    status = await message.reply("⬇️ Twitter/X linki işleniyor, lütfen bekleyin…")
    try:
        asset = await downloader.fetch_asset(tweet_url)
        caption_for_photos = asset.caption
        if asset.video_url:
            video_file = await _download_video(
                asset.video_url,
                timeout=settings.http_timeout_seconds,
                headers=VIDEO_DOWNLOAD_HEADERS,
            )
            await message.answer_video(video=video_file, caption=asset.caption or None)
            caption_for_photos = None

        if asset.photos:
            await send_photo_album(
                message,
                asset.photos,
                caption_for_photos,
                timeout=settings.http_timeout_seconds,
                headers=PHOTO_DOWNLOAD_HEADERS,
                logger=logger,
                error_cls=TwitterDownloadError,
                filename_prefix="twitter_photo",
            )
    except TwitterDownloadError as exc:
        await message.reply(f"⚠️ İndirme başarısız: {exc}")
    except Exception:  # pragma: no cover - geniş hata yakalama
        logger.exception("Twitter içeriği indirilemedi")
        await message.reply("Beklenmeyen bir hata oluştu, lütfen daha sonra tekrar deneyin.")
    finally:
        await _safe_delete(status)


def _extract_twitter_url(message: Message) -> str | None:
    text = message.text or message.caption or ""
    match = TWITTER_URL_RE.search(text)
    if not match:
        return None
    raw_url = match.group("url").strip()
    cleaned = raw_url.rstrip(").,!?")
    if not cleaned.startswith(("http://", "https://")):
        cleaned = f"https://{cleaned}"
    return cleaned


async def _safe_delete(status_message: Message | None) -> None:
    if not status_message:
        return
    try:
        await status_message.delete()
    except Exception:
        logger.debug("Durum mesajı silinemedi", exc_info=True)


async def _download_video(
    video_url: str,
    *,
    timeout: float,
    headers: Mapping[str, str] | None = None,
) -> BufferedInputFile:
    content: bytes
    content_type: str | None
    async with httpx.AsyncClient(
        timeout=timeout,
        headers=dict(headers or {}),
        follow_redirects=True,
    ) as client:
        try:
            response = await client.get(video_url)
            response.raise_for_status()
        except httpx.HTTPError as exc:  # pragma: no cover - ağ hataları
            logger.warning("Video indirilemedi: %s", video_url, exc_info=exc)
            raise TwitterDownloadError("Video indirilemedi.") from exc
        content = response.content
        content_type = response.headers.get("Content-Type")

    filename = _build_video_filename(video_url, content_type)
    return BufferedInputFile(content, filename=filename)


def _build_video_filename(video_url: str, content_type: str | None) -> str:
    parsed = urlparse(video_url)
    path = Path(parsed.path or "")
    suffix = path.suffix if path.suffix and len(path.suffix) <= 5 else ""

    if not suffix and content_type:
        mime = content_type.split(";", 1)[0].strip()
        guessed = mimetypes.guess_extension(mime) or ""
        if guessed == ".jpe":
            guessed = ".jpg"
        suffix = guessed

    if not suffix:
        suffix = ".mp4"

    stem = path.stem or "twitter_video"
    return f"{stem}{suffix}"
