#!/bin/bash

# ============================================================
# 変更をプッシュするスクリプト
# ============================================================

set -e

cd "$(dirname "$0")"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📤 変更をプッシュします"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ステップ1: 新規ファイルをadd
echo "📝 新規ファイルを追加中..."
git add .gitignore
git add CLEANUP_INSTRUCTIONS.md
git add cleanup_git.sh
echo "  ✅ .gitignore"
echo "  ✅ CLEANUP_INSTRUCTIONS.md"
echo "  ✅ cleanup_git.sh"

# ステップ2: リモートの変更をpull
echo ""
echo "⬇️  リモートの変更を取得中..."
git pull origin main

# ステップ3: コミット
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
- Exclude docs/archive/ from version control
- Keep config_sample.json as reference"

# ステップ4: プッシュ
echo ""
echo "⬆️  プッシュ中..."
git push origin main

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ プッシュ完了"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

