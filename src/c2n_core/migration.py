#!/usr/bin/env python3

"""
Migration script for unified URL system
Migrates existing projects from multiple URL sources to default_parent_url only
"""

import os
import json
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path

from c2n_core.logging import load_yaml_file, save_yaml_file
from c2n_core.utils import load_config_for_folder


class URLMigrationManager:
    """
    Manages migration from multiple URL sources to unified default_parent_url system
    """
    
    def __init__(self, target_dir: str):
        self.target_dir = os.path.abspath(target_dir)
        self.c2n_dir = os.path.join(self.target_dir, ".c2n")
        self.config_path = os.path.join(self.c2n_dir, "config.json")
        self.meta_path = os.path.join(self.c2n_dir, "index.yaml")
        
    def analyze_current_state(self) -> Dict[str, Any]:
        """
        Analyze current URL configuration state
        
        Returns:
            Dictionary with current state analysis
        """
        state = {
            "has_config": os.path.exists(self.config_path),
            "has_meta": os.path.exists(self.meta_path),
            "config": {},
            "meta": {},
            "url_sources": {
                "default_parent_url": None,
                "root_page_url": None,
                "first_parent_url": None,
                "env_url": os.environ.get("NOTION_ROOT_URL")
            }
        }
        
        # Load config.json
        if state["has_config"]:
            try:
                state["config"] = load_config_for_folder(self.target_dir)
                state["url_sources"]["default_parent_url"] = state["config"].get("default_parent_url")
            except Exception as e:
                state["config_error"] = str(e)
        
        # Load index.yaml
        if state["has_meta"]:
            try:
                state["meta"] = load_yaml_file(self.meta_path, {})
                state["url_sources"]["root_page_url"] = state["meta"].get("root_page_url")
                
                # Check first item's parent_url
                items = state["meta"].get("items", {})
                if items:
                    first_item = list(items.values())[0]
                    state["url_sources"]["first_parent_url"] = first_item.get("parent_url")
            except Exception as e:
                state["meta_error"] = str(e)
        
        return state
    
    def determine_migration_strategy(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine the best migration strategy based on current state
        
        Returns:
            Migration strategy with actions to take
        """
        strategy = {
            "needs_migration": False,
            "actions": [],
            "target_url": None,
            "warnings": []
        }
        
        url_sources = state["url_sources"]
        
        # Determine target URL (priority: default_parent_url > root_page_url > first_parent_url > env_url)
        if url_sources["default_parent_url"]:
            strategy["target_url"] = url_sources["default_parent_url"]
            strategy["actions"].append("Keep existing default_parent_url")
        elif url_sources["root_page_url"]:
            strategy["target_url"] = url_sources["root_page_url"]
            strategy["actions"].append("Copy root_page_url to default_parent_url")
            strategy["needs_migration"] = True
        elif url_sources["first_parent_url"]:
            strategy["target_url"] = url_sources["first_parent_url"]
            strategy["actions"].append("Copy first_parent_url to default_parent_url")
            strategy["needs_migration"] = True
        elif url_sources["env_url"]:
            strategy["target_url"] = url_sources["env_url"]
            strategy["actions"].append("Copy NOTION_ROOT_URL to default_parent_url")
            strategy["needs_migration"] = True
        else:
            strategy["warnings"].append("No URL source found - manual configuration required")
            return strategy
        
        # Check for inconsistencies
        if url_sources["root_page_url"] and url_sources["default_parent_url"]:
            if url_sources["root_page_url"] != url_sources["default_parent_url"]:
                strategy["warnings"].append(f"URL mismatch: root_page_url ({url_sources['root_page_url']}) != default_parent_url ({url_sources['default_parent_url']})")
        
        return strategy
    
    def execute_migration(self, strategy: Dict[str, Any], dry_run: bool = False) -> bool:
        """
        Execute the migration strategy
        
        Args:
            strategy: Migration strategy from determine_migration_strategy
            dry_run: If True, only show what would be done
            
        Returns:
            True if successful, False otherwise
        """
        if not strategy["target_url"]:
            print("❌ No target URL found - cannot migrate")
            return False
        
        if not strategy["needs_migration"]:
            print("✅ No migration needed - project already uses unified URL system")
            return True
        
        print(f"🔄 {'[DRY RUN] ' if dry_run else ''}Migrating to unified URL system...")
        print(f"   Target URL: {strategy['target_url']}")
        
        try:
            # Ensure .c2n directory exists
            if not dry_run:
                os.makedirs(self.c2n_dir, exist_ok=True)
            
            # Update config.json
            config = {}
            if os.path.exists(self.config_path):
                config = load_config_for_folder(self.target_dir) or {}
            
            if not dry_run:
                config["default_parent_url"] = strategy["target_url"]
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
            
            print(f"   ✅ {'Would update' if dry_run else 'Updated'} config.json")
            
            # Optionally update index.yaml to remove root_page_url (keep for legacy compatibility)
            if os.path.exists(self.meta_path):
                meta = load_yaml_file(self.meta_path, {})
                if meta.get("root_page_url") and meta["root_page_url"] != strategy["target_url"]:
                    if not dry_run:
                        # Keep root_page_url for legacy compatibility, but add a comment
                        meta["_legacy_root_page_url"] = meta["root_page_url"]
                        meta["root_page_url"] = strategy["target_url"]
                        save_yaml_file(self.meta_path, meta)
                    print(f"   ✅ {'Would update' if dry_run else 'Updated'} index.yaml")
            
            print(f"✅ {'[DRY RUN] ' if dry_run else ''}Migration completed successfully")
            return True
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            return False
    
    def migrate_project(self, dry_run: bool = False) -> bool:
        """
        Complete migration process for a project
        
        Args:
            dry_run: If True, only show what would be done
            
        Returns:
            True if successful, False otherwise
        """
        print(f"🔍 Analyzing project: {self.target_dir}")
        
        # Analyze current state
        state = self.analyze_current_state()
        
        # Determine migration strategy
        strategy = self.determine_migration_strategy(state)
        
        # Show analysis results
        print(f"\\n📋 Current State Analysis:")
        print(f"   Config exists: {state['has_config']}")
        print(f"   Meta exists: {state['has_meta']}")
        
        print(f"\\n🔗 URL Sources:")
        for source, url in state["url_sources"].items():
            status = "✅" if url else "❌"
            print(f"   {status} {source}: {url or 'Not set'}")
        
        if strategy["warnings"]:
            print(f"\\n⚠️ Warnings:")
            for warning in strategy["warnings"]:
                print(f"   - {warning}")
        
        print(f"\\n🎯 Migration Strategy:")
        for action in strategy["actions"]:
            print(f"   - {action}")
        
        if not strategy["needs_migration"]:
            return True
        
        # Execute migration
        return self.execute_migration(strategy, dry_run)


def migrate_project_to_unified_urls(target_dir: str, dry_run: bool = False) -> bool:
    """
    Migrate a project to unified URL system
    
    Args:
        target_dir: Target project directory
        dry_run: If True, only show what would be done
        
    Returns:
        True if successful, False otherwise
    """
    migrator = URLMigrationManager(target_dir)
    return migrator.migrate_project(dry_run)


def main():
    """CLI interface for migration"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate project to unified URL system")
    parser.add_argument("target_dir", help="Target project directory")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    
    args = parser.parse_args()
    
    success = migrate_project_to_unified_urls(args.target_dir, args.dry_run)
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
