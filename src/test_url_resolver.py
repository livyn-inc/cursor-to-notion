#!/usr/bin/env python3

"""
Test script for URL resolver functionality
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from c2n_core.url_resolver import URLResolver, get_unified_root_url, ensure_root_url_consistency
from c2n_core.meta_updater import MetaUpdater, ensure_meta_consistency
# Removed unused import: print_url_error, print_consistency_check_results


def create_test_project(test_dir: str, has_default_parent_url: bool = True, has_root_url: bool = True, has_parent_url: bool = True) -> str:
    """Create a test project with configurable URL settings"""
    
    # Create .c2n directory
    c2n_dir = os.path.join(test_dir, ".c2n")
    os.makedirs(c2n_dir, exist_ok=True)
    
    # Create config.json
    config = {
        "sync_mode": "hierarchy"
    }
    
    if has_default_parent_url:
        config["default_parent_url"] = "https://www.notion.so/test-workspace/test-page-12345678901234567890123456789012"
    
    import json
    with open(os.path.join(c2n_dir, "config.json"), "w") as f:
        json.dump(config, f, indent=2)
    
    # Create index.yaml
    meta = {
        "version": 1,
        "generated_at": 1234567890,
        "items": {
            "README.md": {
                "page_id": "12345678-1234-1234-1234-123456789012",
                "page_url": "https://www.notion.so/README-12345678123412341234123456789012",
                "parent_url": "https://www.notion.so/test-workspace/test-page-12345678901234567890123456789012",
                "title": "README",
                "type": "file"
            }
        },
        "ignore": []
    }
    
    if has_root_url:
        meta["root_page_url"] = "https://www.notion.so/test-workspace/test-page-12345678901234567890123456789012"
    
    if not has_parent_url:
        meta["items"]["README.md"]["parent_url"] = ""
    
    import yaml
    with open(os.path.join(c2n_dir, "index.yaml"), "w") as f:
        yaml.dump(meta, f, default_flow_style=False)
    
    return test_dir


def test_url_resolver():
    """Test URL resolver functionality"""
    
    print("🧪 URL Resolver テスト開始")
    print("=" * 50)
    
    # Test 1: Complete configuration
    print("\n📋 Test 1: 完全な設定")
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = create_test_project(temp_dir, has_root_url=True, has_parent_url=True)
        resolver = URLResolver(test_dir)
        
        root_url = resolver.get_root_url()
        print(f"   Root URL: {root_url}")
        
        issues = resolver.validate_url_consistency()
        print(f"   Issues: {len(issues)}")
        
        if issues:
            print("   ⚠️ Issues found:")
            for issue in issues:
                print(f"     - {issue}")
        else:
            print("   ✅ No issues found")
    
    # Test 2: Missing root_page_url
    print("\n📋 Test 2: root_page_url なし")
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = create_test_project(temp_dir, has_root_url=False, has_parent_url=True)
        resolver = URLResolver(test_dir)
        
        root_url = resolver.get_root_url()
        print(f"   Root URL: {root_url}")
        
        issues = resolver.validate_url_consistency()
        print(f"   Issues: {len(issues)}")
        
        if issues:
            print("   ⚠️ Issues found:")
            for issue in issues:
                print(f"     - {issue}")
    
    # Test 3: Missing parent_url
    print("\n📋 Test 3: parent_url なし")
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = create_test_project(temp_dir, has_root_url=True, has_parent_url=False)
        resolver = URLResolver(test_dir)
        
        root_url = resolver.get_root_url()
        print(f"   Root URL: {root_url}")
        
        issues = resolver.validate_url_consistency()
        print(f"   Issues: {len(issues)}")
        
        if issues:
            print("   ⚠️ Issues found:")
            for issue in issues:
                print(f"     - {issue}")
    
    # Test 4: No configuration
    print("\n📋 Test 4: 設定なし")
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = create_test_project(temp_dir, has_root_url=False, has_parent_url=False)
        resolver = URLResolver(test_dir)
        
        root_url = resolver.get_root_url()
        print(f"   Root URL: {root_url}")
        
        issues = resolver.validate_url_consistency()
        print(f"   Issues: {len(issues)}")
        
        if issues:
            print("   ⚠️ Issues found:")
            for issue in issues:
                print(f"     - {issue}")
    
    print("\n✅ URL Resolver テスト完了")


def test_meta_updater():
    """Test meta updater functionality"""
    
    print("\n🧪 Meta Updater テスト開始")
    print("=" * 50)
    
    # Test 1: Fix missing root_page_url
    print("\n📋 Test 1: root_page_url の修復")
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = create_test_project(temp_dir, has_root_url=False, has_parent_url=True)
        updater = MetaUpdater(test_dir)
        
        print("   修復前:")
        updater.print_status()
        
        success = updater.ensure_root_page_url()
        print(f"   修復結果: {success}")
        
        print("   修復後:")
        updater.print_status()
    
    # Test 2: Standardize structure
    print("\n📋 Test 2: 構造の標準化")
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = create_test_project(temp_dir, has_root_url=False, has_parent_url=True)
        updater = MetaUpdater(test_dir)
        
        success = updater.standardize_meta_structure()
        print(f"   標準化結果: {success}")
        
        updater.print_status()
    
    # Test 3: Validate and fix
    print("\n📋 Test 3: 検証と修復")
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = create_test_project(temp_dir, has_root_url=False, has_parent_url=True)
        updater = MetaUpdater(test_dir)
        
        success = updater.validate_and_fix()
        print(f"   検証・修復結果: {success}")
        
        updater.print_status()
    
    print("\n✅ Meta Updater テスト完了")


def test_integration():
    """Test integration with existing projects"""
    
    print("\n🧪 統合テスト開始")
    print("=" * 50)
    
    # Test with existing project
    existing_project = "/Users/daisukemiyata/aipm_v3/Stock/programs/Tools/projects/cursor_to_notion/dev/docs/archive/tests/test_sample_upload"
    
    if os.path.exists(existing_project):
        print(f"\n📋 既存プロジェクトでのテスト: {existing_project}")
        
        resolver = URLResolver(existing_project)
        resolver.print_status()
        
        issues = resolver.validate_url_consistency()
        if issues:
            print("URL consistency issues found:")
            for issue in issues:
                print(f"  - {issue}")
            
            # Try to fix
            print("\n🔧 自動修復を試行...")
            updater = MetaUpdater(existing_project)
            success = updater.validate_and_fix()
            print(f"   修復結果: {success}")
            
            # Re-check
            resolver = URLResolver(existing_project)
            issues = resolver.validate_url_consistency()
            if not issues:
                print("✅ 修復成功")
            else:
                print("❌ 修復失敗")
        else:
            print("✅ 既存プロジェクトに問題なし")
    else:
        print("⚠️ 既存プロジェクトが見つかりません")
    
    print("\n✅ 統合テスト完了")


def main():
    """Main test function"""
    
    print("🚀 URL統一システム テスト開始")
    print("=" * 60)
    
    try:
        test_url_resolver()
        test_meta_updater()
        test_integration()
        
        print("\n🎉 すべてのテストが完了しました")
        
    except Exception as e:
        print(f"\n❌ テスト中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
