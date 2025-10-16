#!/bin/bash

# ===========================================================
# c2n (cursor_to_notion) インストールスクリプト
# ===========================================================

set -e

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ログ関数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# スクリプトのディレクトリを取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_ROOT/.venv"
NIT_CLI_PY="$PROJECT_ROOT/src/nit_cli.py"

echo "=========================================="
echo "c2n (cursor_to_notion) インストーラー"
echo "=========================================="
echo ""

# 1. Python環境チェック
log_info "Python環境をチェック中..."
if ! command -v python3 &> /dev/null; then
    log_error "Python3 が見つかりません。Python3をインストールしてください。"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
log_success "Python3 $PYTHON_VERSION を検出"

# 2. 仮想環境作成
log_info "仮想環境を作成中..."
if [ -d "$VENV_DIR" ]; then
    log_warning "仮想環境は既に存在します: $VENV_DIR"
    read -p "既存の仮想環境を削除して再作成しますか？ (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "既存の仮想環境を削除中..."
        rm -rf "$VENV_DIR"
    else
        log_info "既存の仮想環境を使用します"
    fi
fi

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    log_success "仮想環境を作成しました: $VENV_DIR"
fi

# 3. 依存関係インストール
log_info "依存関係をインストール中..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
REQUIREMENTS_FILE="$PROJECT_ROOT/requirements.txt"
if [ -f "$REQUIREMENTS_FILE" ]; then
    pip install -r "$REQUIREMENTS_FILE"
else
    log_warning "requirements.txt が見つかりません。最低限の依存関係をインストールします。"
    pip install notion-client pyyaml
fi

log_success "依存関係のインストール完了"

# 4. nit_cli.pyの存在確認
if [ ! -f "$NIT_CLI_PY" ]; then
    log_error "nit_cli.py が見つかりません: $NIT_CLI_PY"
    exit 1
fi

log_success "nit_cli.py を確認: $NIT_CLI_PY"

# 5. エイリアス設定
log_info "nitエイリアスを設定中..."

# シェル設定ファイルを特定
SHELL_CONFIG=""
if [ -n "$ZSH_VERSION" ]; then
    SHELL_CONFIG="$HOME/.zshrc"
elif [ -n "$BASH_VERSION" ]; then
    SHELL_CONFIG="$HOME/.bashrc"
else
    # デフォルトでzshrcを試す
    SHELL_CONFIG="$HOME/.zshrc"
fi

# エイリアス定義
NIT_ALIAS="alias nit=\"source $VENV_DIR/bin/activate && python $NIT_CLI_PY\""

# 既存のnitエイリアスをチェック
if grep -q "alias nit=" "$SHELL_CONFIG" 2>/dev/null; then
    log_warning "nitエイリアスは既に設定されています"
    read -p "既存の設定を上書きしますか？ (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # 既存のnitエイリアスを削除
        sed -i.bak '/alias nit=/d' "$SHELL_CONFIG"
        log_info "既存のnitエイリアスを削除しました"
    else
        log_info "既存の設定を保持します"
        exit 0
    fi
fi

# エイリアスを追加
echo "" >> "$SHELL_CONFIG"
echo "# c2n (cursor_to_notion) alias" >> "$SHELL_CONFIG"
echo "$NIT_ALIAS" >> "$SHELL_CONFIG"

log_success "nitエイリアスを設定しました: $SHELL_CONFIG"

# 6. 動作テスト
log_info "動作テストを実行中..."

# 一時的にエイリアスを設定
eval "$NIT_ALIAS"

# テスト実行
if nit --help > /dev/null 2>&1; then
    log_success "nitコマンドの動作テスト成功"
else
    log_error "nitコマンドの動作テスト失敗"
    exit 1
fi

# 7. 完了メッセージ
echo ""
echo "=========================================="
log_success "インストール完了！"
echo "=========================================="
echo ""
echo "使用方法:"
echo "  nit clone <notion_url> <folder>  # Notionページをクローン"
echo "  nit init <folder>                # 既存フォルダを初期化"
echo "  nit push <folder>                # Notionに同期"
echo "  nit pull <folder>                # Notionから取得"
echo "  nit status <folder>              # 状態確認"
echo ""
echo "注意:"
echo "  - 新しいターミナルセッションでnitコマンドが利用可能になります"
echo "  - または 'source $SHELL_CONFIG' で即座に有効化できます"
echo ""
echo "設定ファイル:"
echo "  - 仮想環境: $VENV_DIR"
echo "  - nit_cli.py: $NIT_CLI_PY"
echo "  - シェル設定: $SHELL_CONFIG"
echo ""

# 8. 環境変数設定の案内
echo "=========================================="
echo "環境変数設定（オプション）"
echo "=========================================="
echo ""
echo "Notion APIトークンを設定する場合:"
echo "  export NOTION_TOKEN=\"your_notion_api_key_here\""
echo ""
echo "または .env ファイルを作成:"
echo "  echo 'NOTION_TOKEN=your_notion_api_key_here' > ~/.env"
echo ""

log_success "インストールスクリプト完了！"











