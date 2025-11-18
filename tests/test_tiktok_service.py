import unittest
from unittest.mock import patch

from yt_dlp.utils import DownloadError

from bot.services.tiktok import TikTokDownloadError, TikTokDownloader


class TikTokDownloaderPhotoAlbumTest(unittest.TestCase):
    def setUp(self) -> None:
        self.downloader = TikTokDownloader()

    def test_extract_photo_sources_merges_nested_album_images(self) -> None:
        primary = [
            {"imageURL": {"urlList": [f"https://cdn.example.com/primary_{idx}.jpg"]}}
            for idx in range(3)
        ]
        nested_images = [
            {
                "image_url": f"https://cdn.example.com/extra_{idx}.jpg",
                "display_image": {"url_list": [f"//cdn.example.com/mirror_extra_{idx}.jpg"]},
            }
            for idx in range(2)
        ]
        detail = {
            "desc": "Nested album",
            "imagePost": {"images": primary},
            "image_post_info": {"images": nested_images},
        }

        photos = self.downloader._extract_photo_sources(detail)

        expected = [
            "https://cdn.example.com/primary_0.jpg",
            "https://cdn.example.com/primary_1.jpg",
            "https://cdn.example.com/primary_2.jpg",
            "https://cdn.example.com/extra_0.jpg",
            "https://cdn.example.com/mirror_extra_0.jpg",
            "https://cdn.example.com/extra_1.jpg",
            "https://cdn.example.com/mirror_extra_1.jpg",
        ]
        self.assertEqual(photos, expected)

    def test_build_photo_album_without_photos_raises(self) -> None:
        with self.assertRaises(TikTokDownloadError):
            self.downloader._build_photo_album({"desc": "Empty"}, images=[])


class TikTokDownloaderErrorHandlingTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.downloader = TikTokDownloader(timeout=0.1)
        self.sample_url = "https://www.tiktok.com/@user/video/123"

    async def test_extract_info_converts_download_error(self) -> None:
        with patch.object(
            self.downloader,
            "_extract_sync",
            side_effect=DownloadError("timed out"),
        ):
            with self.assertRaises(TikTokDownloadError) as ctx:
                await self.downloader._extract_info(self.sample_url)

        self.assertIn("zaman aşımı", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
