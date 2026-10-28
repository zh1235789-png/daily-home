#!/usr/bin/env python3
"""YouTube 要約の「投資メモ」を、花子投資スキルが読むノートへ追記する（Claude 不要）。

~/.config/daily-home/youtube.json の各動画の invest_notes（花子さん自身の見方・売買・
判断基準など、後の投資判断に使えるもの）を、
Obsidian 03_Personal/03.6_Finance/花子チャンネル投資戦略分析.md の
「## 9. 最新の発言ログ」節（マーカーの間）の先頭へ足す。

- 動画IDのコメントで二重追記を防ぐ。既存の記録は消さない（追記だけ）
- マーカーが無ければ何もしない（ノートの構成を勝手に変えない）
  python3 build/hanako_log.py            # 追記
  python3 build/hanako_log.py --dry-run  # 追記する内容を表示するだけ
"""
import datetime as dt
import json
import re
import sys
from pathlib import Path

VAULT = Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian Vault"
NOTE = VAULT / "03_Personal/03.6_Finance/花子チャンネル投資戦略分析.md"
SUMMARY = Path.home() / ".config/daily-home/youtube.json"
START = "<!-- hanako-log:start -->"
END = "<!-- hanako-log:end -->"


def load_items(path):
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return []
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []
    return [it for it in items if isinstance(it, dict) and it.get("id")
            and isinstance(it.get("invest_notes"), list) and it["invest_notes"]]


def entry(it):
    head = it.get("headline") or it.get("title", "")
    lines = [f"### {it.get('date', '')} {head} <!-- yt:{it['id']} -->",
             f"[動画]({it.get('url', '')})"]
    lines += [f"- {n}" for n in it["invest_notes"] if isinstance(n, str) and n.strip()]
    return "\n".join(lines)


def merge(md, items, today):
    """追記後の本文と追記した件数。マーカーが無ければ (md, 0)。"""
    if START not in md or END not in md:
        return md, 0
    head, rest = md.split(START, 1)
    body, tail = rest.split(END, 1)
    new = [it for it in sorted(items, key=lambda x: x.get("date") or "")
           if f"<!-- yt:{it['id']} -->" not in body]
    if not new:
        return md, 0
    add = "\n\n".join(entry(it) for it in reversed(new))  # 新しい順に先頭へ
    body = "\n" + add + "\n" + body.lstrip("\n")
    if not body.endswith("\n"):
        body += "\n"
    out = head + START + body + END + tail
    out = re.sub(r"^updated:.*$", f"updated: {today}", out, count=1, flags=re.M)
    return out, len(new)


def main():
    items = load_items(SUMMARY)
    try:
        md = NOTE.read_text(encoding="utf-8")
    except OSError as e:
        print(f"エラー: ノートを読めません（{e}）")
        sys.exit(1)
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date().isoformat()
    out, n = merge(md, items, today)
    if START not in md:
        print("マーカーが無いので追記しません")
        return
    if n and "--dry-run" not in sys.argv:
        NOTE.write_text(out, encoding="utf-8")
    print(f"花子の発言ログ: {n}件追記" + ("（dry-run）" if "--dry-run" in sys.argv else ""))


if __name__ == "__main__":
    main()
