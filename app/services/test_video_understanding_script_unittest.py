import unittest

from app.services.video_understanding_script import (
    build_video_understanding_prompt,
    generate_video_understanding_script,
    normalize_video_understanding_items,
)


class VideoUnderstandingScriptTests(unittest.TestCase):
    def test_prompt_requires_direct_video_understanding_and_short_drama_mix(self):
        prompt = build_video_understanding_prompt(
            video_theme="短剧测试",
            custom_prompt="更强调女主逆袭",
        )

        self.assertIn("直接理解我发送的完整视频", prompt)
        self.assertIn("不会给你逐帧分析结果", prompt)
        self.assertIn("短剧推广", prompt)
        self.assertIn("主动混合 OST=0 和 OST=1", prompt)
        self.assertIn("不要使用 OST=2", prompt)
        self.assertIn("短剧测试", prompt)
        self.assertIn("更强调女主逆袭", prompt)

    def test_generate_video_understanding_script_uses_supplied_video_generator(self):
        def fake_generator(video_path, prompt, system_prompt, temperature, response_format):
            self.assertTrue(video_path.endswith(__file__.split("/")[-1]))
            self.assertIn("完整视频", prompt)
            self.assertIn("OST=0 和 OST=1", system_prompt)
            self.assertEqual(0.7, temperature)
            self.assertEqual("json", response_format)
            return """
            {
              "items": [
                {"timestamp":"0:00:01.0-0:00:04.50","picture":"女主被当众羞辱","narration":"所有人都以为她会忍下去。","OST":0},
                {"timestamp":"00:00:04,500-00:00:08,000","picture":"女主反问男主","narration":"播放原片2","OST":1}
              ]
            }
            """

        items = generate_video_understanding_script(
            video_path=__file__,
            video_generator=fake_generator,
        )

        self.assertEqual(2, len(items))
        self.assertEqual("00:00:01,000-00:00:04,500", items[0]["timestamp"])
        self.assertEqual([0, 1], [item["OST"] for item in items])

    def test_normalize_video_understanding_items_disallows_ost2_and_backfills_mix(self):
        items = normalize_video_understanding_items([
            {
                "timestamp": "00:00:01,000-00:00:04,000",
                "picture": "女主发现秘密",
                "narration": "这一眼，她终于看懂了真相。",
                "OST": 2,
            },
            {
                "timestamp": "00:00:04,000-00:00:08,000",
                "picture": "男主质问女主，双方对峙",
                "narration": "局面彻底失控。",
                "OST": 2,
            },
        ])

        self.assertEqual({0, 1}, {item["OST"] for item in items})
        self.assertNotIn(2, [item["OST"] for item in items])


if __name__ == "__main__":
    unittest.main()
