#!/usr/bin/env python3
"""株価の下落アラート（Claude 不要）。

52週高値（終値）からの下落率が基準を超えた銘柄を stocks.json に書き、
新しく基準を超えた銘柄があれば iPhone のリマインダー「株価アラート」で知らせる。

  指数連動（VOO・QQQ・VT）           … 10% 以上
  強い会社（GAFAM＋殿堂入りのうち大型で安定した会社） … 20% 以上
  その他の歴代Hanako30                 … 30% 以上
その後は固定の段階で知らせ直す（指数 15・20%…／強い会社 30・40%…／Hanako30 40・50%…）。
ダメ株トップ10と、花子が避けるべきとした銘柄は対象外。
銘柄リストは ~/bin/hanako30_drawdown.py の LISTS / DAME_SET / AVOID を使う（新しい年はそちらに足す）。

    python3 build/stock_alert.py              # 取得→stocks.json→新規分を通知
    python3 build/stock_alert.py --no-notify  # 通知しない（確認用）

refresh_listener.sh が毎朝6:30過ぎに1回呼ぶ。
"""
import datetime as dt
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

CONF = Path.home() / ".config/daily-home"
OUT = CONF / "stocks.json"
STATE = CONF / "stocks_state.json"
LISTS_PY = Path.home() / "bin/hanako30_drawdown.py"
REMINDER_LIST = "株価アラート"

INDEX = {"VOO": "S&P500（VOO）", "QQQ": "ナスダック100（QQQ）", "VT": "全世界株（VT）"}
GAFAM = ["GOOGL", "AAPL", "META", "AMZN", "MSFT"]
# 殿堂入り（Hanako30 2022年版）のうち、大型で業績の安定した会社だけ（2026-10-28 ユーザー指示）。
# 外したもの（その他のHanako30として30%基準で見る）: TSLA（値動きが大きい）・KEYS・CMG・INFY（中型）・
# KRUS（小型）・COIN（暗号資産連動）・INTC・PYPL・TGT（業績が不振）
STRONG = ["ORCL", "TXN", "INTU", "HD", "COST", "ADBE", "GS", "ASML", "TSM", "AMAT", "SONY",
          "BAC", "RTX", "NFLX", "LRCX", "QCOM", "XOM"]
GROUPS = {  # key: (表示名, 基準%)
    "index": ("指数連動", 10.0),
    "strong": ("強い会社", 20.0),
    "other": ("Hanako30", 30.0),
}
REARM = 3.0     # 基準より3ポイント戻したら解除（基準付近の上下で何度も通知しない）
# 基準から何%刻みで知らせ直すか（2026-10-28 ユーザー指示: 固定の段階）
#   指数 10→15→20%、強い会社 20→30→40%、Hanako30 30→40→50%
STEP = {"index": 5.0, "strong": 10.0, "other": 10.0}


def tier(drop, th, step):
    """下落率がどの段階にいるか（基準ちょうど=0、基準+step=1 …）"""
    return int((drop - th) / step + 1e-9) if drop >= th else -1
ALIASES = {"GOOG": "GOOGL"}  # 同じ会社の別クラスは1つにまとめる


def load_lists(path=LISTS_PY):
    spec = importlib.util.spec_from_file_location("hanako30_drawdown", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def universe(lists, dame, avoid):
    """{ticker: (group, years)}。ダメ株・避ける銘柄は除く。強いグループを優先する（純粋関数）"""
    years = {}
    for y, s in lists.items():
        for t in s.split():
            years.setdefault(ALIASES.get(t, t), []).append(y)
    out = {t: ("index", []) for t in INDEX}
    hof = set(STRONG)
    for t in GAFAM:
        if t not in dame and t not in avoid:
            out[t] = ("strong", sorted(years.get(t, [])))
    for t, ys in years.items():
        if t in out or t in dame or t in avoid:
            continue
        out[t] = ("strong" if t in hof else "other", sorted(ys))
    return out


def quote(t):
    import urllib.request
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?range=1y&interval=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=15))["chart"]["result"][0]
    pairs = [(ts, c) for ts, c in zip(d["timestamp"], d["indicators"]["quote"][0]["close"]) if c]
    last_ts, last = pairs[-1]
    hi_ts, hi = max(pairs, key=lambda p: p[1])
    day = lambda ts: dt.datetime.fromtimestamp(ts, dt.timezone.utc).date().isoformat()
    return {"last": round(last, 2), "hi": round(hi, 2), "hi_date": day(hi_ts),
            "dd": round((last / hi - 1) * 100, 1), "date": day(last_ts)}


def evaluate(quotes, uni, state, today, failed=()):
    """基準超えの一覧と、今回知らせるもの、次回用の状態を返す（純粋関数）。

    quotes: {ticker: quote()}、state: {ticker: {"since", "notified"}}
    failed: 一時的に取れなかった銘柄。通知状態をそのまま残す（次に取れたとき再通知しない）。
    監視対象（uni）から外れた銘柄の状態は捨てる。
    """
    alerts, notify, new_state = [], [], {}
    for t, q in quotes.items():
        group, years = uni[t]
        label, th = GROUPS[group]
        prev = state.get(t)
        drop = -q["dd"]
        active = drop >= th or (prev is not None and drop > th - REARM)
        if not active:
            continue
        st = dict(prev) if prev else {"since": today, "notified": None}
        # 前回通知した段階より深い段階に入ったら知らせる
        if st["notified"] is None or tier(drop, th, STEP[group]) > tier(st["notified"], th, STEP[group]):
            notify.append(t)
            st["notified"] = drop
        new_state[t] = st
        alerts.append({"ticker": t, "name": INDEX.get(t, t), "group": group, "label": label,
                       "threshold": th, "years": years, "since": st["since"],
                       "new": t in notify, "below": drop >= th, **q})
    for t in failed:
        if t in uni and t in state:
            new_state[t] = state[t]
    order = list(GROUPS)
    alerts.sort(key=lambda a: (order.index(a["group"]), a["dd"]))
    return alerts, notify, new_state


def message(alerts, notify):
    """リマインダーの件名と本文（純粋関数）"""
    hit = [a for a in alerts if a["ticker"] in notify]
    title = "📉 下落アラート: " + "・".join(a["ticker"] for a in hit[:4]) + (f" ほか{len(hit) - 4}件" if len(hit) > 4 else "")
    body = "\n".join(f"{a['name']} 高値から{a['dd']:+.1f}%（{a['label']}・基準{a['threshold']:.0f}%）"
                     f" 終値{a['last']:,} / 高値{a['hi']:,}（{a['hi_date']}）" for a in hit)
    return title, body + "\n\n買い増しの判断は花子の基準で。デイリーホームに一覧があります。"


def notify_reminder(title, body):
    """リマインダーに1件作り、1分後の通知を付ける（iCloud 経由で iPhone に届く）"""
    script = '''
on run argv
  set ttl to item 1 of argv
  set bd to item 2 of argv
  set ln to item 3 of argv
  tell application "Reminders"
    if not (exists list ln) then make new list with properties {name:ln}
    make new reminder at end of list ln with properties {name:ttl, body:bd, remind me date:((current date) + 60)}
  end tell
end run'''
    subprocess.run(["osascript", "-", title, body, REMINDER_LIST], input=script, text=True,
                   capture_output=True, timeout=60, check=True)


def load_json(p, default):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return default


def main():
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))
    today = now.date().isoformat()
    mod = load_lists()
    uni = universe(mod.LISTS, mod.DAME_SET, mod.AVOID)
    quotes, failed = {}, []
    for t in uni:
        try:
            quotes[t] = quote(t)
        except Exception as e:  # noqa: BLE001 取得失敗は銘柄ごとに記録して続ける
            failed.append(t)
            print(f"{t}: 取得失敗 {e}", file=sys.stderr)
        time.sleep(0.3)
    # 半分以上取れないのは通信の問題。前回の結果を残し、通知もしない
    if len(quotes) < len(uni) / 2:
        print(f"株価の取得に失敗（{len(failed)}/{len(uni)}件）。stocks.json は前回のまま", file=sys.stderr)
        sys.exit(1)
    state = load_json(STATE, {})
    alerts, notify, new_state = evaluate(quotes, uni, state, today, failed)
    OUT.write_text(json.dumps({
        "updated": now.isoformat(timespec="minutes"),
        "asof": max(q["date"] for q in quotes.values()),
        "watching": len(quotes), "failed": failed,
        "rules": [{"group": k, "label": v[0], "threshold": v[1]} for k, v in GROUPS.items()],
        "alerts": alerts,
    }, ensure_ascii=False, indent=1))
    if notify and "--no-notify" not in sys.argv:
        try:
            notify_reminder(*message(alerts, notify))
        except (OSError, subprocess.SubprocessError) as e:
            # 通知できなかった分は状態を進めず、次回また知らせる
            for t in notify:
                if state.get(t):
                    new_state[t] = state[t]
                else:
                    new_state.pop(t, None)
            print(f"リマインダー通知に失敗: {e}", file=sys.stderr)
    STATE.write_text(json.dumps(new_state, ensure_ascii=False, indent=1))
    print(f"株価アラート: 監視{len(quotes)}件・基準超え{len(alerts)}件・新規通知{len(notify)}件"
          + (f"・取得失敗{len(failed)}件" if failed else ""))


if __name__ == "__main__":
    main()
