"""Handlers responsible for Reddit downloads."""

from __future__ import annotations

import logging
import re

from aiogram import Router
from aiogram.filters import BaseFilter
from aiogram.types import Message

from ..config import settings
from ..services.reddit import RedditDownloadError, RedditDownloader
from ..utils.telegram_media import send_photo_album

router = Router(name="reddit")
logger = logging.getLogger(__name__)

downloader = RedditDownloader(
    base_url=str(settings.reddit_api_base_url),
    timeout=settings.http_timeout_seconds,
)

REDDIT_URL_RE = re.compile(
    r"(?P<url>(?:https?://)?(?:www\.|old\.|new\.|m\.)?(?:reddit\.com|redd\.it)/[^\s]+)",
    re.IGNORECASE,
)

MEDIA_DOWNLOAD_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.reddit.com/",
}


class RedditLinkFilter(BaseFilter):
    """Detect Reddit links in incoming messages."""

    async def __call__(self, message: Message) -> bool | dict[str, str]:
        url = _extract_reddit_url(message)
        if not url:
            return False
        return {"reddit_url": url}


@router.message(RedditLinkFilter())
async def handle_reddit_link(message: Message, reddit_url: str) -> None:
    """Download Reddit media whenever a link is shared."""

    status = await message.reply("⬇️ Reddit linki işleniyor, lütfen bekleyin…")
    try:
        asset = await downloader.fetch_asset(reddit_url)
        caption_for_photos = asset.caption or None

        if asset.video_url:
            await message.answer_video(video=asset.video_url, caption=asset.caption or None)
            if asset.photos:
                caption_for_photos = None

        if asset.photos:
            await send_photo_album(
                message,
                asset.photos,
                caption_for_photos,
                timeout=settings.http_timeout_seconds,
                headers=MEDIA_DOWNLOAD_HEADERS,
                logger=logger,
                error_cls=RedditDownloadError,
                filename_prefix="reddit_photo",
            )
    except RedditDownloadError as exc:
        await message.reply(f"⚠️ İndirme başarısız: {exc}")
    except Exception:  # pragma: no cover - geniş hata yakalama
        logger.exception("Reddit içeriği indirilemedi")
        await message.reply("Beklenmeyen bir hata oluştu, lütfen daha sonra tekrar deneyin.")
    finally:
        await _safe_delete(status)


def _extract_reddit_url(message: Message) -> str | None:
    text = message.text or message.caption or ""
    match = REDDIT_URL_RE.search(text)
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
