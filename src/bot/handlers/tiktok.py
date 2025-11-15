"""Handlers responsible for TikTok downloads."""

from __future__ import annotations

import logging
import mimetypes
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx
from aiogram import Router
from aiogram.filters import BaseFilter
from aiogram.types import BufferedInputFile, InputMediaPhoto, Message

from ..config import settings
from ..services.tiktok import TikTokDownloadError, TikTokDownloader, TikTokPhotoAlbum
from ..utils.chunk import chunked

router = Router(name="tiktok")
logger = logging.getLogger(__name__)

downloader = TikTokDownloader(
    base_url=str(settings.tikwm_api_url),
    timeout=settings.http_timeout_seconds,
)

TIKTOK_URL_RE = re.compile(
    r"(?P<url>(?:https?://)?(?:[a-z0-9-]+\.)*tiktok\.com/[^\s]+)",
    re.IGNORECASE,
)

PHOTO_DOWNLOAD_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    ),
}


class TikTokLinkFilter(BaseFilter):
    """Detect TikTok links in any incoming message."""

    async def __call__(self, message: Message) -> bool | dict[str, str]:
        url = _extract_tiktok_url(message)
        if not url:
            return False
        return {"tiktok_url": url}


@router.message(TikTokLinkFilter())
async def handle_tiktok_link(message: Message, tiktok_url: str) -> None:
    """Automatically download any TikTok link shared in chat."""

    status = await message.reply("⬇️ TikTok linki işleniyor, lütfen bekleyin…")
    try:
        asset = await downloader.fetch_asset(tiktok_url)
        if isinstance(asset, TikTokPhotoAlbum):
            await _send_album(message, asset.photos, asset.caption)
        else:
            await message.answer_video(video=asset.url, caption=asset.caption)
    except TikTokDownloadError as exc:
        await message.reply(f"⚠️ İndirme başarısız: {exc}")
    except Exception:  # pragma: no cover - geniş hata yakalama
        logger.exception("TikTok içeriği indirilemedi")
        await message.reply("Beklenmeyen bir hata oluştu, lütfen daha sonra tekrar deneyin.")
    finally:
        await _safe_delete(status)


async def _send_album(message: Message, photos: list[str], caption: str) -> None:
    """Send photo albums respecting Telegram's media group constraints."""

    caption_pending = caption
    index = 1
    async with httpx.AsyncClient(
        timeout=settings.http_timeout_seconds,
        headers=PHOTO_DOWNLOAD_HEADERS,
        follow_redirects=True,
    ) as client:
        for chunk in chunked(photos, 10):
            downloaded: list[BufferedInputFile] = []
            for photo in chunk:
                downloaded.append(await _download_photo(photo, client, index))
                index += 1

            if len(downloaded) == 1:
                await message.answer_photo(photo=downloaded[0], caption=caption_pending)
            else:
                media_group = [
                    InputMediaPhoto(
                        media=photo_file,
                        caption=caption_pending if idx == 0 else None,
                    )
                    for idx, photo_file in enumerate(downloaded)
                ]
                await message.answer_media_group(media_group)
            caption_pending = None


def _extract_tiktok_url(message: Message) -> str | None:
    text = message.text or message.caption or ""
    match = TIKTOK_URL_RE.search(text)
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


async def _download_photo(
    photo_url: str,
    client: httpx.AsyncClient,
    sequence: int,
) -> BufferedInputFile:
    try:
        response = await client.get(photo_url)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Fotoğraf indirilemedi: %s", photo_url, exc_info=exc)
        raise TikTokDownloadError("TikTok fotoğrafı indirilemedi.") from exc

    filename = _build_photo_filename(photo_url, response.headers.get("Content-Type"), sequence)
    return BufferedInputFile(response.content, filename=filename)


def _build_photo_filename(photo_url: str, content_type: str | None, sequence: int) -> str:
    parsed = urlparse(photo_url)
    path = Path(parsed.path or "")
    suffix = path.suffix if len(path.suffix) <= 5 else ""

    if not suffix and content_type:
        guessed = mimetypes.guess_extension(content_type.split(";", 1)[0].strip()) or ""
        suffix = ".jpg" if guessed == ".jpe" else guessed

    if not suffix:
        suffix = ".jpg"

    stem = path.stem or f"tiktok_photo_{sequence:02d}"
    return f"{stem}{suffix}"
