"""Utilities for parsing Telegram message links and fetching their media via Telethon."""

from __future__ import annotations

import re
import shutil
import tempfile
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from telethon import TelegramClient
from telethon.errors import ChannelInvalidError, SessionPasswordNeededError
from telethon.sessions import StringSession
from telethon.tl.types import Message as TelethonMessage
from telethon.tl.types import PeerChannel


class TelethonCredentialsError(RuntimeError):
    """Raised when Telethon credentials are missing or unauthorized."""


class TelegramMessageNotFoundError(RuntimeError):
    """Raised when a Telegram message cannot be retrieved."""


class TelegramMediaDownloadError(RuntimeError):
    """Raised when Telegram media cannot be downloaded."""


TELEGRAM_LINK_RE = re.compile(
    r"(?P<link>(?:https?://)?(?:t|telegram)\.me/(?:(?P<username>[A-Za-z0-9_]+)/(?P<public_message_id>\d+)|c/(?P<channel_id>\d+)/(?P<channel_message_id>\d+)))",
    re.IGNORECASE,
)


@dataclass(slots=True)
class TelegramLink:
    """Normalized representation of a Telegram message URL."""

    raw_url: str
    identifier: str
    message_id: int
    kind: Literal["username", "channel"]

    @property
    def is_username(self) -> bool:
        return self.kind == "username"


@dataclass(slots=True)
class TelegramMediaResult:
    """Holds fetched message details and downloaded media metadata."""

    message: TelethonMessage
    media_kind: Literal["photo", "video", "animation", "audio", "voice", "document"] | None
    file_path: Path | None
    file_name: str | None
    _temp_dir: Path | None = None

    @property
    def caption(self) -> str:
        text = self.message.message or ""
        return text.strip()

    def cleanup(self) -> None:
        """Remove any temporary files created during download."""

        if self.file_path:
            try:
                self.file_path.unlink(missing_ok=True)
            except OSError:
                pass

        if self._temp_dir:
            try:
                shutil.rmtree(self._temp_dir, ignore_errors=True)
            except OSError:
                pass


def extract_telegram_link(text: str | None) -> TelegramLink | None:
    """Return the first Telegram message link found in text."""

    if not text:
        return None

    match = TELEGRAM_LINK_RE.search(text)
    if not match:
        return None

    raw_url = match.group("link").strip()
    if not raw_url.startswith(("http://", "https://")):
        raw_url = f"https://{raw_url}"

    username = match.group("username")
    if username:
        message_id = int(match.group("public_message_id"))
        return TelegramLink(
            raw_url=raw_url,
            identifier=username,
            message_id=message_id,
            kind="username",
        )

    channel_id = match.group("channel_id")
    if not channel_id:
        return None

    message_id = int(match.group("channel_message_id"))
    return TelegramLink(
        raw_url=raw_url,
        identifier=channel_id,
        message_id=message_id,
        kind="channel",
    )


class TelegramMessageFetcher:
    """Fetch Telegram messages and download media contents via Telethon."""

    def __init__(self, *, api_id: int, api_hash: str, session_string: str) -> None:
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_string = session_string

    async def fetch(self, link: TelegramLink) -> TelegramMediaResult:
        """Fetch the Telegram message identified by the given link."""

        async with self._client() as client:
            entity = await self._resolve_entity(client, link)
            message = await client.get_messages(entity, ids=link.message_id)
            if isinstance(message, list):
                message = message[0] if message else None
            if not message:
                raise TelegramMessageNotFoundError("Mesaj bulunamadı.")

            media_kind = self._detect_media_kind(message)
            file_path: Path | None = None
            temp_dir: Path | None = None

            if media_kind:
                temp_dir = Path(tempfile.mkdtemp(prefix="telegram_media_"))
                downloaded = await client.download_media(message, file=temp_dir)
                if not downloaded:
                    raise TelegramMediaDownloadError("Medya indirilemedi.")
                file_path = Path(downloaded)

            file_name = self._resolve_file_name(message, file_path)
            return TelegramMediaResult(
                message=message,
                media_kind=media_kind,
                file_path=file_path,
                file_name=file_name,
                _temp_dir=temp_dir,
            )

    @asynccontextmanager
    async def _client(self) -> TelegramClient:
        if not self.api_id or not self.api_hash or not self.session_string:
            raise TelethonCredentialsError("Telethon kimlik bilgileri eksik.")

        client = TelegramClient(
            StringSession(self.session_string),
            self.api_id,
            self.api_hash,
        )
        await client.connect()
        try:
            if not await client.is_user_authorized():
                raise TelethonCredentialsError("Telethon oturumu yetkilendirilmemiş.")
            yield client
        except SessionPasswordNeededError as exc:
            raise TelethonCredentialsError("Telethon hesabı için iki aşamalı doğrulama gerekiyor.") from exc
        finally:
            await client.disconnect()

    async def _resolve_entity(self, client: TelegramClient, link: TelegramLink):
        if link.is_username:
            return await client.get_entity(link.identifier)

        try:
            channel_id = int(link.identifier)
        except ValueError as exc:  # pragma: no cover - regex already enforces digits
            raise ChannelInvalidError(link.identifier) from exc

        peer = PeerChannel(channel_id)
        return await client.get_entity(peer)

    @staticmethod
    def _detect_media_kind(
        message: TelethonMessage,
    ) -> Literal["photo", "video", "animation", "audio", "voice", "document"] | None:
        if message.photo:
            return "photo"
        if message.video:
            return "video"
        if message.gif:
            return "animation"
        if message.audio:
            return "audio"
        if message.voice:
            return "voice"
        if message.document:
            return "document"
        return None

    @staticmethod
    def _resolve_file_name(message: TelethonMessage, file_path: Path | None) -> str | None:
        document = message.document or message.video or message.audio or message.voice
        if document and document.attributes:
            for attribute in document.attributes:
                name = getattr(attribute, "file_name", None)
                if isinstance(name, str) and name.strip():
                    return name
        if message.photo:
            return "photo.jpg"
        if file_path:
            return file_path.name
        return None


__all__ = [
    "TelethonCredentialsError",
    "TelegramLink",
    "TelegramMediaDownloadError",
    "TelegramMediaResult",
    "TelegramMessageFetcher",
    "TelegramMessageNotFoundError",
    "extract_telegram_link",
]
