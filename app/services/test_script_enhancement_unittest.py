import unittest

from app.services.script_enhancement import (
    apply_script_optimization,
    build_script_optimization_prompt,
    clean_generated_title,
    merge_optimized_narrations,
    parse_script_optimization_payload,
    parse_script_items_payload,
)


class ScriptEnhancementTests(unittest.TestCase):
    def test_merge_optimized_narrations_preserves_timing_and_metadata(self):
        original_items = [
            {
                "_id": 1,
                "timestamp": "00:00:00,000-00:00:03,000",
                "picture": "男人推门进入仓库",
                "narration": "他进来了。",
                "OST": 2,
            },
            {
                "_id": 2,
                "timestamp": "00:00:03,000-00:00:06,000",
                "picture": "灯光突然熄灭",
                "narration": "灯灭了。",
                "OST": 1,
            },
        ]
        optimized_items = [
            {
                "_id": 1,
                "timestamp": "99:99:99,999-99:99:99,999",
                "picture": "被模型错误改写的画面",
                "narration": "他刚踏进仓库，真正的危险才刚刚开始。",
                "OST": 0,
            },
            {
                "_id": 2,
                "narration": "下一秒，整间屋子突然陷入黑暗。",
            },
        ]

        merged = merge_optimized_narrations(original_items, optimized_items)

        self.assertEqual("00:00:00,000-00:00:03,000", merged[0]["timestamp"])
        self.assertEqual("男人推门进入仓库", merged[0]["picture"])
        self.assertEqual(2, merged[0]["OST"])
        self.assertEqual("他刚踏进仓库，真正的危险才刚刚开始。", merged[0]["narration"])
        self.assertEqual("00:00:03,000-00:00:06,000", merged[1]["timestamp"])
        self.assertEqual(1, merged[1]["OST"])
        self.assertEqual("下一秒，整间屋子突然陷入黑暗。", merged[1]["narration"])

    def test_merge_optimized_narrations_keeps_original_when_narration_missing(self):
        original_items = [
            {"_id": 1, "timestamp": "00:00:00,000-00:00:03,000", "narration": "原文", "OST": 2}
        ]

        merged = merge_optimized_narrations(original_items, [{"_id": 1, "narration": "   "}])

        self.assertEqual("原文", merged[0]["narration"])

    def test_parse_script_items_payload_accepts_items_object_and_code_fence(self):
        payload = '```json\n{"items":[{"_id":1,"narration":"优化后"}]}\n```'

        items = parse_script_items_payload(payload)

        self.assertEqual([{"_id": 1, "narration": "优化后"}], items)

    def test_parse_script_optimization_payload_extracts_hook_and_items(self):
        payload = '```json\n{"hook":{"source_id":2,"narration":"先别眨眼，最关键的一幕来了。"},"items":[{"_id":1,"narration":"优化后"}]}\n```'

        hook, items = parse_script_optimization_payload(payload)

        self.assertEqual({"source_id": 2, "narration": "先别眨眼，最关键的一幕来了。"}, hook)
        self.assertEqual([{"_id": 1, "narration": "优化后"}], items)

    def test_apply_script_optimization_prepends_core_shot_hook_and_renumbers(self):
        original_items = [
            {
                "_id": 1,
                "timestamp": "00:00:00,000-00:00:03,000",
                "picture": "男人走进走廊",
                "narration": "他走进走廊。",
                "OST": 2,
            },
            {
                "_id": 2,
                "timestamp": "00:00:08,000-00:00:12,000",
                "picture": "女人突然发现桌上的秘密文件",
                "narration": "她发现了文件。",
                "OST": 1,
            },
        ]
        optimized_items = [
            {"_id": 1, "narration": "他刚踏进走廊，危险已经靠近。"},
            {"_id": 2, "narration": "真正的秘密，下一秒就藏不住了。"},
        ]
        hook = {"source_id": 2, "narration": "先别眨眼，所有反转都藏在这份文件里。"}

        result = apply_script_optimization(original_items, optimized_items, hook)

        self.assertEqual([1, 2, 3], [item["_id"] for item in result])
        self.assertEqual("00:00:08,000-00:00:12,000", result[0]["timestamp"])
        self.assertEqual("女人突然发现桌上的秘密文件", result[0]["picture"])
        self.assertEqual("先别眨眼，所有反转都藏在这份文件里。", result[0]["narration"])
        self.assertEqual(2, result[0]["OST"])
        self.assertEqual("00:00:00,000-00:00:03,000", result[1]["timestamp"])
        self.assertEqual("他刚踏进走廊，危险已经靠近。", result[1]["narration"])
        self.assertEqual("00:00:08,000-00:00:12,000", result[2]["timestamp"])
        self.assertEqual("真正的秘密，下一秒就藏不住了。", result[2]["narration"])

    def test_build_script_optimization_prompt_requests_core_shot_hook(self):
        prompt = build_script_optimization_prompt(
            [{"_id": 1, "timestamp": "00:00:00,000-00:00:03,000", "picture": "核心镜头", "narration": "原文", "OST": 2}],
            style="short_drama",
        )

        self.assertIn('"hook"', prompt)
        self.assertIn("最核心", prompt)
        self.assertIn("复制到视频最开始", prompt)

    def test_clean_generated_title_removes_wrappers_and_limits_length(self):
        raw_title = '```\n《所有人都以为她输了，下一秒全场安静》\n```\n第二行说明不要保留'

        title = clean_generated_title(raw_title, max_length=14)

        self.assertEqual("所有人都以为她输了，下一秒全", title)


if __name__ == "__main__":
    unittest.main()
