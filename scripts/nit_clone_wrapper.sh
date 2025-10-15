#!/bin/bash
# Nit Clone Repository Wrapper Script
# URLのクォート問題を解決するための中間スクリプト

set -e

VENV_PYTHON="/Users/daisukemiyata/aipm_v3/Stock/programs/Tools/projects/cursor_to_notion/venv_cursor_notion/bin/python"
C2N_PATH="/Users/daisukemiyata/aipm_v3/Stock/programs/Tools/projects/cursor_to_notion/c2n.py"

NOTION_URL="$1"
CLONE_DIR="$2"
FOLDER_NAME="$3"

echo "🚀 Notionページをクローンしています..."
echo "📍 URL: $NOTION_URL"
echo "📂 保存先ディレクトリ: $CLONE_DIR"
echo "📁 フォルダ名: ${FOLDER_NAME:-（Notionページタイトルを使用）}"
echo ""

# repo cloneを実行
if [ -z "$FOLDER_NAME" ]; then
    "$VENV_PYTHON" "$C2N_PATH" repo clone "$NOTION_URL" --dir "$CLONE_DIR"
else
    "$VENV_PYTHON" "$C2N_PATH" repo clone "$NOTION_URL" --dir "$CLONE_DIR" --name "$FOLDER_NAME"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ クローン完了！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💡 次のステップ:"
echo "   Nit: Push to Notion でNotionに同期"
echo ""




