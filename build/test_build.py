# python3 build/test_build.py
import datetime as dt
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import tempfile
from build import load_goals, parse_goals_note, parse_scores, load_picks, load_stocks, load_youtube, parse_due, parse_hub, parse_routines

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
            self.assertIsNone(s["vix"])
            p.write_text('{"alerts": [], "vix": {"last": 21.5, "date": "2026-10-31"}}')
            self.assertEqual(load_stocks(p)["vix"]["last"], 21.5)
            p.write_text('{"alerts": [], "vix": {"last": "x"}}')
            self.assertIsNone(load_stocks(p)["vix"])

    def test_picks(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "picks.json"
            self.assertIsNone(load_picks(p))
            p.write_text('{"asof": "2026-10-28", "picks": [{"ticker": "AMAT", "level": "buy"}, {"ticker": "X", "level": "maybe"}],'
                         ' "sources": [{"title": "a", "url": "https://a"}, {"title": "b", "url": "javascript:x"}]}')
            r = load_picks(p)
            self.assertEqual([x["ticker"] for x in r["picks"]], ["AMAT"])
            self.assertEqual([x["title"] for x in r["sources"]], ["a"])


GOALS_MD = """# 2026-11-15 (日)
## 🗓 今週の振り返り（11/09〜11/15）
- [ ] 月 予定: ウォーキング
## 🎯 来週の抱負（11/16〜11/22）
- [ ] 🇬🇧 **OET を4日以上**
  - 理由：今週は1/7日だけ
  - 最初の一歩（月）：朝に①を通す
- [x] 🏋️ 筋トレ3回
## ✍️ 自分で書く
- [ ] 混ざらないこと
"""


class Goals(unittest.TestCase):
    def test_parse(self):
        g = parse_goals_note(GOALS_MD, "2026-11-15")
        self.assertEqual((g["start"], g["end"], g["label"]), ("2026-11-16", "2026-11-22", "11/16〜11/22"))
        self.assertEqual([i["text"] for i in g["items"]], ["🇬🇧 **OET を4日以上**", "🏋️ 筋トレ3回"])
        self.assertEqual(g["items"][0]["why"], "今週は1/7日だけ")
        self.assertEqual(g["items"][0]["first"], "朝に①を通す")
        self.assertEqual([i["done"] for i in g["items"]], [False, True])
        self.assertTrue(g["items"][0]["id"].startswith("goal:"))

    def test_none_without_section(self):
        self.assertIsNone(parse_goals_note("# 2026-11-15\n## 📝 ジャーナル\n- [ ] x\n", "2026-11-15"))

    def test_year_end(self):
        g = parse_goals_note("## 🎯 来週の抱負（12/28〜1/3）\n- [ ] a\n", "2026-12-27")
        self.assertEqual((g["start"], g["end"]), ("2026-12-28", "2027-01-03"))

    def test_load_latest_until_end(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "2026-11-08.md").write_text("## 🎯 来週の抱負（11/9〜11/15）\n- [ ] 古い\n")
            Path(d, "2026-11-15.md").write_text(GOALS_MD)
            Path(d, "2026-11-17.md").write_text("# 平日のノート（抱負なし）\n")
            self.assertEqual(load_goals(Path(d), dt.date(2026, 11, 15))["note"], "2026-11-15")
            self.assertEqual(load_goals(Path(d), dt.date(2026, 11, 22))["note"], "2026-11-15")
            self.assertIsNone(load_goals(Path(d), dt.date(2026, 11, 23)))

class Scores(unittest.TestCase):
    MD = """# 週の点数
| 週 | 点数 | 運動 | 英語 | 筋トレ | 有酸素 | KB | OET日数 | 抱負 |
|---|---|---|---|---|---|---|---|---|
| 11/2〜11/8 <!--2026-11-08--> | **10** | 10 | 0 | 1/4 | 0/4 | 2/6 | 0/6 | — |
| [[2026-11-15\\|11/9〜11/15]] | **48** | 40 | 8 | 3/4 | 4/4 | 4/6 | 1/6 | 2.5/4 |
"""

    def test_parse(self):
        r = parse_scores(self.MD)
        self.assertEqual([x["label"] for x in r], ["11/2〜11/8", "11/9〜11/15"])
        self.assertEqual([x["week"] for x in r], ["2026-11-08", "2026-11-15"])
        self.assertEqual((r[1]["total"], r[1]["move"], r[1]["eng"], r[1]["goals"]), (48, 40, 8, "2.5/4"))
        self.assertEqual(r[0]["goals"], "")

    def test_keep_latest(self):
        rows = "".join(f"| [[2026-01-{d:02d}\\\\|w{d}]] | **{d}** | 1 | 1 | a | b | c | d | — |\n" for d in range(1, 13))
        self.assertEqual([x["total"] for x in parse_scores(rows, keep=3)], [10, 11, 12])


if __name__ == "__main__":
    unittest.main()
