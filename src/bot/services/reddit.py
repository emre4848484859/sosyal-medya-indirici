"""Reddit media downloader built on top of the public JSON listing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final
from urllib.parse import urlparse

import httpx


class RedditDownloadError(RuntimeError):
    """Raised when Reddit media cannot be downloaded."""


@dataclass(slots=True)
class RedditMediaAsset:
    """Represents media extracted from a Reddit post."""

    caption: str
    photos: list[str]
    video_url: str | None = None


class RedditDownloader:
    """Fetch Reddit posts via the raw JSON endpoint."""

    _DEFAULT_HEADERS: Final[dict[str, str]] = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
    }

    def __init__(self, *, base_url: str, timeout: float = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def fetch_asset(self, post_url: str) -> RedditMediaAsset:
        """Resolve the post URL and download all related media."""

        api_url = self._build_api_url(post_url)
        params = {"raw_json": 1}
        async with httpx.AsyncClient(
            timeout=self.timeout,
            headers=self._DEFAULT_HEADERS,
            follow_redirects=True,
        ) as client:
            try:
                response = await client.get(api_url, params=params)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise RedditDownloadError("Reddit verilerine ulaşılamadı.") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise RedditDownloadError("Beklenmeyen Reddit yanıtı alındı.") from exc

        post = self._extract_post(payload)
        if not isinstance(post, dict):
            raise RedditDownloadError("Paylaşım bilgisi bulunamadı.")

        return self._build_asset(post)

    def _build_api_url(self, post_url: str) -> str:
        post_id = self._extract_post_id(post_url)
        return f"{self.base_url}/comments/{post_id}.json"

    def _extract_post_id(self, post_url: str) -> str:
        parsed = urlparse(post_url)
        netloc = (parsed.netloc or "").lower()
        path_parts = [part for part in (parsed.path or "").split("/") if part]

        candidate: str | None = None
        if netloc.endswith("redd.it"):
            candidate = path_parts[0] if path_parts else None
        else:
            for idx, part in enumerate(path_parts):
                if part.lower() == "comments" and idx + 1 < len(path_parts):
                    candidate = path_parts[idx + 1]
                    break
            if not candidate and path_parts:
                special_prefixes = {"gallery", "poll"}
                if path_parts[0].lower() in special_prefixes and len(path_parts) >= 2:
                    candidate = path_parts[1]
                elif len(path_parts) == 1:
                    candidate = path_parts[0]

        if not candidate:
            raise RedditDownloadError("Reddit bağlantısı çözümlenemedi.")

        candidate = candidate.split("?", 1)[0].split("#", 1)[0]
        if not candidate or not candidate.isalnum():
            raise RedditDownloadError("Reddit gönderi kimliği bulunamadı.")
        return candidate

    def _extract_post(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, list):
            for item in payload:
                post = self._extract_post(item)
                if post:
                    return post
            return None

        if not isinstance(payload, dict):
            return None

        data = payload.get("data")
        if isinstance(data, dict):
            children = data.get("children")
            if isinstance(children, list):
                for child in children:
                    if isinstance(child, dict):
                        child_data = child.get("data")
                        if isinstance(child_data, dict):
                            return child_data
            elif payload.get("kind") == "t3":
                return data

        if payload.get("kind") == "t3" and isinstance(payload.get("data"), dict):
            return payload["data"]

        return None

    def _build_asset(self, post: dict[str, Any]) -> RedditMediaAsset:
        photos = self._extract_photos(post)
        video_url = self._extract_video(post)

        if not photos and not video_url:
            raise RedditDownloadError("Paylaşımda indirilebilir medya bulunamadı.")

        caption = self._build_caption(post)
        return RedditMediaAsset(caption=caption, photos=photos, video_url=video_url)

    def _extract_photos(self, post: dict[str, Any]) -> list[str]:
        photos = self._extract_gallery_photos(post)
        if photos:
            return photos

        single = self._extract_single_photo(post)
        return [single] if single else []

    def _extract_gallery_photos(self, post: dict[str, Any]) -> list[str]:
        metadata = post.get("media_metadata")
        if not isinstance(metadata, dict):
            return []

        ordered_ids: list[str] = []
        gallery_data = post.get("gallery_data")
        if isinstance(gallery_data, dict):
            for item in gallery_data.get("items") or []:
                media_id = item.get("media_id") if isinstance(item, dict) else None
                if isinstance(media_id, str):
                    ordered_ids.append(media_id)
        if not ordered_ids:
            ordered_ids = list(metadata.keys())

        photos: list[str] = []
        seen: set[str] = set()

        for media_id in ordered_ids:
            entry = metadata.get(media_id)
            url = self._resolve_gallery_url(entry)
            if not url:
                continue
            normalized = self._normalize_url(url)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            photos.append(normalized)

        return photos

    @staticmethod
    def _resolve_gallery_url(entry: Any) -> str | None:
        if not isinstance(entry, dict):
            return None
        if (entry.get("status") or "").lower() != "valid":
            return None

        sources = []
        preferred = entry.get("s")
        if isinstance(preferred, dict):
            sources.append(preferred)
        for preview in entry.get("p") or []:
            if isinstance(preview, dict):
                sources.append(preview)
        for source in sources:
            url = source.get("u") or source.get("url")
            if isinstance(url, str) and url.strip():
                return url
        return None

    def _extract_single_photo(self, post: dict[str, Any]) -> str | None:
        direct = post.get("url_overridden_by_dest") or post.get("url")
        if isinstance(direct, str) and self._is_image_url(direct):
            return self._normalize_url(direct)

        preview = post.get("preview")
        if isinstance(preview, dict):
            images = preview.get("images")
            if isinstance(images, list):
                for image in images:
                    if not isinstance(image, dict):
                        continue
                    source = image.get("source")
                    if isinstance(source, dict):
                        url = source.get("url")
                        if isinstance(url, str) and url:
                            normalized = self._normalize_url(url)
                            if normalized:
                                return normalized
        return None

    def _extract_video(self, post: dict[str, Any]) -> str | None:
        video_sections = [
            post.get("secure_media"),
            post.get("media"),
            (post.get("preview") or {}).get("reddit_video_preview"),
        ]
        for section in video_sections:
            url = self._extract_reddit_video(section)
            if url:
                return url

        direct = post.get("url_overridden_by_dest") or post.get("url")
        if isinstance(direct, str) and self._is_video_url(direct):
            return self._normalize_url(direct)

        for parent in post.get("crosspost_parent_list") or []:
            if isinstance(parent, dict):
                candidate = self._extract_video(parent)
                if candidate:
                    return candidate

        return None

    def _extract_reddit_video(self, section: Any) -> str | None:
        if not isinstance(section, dict):
            return None

        reddit_video = section.get("reddit_video")
        if isinstance(reddit_video, dict):
            for key in ("fallback_url", "scrubber_media_url", "hls_url", "dash_url"):
                url = reddit_video.get(key)
                if isinstance(url, str) and url:
                    normalized = self._normalize_url(url)
                    if normalized:
                        return normalized
            return None

        if section.get("type") == "video":
            url = section.get("fallback_url") or section.get("url")
            if isinstance(url, str):
                normalized = self._normalize_url(url)
                if normalized:
                    return normalized
        return None

    @staticmethod
    def _build_caption(post: dict[str, Any]) -> str:
        title = (post.get("title") or "").strip() or "Reddit"
        author = (post.get("author") or "").strip()
        caption = title
        if author:
            caption = f"{title}\n👤 u/{author}"
        return caption

    @staticmethod
    def _normalize_url(url: str | None) -> str | None:
        if not url:
            return None
        candidate = url.strip()
        if not candidate:
            return None
        candidate = candidate.replace("&amp;", "&")
        if candidate.startswith("//"):
            candidate = f"https:{candidate}"
        if candidate.startswith(("http://", "https://")):
            return candidate
        return None

    @staticmethod
    def _is_image_url(url: str) -> bool:
        normalized = url.lower().split("?", 1)[0]
        image_suffixes = (".jpg", ".jpeg", ".png", ".gif", ".webp")
        return any(normalized.endswith(ext) for ext in image_suffixes)

    @staticmethod
    def _is_video_url(url: str) -> bool:
        normalized = url.lower().split("?", 1)[0]
        video_suffixes = (".mp4", ".mov", ".m4v", ".webm")
        return any(normalized.endswith(ext) for ext in video_suffixes) or "v.redd.it" in normalized

