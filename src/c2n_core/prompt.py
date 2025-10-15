"""
Interactive prompt utilities for CLI commands.
"""
from __future__ import annotations

import os
import sys
from typing import Optional

from c2n_core.utils import extract_id_from_url

__all__ = ["prompt_for_url", "prompt_for_folder"]


def prompt_for_url(
    prompt_text: Optional[str] = None,
    allow_env_fallback: bool = True
) -> str:
    """
    Prompt user for Notion page URL with validation.
    
    Args:
        prompt_text: Custom prompt text (optional)
        allow_env_fallback: Allow fallback to NOTION_ROOT_URL env var
    
    Returns:
        Valid Notion page URL
    
    Raises:
        ValueError: If URL is invalid or not provided
    """
    if not prompt_text:
        prompt_text = """
📝 NotionルートページのURLを入力してください:
（例: https://www.notion.so/workspace/Root-abc123def456...）
"""
    
    print(prompt_text)
    print()
    url = input("> ").strip()
    
    # Fallback to environment variable
    if not url and allow_env_fallback:
        url = os.environ.get("NOTION_ROOT_URL", "")
        if url:
            print(f"💡 環境変数 NOTION_ROOT_URL から取得: {url[:50]}...")
    
    # Validation
    if not url:
        raise ValueError("URLが入力されませんでした")
    
    # URL format check
    page_id = extract_id_from_url(url)
    if not page_id:
        raise ValueError(
            f"無効なURL形式です: {url}\n"
            "正しい形式: https://www.notion.so/workspace/Page-Title-abc123def456..."
        )
    
    return url


def prompt_for_folder(
    prompt_text: Optional[str] = None,
    allow_current_dir: bool = True
) -> str:
    """
    Prompt user for folder path.
    
    Args:
        prompt_text: Custom prompt text (optional)
        allow_current_dir: Allow "." for current directory
    
    Returns:
        Valid folder path
    
    Raises:
        ValueError: If folder path is not provided
    """
    if not prompt_text:
        prompt_text = """
ローカル保存先のフォルダパスを入力してください:
（例: /Users/me/projects/my-notion）
"""
        if allow_current_dir:
            prompt_text += "（カレントディレクトリの場合は「.」を入力）\n"
    
    print(prompt_text)
    print()
    folder = input("> ").strip()
    
    # Allow current directory
    if not folder and allow_current_dir:
        folder = "."
        print("💡 カレントディレクトリを使用します")
    
    # Validation
    if not folder:
        raise ValueError("フォルダパスが入力されませんでした")
    
    # Expand path
    folder = os.path.expanduser(folder)
    folder = os.path.abspath(folder)
    
    return folder


def confirm_action(message: str, default: bool = False) -> bool:
    """
    Ask user for confirmation.
    
    Args:
        message: Confirmation message
        default: Default value if user just presses Enter
    
    Returns:
        True if user confirms, False otherwise
    """
    suffix = " [Y/n]" if default else " [y/N]"
    print(f"{message}{suffix}")
    
    response = input("> ").strip().lower()
    
    if not response:
        return default
    
    return response in ('y', 'yes', 'はい', 'ok')





