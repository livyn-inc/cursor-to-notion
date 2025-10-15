#!/bin/bash
# Fixed integration test script with unified URL resolution

set -e

echo "🚀 統合テスト (URL統一版) 開始"
echo "==============================================="
echo ""

# カラー定義
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0]' # No Color

# 環境変数のチェック
if [ -z "$NOTION_TOKEN" ] || [ -z "$NOTION_ROOT_URL" ]; then
    echo -e "${RED}[ERROR]${NC} 環境変数 NOTION_TOKEN および NOTION_ROOT_URL が設定されていません。"
    echo -e "${YELLOW}💡 ヒント: setup_integration_test.sh を実行して環境変数を設定してください。${NC}"
    exit 1
fi

# Step 1: テストプロジェクト作成
echo -e "${BLUE}[Step 1/6]${NC} テストプロジェクト作成中..."
TEST_DIR="$HOME/test_c2n_url_fixed_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"
echo -e "${GREEN}✅ テストディレクトリ作成: $TEST_DIR${NC}"
echo ""

# Step 2: サンプルMarkdownファイル作成
echo -e "${BLUE}[Step 2/6]${NC} サンプルMarkdownファイル作成中..."

cat > README.md << 'EOF'
# URL統一テストプロジェクト
このプロジェクトはURL統一システムのテスト用です。

## 概要
- URL解決ロジックの統一
- index.yaml構造の標準化
- エラーメッセージの改善

## 機能
- **機能1**: 統一されたURL解決
- **機能2**: 自動整合性チェック
- **機能3**: ユーザーフレンドリーなエラー
EOF

mkdir -p docs
cat > docs/url-resolution.md << 'EOF'
---
title: URL Resolution Guide
category: Documentation
---
# URL Resolution Guide
This document explains the unified URL resolution system.

## URLResolver Class
The URLResolver class provides a single source of truth for URL resolution.

### Methods
- `get_root_url()`: Get root URL with fallback priority
- `get_page_url(file_path)`: Get page URL for specific file
- `validate_url_consistency()`: Check for consistency issues

## MetaUpdater Class
The MetaUpdater class ensures consistent index.yaml structure.

### Methods
- `ensure_root_page_url()`: Set root_page_url in index.yaml
- `standardize_meta_structure()`: Standardize entire structure
- `validate_and_fix()`: Validate and fix issues
EOF

echo -e "${GREEN}✅ 2ファイル作成完了${NC}"
echo "  - README.md"
echo "  - docs/url-resolution.md"
echo ""

# Step 3: nit init実行 (URL統一版)
echo -e "${BLUE}[Step 3/6]${NC} nit init 実行中..."
NIT_CLI_PATH="/Users/daisukemiyata/aipm_v3/Stock/programs/Tools/projects/cursor_to_notion/dev/src/nit_cli_fixed.py"

# 仮想環境をアクティベート
source /Users/daisukemiyata/aipm_v3/Stock/programs/Tools/projects/cursor_to_notion/dev/venv_cursor_notion/bin/activate

python3 "$NIT_CLI_PATH" init . --parent-url "$NOTION_ROOT_URL"

echo -e "${GREEN}✅ nit init 完了${NC}"
echo ""

# Step 4: URL整合性チェック
echo -e "${BLUE}[Step 4/6]${NC} URL整合性チェック中..."
python3 "$NIT_CLI_PATH" status .

echo -e "${GREEN}✅ URL整合性チェック完了${NC}"
echo ""

# Step 5: URL修復テスト
echo -e "${BLUE}[Step 5/6]${NC} URL修復テスト中..."
python3 "$NIT_CLI_PATH" fix-urls .

echo -e "${GREEN}✅ URL修復テスト完了${NC}"
echo ""

# Step 6: 最終状態確認
echo -e "${BLUE}[Step 6/6]${NC} 最終状態確認中..."
python3 "$NIT_CLI_PATH" status .

echo -e "${GREEN}✅ 最終状態確認完了${NC}"
echo ""

echo "📊 実行サマリー:"
echo "  テストディレクトリ: $TEST_DIR"
echo "  作成ファイル数: 2"
echo "  URL統一システム: 動作確認済み"
echo ""
echo -e "${GREEN}🎉 URL統一システム統合テストが正常に完了しました！${NC}"
echo ""
echo "💡 次のステップ:"
echo "  1. 既存のnit_cli.pyにURLResolverを統合"
echo "  2. テストスクリプトを更新"
echo "  3. ドキュメントを更新"




