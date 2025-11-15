"""Handle Telegram message links and relay their media back to the user."""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import BaseFilter
from aiogram.types import FSInputFile, Message
from telethon.errors import (
    ChannelInvalidError,
    ChannelPrivateError,
    MessageIdInvalidError,
    UsernameInvalidError,
    UsernameNotOccupiedError,
)

from ..config import settings
from ..services.telegram_fetcher import (
    TelethonCredentialsError,
    TelegramMediaDownloadError,
    TelegramMediaResult,
    TelegramMessageFetcher,
    TelegramMessageNotFoundError,
    TelegramLink,
    extract_telegram_link,
)

router = Router(name="telegram_media")
logger = logging.getLogger(__name__)

fetcher: TelegramMessageFetcher | None = None
if settings.telethon_enabled():
    fetcher = TelegramMessageFetcher(
        api_id=int(settings.telethon_api_id),
        api_hash=str(settings.telethon_api_hash),
        session_string=str(settings.telethon_session_string),
    )


class TelegramLinkFilter(BaseFilter):
    """Detect Telegram message links."""

    async def __call__(self, message: Message) -> bool | dict[str, TelegramLink]:
        text = message.text or message.caption or ""
        link = extract_telegram_link(text)
        if not link:
            return False
        return {"telegram_link": link}


@router.message(TelegramLinkFilter())
async def handle_telegram_link(message: Message, telegram_link: TelegramLink) -> None:
    """Download the media from a Telegram message link and forward it to the user."""

    status = await message.reply("🔁 Telegram linki işleniyor, lütfen bekleyin…")

    if not fetcher:
        await _update_status(
            status,
            "⚙️ Telethon kimlik bilgileri ayarlanmadığı için bu özellik devre dışı.",
            fallback=message,
        )
        return

    result: TelegramMediaResult | None = None
    try:
        result = await fetcher.fetch(telegram_link)
        if not result.media_kind or not result.file_path:
            await _update_status(status, "ℹ️ Bu mesajda indirilebilir bir medya bulunamadı.", fallback=message)
            return

        await _send_media(message, result)
        await _update_status(status, "✅ Medya başarıyla gönderildi!", fallback=message)
    except TelethonCredentialsError as exc:
        logger.warning("Telethon kimlik bilgileriyle oturum açılamadı: %s", exc)
        await _update_status(
            status,
            "⚙️ Telethon oturumuna bağlanılamadı, lütfen yöneticinize bildiriniz.",
            fallback=message,
        )
    except ChannelPrivateError:
        await _update_status(status, "🚫 Hata: Bu kanala erişimim yok.", fallback=message)
    except (ChannelInvalidError, UsernameInvalidError, UsernameNotOccupiedError):
        await _update_status(
            status,
            "⚠️ Hata: Linkteki kanal ya da kullanıcı adı bulunamadı.",
            fallback=message,
        )
    except (MessageIdInvalidError, TelegramMessageNotFoundError):
        await _update_status(
            status,
            "⚠️ Hata: Mesaj bulunamadı. Linki kontrol eder misin?",
            fallback=message,
        )
    except TelegramMediaDownloadError:
        await _update_status(
            status,
            "⚠️ Medya indirilemedi, lütfen biraz sonra tekrar dene.",
            fallback=message,
        )
    except Exception:  # pragma: no cover - hızlı geri bildirim için geniş kapsama
        logger.exception("Telegram linki işlenemedi")
        await _update_status(
            status,
            "❌ Beklenmeyen bir hata oluştu, lütfen tekrar dene.",
            fallback=message,
        )
    finally:
        if result:
            result.cleanup()


async def _send_media(message: Message, result: TelegramMediaResult) -> None:
    if not result.file_path:
        raise TelegramMediaDownloadError("İndirilen medya bulunamadı.")

    file = FSInputFile(str(result.file_path), filename=result.file_name)
    caption = result.caption or None

    if result.media_kind == "photo":
        await message.answer_photo(file, caption=caption)
    elif result.media_kind == "video":
        await message.answer_video(file, caption=caption)
    elif result.media_kind == "animation":
        await message.answer_animation(file, caption=caption)
    elif result.media_kind == "audio":
        await message.answer_audio(file, caption=caption)
    elif result.media_kind == "voice":
        await message.answer_voice(file, caption=caption)
    else:
        await message.answer_document(file, caption=caption)


async def _update_status(
    status_message: Message | None,
    text: str,
    *,
    fallback: Message | None = None,
) -> None:
    if status_message:
        try:
            await status_message.edit_text(text)
            return
        except Exception:
            logger.debug("Durum mesajı güncellenemedi", exc_info=True)
    target = fallback or status_message
    if target:
        await target.answer(text)
