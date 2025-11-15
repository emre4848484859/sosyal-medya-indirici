"""Handlers responsible for TikTok downloads."""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import InputMediaPhoto, Message

from ..config import settings
from ..services.tiktok import TikTokDownloadError, TikTokDownloader
from ..utils.chunk import chunked

router = Router(name="tiktok")
logger = logging.getLogger(__name__)

downloader = TikTokDownloader(
    base_url=str(settings.tikwm_api_url),
    timeout=settings.http_timeout_seconds,
)


@router.message(Command("tiktok_video"))
async def handle_tiktok_video(message: Message) -> None:
    url = _extract_url_argument(message)
    if not url:
        await message.reply("Lütfen komuttan sonra bir TikTok linki ekleyin.")
        return

    status = await message.reply("🎬 Video hazırlanıyor, lütfen bekleyin…")
    try:
        asset = await downloader.fetch_video(url)
        await message.answer_video(video=asset.url, caption=asset.caption)
    except TikTokDownloadError as exc:
        await message.reply(f"⚠️ İndirme başarısız: {exc}")
    except Exception as exc:  # pragma: no cover - geniş hata yakalama
        logger.exception("TikTok video indirilemedi")
        await message.reply("Beklenmeyen bir hata oluştu, lütfen daha sonra tekrar deneyin.")
    finally:
        await _safe_delete(status)


@router.message(Command("tiktok_story"))
async def handle_tiktok_story(message: Message) -> None:
    url = _extract_url_argument(message)
    if not url:
        await message.reply("Lütfen komuttan sonra bir TikTok linki ekleyin.")
        return

    status = await message.reply("📽️ Hikâye indiriliyor…")
    try:
        asset = await downloader.fetch_story(url)
        await message.answer_video(video=asset.url, caption=f"TikTok Story\n{asset.caption}")
    except TikTokDownloadError as exc:
        await message.reply(f"⚠️ Hikâye indirilemedi: {exc}")
    except Exception:
        logger.exception("TikTok story indirilemedi")
        await message.reply("Beklenmeyen bir hata oluştu, lütfen daha sonra tekrar deneyin.")
    finally:
        await _safe_delete(status)


@router.message(Command("tiktok_photos"))
async def handle_tiktok_photos(message: Message) -> None:
    url = _extract_url_argument(message)
    if not url:
        await message.reply("Lütfen komuttan sonra bir TikTok linki ekleyin.")
        return

    status = await message.reply("🖼️ Fotoğraf albümü indiriliyor…")
    try:
        album = await downloader.fetch_photos(url)
        await _send_album(message, album.photos, album.caption)
    except TikTokDownloadError as exc:
        await message.reply(f"⚠️ Fotoğraflar indirilemedi: {exc}")
    except Exception:
        logger.exception("TikTok fotoğrafları indirilemedi")
        await message.reply("Beklenmeyen bir hata oluştu, lütfen daha sonra tekrar deneyin.")
    finally:
        await _safe_delete(status)


async def _send_album(message: Message, photos: list[str], caption: str) -> None:
    first_batch = True
    for chunk in chunked(photos, 10):
        media_group = []
        for idx, photo_url in enumerate(chunk):
            media_group.append(
                InputMediaPhoto(
                    media=photo_url,
                    caption=caption if first_batch and idx == 0 else None,
                )
            )
        await message.answer_media_group(media_group)
        first_batch = False


def _extract_url_argument(message: Message) -> str | None:
    text = message.text or message.caption or ""
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return None
    url = parts[1].strip()
    return url or None


async def _safe_delete(status_message: Message | None) -> None:
    if not status_message:
        return
    try:
        await status_message.delete()
    except Exception:
        logger.debug("Durum mesajı silinemedi", exc_info=True)
