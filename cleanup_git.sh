#!/bin/bash

# ============================================================
# Git クリーンアップスクリプト
# 不要なファイル・ディレクトリをリポジトリから削除
# ============================================================

set -e

cd "$(dirname "$0")"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧹 Git クリーンアップ開始"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ----
# 1. 機密情報を含む設定ファイル
# ----
echo "📝 機密情報ファイルを削除中..."
git rm -rf --cached config.json 2>/dev/null || true
echo "  ✅ config.json"

# ----
# 2. ドキュメントアーカイブ（開発履歴）
# ----
echo ""
echo "📚 ドキュメントアーカイブを削除中..."
git rm -rf --cached docs/archive/ 2>/dev/null || true
echo "  ✅ docs/archive/"

# ----
# 3. 仮想環境
# ----
echo ""
echo "🐍 仮想環境を削除中..."
git rm -rf --cached .venv/ 2>/dev/null || true
git rm -rf --cached venv/ 2>/dev/null || true
git rm -rf --cached venv_cursor_notion/ 2>/dev/null || true
echo "  ✅ .venv/"
echo "  ✅ venv/"
echo "  ✅ venv_cursor_notion/"

# ----
# 4. Node.js関連
# ----
echo ""
echo "📦 Node.js関連ファイルを削除中..."
git rm -rf --cached node_modules/ 2>/dev/null || true
git rm -rf --cached package-lock.json 2>/dev/null || true
echo "  ✅ node_modules/"
echo "  ✅ package-lock.json"

# ----
# 5. Python キャッシュ
# ----
echo ""
echo "🗑️  Python キャッシュを削除中..."
find . -type d -name "__pycache__" -exec git rm -rf --cached {} + 2>/dev/null || true
find . -type f -name "*.pyc" -exec git rm --cached {} + 2>/dev/null || true
echo "  ✅ __pycache__/"
echo "  ✅ *.pyc"

# ----
# 6. テストディレクトリ
# ----
echo ""
echo "🧪 テストディレクトリを削除中..."
git rm -rf --cached docs/archive/tests/ 2>/dev/null || true
git rm -rf --cached test_markdown_converter.py 2>/dev/null || true
echo "  ✅ docs/archive/tests/"
echo "  ✅ test_markdown_converter.py"

# ----
# 7. Playwright関連
# ----
echo ""
echo "🎭 Playwright関連ファイルを削除中..."
git rm -rf --cached .auth/ 2>/dev/null || true
git rm -rf --cached documents/11_QA実行/integration_tests/v2.1/ux_verification/test_walkthrough_*/ 2>/dev/null || true
echo "  ✅ .auth/"
echo "  ✅ test_walkthrough_*/"

# ----
# 8. スクリーンショット・画像
# ----
echo ""
echo "🖼️  スクリーンショット・画像を削除中..."
find . -type f -name "debug-*.png" -exec git rm --cached {} + 2>/dev/null || true
find . -type f -name "screenshot-*.png" -exec git rm --cached {} + 2>/dev/null || true
echo "  ✅ debug-*.png"
echo "  ✅ screenshot-*.png"

# ----
# 9. .gitignore を追加
# ----
echo ""
echo "📋 .gitignore を追加中..."
git add .gitignore
echo "  ✅ .gitignore"

# ----
# 10. 状態確認
# ----
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 変更確認"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
git status

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ クリーンアップ完了"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "次のステップ:"
echo "1. 変更内容を確認してください"
echo "2. 問題なければコミット:"
echo "   git commit -m \"chore: add comprehensive .gitignore and remove sensitive/dev files\""
echo "3. プッシュ:"
echo "   git push origin main"
echo ""

