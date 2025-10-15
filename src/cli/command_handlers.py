#!/usr/bin/env python3

"""
Command handlers for nit CLI
"""

import argparse
import os
import json
import subprocess
import sys
import time
from typing import Optional, Dict, Any
from notion_client import Client

from c2n_core.meta import ensure_meta
from c2n_core.meta_io import _load_meta, _save_meta
from c2n_core.utils import extract_id_from_url
from c2n_core.env import _load_env_for_target
from c2n_core.error import run_subprocess_with_env, handle_subprocess_error, exit_with_error, print_error

from .config_manager import ConfigManager
from .merge_handler import MergeHandler


class CommandHandlers:
    """Handles nit CLI commands"""
    
    def __init__(self):
        self.notion_client = None
    
    def _get_notion_client(self) -> Optional[Client]:
        """Get Notion client instance"""
        if self.notion_client is None:
            token = os.environ.get('NOTION_TOKEN') or os.environ.get('NOTION_API_KEY')
            if token:
                self.notion_client = Client(auth=token)
        return self.notion_client
    
    def _load_env_for_target(self, target: str) -> None:
        """Load environment variables for target folder"""
        _load_env_for_target(target)
    
    def _extract_page_id_from_url(self, url: str) -> Optional[str]:
        """Extract page ID from URL"""
        return extract_id_from_url(url)
    
    def _get_pull_apply_default(self, target: str) -> bool:
        """Get pull apply default setting"""
        config = ConfigManager(target)
        return config.pull_apply_default
    
    def _update_last_pull_time(self, target: str, mode: str) -> None:
        """Update last pull time"""
        meta = _load_meta(target) or {}
        meta['last_pull_time'] = int(time.time())
        meta['last_pull_mode'] = mode
        _save_meta(target, meta)
    
    def handle_repo_create(self, args) -> None:
        """Handle repo create command"""
        # Create local folder
        base_dir = os.path.abspath(args.dir)
        target = os.path.join(base_dir, args.name)
        os.makedirs(target, exist_ok=True)
        
        # Create meta directory and config
        meta_dir = ensure_meta(target)
        cfg_path = os.path.join(meta_dir, 'config.json')
        with open(cfg_path, 'w', encoding='utf-8') as f:
            json.dump({
                "default_parent_url": args.parent_url,
                "default_title_column": "名前"
            }, f, ensure_ascii=False, indent=2)
        
        # Initialize repository
        self.handle_init(args)
        print(f"repo created: {target}\nparent: {args.parent_url}")
    
    def handle_repo_clone(self, args) -> None:
        """Handle repo clone command"""
        # Load environment
        self._load_env_for_target(os.getcwd())
        
        # Get Notion client
        client = self._get_notion_client()
        
        # Resolve folder name
        folder_name = args.name
        if not folder_name:
            try:
                pid = self._extract_page_id_from_url(args.root_page_url)
                if client and pid:
                    page = client.pages.retrieve(page_id=pid)
                    props = page.get('properties') or {}
                    title_prop = None
                    for v in props.values():
                        if v and v.get('type') == 'title':
                            title_prop = v
                            break
                    if title_prop:
                        arr = title_prop.get('title') or []
                        folder_name = ''.join([t.get('plain_text','') for t in arr]).strip() or 'notion_repo'
            except Exception:
                pass
        
        if not folder_name:
            folder_name = 'notion_repo'
        
        # Sanitize folder name
        try:
            import re
            folder_name = re.sub(r'[\\/:*?"<>|]', '_', folder_name)
            folder_name = folder_name.strip(' .') or 'notion_repo'
        except Exception:
            pass
        
        # Create target directory
        base_dir = os.path.abspath(args.dir)
        target = os.path.join(base_dir, folder_name)
        os.makedirs(target, exist_ok=True)
        
        # Initialize and configure
        # Create a modified args object with folder set to target
        init_args = argparse.Namespace()
        init_args.folder = target
        init_args.parent_url = getattr(args, 'parent_url', None)
        self.handle_init(init_args)
        config = ConfigManager(target)
        
        # Set root_page_url and default_parent_url
        config.root_page_url = args.root_page_url
        if getattr(args, 'parent_url', None):
            config.default_parent_url = args.parent_url
        else:
            config.default_parent_url = args.root_page_url
        
        config.save_config()
        
        # ⭐ Use the same pull logic as regular pull operations
        # This ensures consistent naming, hierarchy, and metadata structure
        print("[c2n] Executing pull operation to download all pages...")
        
        # Import pull command directly
        from nit_cli import cmd_pull
        
        # Execute pull with apply=True to download all pages
        try:
            cmd_pull(target=target, snapshot=False, apply=True)
            print(f"\n✅ Clone completed successfully!")
            print(f"   📁 Cloned to: {target}")
            print(f"   🔗 Source: {args.root_page_url}")
            print(f"\n💡 Next steps:")
            print(f"   1. cd {folder_name}")
            print(f"   2. nit status  # Check sync status")
            print(f"   3. Edit files and use 'nit push' to sync changes back to Notion")
        except Exception as e:
            print_error(f"Clone failed during pull operation: {e}")
            import traceback
            traceback.print_exc()
            return
    
    def handle_init(self, args) -> None:
        """Handle init command"""
        folder = os.path.abspath(args.folder)
        config = ConfigManager(folder)
        
        # Ensure config file exists
        config.ensure_config_file()
        
        # Set parent URL if provided
        if args.parent_url:
            config.default_parent_url = args.parent_url
            config.save_config()
        
        # Initialize meta
        ensure_meta(folder)
        
        print(f"Initialized folder: {folder}")
    
    def handle_push(self, args) -> None:
        """Handle push command"""
        folder = os.path.abspath(args.folder)
        config = ConfigManager(folder)
        
        # Get parent URL
        parent_url = args.parent_url or config.get_effective_parent_url()
        if not parent_url:
            parent_url = config.prompt_for_parent_url()
            if not parent_url:
                exit_with_error('parent URL is required (pass --parent-url or set in config.json)')
        
        # Update config if needed
        if parent_url and parent_url != config.default_parent_url:
            config.default_parent_url = parent_url
            config.save_config()
        
        # Determine changed_only setting
        if args.changed_only is None:
            changed_only = config.push_changed_only_default
        else:
            changed_only = args.changed_only
        
        # Run push
        count = self._run_folder_to_notion(
            folder,
            parent_url=parent_url,
            dryrun=False,
            log_file=None,
            changed_only=changed_only,
            no_dir_update=args.no_dir_update
        )
        
        if count is None:
            exit_with_error("Failed to convert file entries to directories")
        
        print(f"Uploaded {count} items")
    
    def handle_pull(self, args) -> None:
        """Handle pull command"""
        # Get apply argument
        apply = getattr(args, 'apply', True)
        
        # Check sync mode
        config = ConfigManager(args.folder)
        sync_mode = config.sync_mode
        
        if getattr(args, 'full', False):
            # Full sync
            print("[c2n] Full sync: pulling new pages and changed existing pages")
            
            if sync_mode == 'flat':
                self._cmd_pull(args.folder, snapshot=getattr(args, 'snapshot', False), apply=apply)
                self._update_last_pull_time(args.folder, "full-flat")
            else:
                # Hierarchy mode
                new_pages_pulled = self._cmd_pull_new_only(
                    args.folder, 
                    snapshot=getattr(args, 'snapshot', False), 
                    update_time=False, 
                    cleanup_folders=getattr(args, 'cleanup_folders', False)
                )
                existing_pages_pulled = self._cmd_pull_auto(
                    args.folder, 
                    snapshot=getattr(args, 'snapshot', False), 
                    update_time=False
                )
                
                if new_pages_pulled or existing_pages_pulled:
                    self._update_last_pull_time(args.folder, "full")
                    if apply:
                        print("--- Apply Merge (pull latest -> working tree) ---")
                        applied = MergeHandler.apply_merge_from_pull_latest(args.folder)
                        if applied == 0:
                            print("no files to merge (already up-to-date)")
                    else:
                        print("[c2n] Skipping auto-merge (--no-apply). Files are in .c2n/pull/latest/")
                else:
                    print("[c2n] No changes found in full sync")
        
        elif getattr(args, 'new_only', False):
            # New only
            pulled = self._cmd_pull_new_only(
                args.folder,
                snapshot=getattr(args, 'snapshot', False),
                cleanup_folders=True
            )
            if pulled:
                self._update_last_pull_time(args.folder, "new-only")
                if apply:
                    print("--- Apply Merge (pull latest -> working tree) ---")
                    MergeHandler.apply_merge_from_pull_latest(args.folder)
                else:
                    print("[c2n] Skipping auto-merge (--no-apply). Files are in .c2n/pull/latest/")
        else:
            # Default: changed pages only
            self._cmd_pull_auto(args.folder, snapshot=getattr(args, 'snapshot', False))
    
    def handle_dryrun(self, args) -> None:
        """Handle dryrun command"""
        folder = os.path.abspath(args.folder)
        config = ConfigManager(folder)
        
        # Get parent URL
        parent_url = config.get_effective_parent_url()
        if not parent_url:
            parent_url = config.prompt_for_parent_url()
            if not parent_url:
                exit_with_error('parent URL is required (pass --parent-url or set in config.json)')
        
        # Run dryrun
        self._run_folder_to_notion(
            folder,
            parent_url=parent_url,
            dryrun=True,
            log_file=None,
            changed_only=True,
            no_dir_update=False
        )
    
    def _run_folder_to_notion(self, folder: str, parent_url: str, dryrun: bool = False, 
                             log_file: Optional[str] = None, changed_only: bool = False, 
                             no_dir_update: bool = False) -> Optional[int]:
        """Run folder_to_notion subprocess"""
        try:
            # Load environment
            self._load_env_for_target(folder)
            
            # Prepare command
            cmd = [
                sys.executable, 
                os.path.join(os.path.dirname(__file__), '..', 'notion_push.py'),
                folder,
                '--parent-url', parent_url
            ]
            
            if dryrun:
                cmd.append('--dry-run')
            if changed_only:
                cmd.append('--changed-only')
            if no_dir_update:
                cmd.append('--no-dir-update')
            
            # Run subprocess
            result = run_subprocess_with_env(cmd, cwd=folder)
            if result.returncode == 0:
                return 1  # Success
            else:
                handle_subprocess_error(result, "Failed to convert file entries to directories")
                return None
        except Exception as e:
            print_error(f"Error running folder_to_notion: {e}")
            return None
    
    def _cmd_pull(self, target: str, snapshot: bool = False, apply: bool = True) -> None:
        """Execute pull command"""
        # Import required modules
        import subprocess
        import sys
        import os
        
        # Get config
        config = ConfigManager(target)
        sync_mode = config.sync_mode
        
        if sync_mode == 'flat':
            # Flat mode implementation
            parent_url = config.root_page_url or config.default_parent_url
            if not parent_url:
                raise ValueError("Parent page URL is required for flat mode.")
            
            # Prepare output directory
            output_dir = os.path.join(target, '.c2n', 'pull', 'latest')
            os.makedirs(output_dir, exist_ok=True)
            
            # Run notion_pull.py
            cmd = [
                sys.executable,
                os.path.join(os.path.dirname(__file__), '..', 'notion_pull.py'),
                parent_url,
                '-o', output_dir,
                '--flat-mode'
            ]
            
            print('[c2n] Start: pull (flat mode) ...')
            subprocess.run(cmd, check=False)
            
            if apply:
                # Apply merge logic would go here
                pass
        else:
            # Hierarchy mode - simplified implementation
            parent_url = config.root_page_url or config.default_parent_url
            if not parent_url:
                raise ValueError("Parent page URL is required.")
            
            # Run notion_pull.py with children flag
            output_dir = os.path.join(target, '.c2n', 'pull', 'latest')
            os.makedirs(output_dir, exist_ok=True)
            
            cmd = [
                sys.executable,
                os.path.join(os.path.dirname(__file__), '..', 'notion_pull.py'),
                parent_url,
                '-o', output_dir,
                '-c'  # fetch children
            ]
            
            print('[c2n] Start: pull (hierarchy mode) ...')
            subprocess.run(cmd, check=False)
    
    def _cmd_pull_new_only(self, target: str, snapshot: bool = False, 
                          update_time: bool = True, cleanup_folders: bool = False) -> bool:
        """Execute pull new only command"""
        # Implementation would call notion_pull.py subprocess
        return False
    
    def _cmd_pull_auto(self, target: str, snapshot: bool = False, 
                      update_time: bool = True) -> bool:
        """Execute pull auto command"""
        # For clone scenario, we need to pull all content initially
        # So we'll use the same logic as _cmd_pull
        try:
            self._cmd_pull(target, snapshot=snapshot, apply=True)
            return True
        except Exception as e:
            print(f"Pull auto failed: {e}")
            return False
