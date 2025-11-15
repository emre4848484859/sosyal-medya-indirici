import unittest

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


if __name__ == "__main__":
    unittest.main()
