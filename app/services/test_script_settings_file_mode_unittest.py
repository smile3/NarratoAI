import unittest
from pathlib import Path


class ScriptSettingsFileModeTests(unittest.TestCase):
    def test_file_mode_polish_button_uses_short_drama_style_and_generates_title(self):
        source = Path("webui/components/script_settings.py").read_text(encoding="utf-8")

        self.assertIn('tr("AI Polish Short Drama Script")', source)
        self.assertIn('style="short_drama"', source)
        self.assertIn("script_enhancement.generate_script_title", source)
        self.assertIn("get_script_content_for_polishing", source)

    def test_script_settings_persists_title_in_script_document(self):
        source = Path("webui/components/script_settings.py").read_text(encoding="utf-8")

        self.assertIn("script_document.dumps_script_document", source)
        self.assertIn("script_document.build_script_document", source)
        self.assertIn("script_document.loads_script_document", source)


if __name__ == "__main__":
    unittest.main()
