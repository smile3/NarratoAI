import unittest

from app.services.prompts.documentary.narration_generation import NarrationGenerationPrompt
from app.services.prompts.short_drama_editing.plot_extraction import PlotExtractionPrompt
from app.services.prompts.short_drama_editing.subtitle_analysis import SubtitleAnalysisPrompt
from app.services.prompts.short_drama_narration.script_generation import ScriptGenerationPrompt


class PromptDurationRuleTests(unittest.TestCase):
    def test_documentary_narration_prompt_mentions_visual_duration_fit(self):
        template = NarrationGenerationPrompt().get_template()

        self.assertIn("画面时长", template)
        self.assertIn("每秒", template)

    def test_short_drama_editing_prompts_target_under_five_minutes(self):
        analysis_template = SubtitleAnalysisPrompt().get_template()
        extraction_template = PlotExtractionPrompt().get_template()

        for template in [analysis_template, extraction_template]:
            with self.subTest(template=template[:20]):
                self.assertIn("3 分钟", template)
                self.assertIn("5 分钟", template)
                self.assertIn("悬念", template)

        self.assertIn("单个片段", extraction_template)
        self.assertIn("短一点", extraction_template)

    def test_short_drama_narration_prompt_targets_under_five_minutes_and_duration_fit(self):
        template = ScriptGenerationPrompt().get_template()

        self.assertIn("3 分钟", template)
        self.assertIn("5 分钟", template)
        self.assertIn("画面时长", template)
        self.assertIn("每秒", template)
        self.assertIn("留下悬念", template)


if __name__ == "__main__":
    unittest.main()
