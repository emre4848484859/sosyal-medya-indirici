import unittest

from bot.services.twitter import TwitterDownloadError, TwitterDownloader


class TwitterDownloaderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.downloader = TwitterDownloader(base_url="https://api.example.com")

    def test_extract_tweet_id_from_regular_link(self) -> None:
        tweet_id = self.downloader._extract_tweet_id("https://x.com/test/status/17777777777?s=20")
        self.assertEqual(tweet_id, "17777777777")

    def test_extract_tweet_id_from_i_status_link(self) -> None:
        tweet_id = self.downloader._extract_tweet_id("https://twitter.com/i/status/18888888888")
        self.assertEqual(tweet_id, "18888888888")

    def test_parse_payload_prefers_photos(self) -> None:
        payload = {
            "tweet": {
                "text": "Sample",
                "media": [
                    {"type": "photo", "url": "https://pbs.twimg.com/media/photo1.jpg"},
                    {"type": "photo", "media_url_https": "https://pbs.twimg.com/media/photo2.png"},
                ],
            }
        }

        asset = self.downloader._parse_payload(payload)

        self.assertEqual(asset.photos, ["https://pbs.twimg.com/media/photo1.jpg", "https://pbs.twimg.com/media/photo2.png"])
        self.assertIsNone(asset.video_url)

    def test_parse_payload_selects_highest_bitrate_video(self) -> None:
        payload = {
            "tweet": {
                "videos": [
                    {
                        "variants": [
                            {"url": "https://video.twimg.com/video_low.mp4", "bitrate": 256_000},
                            {"url": "https://video.twimg.com/video_high.mp4", "bitrate": 1_024_000},
                        ]
                    }
                ]
            }
        }

        asset = self.downloader._parse_payload(payload)

        self.assertEqual(asset.video_url, "https://video.twimg.com/video_high.mp4")

    def test_parse_payload_without_media_raises(self) -> None:
        with self.assertRaises(TwitterDownloadError):
            self.downloader._parse_payload({"tweet": {"text": "no media"}})

    def test_parse_payload_handles_media_extended_video(self) -> None:
        payload = {
            "text": "Video tweet",
            "mediaURLs": ["https://video.twimg.com/sample/vid_default.mp4?tag=12"],
            "media_extended": [
                {
                    "type": "video",
                    "url": "https://video.twimg.com/sample/vid_360.mp4?tag=12",
                    "variants": [
                        {"url": "https://video.twimg.com/sample/vid_1080.mp4?tag=12", "bitrate": 2_000_000},
                        {"url": "https://video.twimg.com/sample/vid_480.mp4?tag=12", "bitrate": 512_000},
                    ],
                }
            ],
        }

        asset = self.downloader._parse_payload(payload)

        self.assertEqual(asset.video_url, "https://video.twimg.com/sample/vid_1080.mp4?tag=12")
        self.assertEqual(asset.photos, [])


if __name__ == "__main__":
    unittest.main()
