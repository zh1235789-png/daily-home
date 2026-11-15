# python3 build/test_eng_log.py
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from eng_log import merge


class EngLog(unittest.TestCase):
    def test_newest_first_wins(self):
        out, days = merge({}, ["e:20261116:11000", "e:20261116:10000", "e:20261117:00001"])
        self.assertEqual(out, {"2026-11-16": "11000", "2026-11-17": "00001"})
        self.assertEqual(days, ["2026-11-16", "2026-11-17"])

    def test_keeps_other_days_and_ignores_junk(self):
        out, days = merge({"2026-11-10": "11111"}, ["id:abcdef0123", "e:20261116:12", "x"])
        self.assertEqual(out, {"2026-11-10": "11111"})
        self.assertEqual(days, [])

    def test_unchecking_overwrites(self):
        out, _ = merge({"2026-11-16": "11111"}, ["e:20261116:00000"])
        self.assertEqual(out["2026-11-16"], "00000")


if __name__ == "__main__":
    unittest.main()
