import unittest
from unittest.mock import AsyncMock, patch

import httpx

from bot.services.tiktok import TikTokDownloadError, TikTokDownloader


class TikTokDownloaderPhotoAlbumTest(unittest.TestCase):
    def setUp(self) -> None:
        self.downloader = TikTokDownloader(base_url="https://example.com/api/")

    def test_build_photo_album_preserves_all_primary_images(self) -> None:
        photos = [f"https://cdn.example.com/img_{idx}.jpg" for idx in range(12)]
        data = {
            "title": "Sample album",
            "images": photos,
        }

        album = self.downloader._build_photo_album(data, photos)

        self.assertEqual(album.photos, photos)

    def test_build_photo_album_merges_nested_album_images(self) -> None:
        primary = [f"https://cdn.example.com/primary_{idx}.jpg" for idx in range(10)]
        nested_images = [
            {
                "image_url": f"https://cdn.example.com/extra_{idx}.jpg",
                "display_image": {
                    "url_list": [f"//cdn.example.com/extra_{idx}.jpg"],
                },
            }
            for idx in range(14)
        ]
        data = {
            "title": "Nested album",
            "images": primary,
            "image_post_info": {"images": nested_images},
        }

        album = self.downloader._build_photo_album(data, primary)

        self.assertEqual(len(album.photos), 24)
        self.assertEqual(album.photos[:10], primary)
        self.assertEqual(
            album.photos[10:],
            [f"https://cdn.example.com/extra_{idx}.jpg" for idx in range(14)],
        )

    def test_build_photo_album_without_photos_raises(self) -> None:
        with self.assertRaises(TikTokDownloadError):
            self.downloader._build_photo_album({"title": "Empty"}, images=[])


class TikTokDownloaderRequestHandlingTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.downloader = TikTokDownloader(base_url="https://example.com/api/")
        self.sample_url = "https://www.tiktok.com/@user/video/123"

    async def test_request_converts_server_errors(self) -> None:
        async_client = AsyncMock()
        async_client.__aenter__.return_value = async_client

        request = httpx.Request("POST", "https://example.com/api/")
        response = httpx.Response(status_code=500, request=request)
        async_client.post.return_value = response

        with patch("bot.services.tiktok.httpx.AsyncClient", return_value=async_client):
            with self.assertRaises(TikTokDownloadError) as ctx:
                await self.downloader._request(self.sample_url)

        self.assertIn("geçici bir sorun", str(ctx.exception))
        self.assertIn("HTTP 500", str(ctx.exception))

    async def test_request_converts_network_errors(self) -> None:
        async_client = AsyncMock()
        async_client.__aenter__.return_value = async_client

        request = httpx.Request("POST", "https://example.com/api/")
        async_client.post.side_effect = httpx.ReadTimeout("timeout", request=request)

        with patch("bot.services.tiktok.httpx.AsyncClient", return_value=async_client):
            with self.assertRaises(TikTokDownloadError) as ctx:
                await self.downloader._request(self.sample_url)

        self.assertIn("ağ hatası", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
