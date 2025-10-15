#!/usr/bin/env python3

"""
Fixed nit CLI with unified URL resolution
"""

import os
import sys
import time
import argparse
from typing import Optional, Dict, Any

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from c2n_core.url_resolver import URLResolver, ensure_root_url_consistency
from c2n_core.meta_updater import MetaUpdater, ensure_meta_consistency
from c2n_core.error_improved import (
    print_user_friendly_error, print_success, 
    print_warning, print_info, print_consistency_check_results
)
from c2n_core.utils import load_config_for_folder, save_config_for_folder
from c2n_core.logging import load_yaml_file, save_yaml_file


def cmd_fix_urls(target: str) -> bool:
    """
    Fix URL consistency issues in the project.
    
    Args:
        target: Target directory path
        
    Returns:
        True if successful, False otherwise
    """
    target = os.path.abspath(target)
    
    print(f"🔧 URL整合性修復を開始: {target}")
    
    # Check if project is initialized
    meta_dir = os.path.join(target, ".c2n")
    if not os.path.exists(meta_dir):
        print_user_friendly_error(
            "プロジェクトが初期化されていません",
            "nit init を実行してプロジェクトを初期化してください",
            "url"
        )
        return False
    
    # Initialize resolver and updater
    resolver = URLResolver(target)
    updater = MetaUpdater(target)
    
    # Print current status
    print("📋 現在の状況:")
    resolver.print_status()
    
    # Check for issues
    issues = resolver.validate_url_consistency()
    if not issues:
        print_success("URL設定に問題はありません")
        return True
    
    print(f"⚠️ {len(issues)} 件の問題を発見")
    print_consistency_check_results(issues)
    
    # Fix issues
    print("🔧 問題を修復中...")
    
    # Ensure metadata consistency
    if not updater.validate_and_fix():
        print_user_friendly_error(
            "メタデータの修復に失敗しました",
            "手動で設定ファイルを確認してください",
            "url"
        )
        return False
    
    # Re-validate
    issues = resolver.validate_url_consistency()
    if issues:
        print_user_friendly_error(
            f"修復後も {len(issues)} 件の問題が残っています",
            "手動で設定ファイルを確認してください",
            "url"
        )
        return False
    
    print_success("URL整合性修復が完了しました")
    return True


def cmd_init_fixed(target: str, parent_url: str = "") -> bool:
    """
    Initialize project with improved URL handling.
    
    Args:
        target: Target directory path
        parent_url: Parent URL for the project
        
    Returns:
        True if successful, False otherwise
    """
    target = os.path.abspath(target)
    
    if not os.path.isdir(target):
        print_user_friendly_error(f"ディレクトリが見つかりません: {target}")
        return False
    
    meta_dir = os.path.join(target, ".c2n")
    cfg_path = os.path.join(meta_dir, "config.json")
    
    # Check if already initialized
    if os.path.exists(cfg_path):
        print_warning(f"プロジェクトは既に初期化されています: {cfg_path}")
        return True
    
    # Create .c2n directory
    os.makedirs(meta_dir, exist_ok=True)
    
    # Load or create config
    config = load_config_for_folder(target) or {}
    
    # Set default_parent_url if provided
    if parent_url:
        config['default_parent_url'] = parent_url
        print_info(f"デフォルト親URLを設定: {parent_url}")
    
    # Save config
    save_config_for_folder(target, {
        "repo_create_url": config.get("repo_create_url", ""),
        "default_parent_url": config.get("default_parent_url", ""),
        "default_title_column": config.get("default_title_column", "名前"),
        "pull_apply_default": config.get("pull_apply_default", True),
        "push_changed_only_default": config.get("push_changed_only_default", True),
        "no_dir_update_default": config.get("no_dir_update_default", True),
        "sync_mode": config.get("sync_mode", "hierarchy")
    })
    
    print_success(f"設定ファイルを作成: {cfg_path}")
    
    # Create .c2n_ignore
    ign_path = os.path.join(target, ".c2n_ignore")
    if not os.path.exists(ign_path):
        with open(ign_path, 'w', encoding='utf-8') as f:
            f.write('# .c2n_ignore\n')
            f.write('# /Dev/\n')
            f.write('**/__pycache__/\n')
            f.write('**/*.drawio.md\n')
        print_success(f"無視ファイルを作成: {ign_path}")
    
    # Create index.yaml with proper structure
    idx_path = os.path.join(meta_dir, "index.yaml")
    if not os.path.exists(idx_path):
        meta_data = {
            "version": 1,
            "generated_at": int(time.time()),
            "root_page_url": parent_url if parent_url else "",
            "items": {},
            "ignore": []
        }
        save_yaml_file(idx_path, meta_data)
        print_success(f"メタデータファイルを作成: {idx_path}")
    
    # Ensure consistency
    if parent_url:
        print("🔧 URL整合性を確認中...")
        if ensure_meta_consistency(target):
            print_success("URL整合性確認完了")
        else:
            print_warning("URL整合性に問題があります")
    
    return True


def cmd_status_fixed(target: str) -> bool:
    """
    Show project status with improved URL information.
    
    Args:
        target: Target directory path
        
    Returns:
        True if successful, False otherwise
    """
    target = os.path.abspath(target)
    
    # Check if project is initialized
    meta_dir = os.path.join(target, ".c2n")
    if not os.path.exists(meta_dir):
        print_user_friendly_error(
            "プロジェクトが初期化されていません",
            "nit init を実行してプロジェクトを初期化してください",
            "url"
        )
        return False
    
    # Initialize resolver
    resolver = URLResolver(target)
    
    # Print status
    resolver.print_status()
    
    # Check for issues
    issues = resolver.validate_url_consistency()
    if issues:
        print_consistency_check_results(issues)
        print("💡 修復方法: nit fix-urls .")
    else:
        print_success("プロジェクト状態: 正常")
    
    return True


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Fixed nit CLI with unified URL resolution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  nit-fixed init <folder>                    # Initialize a folder for Notion sync
  nit-fixed fix-urls <folder>                # Fix URL consistency issues
  nit-fixed status <folder>                  # Show project status
        """
    )
    
    parser.add_argument('cmd', choices=['init', 'fix-urls', 'status'],
                       help='Command to execute')
    parser.add_argument('folder', help='Target folder')
    parser.add_argument('--parent-url', help='Parent URL for init command')
    
    args = parser.parse_args()
    
    # Validate folder
    if not os.path.exists(args.folder):
        print_user_friendly_error(f"ディレクトリが見つかりません: {args.folder}")
        sys.exit(1)
    
    if not os.path.isdir(args.folder):
        print_user_friendly_error(f"パスはディレクトリではありません: {args.folder}")
        sys.exit(1)
    
    # Execute command
    success = False
    
    if args.cmd == 'init':
        success = cmd_init_fixed(args.folder, args.parent_url or "")
    elif args.cmd == 'fix-urls':
        success = cmd_fix_urls(args.folder)
    elif args.cmd == 'status':
        success = cmd_status_fixed(args.folder)
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
