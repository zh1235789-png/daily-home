#!/usr/bin/env bash
# データを作り直して data.enc.json だけを push する（スケジュールタスクから呼ぶ）
set -euo pipefail
cd "$(dirname "$0")/.."
python3 build/build.py
git add data.enc.json
if git diff --cached --quiet; then
  # 前回 commit 後の push が失敗していたら、データだけのコミットに限って押し直す
  git fetch -q origin main 2>/dev/null || true
  pending="$(git diff --name-only origin/main..HEAD 2>/dev/null)"
  if [ "$pending" = "data.enc.json" ]; then
    SKIP_CODEX=1 SKIP_AGY=1 git push -q origin main
    echo "未pushのデータを push しました"; exit 0
  fi
  echo "変更なし"; exit 0
fi
git commit -q -m "データ更新 $(date '+%Y-%m-%d %H:%M')"
# 中身は暗号文なので AI レビューは省く（個人情報ゲート・lint・テストは通す）
SKIP_CODEX=1 SKIP_AGY=1 git push -q origin main
echo "push しました"
