"""Generic bot commands (start/help/about)."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

router = Router(name="base")

HELP_TEXT = "\n".join(
    [
        "<b>Sosyal Medya İndirici Bot</b>",
        "",
        "Nasıl kullanırım?",
        " • TikTok, X (Twitter) ya da Reddit linkini sohbete yapıştır, içerik otomatik iner.",
        " • Aynı mesajda birden fazla link gönderebilirsin; bot hepsini sırayla işler.",
        "",
        "Desteklenen içerikler:",
        " • TikTok videoları, hikâyeleri ve fotoğraf albümleri",
        " • X (Twitter) fotoğrafları, GIF'ler ve videolar",
        " • Reddit videoları, tekil görselleri ve galerileri",
        "",
        "İpuçları:",
        " • Paylaşımlar herkese açık olmalı, aksi hâlde içerik indirilemez.",
        " • Fotoğraf albümleri Telegram sınırı nedeniyle 10'lu paketler hâlinde gelir; kalan görseller tek tek gönderilir.",
        " • Videoları ya da fotoğrafları tekrar paylaşmak istersen mesajı yönlendirmen yeterli.",
    ]
)


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    """Greet the user and point them to /help."""

    await message.answer(
        "Merhaba! 👋\n\n"
          "TikTok, X (Twitter) ve Reddit linklerini bana gönder, videoları ve fotoğrafları senin için indirip paylaşayım.\n"
        "Her şey nasıl çalışıyor merak ediyorsan /help yazman yeterli."
    )


@router.message(Command(commands=["help"]))
async def handle_help(message: Message) -> None:
    """Explain how to control the bot."""

    await message.answer(HELP_TEXT)
