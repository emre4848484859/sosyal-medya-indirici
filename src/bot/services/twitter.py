"""Twitter/X media downloader built on the VXTwitter API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx


class TwitterDownloadError(RuntimeError):
    """Raised when a Twitter/X asset could not be downloaded."""


@dataclass(slots=True)
class TwitterMediaAsset:
    """Represents a set of media extracted from a single tweet."""

    caption: str
    photos: list[str]
    video_url: str | None = None


class TwitterDownloader:
    """Thin wrapper around VXTwitter's JSON API."""

    def __init__(self, *, base_url: str, timeout: float = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def fetch_asset(self, tweet_url: str) -> TwitterMediaAsset:
        """Fetch tweet media contents by delegating to VXTwitter."""

        api_url = self._build_api_url(tweet_url)
        async with httpx.AsyncClient(
            timeout=self.timeout,
            headers={"Accept": "application/json"},
            follow_redirects=True,
        ) as client:
            try:
                response = await client.get(api_url)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                message = self._build_error_message(exc.response)
                raise TwitterDownloadError(message) from exc
            except httpx.HTTPError as exc:
                raise TwitterDownloadError("Twitter verilerine ulaşılamadı.") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise TwitterDownloadError("Beklenmeyen API yanıtı alındı.") from exc

        return self._parse_payload(payload)

    def _build_api_url(self, tweet_url: str) -> str:
        tweet_id = self._extract_tweet_id(tweet_url)
        return f"{self.base_url}/Twitter/status/{tweet_id}"

    @staticmethod
    def _extract_tweet_id(tweet_url: str) -> str:
        parsed = urlparse(tweet_url)
        if not parsed.path:
            msg = "Tweet bağlantısı çözümlenemedi."
            raise TwitterDownloadError(msg)

        path_parts = [part for part in parsed.path.split("/") if part]
        tweet_id = ""
        for idx, part in enumerate(path_parts):
            if part.lower() in {"status", "statuses"} and idx + 1 < len(path_parts):
                tweet_id = path_parts[idx + 1]
                break

        if not tweet_id:
            msg = "Tweet kimliği bulunamadı."
            raise TwitterDownloadError(msg)

        tweet_id = tweet_id.split("?", 1)[0]
        if not tweet_id.isdigit():
            msg = "Tweet kimliği geçersiz."
            raise TwitterDownloadError(msg)
        return tweet_id

    def _parse_payload(self, payload: dict[str, Any]) -> TwitterMediaAsset:
        tweet = payload.get("tweet") if isinstance(payload, dict) else None
        if not tweet:
            if isinstance(payload, dict):
                tweet = payload
            else:
                raise TwitterDownloadError("Tweet bilgisi çözümlenemedi.")

        caption = self._extract_caption(tweet, payload)
        photos = self._extract_photos(tweet, payload)
        video_url = self._extract_video(tweet, payload)

        if not photos and not video_url:
            msg = "Paylaşımda indirilebilir medya bulunamadı."
            raise TwitterDownloadError(msg)

        return TwitterMediaAsset(
            caption=caption,
            photos=photos,
            video_url=video_url,
        )

    @staticmethod
    def _extract_caption(tweet: dict[str, Any], payload: dict[str, Any]) -> str:
        for field in ("full_text", "text", "description", "content"):
            candidate = tweet.get(field) or payload.get(field)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        return ""

    def _extract_photos(self, tweet: dict[str, Any], payload: dict[str, Any]) -> list[str]:
        photos: list[str] = []
        for entry in tweet.get("media") or []:
            if isinstance(entry, dict) and (entry.get("type") or "").lower() == "photo":
                url = entry.get("url") or entry.get("media_url_https") or entry.get("media_url")
                if url:
                    normalized = self._normalize_url(url)
                    if normalized not in photos:
                        photos.append(normalized)

        if not photos:
            for url in payload.get("mediaURLs") or tweet.get("mediaURLs") or []:
                if isinstance(url, str):
                    normalized = self._normalize_url(url)
                    if "video.twimg.com" not in normalized and normalized not in photos:
                        photos.append(normalized)

        return photos

    def _extract_video(self, tweet: dict[str, Any], payload: dict[str, Any] | None = None) -> str | None:
        best_url: str | None = None
        best_score = -1
        payload = payload or {}

        def consider(url: str | None, bitrate: int | float | None = None) -> None:
            nonlocal best_url, best_score
            if not url:
                return
            normalized = self._normalize_url(url)
            if not self._is_video_url(normalized):
                return
            score = int(bitrate or 0)
            if score > best_score:
                best_url = normalized
                best_score = score

        sections = []
        video_section = tweet.get("video")
        if isinstance(video_section, dict):
            sections.append(video_section)
        sections.extend([item for item in tweet.get("videos") or [] if isinstance(item, dict)])

        for entry in sections:
            consider(entry.get("url"), entry.get("bitrate"))
            for variant in entry.get("variants") or []:
                if isinstance(variant, dict):
                    consider(variant.get("url"), variant.get("bitrate"))

        media_collections: list[list[dict[str, Any]]] = []

        def collect_media(value: Any) -> None:
            if isinstance(value, list):
                media_collections.append([entry for entry in value if isinstance(entry, dict)])

        collect_media(tweet.get("media"))
        collect_media(tweet.get("media_extended"))
        collect_media(payload.get("media_extended"))

        extended_entities = tweet.get("extended_entities")
        if isinstance(extended_entities, dict):
            collect_media(extended_entities.get("media"))

        for collection in media_collections:
            for media in collection:
                media_type = (media.get("type") or "").lower()
                if media_type not in {"video", "animated_gif"}:
                    continue
                consider(media.get("url") or media.get("video_url"), media.get("bitrate") or media.get("bit_rate"))
                for variant in media.get("variants") or []:
                    if isinstance(variant, dict):
                        consider(variant.get("url"), variant.get("bitrate") or variant.get("bit_rate"))

        def consider_url_sequence(urls: Any) -> None:
            if isinstance(urls, str):
                consider(urls, None)
            elif isinstance(urls, list):
                for url in urls:
                    if isinstance(url, str):
                        consider(url, None)

        consider_url_sequence(tweet.get("mediaURLs"))
        consider_url_sequence(payload.get("mediaURLs"))

        for key in ("combinedMediaUrl", "combinedMediaURL", "combined_media_url"):
            consider_url_sequence(tweet.get(key))
            consider_url_sequence(payload.get(key))

        return best_url

    @staticmethod
    def _is_video_url(url: str) -> bool:
        lowered = url.lower()
        if "video.twimg.com" in lowered:
            return True
        video_suffixes = (".mp4", ".mov", ".m4v", ".webm", ".mkv", ".m3u8")
        bare = lowered.split("?", 1)[0]
        return any(bare.endswith(ext) for ext in video_suffixes)

    @staticmethod
    def _normalize_url(url: str) -> str:
        if url.startswith("//"):
            return f"https:{url}"
        return url

    @staticmethod
    def _build_error_message(response: httpx.Response) -> str:
        try:
            data = response.json()
            for key in ("detail", "message", "error"):
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        except ValueError:
            pass
        return f"Twitter API hatası: {response.status_code}"
