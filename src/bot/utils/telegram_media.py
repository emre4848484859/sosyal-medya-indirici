"""Helpers for sending Telegram media responses."""

from __future__ import annotations

import logging
import mimetypes
from pathlib import Path
from typing import Mapping, MutableMapping, Sequence
from urllib.parse import urlparse

import httpx
from aiogram.types import BufferedInputFile, InputMediaPhoto, Message

from .chunk import chunked


async def send_photo_album(
    message: Message,
    photos: Sequence[str],
    caption: str | None,
    *,
    timeout: float,
    headers: Mapping[str, str] | None = None,
    logger: logging.Logger | None = None,
    error_cls: type[Exception] = RuntimeError,
    filename_prefix: str = "photo",
    chunk_size: int = 10,
) -> None:
    """Download photos and send them respecting Telegram media group limits."""

    if not photos:
        raise error_cls("Gönderilebilecek fotoğraf bulunamadı.")

    caption_pending = caption
    sequence = 1
    async with httpx.AsyncClient(
        timeout=timeout,
        headers=_build_headers(headers),
        follow_redirects=True,
    ) as client:
        for chunk in chunked(photos, chunk_size):
            downloaded = []
            for photo_url in chunk:
                downloaded.append(
                    await _download_photo(
                        photo_url,
                        client,
                        sequence,
                        error_cls=error_cls,
                        filename_prefix=filename_prefix,
                        logger=logger,
                    )
                )
                sequence += 1

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


async def _download_photo(
    photo_url: str,
    client: httpx.AsyncClient,
    sequence: int,
    *,
    error_cls: type[Exception],
    filename_prefix: str,
    logger: logging.Logger | None,
) -> BufferedInputFile:
    try:
        response = await client.get(photo_url)
        response.raise_for_status()
    except httpx.HTTPError as exc:  # pragma: no cover - httpx already tested
        if logger:
            logger.warning("Fotoğraf indirilemedi: %s", photo_url, exc_info=exc)
        raise error_cls("Fotoğraf indirilemedi.") from exc

    filename = _build_photo_filename(
        photo_url,
        response.headers.get("Content-Type"),
        sequence,
        filename_prefix=filename_prefix,
    )
    return BufferedInputFile(response.content, filename=filename)


def _build_photo_filename(
    photo_url: str,
    content_type: str | None,
    sequence: int,
    *,
    filename_prefix: str,
) -> str:
    parsed = urlparse(photo_url)
    path = Path(parsed.path or "")
    suffix = path.suffix if len(path.suffix) <= 5 else ""

    if not suffix and content_type:
        guessed = mimetypes.guess_extension(content_type.split(";", 1)[0].strip()) or ""
        suffix = ".jpg" if guessed == ".jpe" else guessed

    if not suffix:
        suffix = ".jpg"

    stem = path.stem or f"{filename_prefix}_{sequence:02d}"
    return f"{stem}{suffix}"


def _build_headers(headers: Mapping[str, str] | None) -> MutableMapping[str, str]:
    if headers is None:
        return {}
    return dict(headers)
