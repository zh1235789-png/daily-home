#!/usr/bin/env python3
"""デイリーホームのデータを作る。

Obsidian のタスクハブ・今日のOETノート、それと ~/.config/daily-home/ に置いた
calendar.json / gmail.json（Claude のスケジュールタスクが書く）をまとめて、
パスフレーズで暗号化した data.enc.json をリポジトリ直下に書き出す。

公開リポジトリなので、平文はリポジトリに一切置かない。
  python3 build/build.py            # 暗号化して data.enc.json を更新
  python3 build/build.py --plain    # 平文JSONを標準出力へ（確認用）
"""
import base64
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path

HOME = Path.home()
VAULT = HOME / "Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian Vault"
HUB = VAULT / "03_Personal/03.1_Tasks/タスクハブ.md"
OET = VAULT / "📌 今日のOET学習.md"
CONF = HOME / ".config/daily-home"
REPO = Path(__file__).resolve().parent.parent
ITERATIONS = 200_000


# ---------- 共通 ----------

def item_id(*parts):
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:10]


def section(md, heading_prefix):
    """`## <prefix>` から次の `## ` まで（見出し行は除く）。"""
    m = re.search(rf"^## {re.escape(heading_prefix)}.*$", md, re.M)
    if not m:
        return ""
    rest = md[m.end():]
    n = re.search(r"^## ", rest, re.M)
    return rest[: n.start()] if n else rest


def links(text):
    """末尾の「→ [[ノート]]」を取り出し、本文から外す。"""
    notes = re.findall(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", text)
    if re.search(r"→\s*同上\s*$", text):
        notes = ["同上"]
    body = re.sub(r"\s*→\s*((\[\[[^\]]+\]\]\s*(/\s*)?)+|同上)\s*$", "", text).strip()
    return body, notes


def inherit(items):
    """「同上」のリンクは付けない。

    タスクハブの「同上」は行の並べ替えで指す先がずれていることがある
    （例：HIRAMATSUの行が直上のNVDAのノートを指していた）。間違ったノートへ
    飛ばすより、リンク無しのほうがよい。
    """
    for it in items:
        if it["notes"] == ["同上"]:
            it["notes"] = []
    return items


def is_struck(text):
    t = text.strip().strip("*").strip()
    return t.startswith("~~") and "~~" in t[2:]


def infer_date(y, m, d):
    try:
        x = dt.date(y, m, d)
    except ValueError:
        return None
    return x


DATE_RE = re.compile(r"(?:(\d{4})[/年])?(\d{1,2})/(\d{1,2})")


def parse_due(text, today):
    """期限の文字列から (start, due) を返す。日付が読めなければ (None, None)。

    例: "**10/15（木）**" → (None, 10/15)、"〜12/15" → (None, 12/15)、
        "12/1〜12/24" → (12/1, 12/24)、"2027/1/7" → (None, 2027/1/7)
    年が無ければ今年。半年以上前になるなら翌年とみなす。
    """
    plain = re.sub(r"~~.*?~~", "", text)
    found = []
    year = None
    for m in DATE_RE.finditer(plain):
        if m.group(1):
            year = int(m.group(1))
        y = year or today.year
        x = infer_date(y, int(m.group(2)), int(m.group(3)))
        if x is None:
            continue
        if not m.group(1) and year is None and (today - x).days > 183:
            x = x.replace(year=x.year + 1)
        found.append(x)
    if not found:
        return None, None
    if len(found) >= 2 and "〜" in plain:
        return found[0], found[-1]
    return None, found[0]


# ---------- タスクハブ ----------

def parse_checklist(block, area):
    """`- [ ]` の箇条書き。インデントされた子項目は親の children に入れる。"""
    items = []
    for line in block.splitlines():
        m = re.match(r"^(\s*)- \[( |x|X)\] (.+)$", line)
        if not m:
            continue
        indent, mark, text = len(m.group(1).expandtabs(4)), m.group(2), m.group(3).strip()
        body, notes = links(text)
        it = {"id": item_id(area, body), "text": body, "notes": notes,
              "done": mark.lower() == "x", "children": []}
        if indent > 0 and items:
            items[-1]["children"].append(it)
        else:
            items.append(it)
    return items


def parse_table(block):
    rows = []
    for line in block.splitlines():
        if not line.startswith("|") or re.match(r"^\|\s*-", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rows.append(cells)
    return rows[1:] if rows else []  # 先頭は見出し


def parse_hub(md, today):
    week = parse_checklist(section(md, "🔥"), "week")
    for it in week:
        # 「〜10/11 両親に電話」のように本文に期限が書かれていれば拾う
        m = re.match(r"^\**\s*〜\s*(\d{1,2}/\d{1,2})", it["text"])
        it["due"] = parse_due(m.group(1), today)[1].isoformat() if m else None

    dated = []
    for cells in parse_table(section(md, "📅")):
        if len(cells) < 3:
            continue
        due_s, area, what = cells[0], cells[1], cells[2]
        detail = cells[3] if len(cells) > 3 else ""
        start, due = parse_due(due_s, today)
        notes = ["同上"] if detail.strip() == "同上" else re.findall(r"\[\[([^\]|]+)", detail)
        dated.append({
            "id": item_id("dated", due_s, what),
            "label": re.sub(r"\*\*|~~", "", due_s).strip(),
            "area": area,
            "text": what,
            "notes": notes,
            "done": is_struck(due_s) or is_struck(what),
            "start": start.isoformat() if start else None,
            "due": due.isoformat() if due else None,
            "asap": "早め" in due_s,
        })

    inherit(week)
    inherit(dated)
    return {
        "week": week,
        "dated": dated,
        "big": parse_checklist(section(md, "📌"), "big"),
        "someday": parse_checklist(section(md, "🗂"), "someday"),
    }


# ---------- 今日のOET ----------

def parse_oet_note(md):
    m = re.search(r"^date:\s*(\S+)", md, re.M)
    date = m.group(1) if m else None
    m = re.search(r"^# (.+)$", md, re.M)
    title = m.group(1).strip() if m else "今日のOET学習"
    menu = []
    for cells in parse_table(section(md, "✅ 今日のメニュー")):
        if len(cells) >= 4:
            menu.append({"id": item_id("oet", date or "", cells[2]), "prio": cells[0],
                         "skill": cells[1], "text": cells[2], "time": cells[3]})
    m = re.search(r"^## ✅ 今日のメニュー（(.+?)）", md, re.M)
    total = m.group(1) if m else ""
    # 冒頭の引用（今日の要点）
    lead = []
    top = md.split("## ✅ 今日のメニュー")[0]
    for line in top.splitlines():
        if line.startswith("> ") and "毎朝6:30" not in line:
            lead.append(line[2:].strip())
    record = parse_checklist(section(md, "📝 終わったら記録"), "oet-rec:" + (date or ""))
    return {"date": date, "title": title, "total": total, "lead": lead,
            "menu": menu, "record": record}


# ---------- 組み立て・暗号化 ----------

def load_json(path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def build(today=None):
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))
    today = today or now.date()
    data = {
        "generated": now.isoformat(timespec="minutes"),
        "hub": parse_hub(HUB.read_text(), today),
        "oet": parse_oet_note(OET.read_text()) if OET.exists() else None,
        "calendar": load_json(CONF / "calendar.json", {"updated": None, "events": []}),
        "gmail": load_json(CONF / "gmail.json", {"updated": None, "items": []}),
        "refresh": load_json(CONF / "status.json", None),
    }
    return data


def encrypt(obj, passphrase):
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    salt, iv = os.urandom(16), os.urandom(12)
    key = PBKDF2HMAC(hashes.SHA256(), 32, salt, ITERATIONS).derive(passphrase.encode())
    ct = AESGCM(key).encrypt(iv, json.dumps(obj, ensure_ascii=False).encode(), None)
    b = lambda x: base64.b64encode(x).decode()
    return {"v": 1, "iter": ITERATIONS, "salt": b(salt), "iv": b(iv), "ct": b(ct)}


def main():
    data = build()
    if "--plain" in sys.argv:
        print(json.dumps(data, ensure_ascii=False, indent=1))
        return
    passphrase = (CONF / "passphrase").read_text().strip()
    (REPO / "data.enc.json").write_text(json.dumps(encrypt(data, passphrase)))
    print("data.enc.json を更新しました", data["generated"])


if __name__ == "__main__":
    main()
