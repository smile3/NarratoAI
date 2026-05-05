import os
import tempfile
import unittest

from app.services import local_whisper_subtitle as lws


class LocalWhisperSubtitleTests(unittest.TestCase):
    def test_segments_to_srt_formats_segment_objects(self):
        class Segment:
            start = 1.2
            end = 3.45
            text = "  你好，世界  "

        srt = lws.segments_to_srt([Segment()])

        self.assertIn("1\n00:00:01,200 --> 00:00:03,450\n你好，世界", srt)

    def test_create_with_local_whisper_uses_injected_transcriber_and_writes_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            media = os.path.join(tmp_dir, "demo.mp4")
            output = os.path.join(tmp_dir, "demo.srt")
            with open(media, "wb") as f:
                f.write(b"demo")

            def fake_transcriber(path):
                self.assertEqual(media, path)
                return [{"start": 0, "end": 2.5, "text": "本地字幕"}]

            result = lws.create_with_local_whisper(media, output, transcriber=fake_transcriber)

            self.assertEqual(output, result)
            self.assertTrue(os.path.exists(output))
            self.assertIn("本地字幕", open(output, encoding="utf-8").read())

    def test_default_subtitle_path_uses_subtitle_dir_and_media_name(self):
        path = lws.default_subtitle_path_for_media("/tmp/My Video.mp4")

        self.assertTrue(path.endswith("My Video_whisper.srt"))


if __name__ == "__main__":
    unittest.main()
