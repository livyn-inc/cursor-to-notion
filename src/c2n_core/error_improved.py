#!/usr/bin/env python3

"""
Improved error handling with user-friendly messages
"""

import sys
import os
# typing imports removed as they are not used


def print_url_error(target_dir: str, error_type: str = "missing") -> None:
    """
    Print user-friendly URL error message with solutions.

    Args:
        target_dir: Target directory path
        error_type: Type of error (missing, invalid, etc.)
    """
    if error_type == "missing":
        print("""
❌ ルートURLが設定されていません

解決方法:
1. nit init を実行してプロジェクトを初期化
2. config.json に default_parent_url を設定
3. 環境変数 NOTION_ROOT_URL を設定

例:
nit init . --parent-url "https://www.notion.so/your-workspace/your-page-id"

設定ファイル例 (config.json):
{
  "default_parent_url": "https://www.notion.so/your-workspace/your-page-id"
}

環境変数例:
export NOTION_ROOT_URL="https://www.notion.so/your-workspace/your-page-id"
""")
    elif error_type == "invalid":
        print("""
❌ 無効なURL形式です

正しいURL形式:
https://www.notion.so/your-workspace/Page-Title-32文字のID

確認事項:
- URLに32文字のIDが含まれているか
- ページがNotionで正常に表示できるか
- ワークスペースの権限があるか
""")
    elif error_type == "inconsistent":
        print("""
❌ URL設定に不整合があります

解決方法:
1. メタデータを再生成
2. 設定ファイルを確認
3. 環境変数を確認

自動修復:
nit fix-urls .
""")

    print(f"💡 詳細情報: {target_dir}")


def print_user_friendly_error(message: str, suggestion: str = "", error_type: str = "general") -> None:
    """
    Print user-friendly error message with helpful suggestions.

    Args:
        message: Error message
        suggestion: Helpful suggestion
        error_type: Type of error for specific handling
    """
    print(f"❌ {message}", file=sys.stderr)

    if suggestion:
        print(f"💡 解決方法: {suggestion}", file=sys.stderr)

    if error_type == "url":
        print("""
🔧 URL関連のトラブルシューティング:
1. nit init でプロジェクトを再初期化
2. config.json の default_parent_url を確認
3. 環境変数 NOTION_ROOT_URL を設定
4. nit fix-urls で自動修復を試行
""")
    elif error_type == "permission":
        print("""
🔧 権限関連のトラブルシューティング:
1. Notion API トークンの権限を確認
2. ワークスペースのアクセス権限を確認
3. ページの共有設定を確認
""")
    elif error_type == "network":
        print("""
🔧 ネットワーク関連のトラブルシューティング:
1. インターネット接続を確認
2. プロキシ設定を確認
3. ファイアウォール設定を確認
""")


def print_success(message: str) -> None:
    """Print a success message with consistent formatting."""
    print(f"✅ {message}")


def print_warning(message: str) -> None:
    """Print a warning message with consistent formatting."""
    print(f"⚠️ {message}")


def print_info(message: str) -> None:
    """Print an info message with consistent formatting."""
    print(f"ℹ️ {message}")


def print_debug(message: str) -> None:
    """Print a debug message with consistent formatting."""
    if os.environ.get('DEBUG'):
        print(f"🐛 {message}")


def print_step(step: str, message: str) -> None:
    """Print a step message with consistent formatting."""
    print(f"📋 {step}: {message}")


def print_progress(current: int, total: int, message: str = "") -> None:
    """Print progress information."""
    percentage = (current / total) * 100 if total > 0 else 0
    print(f"📊 進捗: {current}/{total} ({percentage:.1f}%) {message}")


def print_summary(success_count: int, error_count: int, warning_count: int = 0) -> None:
    """Print operation summary."""
    total = success_count + error_count + warning_count
    if total == 0:
        print("📊 実行結果: 処理対象なし")
        return

    print(f"📊 実行結果: 成功 {success_count}, エラー {error_count}, 警告 {warning_count} (合計 {total})")

    if error_count > 0:
        print(f"❌ {error_count} 件のエラーが発生しました")
    elif warning_count > 0:
        print(f"⚠️ {warning_count} 件の警告があります")
    else:
        print("✅ すべて正常に完了しました")


def format_error_with_context(error: Exception, context: str = "") -> str:
    """
    Format error with context information.

    Args:
        error: Exception object
        context: Additional context information

    Returns:
        Formatted error message
    """
    error_msg = str(error)
    if context:
        return f"{context}: {error_msg}"
    return error_msg


def print_error_with_solution(error: Exception, solution: str, context: str = "") -> None:
    """
    Print error with solution.

    Args:
        error: Exception object
        solution: Solution suggestion
        context: Additional context
    """
    error_msg = format_error_with_context(error, context)
    print_user_friendly_error(error_msg, solution)


def print_url_validation_error(url: str, issue: str) -> None:
    """
    Print URL validation error with specific issue.

    Args:
        url: The URL that failed validation
        issue: Specific validation issue
    """
    print(f"❌ URL検証エラー: {url}")
    print(f"   問題: {issue}")

    if "32文字" in issue or "ID" in issue:
        print("""
💡 解決方法:
- Notionページの完全なURLをコピーしてください
- ブラウザのアドレスバーからURLを取得してください
- URLに32文字のIDが含まれていることを確認してください
""")
    elif "権限" in issue or "アクセス" in issue:
        print("""
💡 解決方法:
- Notion API トークンの権限を確認してください
- ワークスペースのアクセス権限を確認してください
- ページの共有設定を確認してください
""")
    elif "形式" in issue or "フォーマット" in issue:
        print("""
💡 解決方法:
- 正しいNotion URL形式を使用してください
- https://www.notion.so/ で始まるURLを使用してください
- ワークスペース名とページ名が含まれていることを確認してください
""")


def print_consistency_check_results(issues: list) -> None:
    """
    Print consistency check results.

    Args:
        issues: List of consistency issues
    """
    if not issues:
        print("✅ URL設定の整合性チェック: 問題なし")
        return

    print(f"⚠️ URL設定の整合性チェック: {len(issues)} 件の問題を発見")
    for i, issue in enumerate(issues, 1):
        print(f"   {i}. {issue}")

    print("""
💡 解決方法:
1. nit fix-urls . で自動修復を試行
2. 手動で設定ファイルを修正
3. プロジェクトを再初期化

詳細情報:
- config.json の default_parent_url を確認
- .c2n/index.yaml の root_page_url を確認
- 環境変数 NOTION_ROOT_URL を確認
""")
