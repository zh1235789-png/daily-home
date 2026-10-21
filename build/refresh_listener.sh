#!/usr/bin/env bash
# デイリーホームの「更新」ボタンを受けて、データを作り直す。
# launchd（~/Library/LaunchAgents/com.daily-home.refresh.plist）から1分おきに呼ばれる。
#
# ボタンを押すと、ページが本人のトークンで GitHub に title=refresh の issue を立てる。
# ここではそれを見つけたら閉じて、
#   1) タスクハブ・今日のOETを読み直して push（数十秒）
#   2) Claude CLI でカレンダー・Gmail を取り直して、もう一度 push（数分）
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

ids=$(gh api "repos/$REPO_SLUG/issues?state=open&creator=$OWNER&per_page=20" \
  --jq '.[] | select(.title == "refresh") | .number' 2>>"$LOG") || exit 0
ids=$(printf '%s\n' "$ids" | grep -E '^[0-9]+$' | tr '\n' ' ')
[ -z "${ids// /}" ] && exit 0

# 前の更新がまだ走っていれば、今回の issue は閉じるだけ（続けて押されたとき）
if ! mkdir "$LOCK" 2>/dev/null; then
  if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +20)" ]; then rmdir "$LOCK"; mkdir "$LOCK"; else
    for n in $ids; do gh api -X PATCH "repos/$REPO_SLUG/issues/$n" -f state=closed >/dev/null 2>&1; done
    exit 0
  fi
fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

for n in $ids; do gh api -X PATCH "repos/$REPO_SLUG/issues/$n" -f state=closed -f state_reason=completed >/dev/null 2>>"$LOG"; done
log "refresh requested: $ids"

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
# shellcheck disable=SC2086
if claude -p "$prompt" --model sonnet \
     --allowedTools Read "Write($CONF/calendar.json)" "Write($CONF/gmail.json)" \
       "Bash($HOME/daily-home/build/publish.sh)" "Bash(~/daily-home/build/publish.sh)" $tools \
     >>"$LOG" 2>&1; then
  status done "更新しました"
else
  status error "メールと予定の取得に失敗しました（Macのログを確認）"
fi
"$HERE/publish.sh" >>"$LOG" 2>&1
log "refresh finished"
