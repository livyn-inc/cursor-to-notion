#!/usr/bin/env python3

"""
notion_page_manager.py - Page management operations for cursor_to_notion tool
"""

import os
import json
import argparse
import re
from notion_client import Client
try:
    from notion_client.errors import RequestTimeoutError  # type: ignore
except Exception:
    RequestTimeoutError = None  # type: ignore
import time
from markdown_converter import convert_markdown_to_notion_blocks
from c2n_core.utils import load_config_for_folder, extract_id_from_url_strict, extract_id_from_url

# Import page components
from page.page_creator import PageCreator
from page.page_updater import PageUpdater
from page.block_manager import BlockManager

# Notion APIキーを環境変数から取得
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")

# Notionクライアントの初期化
notion = Client(auth=NOTION_TOKEN)

def _with_retry(fn, *args, **kwargs):
    """Retry wrapper for transient Notion API failures (timeouts/5xx)."""
    attempts = 5
    delay = 0.5
    for i in range(attempts):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            msg = str(e).lower()
            retriable = False
            # Known exception types
            try:
                if RequestTimeoutError and isinstance(e, RequestTimeoutError):
                    retriable = True
            except Exception:
                pass
            if ("timeout" in msg) or ("502" in msg) or ("bad gateway" in msg) or ("service unavailable" in msg) or ("temporarily" in msg):
                retriable = True
            # Try response status if available
            try:
                status = getattr(e, 'status', None) or getattr(getattr(e, 'response', None), 'status_code', None)
                if status and int(status) >= 500:
                    retriable = True
            except Exception:
                pass
            if retriable and i < attempts - 1:
                try:
                    time.sleep(delay)
                except Exception:
                    pass
                delay = min(delay * 2, 4.0)
                continue
            raise

def load_config():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return load_config_for_folder(os.getcwd(), prefer_c2n=False, script_dir=script_dir)

# Delegate to BlockManager
def clear_page_content(page_id: str):
    """ページの既存コンテンツをすべて削除する"""
    manager = BlockManager(notion)
    manager.clear_page_content(page_id)

# Delegate to PageCreator and PageUpdater
def create_or_update_notion_page(title: str, blocks: list, url: str, title_column: str = "名前", update_mode: bool = False):
    """Create or update a Notion page"""
    if update_mode:
        # Update mode: url is the page URL to update
        page_id = extract_id_from_url(url)
        if not page_id:
            raise ValueError("Invalid Notion URL provided")
        # Delegate to PageUpdater
        # ✅ FIX BUG-011: Provide root_dir and root_meta for PageUpdater
        root_dir = os.getcwd()
        root_meta = {}
        updater = PageUpdater(notion, root_dir, root_meta)
        return updater.update_page(page_id, title, blocks)
    else:
        # Create mode: url is the parent URL
        parent_url = url
        # Delegate to PageCreator
        # For standalone usage, provide minimal root_dir and root_meta
        root_dir = os.getcwd()
        root_meta = {}
        creator = PageCreator(notion, root_dir, root_meta)
        return creator.create_page(title, blocks, parent_url)

# Delegate to BlockManager
def _split_long_rich_text(rich_text: list, max_len: int = 1900) -> list:
    """Split any rich_text entry whose text.content exceeds Notion's 2000 chars limit."""
    manager = BlockManager(notion)
    return manager.split_long_rich_text(rich_text, max_len)

# Delegate to BlockManager
def _normalize_long_text_blocks(blocks: list) -> list:
    """Backward-compatible no-op wrapper. Kept for legacy callers."""
    manager = BlockManager(notion)
    return manager.normalize_long_text_blocks(blocks)

# Delegate to BlockManager
def _expand_block_for_limits(block: dict) -> list:
    """Expand a single block to satisfy Notion limits"""
    manager = BlockManager(notion)
    return manager.expand_block_for_limits(block)

# Delegate to BlockManager
def append_blocks_with_table_support(parent_id: str, blocks: list) -> None:
    """page直下にブロックを追加しつつ、table_rowはtableブロックに対してのみ追加する"""
    manager = BlockManager(notion)
    manager.append_blocks_with_table_support(parent_id, blocks)

def extract_url_from_markdown(markdown_content: str) -> str:
    url_match = re.search(r"//url:(https://www\.notion\.so/[^\s]+)", markdown_content)
    if url_match:
        return url_match.group(1)
    return None


def main():
    print("スクリプトを開始します")
    config = load_config()
    default_parent_url = config.get('default_parent_url', '')
    default_title_column = config.get('default_title_column', '名前')

    parser = argparse.ArgumentParser(description="Convert Markdown file to Notion page or update existing page")
    parser.add_argument("file", help="Path to the Markdown file")
    parser.add_argument("url", nargs='?', default=default_parent_url, help="URL of the parent page/database or the page to update")
    parser.add_argument("-t", "--title", help="Title for the Notion page (default: Markdown filename without extension)")
    parser.add_argument("-c", "--column", default=default_title_column, help=f"Name of the title column for database (default: '{default_title_column}')")
    args = parser.parse_args()

    print(f"Markdownファイルを読み込みます: {args.file}")
    try:
        with open(args.file, "r", encoding="utf-8") as f:
            markdown_content = f.read()
        print("Markdownファイルの読み込みが完了しました")
    except FileNotFoundError:
        print(f"エラー: ファイル '{args.file}' が見つかりません。")
        return
    except Exception as e:
        print(f"エラー: ファイルの読み込み中に問題が発生しました: {e}")
        return

    # Markdownの末尾からURLを抽出
    update_url = extract_url_from_markdown(markdown_content)
    
    # URLが見つかった場合は更新モード、そうでない場合は新規作成モード
    if update_url:
        print(f"更新モード: {update_url}")
        parent_url = update_url
        update_mode = True
    else:
        print("新規作成モード")
        update_mode = False
        parent_url = args.url
        if not parent_url:
            print("エラー: 親ページまたはデータベースのURLが指定されていません。コマンドラインで指定するか、config.jsonファイルに設定してください。")
            return

    print("Markdownの変換を開始します")
    # URLの行を除いてからブロックに変換
    markdown_content = re.sub(r"\n//url:https://www\.notion\.so/[^\s]+", "", markdown_content)
    blocks = convert_markdown_to_notion_blocks(markdown_content)
    print("Markdownの変換が完了しました")

    # タイトルが指定されていない場合、Markdownファイルの名前を使用
    if args.title is None:
        args.title = os.path.splitext(os.path.basename(args.file))[0]

    try:
        page_url = create_or_update_notion_page(args.title, blocks, parent_url, args.column, update_mode=update_mode)
        if update_mode:
            print(f"���ージが更新されました: {page_url}")
        else:
            print(f"新しいページが作成されました: {page_url}")
    except Exception as e:
        print(f"エラー: Notionページの作成/更新中に問題が発生しました: {e}")

if __name__ == "__main__":
    main()