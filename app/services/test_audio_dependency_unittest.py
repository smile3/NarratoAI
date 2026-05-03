import sys
import unittest
from pathlib import Path


class AudioDependencyTests(unittest.TestCase):
    def test_python_313_has_audioop_compat_dependency_declared(self):
        requirements = Path("requirements.txt").read_text(encoding="utf-8")

        self.assertIn("audioop-lts", requirements)
        self.assertIn("python_version >= \"3.13\"", requirements)

    def test_audio_merger_imports_on_current_python(self):
        if sys.version_info < (3, 13):
            self.skipTest("audioop compatibility package is only needed on Python 3.13+")

        __import__("app.services.audio_merger")


if __name__ == "__main__":
    unittest.main()
