#!/usr/bin/env python3
"""デイリーホームで付けた「📚 毎日の英語」のチェックを Mac に記録する。

  python3 build/eng_log.py e:20261116:10110 [e:...]

ページは title=done の issue に「e:日付:5桁の0/1」を書いて送る（公開 issue なので中身は 0/1 だけ）。
5桁は index.html の ENG_DAILY の順（瞬間英作文・Langaku・OET Reading・OET Speaking・OET Listening）。
同じ日が何度も来たら、引数で先に来た方（＝新しい issue）を採る。リスナーは新しい issue から順に渡す。
記録先: ~/.config/daily-home/eng_log.json  {"2026-11-16": "10110", ...}
週の点数（~/bin/week_score.py）がこれを読む。
"""
import json
import os
import re
import sys
import tempfile
from pathlib import Path

LOG = Path.home() / ".config/daily-home/eng_log.json"
KEYS = ["shunkan", "langaku", "reading", "speaking", "listening"]
LINE = re.compile(r"^e:(\d{4})(\d{2})(\d{2}):([01]{5})$")


def merge(current, args):
    out = dict(current)
    seen = set()
    for a in args:
        m = LINE.match(a.strip())
        if not m:
            continue
        d = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        if d in seen:
            continue
        seen.add(d)
        out[d] = m.group(4)
    return out, sorted(seen)


def main():
    try:
        cur = json.loads(LOG.read_text())
        if not isinstance(cur, dict):
            cur = {}
    except (OSError, ValueError):
        cur = {}
    new, days = merge(cur, sys.argv[1:])
    if days:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=LOG.parent, suffix=".tmp")
        with os.fdopen(fd, "w") as f:
            json.dump(dict(sorted(new.items())), f, ensure_ascii=False, indent=1)
        os.replace(tmp, LOG)
    for d in days:
        print(f"英語 {d} {new[d].count('1')}/5")


if __name__ == "__main__":
    main()
