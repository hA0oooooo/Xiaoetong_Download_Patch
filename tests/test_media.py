import unittest

from xiaoetong_assistant.media import https_url, rewrite_playlist

PLAYLIST = '''#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:2
#EXT-X-KEY:METHOD=AES-128,URI="https://example.invalid/key?mid=material"
#EXTINF:2.0,
one.ts
#EXTINF:1.5,
/two.ts
#EXT-X-ENDLIST
'''


class MediaTests(unittest.TestCase):
    def test_native_transport_rewrites_segments_and_keeps_key_out_of_manifest(self):
        text, mapping, duration, encrypted = rewrite_playlist(PLAYLIST, "https://example.invalid/master.m3u8", {"host": "https://cdn.example", "path": "private", "param": "signed=secret"})
        self.assertTrue(encrypted)
        self.assertEqual(duration, 3.5)
        self.assertEqual(mapping["/segment/0"], "https://cdn.example/private/one.ts?signed=secret")
        self.assertEqual(mapping["/segment/1"], "https://cdn.example/private/two.ts?signed=secret")
        self.assertIn('URI="/key"', text)
        self.assertNotIn("signed=secret", text)
        self.assertNotIn("example.invalid", text)

    def test_live_or_incomplete_playlist_rejected(self):
        with self.assertRaises(ValueError):
            rewrite_playlist(PLAYLIST.replace("#EXT-X-ENDLIST", ""), "https://example.invalid/movie.m3u8")

    def test_unsupported_encryption_not_silently_saved(self):
        with self.assertRaises(ValueError):
            rewrite_playlist(PLAYLIST.replace("AES-128", "SAMPLE-AES"), "https://example.invalid/movie.m3u8")

    def test_network_destination_cannot_be_local(self):
        for url in ("http://example.com/video", "https://127.0.0.1/video", "https://10.0.0.1/video", "https://localhost/video", "https://user:secret@example.com/video"):
            with self.assertRaises(ValueError):
                https_url(url)
