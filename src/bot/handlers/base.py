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
            "Nasıl kullanılır?",
            " • Herhangi bir TikTok linkini sohbete gönderin, bot otomatik olarak indirir.",
            " • Videolar, story'ler ve fotoğraf albümleri tek komutla ayırt edilir.",
            "",
            "İpuçları:",
            " • Linkin herkese açık ve erişilebilir olduğundan emin olun.",
            " • Fotoğraf albümleri Telegram kısıtlamaları nedeniyle en fazla 10'lu paketlerle paylaşılır; kalan görseller tekil mesajlarla gönderilir.",
        ]
    )
)


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    """Greet the user and point them to /help."""

    await message.answer(
        "Merhaba! 👋\n"
        "TikTok linklerini direkt sohbete gönder, kalanını ben hallederim.\n"
        "Detaylar için /help yazabilirsin."
    )


@router.message(Command(commands=["help"]))
async def handle_help(message: Message) -> None:
    """Explain how to control the bot."""

    await message.answer(HELP_TEXT)
