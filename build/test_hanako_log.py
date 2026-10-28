# python3 build/test_hanako_log.py
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from hanako_log import merge

MD = "---\nupdated: 2026-05-29\n---\n# 本文\n\n## 9\n<!-- hanako-log:start -->\n<!-- hanako-log:end -->\n末尾\n"
A = {"id": "a", "date": "2026-10-26", "headline": "A回", "url": "u", "invest_notes": ["**X**: 見方"]}
B = {"id": "b", "date": "2026-10-27", "headline": "B回", "url": "u", "invest_notes": ["**Y**: 見方"]}


class Merge(unittest.TestCase):
    def test_newest_first_and_idempotent(self):
        out, n = merge(MD, [A, B], "2026-10-28")
        self.assertEqual(n, 2)
        self.assertLess(out.index("yt:b"), out.index("yt:a"))
        self.assertIn("updated: 2026-10-28", out)
        self.assertTrue(out.endswith("<!-- hanako-log:end -->\n末尾\n"))
        again, n2 = merge(out, [A, B], "2026-10-29")
        self.assertEqual((again, n2), (out, 0))

    def test_keeps_old_entries_and_adds_new_on_top(self):
        out, _ = merge(MD, [A], "2026-10-28")
        out2, n = merge(out, [A, B], "2026-10-28")
        self.assertEqual(n, 1)
        self.assertLess(out2.index("yt:b"), out2.index("yt:a"))
        self.assertEqual(out2.count("yt:a"), 1)

    def test_no_marker_no_change(self):
        md = "# マーカー無し\n"
        self.assertEqual(merge(md, [A], "2026-10-28"), (md, 0))


if __name__ == "__main__":
    unittest.main()
