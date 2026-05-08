import unittest
from pathlib import Path


class ScriptSettingsSubtitleModeTests(unittest.TestCase):
    def test_script_settings_declares_frame_subtitle_mode_and_local_whisper_fallback(self):
        source = Path("webui/components/script_settings.py").read_text(encoding="utf-8")

        self.assertIn("MODE_FRAME_SUBTITLE", source)
        self.assertIn('tr("Frame Subtitle Generate")', source)
        self.assertIn("ensure_subtitle_for_current_video", source)
        self.assertIn("local_whisper_subtitle", source)

    def test_script_settings_declares_video_understanding_mode_without_subtitle_requirement(self):
        source = Path("webui/components/script_settings.py").read_text(encoding="utf-8")

        self.assertIn("MODE_VIDEO_UNDERSTANDING", source)
        self.assertIn('tr("Video Understanding Generate")', source)
        self.assertIn("generate_video_understanding_script_tool", source)
        self.assertIn("MODE_VIDEO_UNDERSTANDING]", source)
        self.assertNotIn("SUBTITLE_REQUIRED_MODES = [MODE_SHORT, MODE_SUMMARY, MODE_FRAME_SUBTITLE, MODE_VIDEO_UNDERSTANDING]", source)

    def test_script_settings_no_longer_renders_aliyun_fun_asr_panel(self):
        source = Path("webui/components/script_settings.py").read_text(encoding="utf-8")

        self.assertNotIn("阿里百炼 Fun-ASR 字幕转录", source)
        self.assertNotIn("fun_asr_subtitle", source)


if __name__ == "__main__":
    unittest.main()
