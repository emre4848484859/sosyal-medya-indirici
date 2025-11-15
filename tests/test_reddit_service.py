import unittest

from bot.services.reddit import RedditDownloadError, RedditDownloader


class RedditDownloaderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.downloader = RedditDownloader(base_url="https://www.reddit.com")

    def test_extract_post_id_from_standard_link(self) -> None:
        url = "https://www.reddit.com/r/pics/comments/abc123/my_title/"
        self.assertEqual(self.downloader._extract_post_id(url), "abc123")

    def test_extract_post_id_from_gallery_link(self) -> None:
        url = "https://www.reddit.com/gallery/def456"
        self.assertEqual(self.downloader._extract_post_id(url), "def456")

    def test_build_asset_from_gallery_collects_all_items(self) -> None:
        post = {
            "title": "Gallery",
            "author": "tester",
            "media_metadata": {
                "abc": {
                    "status": "valid",
                    "s": {"u": "https://i.redd.it/photo1.jpg"},
                },
                "def": {
                    "status": "valid",
                    "p": [
                        {"u": "https://preview.redd.it/photo2.png?width=640&crop=smart&auto=webp"},
                        {"u": "https://i.redd.it/photo2.png"},
                    ],
                },
            },
            "gallery_data": {
                "items": [
                    {"media_id": "abc"},
                    {"media_id": "def"},
                ]
            },
        }

        asset = self.downloader._build_asset(post)

        self.assertEqual(
            asset.photos,
            ["https://i.redd.it/photo1.jpg", "https://preview.redd.it/photo2.png?width=640&crop=smart&auto=webp"],
        )
        self.assertIsNone(asset.video_url)

    def test_build_asset_prefers_video_when_available(self) -> None:
        post = {
            "title": "Video",
            "author": "tester",
            "secure_media": {
                "reddit_video": {
                    "fallback_url": "https://v.redd.it/video123/DASH_1080.mp4?source=fallback",
                }
            },
        }

        asset = self.downloader._build_asset(post)

        self.assertEqual(asset.video_url, "https://v.redd.it/video123/DASH_1080.mp4?source=fallback")
        self.assertEqual(asset.photos, [])

    def test_build_asset_without_media_raises(self) -> None:
        with self.assertRaises(RedditDownloadError):
            self.downloader._build_asset({"title": "Empty"})


if __name__ == "__main__":
    unittest.main()
