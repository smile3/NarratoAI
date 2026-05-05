import unittest

from app.services.frame_subtitle_script import (
    build_frame_subtitle_prompt,
    generate_frame_subtitle_script,
)


class FrameSubtitleScriptTests(unittest.TestCase):
    def test_prompt_combines_visual_analysis_and_subtitles(self):
        prompt = build_frame_subtitle_prompt(
            frame_analysis_markdown="## 片段 1\n- 时间范围：00:00:00,000-00:00:05,000\n- 片段描述：女主转身",
            subtitle_content="1\n00:00:01,000 --> 00:00:02,000\n你到底是谁",
            video_theme="短剧测试",
        )

        self.assertIn("画面分析", prompt)
        self.assertIn("字幕内容", prompt)
        self.assertIn("短剧测试", prompt)
        self.assertIn("画面和字幕", prompt)
        self.assertIn("不要只依赖字幕", prompt)

    def test_generate_frame_subtitle_script_normalizes_items(self):
        def fake_generator(prompt, system_prompt, temperature, response_format):
            self.assertIn("画面分析", prompt)
            self.assertEqual("json", response_format)
            return '{"items":[{"timestamp":"00:00:01,000-00:00:05,000","picture":"女主发现秘密","narration":"她终于发现了真相。","OST":0}]}'

        items = generate_frame_subtitle_script(
            frame_analysis_markdown="frames",
            subtitle_content="subs",
            text_generator=fake_generator,
        )

        self.assertEqual(1, len(items))
        self.assertEqual(1, items[0]["_id"])
        self.assertEqual(2, items[0]["OST"])
        self.assertEqual("女主发现秘密", items[0]["picture"])


if __name__ == "__main__":
    unittest.main()
