"""Handlers responsible for TikTok downloads."""

from __future__ import annotations

import logging

import re

from aiogram import Router
from aiogram.filters import BaseFilter
from aiogram.types import InputMediaPhoto, Message

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
    for chunk in chunked(photos, 10):
        if len(chunk) == 1:
            await message.answer_photo(photo=chunk[0], caption=caption_pending)
        else:
            media_group = [
                InputMediaPhoto(
                    media=photo_url,
                    caption=caption_pending if idx == 0 else None,
                )
                for idx, photo_url in enumerate(chunk)
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
