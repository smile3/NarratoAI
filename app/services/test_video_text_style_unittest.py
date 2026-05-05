import unittest

from app.models.schema import VideoClipParams
from app.services.video_overlay import resolve_fixed_text_font_sizes
from pathlib import Path


class VideoTextStyleTests(unittest.TestCase):
    def test_default_subtitle_stroke_is_white(self):
        params = VideoClipParams()

        self.assertIn(params.text_fore_color.lower(), {"white", "#ffffff"})
        self.assertIn(params.stroke_color.lower(), {"white", "#ffffff"})

    def test_title_and_episode_are_larger_than_subtitles_and_close_in_size(self):
        title_size, episode_size = resolve_fixed_text_font_sizes(60)

        self.assertGreaterEqual(title_size, 78)
        self.assertGreaterEqual(episode_size, 72)
        self.assertLessEqual(abs(title_size - episode_size), 10)

    def test_task_passes_subtitle_stroke_options_to_final_merge(self):
        source = Path("app/services/task.py").read_text(encoding="utf-8")

        self.assertIn("'stroke_color': params.stroke_color", source)
        self.assertIn("'stroke_width': params.stroke_width", source)

    def test_final_merge_default_stroke_is_white(self):
        source = Path("app/services/generate_video.py").read_text(encoding="utf-8")

        self.assertIn("options.get('stroke_color', '#FFFFFF')", source)


if __name__ == "__main__":
    unittest.main()
