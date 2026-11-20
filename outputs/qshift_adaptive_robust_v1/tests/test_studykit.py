"""studykit reproduces the frozen AD1 freeze format exactly, and every freeze in the package is intact."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
import freeze_ad1  # noqa: E402
import studykit as K  # noqa: E402


class StudykitTests(unittest.TestCase):
    def test_reproduces_ad1_freeze(self):
        frozen = json.loads((PKG / "AD1_FREEZE.json").read_text(encoding="utf-8"))
        doc = K.freeze_doc(frozen["schema"], frozen["study"], freeze_ad1.FILES, "Run AD1")
        self.assertEqual(doc, frozen)

    def test_all_freezes_intact(self):
        for fz in sorted(PKG.glob("*_FREEZE.json")):
            self.assertEqual(K.check_freeze(fz), [], fz.name)

    def test_write_once(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "r.json"
            K.write_once_json(p, {"b": 1, "a": 2})
            self.assertEqual(p.read_bytes(), b'{\n  "a": 2,\n  "b": 1\n}\n')
            with self.assertRaises(SystemExit):
                K.write_once_json(p, {})


if __name__ == "__main__":
    unittest.main()
