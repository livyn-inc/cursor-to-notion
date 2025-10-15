#!/usr/bin/env python3

"""
Unified URL resolution for cursor_to_notion tool
"""

import os
import re
from typing import Optional, Dict, Any, List
from pathlib import Path

from c2n_core.utils import load_config_for_folder, extract_id_from_url
from c2n_core.logging import load_yaml_file


class URLResolver:
    """
    Unified URL resolution for cursor_to_notion tool.
    
    This class provides a single source of truth for URL resolution,
    eliminating the confusion between root_page_url, parent_url, and default_parent_url.
    """
    
    def __init__(self, target_dir: str):
        self.target_dir = os.path.abspath(target_dir)
        self.config = self._load_config()
        self.meta = self._load_meta()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load config.json"""
        try:
            return load_config_for_folder(self.target_dir) or {}
        except Exception:
            return {}
    
    def _load_meta(self) -> Dict[str, Any]:
        """Load index.yaml"""
        meta_path = os.path.join(self.target_dir, ".c2n", "index.yaml")
        try:
            return load_yaml_file(meta_path, {})
        except Exception:
            return {}
    
    def get_project_url(self) -> str:
        """
        Get project URL (v2.1 primary method)
        
        Priority:
        1. config.json project_url
        2. config.json default_parent_url (backward compatibility)
        3. Environment variable NOTION_PROJECT_URL
        4. Environment variable NOTION_ROOT_URL (legacy)
        
        Returns:
            Project URL string
        
        Raises:
            ValueError: If no URL is configured
        """
        # 1. config.json project_url (v2.1)
        project_url = self.config.get('project_url')
        if project_url:
            return project_url
        
        # 2. Backward compatibility: default_parent_url (v2.0)
        default_parent_url = self.config.get('default_parent_url')
        if default_parent_url:
            # Auto-migrate to new format
            print("🔄 設定を v2.1 フォーマットに自動移行中...")
            self._migrate_to_v21(default_parent_url)
            return default_parent_url
        
        # 3. Environment variable NOTION_PROJECT_URL (v2.1)
        env_project_url = os.environ.get('NOTION_PROJECT_URL')
        if env_project_url:
            print("💡 環境変数 NOTION_PROJECT_URL から取得")
            return env_project_url
        
        # 4. Legacy environment variable NOTION_ROOT_URL
        env_root_url = os.environ.get('NOTION_ROOT_URL')
        if env_root_url:
            print("💡 環境変数 NOTION_ROOT_URL から取得（レガシー）")
            return env_root_url
        
        # 5. Error
        raise ValueError(
            "プロジェクトURLが設定されていません。\n\n"
            "新規プロジェクトの場合:\n"
            "  nit init . --workspace <ワークスペースURL> --name <プロジェクト名>\n\n"
            "既存プロジェクトの場合:\n"
            "  nit clone <プロジェクトURL> <ローカルフォルダ>\n\n"
            "または環境変数を設定:\n"
            "  export NOTION_PROJECT_URL=<プロジェクトURL>"
        )
    
    def _migrate_to_v21(self, url: str) -> None:
        """
        Migrate from old format to v2.1
        
        Args:
            url: The URL from default_parent_url to migrate
        """
        try:
            import datetime
            from c2n_core.utils import save_config_for_folder
            
            # Update config with v2.1 fields
            self.config['project_url'] = url
            self.config['version'] = '2.1'
            
            if 'created_at' not in self.config:
                self.config['created_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            
            # Keep default_parent_url for backward compatibility
            # (already exists in self.config)
            
            save_config_for_folder(self.target_dir, self.config)
            print("✅ v2.1 フォーマットに移行しました")
            
        except Exception as e:
            print(f"⚠️  移行時の警告: {e}")
    
    def get_root_url(self) -> Optional[str]:
        """
        Get root URL (legacy method, use get_project_url instead)
        
        This method is kept for backward compatibility.
        New code should use get_project_url().
        
        Returns:
            Root URL string or None if not found
        """
        try:
            return self.get_project_url()
        except ValueError:
            return None
    
    def get_page_url(self, file_path: str) -> Optional[str]:
        """
        Get page URL for a specific file path.
        
        Args:
            file_path: Relative file path from project root
            
        Returns:
            Page URL string or None if not found
        """
        items = self.meta.get('items', {})
        if file_path in items:
            return items[file_path].get('page_url')
        return None
    
    def get_parent_url(self, file_path: str) -> Optional[str]:
        """
        Get parent URL for a specific file path.
        
        Args:
            file_path: Relative file path from project root
            
        Returns:
            Parent URL string or None if not found
        """
        items = self.meta.get('items', {})
        if file_path in items:
            return items[file_path].get('parent_url')
        return None
    
    def ensure_root_url_in_meta(self, root_url: str) -> bool:
        """
        Ensure root_page_url is set in index.yaml.
        
        Args:
            root_url: The root URL to set
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update meta with root_page_url
            self.meta['root_page_url'] = root_url
            
            # Save back to index.yaml
            meta_path = os.path.join(self.target_dir, ".c2n", "index.yaml")
            from c2n_core.logging import save_yaml_file
            save_yaml_file(meta_path, self.meta)
            
            # Update local cache
            self.meta = self._load_meta()
            return True
            
        except Exception as e:
            print(f"Failed to update root_page_url: {e}")
            return False
    
    def validate_url_consistency(self) -> List[str]:
        """
        Validate URL consistency across the project.
        
        Returns:
            List of consistency issues found
        """
        issues = []
        
        root_url = self.get_root_url()
        if not root_url:
            issues.append("No root URL found - check default_parent_url in config.json or NOTION_ROOT_URL environment variable")
            return issues
        
        # Check if default_parent_url exists in config (primary source)
        default_parent_url = self.config.get('default_parent_url')
        if not default_parent_url:
            issues.append("default_parent_url not found in config.json")
        
        # Legacy compatibility check: warn if root_page_url exists but differs
        root_page_url = self.meta.get('root_page_url')
        if root_page_url and default_parent_url and root_page_url != default_parent_url:
            issues.append(f"Legacy root_page_url ({root_page_url}) differs from default_parent_url ({default_parent_url}) - consider migration")
        
        # Check items consistency
        items = self.meta.get('items', {})
        for path, item in items.items():
            if not item.get('page_url'):
                issues.append(f"Missing page_url for: {path}")
            
            if not item.get('parent_url'):
                issues.append(f"Missing parent_url for: {path}")
            
            # parent_url is now page-specific, not used for root resolution
            # Legacy compatibility check only
        
        return issues
    
    def get_url_hierarchy(self) -> Dict[str, Any]:
        """
        Get the complete URL hierarchy for the project.
        
        Returns:
            Dictionary containing root_url, items, and hierarchy info
        """
        root_url = self.get_root_url()
        items = self.meta.get('items', {})
        
        hierarchy = {
            'root_url': root_url,
            'items': items,
            'total_items': len(items),
            'has_root_in_meta': bool(self.meta.get('root_page_url')),
            'issues': self.validate_url_consistency()
        }
        
        return hierarchy
    
    def print_status(self) -> None:
        """Print current URL resolution status"""
        root_url = self.get_root_url()
        issues = self.validate_url_consistency()
        
        print(f"📋 URL Resolution Status for: {self.target_dir}")
        print(f"   Root URL: {root_url or 'Not found'}")
        print(f"   Items: {len(self.meta.get('items', {}))}")
        print(f"   Issues: {len(issues)}")
        
        if issues:
            print("   ⚠️ Issues found:")
            for issue in issues:
                print(f"     - {issue}")
        else:
            print("   ✅ No issues found")


def get_unified_root_url(target_dir: str) -> Optional[str]:
    """
    Convenience function to get unified root URL.
    
    Args:
        target_dir: Target directory path
        
    Returns:
        Root URL string or None if not found
    """
    resolver = URLResolver(target_dir)
    return resolver.get_root_url()


def ensure_root_url_consistency(target_dir: str) -> bool:
    """
    Ensure root URL consistency across all sources.
    
    Args:
        target_dir: Target directory path
        
    Returns:
        True if consistent, False otherwise
    """
    resolver = URLResolver(target_dir)
    
    # Get root URL from any source
    root_url = resolver.get_root_url()
    if not root_url:
        print("❌ No root URL found in any source")
        return False
    
    # Ensure it's set in index.yaml
    if not resolver.meta.get('root_page_url'):
        print(f"🔧 Setting root_page_url in index.yaml: {root_url}")
        return resolver.ensure_root_url_in_meta(root_url)
    
    # Check for other issues
    issues = resolver.validate_url_consistency()
    if issues:
        print(f"⚠️ Found {len(issues)} consistency issues:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    
    print("✅ URL consistency verified")
    return True


# Backward compatibility functions
def get_root_page_url(target_dir: str) -> Optional[str]:
    """Backward compatibility: get root page URL"""
    return get_unified_root_url(target_dir)


def get_default_parent_url(target_dir: str) -> Optional[str]:
    """Backward compatibility: get default parent URL"""
    return get_unified_root_url(target_dir)
