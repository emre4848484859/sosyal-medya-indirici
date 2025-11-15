"""Entrypoint for the Telegram bot."""

from __future__ import annotations

import asyncio

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from .config import settings
from .handlers.base import router as base_router
from .handlers.tiktok import router as tiktok_router
from .handlers.twitter import router as twitter_router
from .logging import setup_logging


def _build_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.include_router(base_router)
    dispatcher.include_router(tiktok_router)
    dispatcher.include_router(twitter_router)
    return dispatcher


async def _run_polling() -> None:
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = _build_dispatcher()

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


async def _run_webhook() -> None:
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = _build_dispatcher()

    webhook_path = settings.webhook_path.strip() or "/webhook"
    if not webhook_path.startswith("/"):
        webhook_path = f"/{webhook_path}"

    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=webhook_path)
    setup_application(app, dp, bot=bot)

    async def on_startup(_: web.Application) -> None:
        await bot.set_webhook(
            url=settings.webhook_url(),
            secret_token=settings.webhook_secret,
            drop_pending_updates=True,
        )

    async def on_shutdown(_: web.Application) -> None:
        await bot.delete_webhook()

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=settings.port)
    await site.start()

    try:
        await asyncio.Future()
    except asyncio.CancelledError:
        pass
    finally:
        await runner.cleanup()


def main() -> None:
    setup_logging()
    if settings.bot_mode == "webhook":
        asyncio.run(_run_webhook())
    else:
        asyncio.run(_run_polling())


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        pass
