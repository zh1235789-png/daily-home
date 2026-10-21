# python3 build/test_apply_done.py
import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from apply_done import apply  # noqa: E402
from build import parse_hub  # noqa: E402

T = dt.date(2026, 10, 21)
MD = """---
updated: 2026-10-14
---
# タスクハブ

## 🔥 今週（〜10/11）

- [ ] 記録する → [[ノートA]]
- [ ] **〜10/11 電話**：店に伝える → 同上

## 📅 期限あり（直近順）

| 期限 | 分野 | やること | 詳細 |
|---|---|---|---|
| **10/15（木）** | お金 | 株を売る | [[ノートB]] |
| 11/6（金） | 旅行 | 期限 | 同上 |

## 📌 期限はないが大きいもの（金額・影響順）

- [ ] **親タスク**
    - [x] 済んだ子
    - [ ] 子タスク
- [ ] 別の大きいもの

## ✅ 完了（直近）

- [x] 前からある完了
"""


def ids_of(md):
    h = parse_hub(md, T)
    return h


class Apply(unittest.TestCase):
    def test_checklist_item_moves_to_done(self):
        h = ids_of(MD)
        text, found = apply(MD, [h["week"][0]["id"]], T)
        self.assertEqual(found, [h["week"][0]["id"]])
        self.assertNotIn("- [ ] 記録する", text)
        done = text.split("## ✅ 完了（直近）")[1]
        self.assertTrue(done.strip().startswith("- [x] 記録する → [[ノートA]]（10/21 完了）"))
        self.assertIn("- [x] 前からある完了", done)
        self.assertIn("updated: 2026-10-21", text)
        # 反映後のハブを読み直すと、もうその項目は出てこない
        self.assertEqual([w["text"] for w in parse_hub(text, T)["week"]], ["**〜10/11 電話**：店に伝える"])

    def test_table_row_removed(self):
        h = ids_of(MD)
        rid = h["dated"][0]["id"]
        text, found = apply(MD, [rid], T)
        self.assertEqual(found, [rid])
        self.assertNotIn("| 株を売る |", text)
        self.assertIn("- [x] 10/15（木）：株を売る（10/21 完了）", text)
        self.assertEqual(len(parse_hub(text, T)["dated"]), 1)

    def test_parent_moves_with_children_and_child_checks_in_place(self):
        h = ids_of(MD)
        child = h["big"][0]["children"][1]["id"]
        text, _ = apply(MD, [child], T)
        self.assertIn("    - [x] 子タスク", text)
        parent = h["big"][0]["id"]
        text, _ = apply(MD, [parent], T)
        big = text.split("## 📌")[1].split("## ✅")[0]
        self.assertNotIn("親タスク", big)
        self.assertIn("別の大きいもの", big)
        done = text.split("## ✅ 完了（直近）")[1]
        self.assertIn("- [x] **親タスク**（10/21 完了）\n    - [x] 済んだ子\n    - [ ] 子タスク", done)

    def test_unknown_id_changes_nothing(self):
        text, found = apply(MD, ["0123456789"], T)
        self.assertEqual(found, [])
        self.assertEqual(text, MD)


if __name__ == "__main__":
    unittest.main()
