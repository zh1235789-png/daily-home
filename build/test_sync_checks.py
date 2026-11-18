# python3 build/test_sync_checks.py
import unittest

from sync_checks import merge, published


class T(unittest.TestCase):
    def test_newer_issue_wins(self):
        cur = {"eng:2026-11-18:langaku": [1, 70, "2026-11-18"]}
        out, ids = merge(cur, ["63 k:eng:2026-11-18:langaku=0", "71 k:train:2026-11-18:run=1"], "2026-11-18")
        self.assertEqual(out["eng:2026-11-18:langaku"], [1, 70, "2026-11-18"])
        self.assertEqual(out["train:2026-11-18:run"], [1, 71, "2026-11-18"])
        out, _ = merge(out, ["72 k:eng:2026-11-18:langaku=0"], "2026-11-18")
        self.assertEqual(out["eng:2026-11-18:langaku"][0], 0)

    def test_rejects_other_shapes(self):
        out, ids = merge({}, ["5 k:id:abc=1", "5 k:mail:https://x=1", "x k:0123456789=1", "5 k:goal:0123456789=1",
                              "5 k:0123456789=2", "5 k:train:2026-11-18:Run=1"], "2026-11-18")
        self.assertEqual(list(out), ["goal:0123456789"])

    def test_prunes_old(self):
        cur = {"0123456789": [1, 3, "2026-10-01"], "abcdefabcd": [1, 4, "2026-11-10"]}
        out, _ = merge(cur, [], "2026-11-18")
        self.assertEqual(list(out), ["abcdefabcd"])
        self.assertEqual(published(out), {"abcdefabcd": [1, 4]})


if __name__ == "__main__":
    unittest.main()
