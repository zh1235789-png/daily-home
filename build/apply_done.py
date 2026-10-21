#!/usr/bin/env python3
"""デイリーホームで完了にしたタスクを、Obsidian のタスクハブに反映する。

  python3 build/apply_done.py <id> [<id> ...]

id は build.py が付ける項目ID（公開の issue には本文を書かず、この ID だけを送る）。
- チェックリストの項目 `- [ ]` … 親項目なら子ごと「✅ 完了（直近）」の先頭へ移し `[x]` にする。
  子項目ならその場で `[x]` にする
- 「📅 期限あり」の表の行 … 表から消し、「✅ 完了（直近）」の先頭に1行足す
見つからない id は何もしない（もう消えている・すでに反映済み）。結果を1行ずつ表示する。
"""
import datetime as dt
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import HUB, is_struck, item_id, links  # noqa: E402

AREAS = {"🔥": "week", "📌": "big", "🗂": "someday"}
CHECK = re.compile(r"^(\s*)- \[( |x|X)\] (.+)$")


def apply(md, ids, today):
    lines = md.split("\n")
    want = set(ids)
    moved = []          # 完了欄に足す行
    drop = set()        # 消す行番号
    found = []
    area = None
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("## "):
            area = next((v for k, v in AREAS.items() if line[3:].startswith(k)), None)
            if line[3:].startswith("📅"):
                area = "dated"
            elif line[3:].startswith("✅"):
                area = None
            i += 1
            continue
        m = CHECK.match(line)
        if area in ("week", "big", "someday") and m and m.group(2) == " ":
            indent, text = len(m.group(1).expandtabs(4)), m.group(3).strip()
            body, _ = links(text)
            iid = item_id(area, body)
            if iid in want:
                found.append(iid)
                if indent > 0:
                    lines[i] = line.replace("- [ ]", "- [x]", 1)
                else:
                    # 親項目：子（インデントされた続きの行）ごと移す
                    j = i + 1
                    while j < len(lines) and lines[j].strip() and (lines[j][:1] in " \t"):
                        j += 1
                    block = [f"- [x] {text}（{today.month}/{today.day} 完了）"] + lines[i + 1:j]
                    moved.extend(block)
                    drop.update(range(i, j))
                    i = j
                    continue
        elif area == "dated" and line.startswith("|") and not re.match(r"^\|\s*-", line):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 3 and not is_struck(cells[0]):
                iid = item_id("dated", cells[0], cells[2])
                if iid in want:
                    found.append(iid)
                    label = re.sub(r"\*\*|~~", "", cells[0]).strip()
                    moved.append(f"- [x] {label}：{cells[2]}（{today.month}/{today.day} 完了）")
                    drop.add(i)
        i += 1

    out = [l for k, l in enumerate(lines) if k not in drop]
    if moved:
        h = next((k for k, l in enumerate(out) if l.startswith("## ✅")), None)
        if h is None:
            out += ["", "## ✅ 完了（直近）", ""] + moved
        else:
            k = h + 1
            while k < len(out) and not out[k].strip():
                k += 1
            out[k:k] = moved
    text = "\n".join(out)
    if found:
        text = re.sub(r"^updated: .*$", f"updated: {today.isoformat()}", text, count=1, flags=re.M)
    return text, found


def main():
    ids = [x for x in sys.argv[1:] if re.fullmatch(r"[0-9a-f]{10}", x)]
    if not ids:
        return
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()
    md = HUB.read_text()
    text, found = apply(md, ids, today)
    if found:
        fd, tmp = tempfile.mkstemp(dir=HUB.parent, suffix=".tmp")
        with os.fdopen(fd, "w") as f:
            f.write(text)
        os.replace(tmp, HUB)
    for i in ids:
        print(("反映" if i in found else "見つからず") + " " + i)


if __name__ == "__main__":
    main()
