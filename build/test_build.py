# python3 build/test_build.py
import datetime as dt
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import tempfile
from build import load_picks, load_stocks, load_youtube, parse_due, parse_hub, parse_routines

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


class Routines(unittest.TestCase):
    def test_today_and_yesterday_only_newest_first(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "2026-10-20_泌尿器科週次アップデート.md").write_text(
                '---\ndate: 2026-10-20\nroutine: 泌尿器科週次アップデート\ntime: "09:12"\n'
                'headline: "3件: THOR-2続報など"\noutput: "泌尿器科アップデート_2026-10-20"\n'
                'tags:\n  - claude-routine\n---\n\n# 泌尿器科週次アップデート — 2026-10-20 09:12\n\n本文\n')
            # 要約なしの古い形式：本文の短い行を拾う（見出し・表は飛ばす）
            (p / "2026-10-19_iCloud月次ファイル整理.md").write_text(
                '---\ndate: 2026-10-19\nroutine: iCloud月次ファイル整理\ntags:\n  - claude-routine\n---\n\n'
                '# iCloud月次ファイル整理 — 2026-10-19 10:05\n\n## 実行結果\n\n✅ 移動したファイル\n- なし\n| a | b |\n')
            (p / "2026-10-18_古い.md").write_text("---\ndate: 2026-10-18\n---\n")
            (p / "メモ.md").write_text("x")
            r = parse_routines(p, T)
        self.assertEqual([x["date"] for x in r], ["2026-10-20", "2026-10-19"])
        self.assertEqual(r[0]["headline"], "3件: THOR-2続報など")
        self.assertEqual(r[0]["output"], "泌尿器科アップデート_2026-10-20")
        self.assertEqual(r[0]["time"], "09:12")
        self.assertEqual(r[0]["lines"], [])
        self.assertEqual(r[1]["name"], "iCloud月次ファイル整理")
        self.assertEqual(r[1]["lines"], ["✅ 移動したファイル", "なし"])

    def test_missing_folder(self):
        self.assertEqual(parse_routines(Path("/nonexistent/x"), T), [])


class Youtube(unittest.TestCase):
    def test_newest_first_and_broken(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "youtube.json"
            self.assertIsNone(load_youtube(p))
            p.write_text("{壊れた")
            self.assertIsNone(load_youtube(p))
            p.write_text('{"updated":"x","items":[{"id":"a","title":"A","date":"2026-10-26"},'
                         '{"id":"b","title":"B","date":"2026-10-27"},{"title":"IDなし"}]}')
            y = load_youtube(p, keep=5)
            self.assertEqual([i["id"] for i in y["items"]], ["b", "a"])


class Stocks(unittest.TestCase):
    def test_load(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "stocks.json"
            self.assertIsNone(load_stocks(p))
            p.write_text("{壊れ")
            self.assertIsNone(load_stocks(p))
            p.write_text('{"asof": "2026-10-28", "alerts": [{"ticker": "GOOGL", "dd": -20.4}, {"ticker": "X"}, 3]}')
            s = load_stocks(p)
            self.assertEqual([a["ticker"] for a in s["alerts"]], ["GOOGL"])
            self.assertEqual(s["asof"], "2026-10-28")

    def test_picks(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "picks.json"
            self.assertIsNone(load_picks(p))
            p.write_text('{"asof": "2026-10-28", "picks": [{"ticker": "AMAT", "level": "buy"}, {"ticker": "X", "level": "maybe"}],'
                         ' "sources": [{"title": "a", "url": "https://a"}, {"title": "b", "url": "javascript:x"}]}')
            r = load_picks(p)
            self.assertEqual([x["ticker"] for x in r["picks"]], ["AMAT"])
            self.assertEqual([x["title"] for x in r["sources"]], ["a"])


if __name__ == "__main__":
    unittest.main()
