import unittest
from pathlib import Path


class ScriptSettingsFileModeTests(unittest.TestCase):
    def test_file_mode_polish_button_uses_short_drama_style_and_generates_title(self):
        source = Path("webui/components/script_settings.py").read_text(encoding="utf-8")

        self.assertIn('tr("AI Polish Short Drama Script")', source)
        self.assertIn('style="short_drama"', source)
        self.assertIn("script_enhancement.generate_script_title", source)
        self.assertIn("get_script_content_for_polishing", source)


if __name__ == "__main__":
    unittest.main()
