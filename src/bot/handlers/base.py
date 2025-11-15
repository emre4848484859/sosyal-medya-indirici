"""Generic bot commands (start/help/about)."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

router = Router(name="base")

HELP_TEXT = (
    "\n".join(
        [
            "<b>Sosyal Medya İndirici Bot</b>",
            "",
            "Komutlar:",
            " • /tiktok_video <link> — videoyu indirir",
            " • /tiktok_story <link> — hikâyeyi kaydeder",
            " • /tiktok_photos <link> — fotoğraf/albümleri yollar",
            "",
            "İpuçları:",
            " • Komutları özel sohbetten veya gruplardan kullanabilirsiniz.",
            " • Linkin herkese açık ve erişilebilir olduğundan emin olun.",
            " • Fotoğraf albümleri Telegram sınırı nedeniyle 10'lu paketlerle gönderilir.",
        ]
    )
)


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    """Greet the user and point them to /help."""

    await message.answer(
        "Merhaba! 👋\n"
        "TikTok içeriklerini indirmek için /help komutuyla detaylı bilgilere ulaşabilirsin."
    )


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    """Explain how to control the bot."""

    await message.answer(HELP_TEXT)
