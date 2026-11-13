#!/usr/bin/env python3
"""デイリーホームで「対応済み」にしたメールを、以後の要対応メールに出さないようにする。

  python3 build/dismiss_mail.py <id> [<id> ...]

id は build.py の mail_id()（スレッド番号から作る10桁）。公開の issue にはこの ID だけが載る。
- gmail.json の該当メールを消す（次の公開でページから消える）
- gmail_dismissed.json に スレッド番号・差出人・件名 を足す（daily-home-refresh はここに載ったスレッドを出さない）
見つからない id は何もしない。結果を1行ずつ表示する。
"""
import datetime as dt
import json
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import CONF, load_json, mail_id, mail_thread  # noqa: E402


def dismiss(gmail, dismissed, ids, today):
    """純粋関数。(新しい gmail, 新しい dismissed, 処理した件名のリスト) を返す。"""
    want = set(ids)
    items = (gmail or {}).get("items") or []
    threads = list((dismissed or {}).get("threads") or [])
    known = {t.get("thread") for t in threads if isinstance(t, dict)}
    keep, done = [], []
    for it in items:
        mid = mail_id(it.get("url")) if isinstance(it, dict) else ""
        if mid and mid in want:
            th = mail_thread(it.get("url"))
            if th not in known:
                threads.append({"thread": th, "from": it.get("from", ""), "subject": it.get("subject", ""),
                                "note": "デイリーホームで対応済み", "date": today})
                known.add(th)
            done.append((mid, it.get("subject", "")))
        else:
            keep.append(it)
    g = dict(gmail or {})
    g["items"] = keep
    return g, {"threads": threads}, done


def write_json(path, obj):
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-")
    with os.fdopen(fd, "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def main():
    ids = [x for x in sys.argv[1:] if re.fullmatch(r"[0-9a-f]{10}", x)]
    if not ids:
        return
    conf = Path(os.environ.get("DAILY_HOME_CONF", str(CONF)))
    gp, dp = conf / "gmail.json", conf / "gmail_dismissed.json"
    gmail = load_json(gp, {"updated": None, "items": []})
    dismissed = load_json(dp, {"threads": []})
    g, d, done = dismiss(gmail, dismissed, ids, dt.date.today().isoformat())
    if done:
        write_json(dp, d)
        write_json(gp, g)
    for mid, _ in done:
        print("除外 " + mid)
    for mid in sorted(set(ids) - {m for m, _ in done}):
        print("見つからない " + mid)


if __name__ == "__main__":
    main()
