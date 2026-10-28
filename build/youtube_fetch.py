#!/usr/bin/env python3
"""「高校生でも分かる米国株」（@USStockhanako）の新着動画・ライブの字幕を取ってくる。

Claude は使わない。yt-dlp で「動画」「ライブ」タブの新しいものを見て、
まだ取っていない動画の日本語字幕（自動生成）を ~/.config/daily-home/youtube/<id>.txt に置く。
要約は朝夕のスケジュールタスク daily-home-refresh（Claude）が youtube.json に書く。

  python3 build/youtube_fetch.py          # 取得して「要約待ち N件」を表示
  python3 build/youtube_fetch.py --pending  # 取得せず、要約待ちのファイルだけ表示

- ショートは対象外。配信予定・配信中は字幕が無いので次回に回す
- 字幕がまだ出ていなければ次回に再試行。48時間たっても無ければ説明文だけで要約に回す
- 公開から MAX_AGE_DAYS 日より古いものは取らない（初回に過去分を大量に拾わないため）
"""
import datetime as dt
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CHANNEL = "https://www.youtube.com/@USStockhanako"
TABS = ("videos", "streams")
PER_TAB = 4
MAX_AGE_DAYS = 3
NO_SUB_GIVEUP_H = 48
KEEP_DAYS = 10

CONF = Path.home() / ".config/daily-home"
DIR = CONF / "youtube"
STATE = DIR / "state.json"       # 取得済み・対象外にした動画ID
SUMMARY = CONF / "youtube.json"  # Claude が書く要約
JST = dt.timezone(dt.timedelta(hours=9))


def ytdlp():
    for c in (shutil.which("yt-dlp"), "/opt/homebrew/bin/yt-dlp", "/usr/local/bin/yt-dlp"):
        if c and Path(c).exists():
            return c
    return None


def load_json(path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def summarized_ids():
    return {it.get("id") for it in load_json(SUMMARY, {}).get("items", [])}


def pending():
    """字幕はあるがまだ要約されていないファイル（古い順）。"""
    done = summarized_ids()
    files = [p for p in DIR.glob("*.txt") if p.stem not in done]
    return sorted(files, key=lambda p: p.stat().st_mtime)


def transcript_text(json3_path):
    """json3 字幕を1本の文章にする（重複する改行・空白を除く）。"""
    d = json.loads(Path(json3_path).read_text())
    parts = []
    for e in d.get("events", []):
        t = "".join(s.get("utf8", "") for s in e.get("segs", []) or [])
        t = t.replace("\n", " ").strip()
        if t:
            parts.append(t)
    return " ".join(parts)


def list_ids(exe, tab):
    out = subprocess.run(
        [exe, "--flat-playlist", "--playlist-end", str(PER_TAB), "--print", "%(id)s", f"{CHANNEL}/{tab}"],
        capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise RuntimeError(f"{tab} の一覧取得に失敗: {out.stderr.strip()[-200:]}")
    return [x.strip() for x in out.stdout.splitlines() if len(x.strip()) == 11]


def fetch_one(exe, vid, kind, tmp):
    """メタデータと字幕を取る。戻り値: ("ok"|"later"|"skip", 理由)"""
    out = subprocess.run(
        [exe, "--extractor-args", "youtube:lang=ja", "--skip-download", "--write-info-json",
         "--write-auto-subs", "--write-subs", "--sub-langs", "ja,ja-orig", "--sub-format", "json3",
         "-o", f"{tmp}/%(id)s", f"https://www.youtube.com/watch?v={vid}"],
        capture_output=True, text=True, timeout=180)
    info = load_json(Path(tmp) / f"{vid}.info.json", None)
    if not info:
        # 配信予定のライブは yt-dlp がエラーで返すことがある
        return "later", (out.stderr.strip().splitlines() or ["情報なし"])[-1][:200]
    if info.get("live_status") in ("is_upcoming", "is_live"):
        return "later", info["live_status"]
    up = info.get("upload_date") or ""
    try:
        up_d = dt.date(int(up[:4]), int(up[4:6]), int(up[6:8]))
    except ValueError:
        up_d = dt.datetime.now(JST).date()
    age_days = (dt.datetime.now(JST).date() - up_d).days
    if age_days > MAX_AGE_DAYS:
        return "skip", "古い"
    if (info.get("duration") or 0) <= 70 and "/shorts/" in (info.get("webpage_url") or ""):
        return "skip", "ショート"

    subs = sorted(Path(tmp).glob(f"{vid}.*.json3"))
    text = transcript_text(subs[0]) if subs else ""
    if not text:
        # 終了時刻（無ければ公開日）から48時間は字幕待ち
        ts = info.get("release_timestamp") or info.get("timestamp")
        waited_h = (dt.datetime.now().timestamp() - ts) / 3600 if ts else age_days * 24
        if waited_h < NO_SUB_GIVEUP_H:
            return "later", "字幕がまだ無い"

    kind = "live" if info.get("was_live") or kind == "streams" else "video"
    header = {
        "id": vid,
        "date": up_d.isoformat(),
        "title": info.get("title", ""),
        "url": f"https://www.youtube.com/watch?v={vid}",
        "kind": kind,
        "minutes": round((info.get("duration") or 0) / 60),
        "transcript": bool(text),
    }
    body = ("# " + json.dumps(header, ensure_ascii=False) + "\n\n## 説明文\n" +
            (info.get("description") or "").strip() + "\n\n## 字幕（自動生成）\n" +
            (text or "（字幕なし。説明文とタイトルだけで要約する）") + "\n")
    (DIR / f"{vid}.txt").write_text(body, encoding="utf-8")
    return "ok", f"{header['date']} {header['title']}"


def cleanup():
    cutoff = dt.datetime.now().timestamp() - KEEP_DAYS * 86400
    for p in DIR.glob("*.txt"):
        if p.stat().st_mtime < cutoff:
            p.unlink()


def main():
    DIR.mkdir(parents=True, exist_ok=True)
    if "--pending" not in sys.argv:
        exe = ytdlp()
        if not exe:
            print("エラー: yt-dlp が見つかりません（brew install yt-dlp）")
            sys.exit(1)
        state = load_json(STATE, {"done": [], "skip": []})
        known = set(state["done"]) | set(state["skip"]) | summarized_ids() | {p.stem for p in DIR.glob("*.txt")}
        try:
            targets = [(v, tab) for tab in TABS for v in list_ids(exe, tab) if v not in known]
        except (RuntimeError, subprocess.SubprocessError, OSError) as e:
            print(f"エラー: {e}")
            sys.exit(1)
        for vid, tab in targets:
            with tempfile.TemporaryDirectory() as tmp:
                try:
                    res, why = fetch_one(exe, vid, tab, tmp)
                except (subprocess.SubprocessError, OSError, ValueError) as e:
                    res, why = "later", str(e)[:200]
            print(f"{res}\t{vid}\t{why}")
            if res == "ok":
                state["done"].append(vid)
            elif res == "skip":
                state["skip"].append(vid)
        state = {k: v[-200:] for k, v in state.items()}
        STATE.write_text(json.dumps(state))
        cleanup()
    files = pending()
    print(f"要約待ち {len(files)}件")
    for p in files:
        print(p)


if __name__ == "__main__":
    main()
