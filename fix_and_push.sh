#!/bin/bash

# ============================================================
# コンフリクトを解決してプッシュ
# ============================================================

set -e

cd "$(dirname "$0")"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 コンフリクトを解決してプッシュします"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ステップ1: マージを中止
echo "🔙 マージを中止中..."
git merge --abort 2>/dev/null || true

# ステップ2: ローカル変更をstash
echo ""
echo "📦 ローカル変更を一時保存中..."
git stash push -u -m "Cleanup scripts and gitignore"

# ステップ3: リモートの変更をpull
echo ""
echo "⬇️  リモートの変更を取得中..."
git pull origin main

# ステップ4: stashを適用（競合があれば手動解決が必要）
echo ""
echo "📂 ローカル変更を復元中..."
git stash pop

# ステップ5: 新規ファイルを追加
echo ""
echo "📝 ファイルを追加中..."
git add .gitignore
git add CLEANUP_INSTRUCTIONS.md
git add cleanup_git.sh
git add push_changes.sh
git add fix_and_push.sh

# ステップ6: コミット
echo ""
echo "💾 コミット中..."
git commit -m "chore: add comprehensive .gitignore and cleanup scripts

- Add comprehensive .gitignore with all necessary exclusions
  - Python cache and virtual environments
  - config.json and .c2n metadata (sensitive data)
  - Node.js dependencies
  - Test data and archives
  - Playwright auth and screenshots
- Add cleanup_git.sh script to remove tracked files
- Add CLEANUP_INSTRUCTIONS.md with detailed steps
- Add helper scripts (push_changes.sh, fix_and_push.sh)
- Exclude docs/archive/ from version control
- Keep config_sample.json as reference"

# ステップ7: プッシュ
echo ""
echo "⬆️  プッシュ中..."
git push origin main

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ プッシュ完了"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

