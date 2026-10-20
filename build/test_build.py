# python3 build/test_build.py
import datetime as dt
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from build import parse_due, parse_hub

T = dt.date(2026, 10, 20)


class Due(unittest.TestCase):
    def d(self, s):
        a, b = parse_due(s, T)
        return (a and a.isoformat(), b and b.isoformat())

    def test_forms(self):
        self.assertEqual(self.d("**10/15（木）**"), (None, "2026-10-15"))
        self.assertEqual(self.d("**〜12/15**"), (None, "2026-12-15"))
        self.assertEqual(self.d("**12/1〜12/24**"), ("2026-12-01", "2026-12-24"))
        self.assertEqual(self.d("2027/1/7"), (None, "2027-01-07"))
        self.assertEqual(self.d("**2027/9/27〜10/18**"), ("2027-09-27", "2027-10-18"))
        self.assertEqual(self.d("早めに"), (None, None))
        self.assertEqual(self.d("~~10/10（土）~~"), (None, None))

    def test_year_rollover(self):
        # 年が無く半年以上前になる日付は翌年
        self.assertEqual(self.d("1/7"), (None, "2027-01-07"))


class Hub(unittest.TestCase):
    def test_same_as_above_has_no_link_and_struck(self):
        md = """## 🔥 今週
- [ ] 記録する → [[NVIDIA]]
- [ ] **〜10/11 電話** → 同上
## 📅 期限あり
| 期限 | 分野 | やること | 詳細 |
|---|---|---|---|
| ~~10/10（土）~~ | 保険 | ~~解約~~ | [[契約台帳]] |
| 11/6（金） | 旅行 | 期限 | 同上 |
"""
        h = parse_hub(md, T)
        self.assertEqual(h["week"][1]["notes"], [])
        self.assertEqual(h["week"][1]["due"], "2026-10-11")
        self.assertEqual(h["week"][1]["text"], "**〜10/11 電話**")
        self.assertTrue(h["dated"][0]["done"])
        self.assertEqual(h["dated"][1]["notes"], [])


if __name__ == "__main__":
    unittest.main()
