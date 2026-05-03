import unittest
from pathlib import Path


class StreamlitStatePatternTests(unittest.TestCase):
    def test_episode_name_widget_does_not_reassign_same_session_key_after_creation(self):
        source = Path("webui/components/subtitle_settings.py").read_text(encoding="utf-8")
        widget_index = source.index('key="episode_name"')
        forbidden_assignment = "st.session_state['episode_name'] ="

        self.assertNotIn(forbidden_assignment, source[widget_index:])


if __name__ == "__main__":
    unittest.main()
