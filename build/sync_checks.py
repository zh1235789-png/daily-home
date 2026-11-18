#!/usr/bin/env python3
"""デイリーホームの英語・OET・ラン筋トレ・抱負のチェックを、端末間で揃えるために記録する。

  printf '63 k:eng:2026-11-18:langaku=1\\n' | python3 build/sync_checks.py

標準入力の各行は「issue番号 k:<ID>=0/1」（リスナーが title=done の issue 本文から作る）。
同じ ID は issue 番号の大きい方（＝新しい変更）を採る。記録先 ~/.config/daily-home/checks_sync.json
  {"<ID>": [0/1, issue番号, "受け取った日"]}
build.py がこれを DATA.sync として暗号化データに載せ、各端末が開いたときに取り込む。
21日より前に受け取ったものは消す（ページに出るのは今日・今週の項目だけ）。
"""
import datetime as dt
import json
import os
import re
import sys
import tempfile
from pathlib import Path

PATH = Path.home() / ".config/daily-home/checks_sync.json"
# index.html の SYNC_RE と同じ形だけ受け取る（公開 issue なので任意の文字列は通さない）
LINE = re.compile(r"^(\d+) k:((?:(?:eng|train):\d{4}-\d{2}-\d{2}:[a-z]+|goal:[0-9a-f]{10}|[0-9a-f]{10}))=([01])$")
KEEP_DAYS = 21


def merge(current, lines, today):
    out = {k: v for k, v in current.items()
           if isinstance(v, list) and len(v) == 3 and isinstance(v[1], int)}
    changed = []
    for raw in lines:
        m = LINE.match(raw.strip())
        if not m:
            continue
        n, cid, val = int(m.group(1)), m.group(2), int(m.group(3))
        cur = out.get(cid)
        if cur and cur[1] > n:
            continue
        out[cid] = [val, n, today]
        changed.append(cid)
    limit = (dt.date.fromisoformat(today) - dt.timedelta(days=KEEP_DAYS)).isoformat()
    out = {k: v for k, v in out.items() if str(v[2]) >= limit}
    return out, sorted(set(changed))


def published(current):
    """build.py が載せる形 {ID: [0/1, issue番号]}"""
    return {k: [v[0], v[1]] for k, v in (current or {}).items()
            if isinstance(v, list) and len(v) == 3 and isinstance(v[1], int)}


def main():
    try:
        cur = json.loads(PATH.read_text())
        if not isinstance(cur, dict):
            cur = {}
    except (OSError, ValueError):
        cur = {}
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date().isoformat()
    new, ids = merge(cur, sys.stdin.read().splitlines(), today)
    PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=PATH.parent, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(dict(sorted(new.items())), f, ensure_ascii=False, indent=1)
    os.replace(tmp, PATH)
    print(f"同期 {len(ids)}件")


if __name__ == "__main__":
    main()
