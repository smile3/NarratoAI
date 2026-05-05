import json
import unittest

from app.utils import check_script
from app.utils.script_document import build_script_document, loads_script_document


SAMPLE_ITEM = {
    "_id": 1,
    "timestamp": "00:00:00,000-00:00:03,000",
    "picture": "主角抬头看向门口",
    "narration": "门一开，所有人的脸色都变了。",
    "OST": 2,
}


class ScriptDocumentTests(unittest.TestCase):
    def test_script_document_keeps_title_and_items(self):
        payload = build_script_document([SAMPLE_ITEM], "生日宴真相曝光")
        document = loads_script_document(json.dumps(payload, ensure_ascii=False))

        self.assertEqual("生日宴真相曝光", document.script_title)
        self.assertEqual([SAMPLE_ITEM], document.items)

    def test_check_format_accepts_title_document(self):
        payload = build_script_document([SAMPLE_ITEM], "生日宴真相曝光")

        result = check_script.check_format(json.dumps(payload, ensure_ascii=False))

        self.assertTrue(result.get("success"), result)

    def test_legacy_array_script_still_loads(self):
        document = loads_script_document(json.dumps([SAMPLE_ITEM], ensure_ascii=False))

        self.assertEqual("", document.script_title)
        self.assertEqual([SAMPLE_ITEM], document.items)


if __name__ == "__main__":
    unittest.main()
