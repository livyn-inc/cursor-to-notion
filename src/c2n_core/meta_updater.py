#!/usr/bin/env python3

"""
Metadata updater for ensuring consistent index.yaml structure
"""

import os
import time
from typing import Dict, Any, Optional, List
from pathlib import Path

from c2n_core.logging import load_yaml_file, save_yaml_file
from c2n_core.url_resolver import URLResolver


class MetaUpdater:
    """
    Updates metadata to ensure consistent index.yaml structure.
    
    This class ensures that root_page_url is always set in index.yaml,
    eliminating the inconsistency that causes test failures.
    """
    
    def __init__(self, target_dir: str):
        self.target_dir = os.path.abspath(target_dir)
        self.meta_path = os.path.join(self.target_dir, ".c2n", "index.yaml")
        self.resolver = URLResolver(target_dir)
    
    def load_meta(self) -> Dict[str, Any]:
        """Load current metadata"""
        try:
            return load_yaml_file(self.meta_path, {})
        except Exception:
            return {
                "version": 1,
                "generated_at": int(time.time()),
                "items": {},
                "ignore": []
            }
    
    def save_meta(self, meta: Dict[str, Any]) -> None:
        """Save metadata to index.yaml"""
        try:
            save_yaml_file(self.meta_path, meta)
        except Exception as e:
            print(f"Failed to save metadata: {e}")
    
    def ensure_root_page_url(self) -> bool:
        """
        Ensure root_page_url is set in index.yaml.
        
        Returns:
            True if successful, False otherwise
        """
        meta = self.load_meta()
        
        # Check if root_page_url already exists
        if meta.get('root_page_url'):
            return True
        
        # Get root URL from resolver
        root_url = self.resolver.get_root_url()
        if not root_url:
            print("❌ No root URL found to set in index.yaml")
            return False
        
        # Set root_page_url
        meta['root_page_url'] = root_url
        self.save_meta(meta)
        
        print(f"✅ Set root_page_url in index.yaml: {root_url}")
        return True
    
    def update_item_parent_urls(self) -> bool:
        """
        Update parent_url for root items to match root_page_url.
        
        Returns:
            True if successful, False otherwise
        """
        meta = self.load_meta()
        root_url = meta.get('root_page_url')
        
        if not root_url:
            print("❌ No root_page_url found in index.yaml")
            return False
        
        items = meta.get('items', {})
        updated = False
        
        for path, item in items.items():
            # Check if this is a root-level item (no parent in items)
            is_root_item = True
            for other_path, other_item in items.items():
                if other_item.get('page_url') == item.get('parent_url'):
                    is_root_item = False
                    break
            
            # Update parent_url for root items
            if is_root_item and item.get('parent_url') != root_url:
                item['parent_url'] = root_url
                updated = True
                print(f"🔧 Updated parent_url for root item: {path}")
        
        if updated:
            self.save_meta(meta)
            print("✅ Updated parent_urls for root items")
        
        return True
    
    def standardize_meta_structure(self) -> bool:
        """
        Standardize the entire metadata structure.
        
        Returns:
            True if successful, False otherwise
        """
        meta = self.load_meta()
        
        # Ensure required fields exist
        if 'version' not in meta:
            meta['version'] = 1
        
        if 'generated_at' not in meta:
            meta['generated_at'] = int(time.time())
        
        if 'items' not in meta:
            meta['items'] = {}
        
        if 'ignore' not in meta:
            meta['ignore'] = []
        
        # Ensure root_page_url exists
        if not meta.get('root_page_url'):
            root_url = self.resolver.get_root_url()
            if root_url:
                meta['root_page_url'] = root_url
                print(f"🔧 Added root_page_url: {root_url}")
            else:
                print("⚠️ No root URL found, root_page_url not set")
        
        # Update parent_urls for consistency
        self.update_item_parent_urls()
        
        # Save updated metadata
        self.save_meta(meta)
        
        print("✅ Standardized metadata structure")
        return True
    
    def validate_and_fix(self) -> bool:
        """
        Validate metadata and fix any issues found.
        
        Returns:
            True if all issues were fixed, False otherwise
        """
        print("🔍 Validating metadata structure...")
        
        # Check for issues
        issues = self.resolver.validate_url_consistency()
        
        if not issues:
            print("✅ No issues found")
            return True
        
        print(f"⚠️ Found {len(issues)} issues:")
        for issue in issues:
            print(f"   - {issue}")
        
        # Fix issues
        print("🔧 Fixing issues...")
        
        # Ensure root_page_url exists
        if not self.ensure_root_page_url():
            return False
        
        # Standardize structure
        if not self.standardize_meta_structure():
            return False
        
        # Re-validate
        issues = self.resolver.validate_url_consistency()
        if issues:
            print(f"❌ {len(issues)} issues remain after fix attempt")
            return False
        
        print("✅ All issues fixed")
        return True
    
    def print_status(self) -> None:
        """Print current metadata status"""
        meta = self.load_meta()
        
        print(f"📋 Metadata Status for: {self.target_dir}")
        print(f"   Version: {meta.get('version', 'Unknown')}")
        print(f"   Generated: {meta.get('generated_at', 'Unknown')}")
        print(f"   Root URL: {meta.get('root_page_url', 'Not set')}")
        print(f"   Items: {len(meta.get('items', {}))}")
        print(f"   Ignore: {len(meta.get('ignore', []))}")
        
        # Check for issues
        issues = self.resolver.validate_url_consistency()
        if issues:
            print(f"   Issues: {len(issues)}")
            for issue in issues:
                print(f"     - {issue}")
        else:
            print("   ✅ No issues found")


def ensure_meta_consistency(target_dir: str) -> bool:
    """
    Convenience function to ensure metadata consistency.
    
    Args:
        target_dir: Target directory path
        
    Returns:
        True if consistent, False otherwise
    """
    updater = MetaUpdater(target_dir)
    return updater.validate_and_fix()


def standardize_meta_structure(target_dir: str) -> bool:
    """
    Convenience function to standardize metadata structure.
    
    Args:
        target_dir: Target directory path
        
    Returns:
        True if successful, False otherwise
    """
    updater = MetaUpdater(target_dir)
    return updater.standardize_meta_structure()
