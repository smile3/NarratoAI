import unittest

from app.services.frame_subtitle_script import (
    build_frame_subtitle_prompt,
    generate_frame_subtitle_script,
    normalize_frame_subtitle_items,
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
        self.assertIn("主动混合 OST=0 和 OST=1", prompt)
        self.assertIn("不要使用 OST=2", prompt)

    def test_generate_frame_subtitle_script_preserves_mixed_ost_items(self):
        def fake_generator(prompt, system_prompt, temperature, response_format):
            self.assertIn("画面分析", prompt)
            self.assertIn("主动混合 OST=0 和 OST=1", prompt)
            self.assertIn("OST=0 和 OST=1", system_prompt)
            self.assertEqual("json", response_format)
            return """
            {
              "items": [
                {"timestamp":"00:00:01,000-00:00:05,000","picture":"女主发现秘密","narration":"她终于发现了真相。","OST":0},
                {"timestamp":"00:00:05,000-00:00:08,000","picture":"男主质问女主","narration":"播放原片2","OST":1}
              ]
            }
            """

        items = generate_frame_subtitle_script(
            frame_analysis_markdown="frames",
            subtitle_content="subs",
            text_generator=fake_generator,
        )

        self.assertEqual(2, len(items))
        self.assertEqual(1, items[0]["_id"])
        self.assertEqual(0, items[0]["OST"])
        self.assertEqual("女主发现秘密", items[0]["picture"])
        self.assertEqual(2, items[1]["_id"])
        self.assertEqual(1, items[1]["OST"])

    def test_normalize_frame_subtitle_items_converts_legacy_ost2_to_ost0_or_ost1(self):
        items = normalize_frame_subtitle_items([
            {
                "timestamp": "00:00:01,000-00:00:05,000",
                "picture": "女主转身离开",
                "narration": "没想到，她真正的反击才刚刚开始。",
                "OST": 2,
            },
            {
                "timestamp": "00:00:05,000-00:00:08,000",
                "picture": "男主当场质问，双方对峙",
                "narration": "播放原片2",
                "OST": 2,
            },
        ])

        self.assertEqual([0, 1], [item["OST"] for item in items])

    def test_normalize_frame_subtitle_items_adds_original_audio_when_model_returns_only_narration(self):
        items = normalize_frame_subtitle_items([
            {
                "timestamp": "00:00:01,000-00:00:05,000",
                "picture": "女主发现秘密",
                "narration": "她终于发现了真相。",
                "OST": 0,
            },
            {
                "timestamp": "00:00:05,000-00:00:08,000",
                "picture": "男主质问女主，双方对峙",
                "narration": "这个质问让局面彻底失控。",
                "OST": 0,
            },
        ])

        self.assertEqual({0, 1}, {item["OST"] for item in items})
        self.assertEqual("播放原片2", items[1]["narration"])

    def test_normalize_frame_subtitle_items_adds_narration_when_model_returns_only_original_audio(self):
        items = normalize_frame_subtitle_items([
            {
                "timestamp": "00:00:01,000-00:00:05,000",
                "picture": "女主沉默转身",
                "narration": "播放原片1",
                "OST": 1,
            },
            {
                "timestamp": "00:00:05,000-00:00:08,000",
                "picture": "男主当场质问",
                "narration": "播放原片2",
                "OST": 1,
            },
        ])

        self.assertEqual({0, 1}, {item["OST"] for item in items})
        self.assertEqual(0, items[0]["OST"])
        self.assertIn("女主沉默转身", items[0]["narration"])


if __name__ == "__main__":
    unittest.main()
