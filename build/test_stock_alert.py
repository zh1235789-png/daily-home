# python3 build/test_stock_alert.py
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from stock_alert import evaluate, message, universe

LISTS = {2022: "AMZN GOOG INTC KRUS", 2025: "GOOG OKLO CGC MSTR", 2026: "COIN"}
UNI = universe(LISTS, dame={"MSTR"}, avoid={"CGC": "避ける"})


def q(dd):
    return {"last": 100 + dd, "hi": 100, "hi_date": "2026-05-01", "dd": dd, "date": "2026-10-28"}


class Universe(unittest.TestCase):
    def test_groups(self):
        self.assertEqual(UNI["VOO"][0], "index")
        self.assertEqual(UNI["META"][0], "strong")        # GAFAM はリストに無くても強い会社
        self.assertEqual(UNI["KRUS"][0], "strong")        # 殿堂入り（2022年版）
        self.assertEqual(UNI["GOOGL"], ("strong", [2022, 2025]))  # GOOG は GOOGL にまとめる
        self.assertNotIn("GOOG", UNI)
        self.assertEqual(UNI["OKLO"], ("other", [2025]))
        self.assertNotIn("MSTR", UNI)                     # ダメ株は対象外
        self.assertNotIn("CGC", UNI)                      # 避ける銘柄も対象外
        self.assertNotIn("META", universe(LISTS, dame={"META"}, avoid={}))  # GAFAMでもダメ株なら外す


class Evaluate(unittest.TestCase):
    def test_thresholds(self):
        quotes = {"VOO": q(-10.0), "QQQ": q(-9.9), "GOOGL": q(-20.4), "KRUS": q(-19), "OKLO": q(-29), "COIN": q(-31)}
        alerts, notify, state = evaluate(quotes, UNI, {}, "2026-10-28")
        self.assertEqual([a["ticker"] for a in alerts], ["VOO", "GOOGL", "COIN"])  # 指数→強い→その他
        self.assertEqual(sorted(notify), ["COIN", "GOOGL", "VOO"])
        self.assertEqual(state["GOOGL"], {"since": "2026-10-28", "notified": 20.4})

    def test_no_repeat_until_deeper_or_reset(self):
        st = {"GOOGL": {"since": "2026-10-20", "notified": 21.0}}
        _, notify, st2 = evaluate({"GOOGL": q(-25)}, UNI, st, "2026-10-28")
        self.assertEqual(notify, [])                      # 4ポイント深いだけでは再通知しない
        self.assertEqual(st2["GOOGL"]["since"], "2026-10-20")
        _, notify, st3 = evaluate({"GOOGL": q(-31.5)}, UNI, st2, "2026-10-29")
        self.assertEqual(notify, ["GOOGL"])               # さらに10ポイント下げたら再通知
        self.assertEqual(st3["GOOGL"]["notified"], 31.5)

    def test_rearm(self):
        st = {"GOOGL": {"since": "2026-10-20", "notified": 21.0}}
        alerts, _, st2 = evaluate({"GOOGL": q(-18)}, UNI, st, "2026-10-28")
        self.assertEqual(len(alerts), 1)                  # 基準−3ポイントまでは表示を続ける
        self.assertFalse(alerts[0]["below"])
        alerts, _, st3 = evaluate({"GOOGL": q(-16.9)}, UNI, st2, "2026-10-29")
        self.assertEqual((alerts, st3), ([], {}))         # 戻したら解除
        _, notify, _ = evaluate({"GOOGL": q(-20)}, UNI, st3, "2026-10-30")
        self.assertEqual(notify, ["GOOGL"])               # 解除後にまた割れたら通知

    def test_state_on_failure_and_exclusion(self):
        st = {"GOOGL": {"since": "2026-10-20", "notified": 21.0}, "MSTR": {"since": "2026-10-01", "notified": 40.0}}
        _, notify, st2 = evaluate({}, UNI, st, "2026-10-28", failed=["GOOGL"])
        self.assertEqual(notify, [])
        self.assertEqual(st2, {"GOOGL": st["GOOGL"]})     # 取得失敗は保持、対象外（ダメ株）は捨てる

    def test_message(self):
        quotes = {t: q(-35) for t in ["VOO", "GOOGL", "KRUS", "OKLO", "COIN"]}
        alerts, notify, _ = evaluate(quotes, UNI, {}, "2026-10-28")
        title, body = message(alerts, notify)
        self.assertIn("ほか1件", title)
        self.assertIn("S&P500（VOO） 高値から-35.0%（指数連動・基準10%）", body)


if __name__ == "__main__":
    unittest.main()
