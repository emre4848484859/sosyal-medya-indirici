"""Entrypoint for the Telegram bot."""

from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from .config import settings
from .handlers.base import router as base_router
from .handlers.tiktok import router as tiktok_router
from .logging import setup_logging


async def _run() -> None:
    setup_logging()

    bot = Bot(token=settings.bot_token, parse_mode=ParseMode.HTML)
    dp = Dispatcher()

    dp.include_router(base_router)
    dp.include_router(tiktok_router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        pass
