import unittest

from app.services.video_overlay import resolve_fixed_text_overlay_position


class GenerateVideoOverlayPositionTests(unittest.TestCase):
    def test_portrait_defaults_place_title_top_and_episode_above_subtitles(self):
        video_size = (1080, 1920)

        title_pos = resolve_fixed_text_overlay_position(
            kind="title",
            position="top",
            video_size=video_size,
            clip_size=(900, 80),
            subtitle_position="bottom",
        )
        episode_pos = resolve_fixed_text_overlay_position(
            kind="episode",
            position="bottom",
            video_size=video_size,
            clip_size=(260, 56),
            subtitle_position="bottom",
        )
        subtitle_y = 1920 * 0.95 - 96

        self.assertEqual("center", title_pos[0])
        self.assertLess(title_pos[1], 1920 * 0.12)
        self.assertLess(episode_pos[1] + 56, subtitle_y)
        self.assertGreater(episode_pos[1], 1920 * 0.70)


if __name__ == "__main__":
    unittest.main()
