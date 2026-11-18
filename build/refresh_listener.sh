#!/usr/bin/env bash
# デイリーホームの「更新」ボタンを受けて、データを作り直す。
# launchd（~/Library/LaunchAgents/com.daily-home.refresh.plist）から1分おきに呼ばれる。
#
# ボタンを押すと、ページが本人のトークンで GitHub に title=refresh の issue を立てる。
# ここではそれを見つけたら閉じて、
#   1) タスクハブ・今日のOETを読み直して push（数十秒）
#   2) Claude CLI でカレンダー・Gmail を取り直して、もう一度 push（数分）
# を行う。チェックしたタスクは title=done の issue（本文は ID だけ）で届き、
#   0) apply_done.py でタスクハブに完了を書き込んで push（数秒）
# を行う。公開リポジトリなので、本人以外が立てた issue は無視する。
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

REPO_SLUG="zh1235789-png/daily-home"
OWNER="zh1235789-png"
HERE="$(cd "$(dirname "$0")" && pwd)"
CONF="$HOME/.config/daily-home"
STATUS="$CONF/status.json"
LOCK="$CONF/refresh.lock"
LOG="$CONF/refresh.log"
SKILL="$HOME/.claude/scheduled-tasks/daily-home-refresh/SKILL.md"

log() { echo "$(date '+%F %T') $*" >> "$LOG"; }
status() { # status <段階> <メッセージ>  … 今回受けた issue 番号（$ids）も書く。ページは番号で自分の依頼を見分ける
  python3 - "$STATUS" "$1" "$2" "$ids" <<'EOF'
import json, sys, datetime as dt
p, stage, msg, ids = sys.argv[1:]
now = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec="seconds")
json.dump({"stage": stage, "message": msg, "at": now, "req": [int(x) for x in ids.split()]},
          open(p, "w"), ensure_ascii=False)
EOF
}

# 定時の公開（Claude 不要）。昼12:50・夜21:50を過ぎたら、その日1回ずつタスクハブと今日のOETだけ読み直し、
# 変わっていれば push する（publish.sh が「変更なし」で正常終了したときも、その回は済みとする）。
# 予定・メールは朝夕のスケジュールタスク（Claude）が書いた分をそのまま使う。Mac が寝ていたら起きた後に追いつく。
now_hm=$(date +%H%M); today=$(date +%F)
for slot in 1250 2150; do
  stamp="$CONF/scheduled-$today-$slot"
  # 失敗したら印を付けず、10分おきに再試行する
  [ -n "$(find "$stamp.fail" -mmin -10 2>/dev/null)" ] && continue
  if [ "$now_hm" -ge "$slot" ] && [ ! -e "$stamp" ] && mkdir "$LOCK" 2>/dev/null; then
    log "scheduled publish $slot"
    if "$HERE/publish.sh" >>"$LOG" 2>&1; then
      touch "$stamp"; rm -f "$stamp.fail"
    else
      touch "$stamp.fail"; log "scheduled publish $slot failed (10分後に再試行)"
    fi
    rmdir "$LOCK"
  fi
done
find "$CONF" -maxdepth 1 -name 'scheduled-*' -mtime +3 -delete 2>/dev/null

# 花子の米国株（YouTube）の字幕取得（Claude 不要）。2時間おき。要約は朝夕の Claude の回が行う
YT_STAMP="$CONF/youtube-fetched"
if [ -z "$(find "$YT_STAMP" -mmin -120 2>/dev/null)" ] && mkdir "$CONF/youtube.lock" 2>/dev/null; then
  touch "$YT_STAMP"
  # 30秒ほどかかるので裏で回し、更新ボタンの処理を待たせない
  ( python3 "$HERE/youtube_fetch.py" >>"$LOG" 2>&1 || log "youtube fetch failed"; rmdir "$CONF/youtube.lock" ) &
fi
find "$CONF/youtube.lock" -maxdepth 0 -mmin +30 -exec rmdir {} \; 2>/dev/null

# 株価の下落アラート（Claude 不要）。米国市場の引け後、毎朝6:30を過ぎたら1日1回。
# 新しく基準を超えた銘柄はリマインダー「株価アラート」で通知し、一覧は次の公開でデイリーホームに載る。
# 失敗したら印を付けず、30分おきに再試行する。
# 裏で回すと launchd がこのスクリプトの終了と同時に止めてしまうので、1日1回（40秒ほど）はここで待つ
SK_STAMP="$CONF/stocks-$today"
if [ "$now_hm" -ge 0630 ] && [ ! -e "$SK_STAMP" ] && [ -z "$(find "$SK_STAMP.fail" -mmin -30 2>/dev/null)" ]; then
  if python3 "$HERE/stock_alert.py" >>"$LOG" 2>&1; then touch "$SK_STAMP"; rm -f "$SK_STAMP.fail"
  else touch "$SK_STAMP.fail"; log "stock alert failed (30分後に再試行)"; fi
fi
find "$CONF" -maxdepth 1 -name 'stocks-*' -mtime +3 -delete 2>/dev/null

open_json=$(gh api "repos/$REPO_SLUG/issues?state=open&creator=$OWNER&per_page=30" 2>>"$LOG") || exit 0
nums() { printf '%s' "$open_json" | jq -r --arg t "$1" '.[] | select(.title == $t) | .number' | grep -E '^[0-9]+$' | tr '\n' ' '; }
refresh_ids=$(nums refresh)
# title=done の本文は「id:<10桁の16進>」（タスク）と「mail:<10桁の16進>」（メール）の行だけ
# （公開 issue なのでタスクの文面・メールの件名やスレッド番号は送らない）
done_ids=$(nums done)
done_body=$(printf '%s' "$open_json" | jq -r '.[] | select(.title == "done") | .body // ""')
task_ids=$(printf '%s\n' "$done_body" | grep -oE '(^|[^a-z])id:[0-9a-f]{10}' | grep -oE '[0-9a-f]{10}$' | sort -u | tr '\n' ' ')
mail_ids=$(printf '%s\n' "$done_body" | grep -oE 'mail:[0-9a-f]{10}' | cut -c6- | sort -u | tr '\n' ' ')
# 毎日の英語の記録「e:日付:5桁」。新しい issue が先に来る順のまま渡す（同じ日は先の方を採る）
eng_lines=$(printf '%s\n' "$done_body" | { grep -oE '^e:[0-9]{8}:[01]{5}$' || true; } | tr '\n' ' ')
# 英語・OET・ラン筋トレ・抱負のチェック「k:<ID>=0/1」。端末間で揃えるので issue 番号を付けて渡す（新しい方を採る）
sync_lines=$(printf '%s' "$open_json" | jq -r '.[] | select(.title == "done") | .number as $n | (.body // "") | split("\n")[] | select(test("^k:[a-z0-9:-]+=[01]$")) | "\($n) \(.)"' 2>>"$LOG" || true)
ids="$done_ids $refresh_ids"
[ -z "${ids// /}" ] && exit 0

# 前の更新がまだ走っていれば、更新の依頼は閉じるだけ（続けて押されたとき）。完了の依頼は次の回に回す
if ! mkdir "$LOCK" 2>/dev/null; then
  if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +20)" ]; then rmdir "$LOCK"; mkdir "$LOCK"; else
    for n in $refresh_ids; do gh api -X PATCH "repos/$REPO_SLUG/issues/$n" -f state=closed >/dev/null 2>&1; done
    exit 0
  fi
fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

for n in $ids; do gh api -X PATCH "repos/$REPO_SLUG/issues/$n" -f state=closed -f state_reason=completed >/dev/null 2>>"$LOG"; done
log "requested: done=[$done_ids] tasks=[$task_ids] mails=[$mail_ids] eng=[$eng_lines] sync=[$(printf '%s' "$sync_lines" | grep -c . || true)] refresh=[$refresh_ids]"

# 0) 完了の反映（Claude 不要・数秒）
if [ -n "${done_ids// /}" ]; then
  msg="" ok=1
  if [ -n "${task_ids// /}" ]; then
    # shellcheck disable=SC2086
    if res=$(python3 "$HERE/apply_done.py" $task_ids 2>>"$LOG"); then
      log "$res"
      n_ok=$(printf '%s\n' "$res" | grep -c '^反映' || true)
      msg="完了をObsidianに反映しました（${n_ok}件）"
    else ok=0; fi
  fi
  # 対応済みにしたメールは gmail.json から消し、gmail_dismissed.json に足す（以後の更新でも出さない）
  if [ -n "${mail_ids// /}" ]; then
    # shellcheck disable=SC2086
    if res=$(python3 "$HERE/dismiss_mail.py" $mail_ids 2>>"$LOG"); then
      log "$res"
      n_m=$(printf '%s\n' "$res" | grep -c '^除外' || true)
      msg="${msg:+$msg・}メール${n_m}件を対応済みにしました"
    else ok=0; fi
  fi
  if [ -n "${eng_lines// /}" ]; then
    # shellcheck disable=SC2086
    if res=$(python3 "$HERE/eng_log.py" $eng_lines 2>>"$LOG"); then
      log "$res"; msg="${msg:+$msg・}毎日の英語を記録しました"
    else ok=0; fi
  fi
  if [ -n "$sync_lines" ]; then
    if res=$(printf '%s\n' "$sync_lines" | python3 "$HERE/sync_checks.py" 2>>"$LOG"); then
      log "$res"; msg="${msg:+$msg・}チェックをほかの端末へ配ります"
    else ok=0; fi
  fi
  if [ "$ok" = 1 ]; then status done "${msg:-完了を受け取りました}"
  else status error "完了の反映に失敗しました（Macのログを確認）"; fi
  if [ -z "${refresh_ids// /}" ]; then
    "$HERE/publish.sh" >>"$LOG" 2>&1
    exit 0
  fi
fi

# 1) タスク・OET（Claude 不要）
status tasks "タスクを更新しました。メールと予定を取得中…"
if ! "$HERE/publish.sh" >>"$LOG" 2>&1; then
  status error "タスクの更新に失敗しました（Macのログを確認）"; log "publish failed"
  "$HERE/publish.sh" >>"$LOG" 2>&1  # 一時的な失敗なら、せめてエラー状態だけでも届ける
  exit 1
fi

# 2) カレンダー・Gmail（Claude CLI が必要）
if ! claude auth status 2>/dev/null | grep -q '"loggedIn": true'; then
  status error "メールと予定は前回のまま（MacのClaude CLIが未ログイン：claude auth login）"
  "$HERE/publish.sh" >>"$LOG" 2>&1
  exit 0
fi
prompt="$(awk 'f>=2{print} /^---$/{f++}' "$SKILL")"
tools="$(grep -v '^#' "$CONF/claude_allowed_tools" 2>/dev/null | tr '\n' ' ')"
cd "$HOME/daily-home" || exit 1
# メール本文は信頼できない入力なので、送信・削除系は与えず、読み取りと所定ファイルの書き込みだけ許可する
# ファイルの許可は Edit(~/…) で書き（Write(…) やスラッシュ1本の絶対パスは効かない）、
# プロジェクト外の設定フォルダは --add-dir で作業範囲に入れる。公開はこのスクリプトが後で行う。
# claude が 0 で終わっても書けていないことがあるので、ファイルが新しくなったかで成否を判断する
yt_out="$(python3 "$HERE/youtube_fetch.py" --pending 2>&1)"
prompt="$prompt

（このコマンドライン実行では手順4の publish.sh は実行しない。JSONを書いたら報告して終わる。公開は呼び出し側が行う。
この実行で使えるのは Read・WebSearch・上のMCPツールと、4つのJSONへの Edit だけ。Bash・chmod・Write・/tmp やスクリプトファイルの作成は使えないので試さない。
4ファイルは Edit で中身を書き換える（権限600は既存ファイルのまま保たれる）。JSONの構文チェック・権限600の確認・公開は呼び出し側が後で行うので、報告で未完了に挙げない。
手順3の取得スクリプトは呼び出し側で実行済み。その出力:
$yt_out
）"
before="$(stat -f %m "$CONF/gmail.json" "$CONF/calendar.json" 2>/dev/null | tr '\n' ' ')"
# shellcheck disable=SC2086
# 買い候補（手順3b）は Obsidian の投資ノートを読み、WebSearch でニュースを確かめて picks.json に書く
FIN="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian Vault/03_Personal/03.6_Finance"
claude -p "$prompt" --model sonnet --add-dir "$CONF" --add-dir "$FIN" \
  --allowedTools Read WebSearch "Edit(~/.config/daily-home/calendar.json)" "Edit(~/.config/daily-home/gmail.json)" "Edit(~/.config/daily-home/youtube.json)" "Edit(~/.config/daily-home/picks.json)" $tools \
  >>"$LOG" 2>&1
after="$(stat -f %m "$CONF/gmail.json" "$CONF/calendar.json" 2>/dev/null | tr '\n' ' ')"
# Claude には Bash を渡していないので、権限600と JSON の構文はここで確かめる
broken=""
for f in calendar gmail youtube picks; do
  [ -f "$CONF/$f.json" ] || continue
  chmod 600 "$CONF/$f.json"
  python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$CONF/$f.json" 2>/dev/null || broken="$broken $f.json"
done
if [ -n "$broken" ]; then
  log "JSON broken:$broken"
  status error "書き出したJSONが壊れています:$broken（Macのログを確認）"
elif [ "$before" != "$after" ]; then
  status done "更新しました"
else
  status error "メールと予定の取得に失敗しました（Macのログを確認）"
fi
"$HERE/publish.sh" >>"$LOG" 2>&1
log "refresh finished"
