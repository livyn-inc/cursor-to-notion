#!/usr/bin/env python3

"""
Directory processing for push operations
"""

import os
import time
from typing import List, Tuple, Dict, Any, Optional
from notion_client import Client

from c2n_core.utils import extract_id_from_url_strict
from c2n_core.notion_api.icons import auto_set_page_icon as core_auto_icon
from notion_page_manager import create_or_update_notion_page  # type: ignore
from push.file_processor import FileProcessor


class DirectoryProcessor:
    """Handles directory processing for push operations"""
    
    def __init__(self, client: Client, root_dir: str, root_meta: Dict[str, Any]):
        self.client = client
        self.root_dir = root_dir
        self.root_meta = root_meta
        # Initialize FileProcessor for handling Markdown files
        self.file_processor = FileProcessor(client, root_dir, root_meta)
    
    def walk_and_upload(self, root_dir: str, root_parent_url: str, *, dry_run: bool = False, changed_only: bool = False, no_dir_update: bool = False, precount_total: Optional[int] = None) -> None:
        """Walk directory tree and upload to Notion
        
        BUG-009 Fix: 呼び出し元で create_folder_page=False を指定することで、
        ルートディレクトリの中身を直接parent_url配下に配置する
        """
        try:
            # Validate directory exists
            if not os.path.exists(root_dir):
                raise FileNotFoundError(f"Directory not found: {root_dir}")
            
            if not os.path.isdir(root_dir):
                raise NotADirectoryError(f"Path is not a directory: {root_dir}")
            
            # Validate Notion client
            if not self.client:
                raise Exception("Notion client not available")
            
            # 🔧 BUG-009 Fix: create_folder_page=False で呼び出し
            # ルートディレクトリ自体をフォルダとして作成せず、中身だけを配置
            page_url, has_changes = self.process_dir(
                root_dir, root_parent_url,
                create_folder_page=False,  # ★ 呼び出し元で制御
                dry_run=dry_run,
                changed_only=changed_only,
                no_dir_update=no_dir_update
            )
            
            # 🔧 BUG-009 Fix: root_page_urlをparent_url（project_url）に設定
            if not dry_run:
                self.root_meta['root_page_url'] = root_parent_url
            
            # For dry run, we don't actually upload but simulate the process
            if dry_run:
                print(f"Processing directory: {root_dir}")
                print(f"Parent URL: {root_parent_url}")
                print(f"Dry run: {dry_run}")
                print(f"Changed only: {changed_only}")
                print(f"No dir update: {no_dir_update}")
                print(f"Precount total: {precount_total}")
            
            # Save metadata if not dry run
            if not dry_run and has_changes:
                from c2n_core.logging import save_yaml_file
                meta_path = os.path.join(root_dir, '.c2n', 'index.yaml')
                save_yaml_file(meta_path, self.root_meta)
                
        except Exception as e:
            print(f"Error in walk_and_upload: {e}")
            raise
    
    def _get_remote_last_edited(self, page_url: str) -> Optional[int]:
        """Get remote last edited time for page"""
        # This would typically make an API call to get the last edited time
        # For now, return None as a placeholder
        return None
    
    def _auto_set_page_icon(self, page_url: str, force_update: bool = False, is_folder: bool = None) -> bool:
        """Auto-set page icon"""
        try:
            # ✅ FIX: Extract page_id from page_url before calling core_auto_icon
            page_id = extract_id_from_url_strict(page_url)
            if not page_id:
                print(f"Failed to extract page ID from URL: {page_url}")
                return False
            return core_auto_icon(self.client, page_id, force_update=force_update, is_folder=is_folder)
        except Exception as e:
            print(f"Failed to auto-set icon for {page_url}: {e}")
            return False
    
    def _update_index_page(self, page_url: str, child_links: List[Tuple[str, str]], keep_title: str = None) -> None:
        """Update index page with child links"""
        try:
            # Create index content
            index_content = f"# {keep_title or 'Index'}\n\n"
            for name, url in child_links:
                index_content += f"- [{name}]({url})\n"
            
            # Update page content
            create_or_update_notion_page(
                title=keep_title or "Index",
                blocks=[],  # Would need to convert markdown to blocks
                url=page_url,
                update_mode=True
            )
        except Exception as e:
            print(f"Failed to update index page: {e}")
    
    def _dedup_child_pages_by_title(self, page_url: str, child_names: List[str]) -> None:
        """Deduplicate child pages by title"""
        try:
            # This would implement deduplication logic
            # For now, it's a placeholder
            pass
        except Exception as e:
            print(f"Failed to deduplicate child pages: {e}")
    
    def setup_directory_page(self, dir_path: str, parent_url: str, dry_run: bool = False) -> Tuple[str, bool, bool]:
        """Set up directory page in Notion"""
        try:
            # Get directory name
            dir_name = os.path.basename(dir_path)
            
            # Import ensure_page for compatibility with tests
            from notion_push import ensure_page
            
            # Call ensure_page (this will be mocked in tests)
            page_url = ensure_page(
                parent_url,
                dir_name,
                dry_run=dry_run
            )
            
            if dry_run:
                return parent_url, False, False
            
            # Check if directory page already exists
            existing_item = self.root_meta.get("items", {}).get(dir_path)
            if existing_item and existing_item.get("page_url"):
                # Update existing page metadata
                # ✅ FIX: Fallback to current UTC time if remote_last is None
                import datetime
                remote_last = self._get_remote_last_edited(page_url)
                last_sync_value = remote_last or datetime.datetime.now(datetime.timezone.utc).isoformat()
                self.root_meta["items"][dir_path].update({
                    "local_mtime_ns": int(time.time() * 1_000_000_000),
                    "remote_last_edited": remote_last,
                    "last_sync_at": last_sync_value,
                    "updated_at": int(time.time()),
                })
                
                # Auto-set icon
                self._auto_set_page_icon(page_url, force_update=False, is_folder=True)
                
                return page_url, False, True
            else:
                if page_url:
                    # Auto-set icon
                    self._auto_set_page_icon(page_url, force_update=False, is_folder=True)
                    
                    # Update metadata
                    # ✅ FIX: Fallback to current UTC time if remote_last is None
                    import datetime
                    remote_last_new_dir = self._get_remote_last_edited(page_url)
                    last_sync_value_new_dir = remote_last_new_dir or datetime.datetime.now(datetime.timezone.utc).isoformat()
                    self.root_meta.setdefault("items", {})
                    self.root_meta["items"][dir_path] = {
                        "type": "directory",
                        "title": dir_name,
                        "page_url": page_url,
                        "page_id": extract_id_from_url_strict(page_url),
                        "parent_url": parent_url,
                        "local_mtime_ns": int(time.time() * 1_000_000_000),
                        "remote_last_edited": remote_last_new_dir,
                        "last_sync_at": last_sync_value_new_dir,
                        "updated_at": int(time.time()),
                    }
                
                return page_url, True, False
                
        except Exception as e:
            print(f"Failed to setup directory page for {dir_path}: {e}")
            # Re-raise the exception for error handling tests
            raise
    
    def get_directory_contents(self, dir_path: str) -> Tuple[List[str], List[str]]:
        """Get directory contents (subdirectories and files)"""
        try:
            # Get cached contents from snapshot
            from .snapshot_manager import SnapshotManager
            snapshot_manager = SnapshotManager(self.root_dir)
            cached_contents = snapshot_manager.get_directory_snapshot(dir_path)
            
            if cached_contents:
                # Filter out hidden files and directories
                dirs = [item for item in cached_contents if os.path.isdir(os.path.join(dir_path, item)) and not item.startswith('.')]
                
                # ✅ v2.1: 画像ファイルを一時的に除外（将来的に復活する可能性あり）
                IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp', '.ico', '.tiff', '.tif'}
                files = [item for item in cached_contents 
                        if os.path.isfile(os.path.join(dir_path, item)) 
                        and not item.startswith('.')
                        and os.path.splitext(item.lower())[1] not in IMAGE_EXTENSIONS]  # 画像ファイルを除外
                return dirs, files
            else:
                # Fallback to directory listing
                try:
                    contents = os.listdir(dir_path)
                    dirs = [item for item in contents if os.path.isdir(os.path.join(dir_path, item)) and not item.startswith('.')]
                    
                    # ✅ v2.1: 画像ファイルを一時的に除外（将来的に復活する可能性あり）
                    IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp', '.ico', '.tiff', '.tif'}
                    files = [item for item in contents 
                            if os.path.isfile(os.path.join(dir_path, item)) 
                            and not item.startswith('.')
                            and os.path.splitext(item.lower())[1] not in IMAGE_EXTENSIONS]  # 画像ファイルを除外
                    return dirs, files
                except Exception:
                    return [], []
        except Exception as e:
            print(f"Failed to get directory contents for {dir_path}: {e}")
            return [], []
    
    def process_child_directories(self, dir_path: str, page_url: str, parent_url: str, 
                                cached_dirs: List[str], dry_run: bool = False, 
                                changed_only: bool = False, no_dir_update: bool = False) -> List[Tuple[str, str]]:
        """Process child directories recursively"""
        child_links = []
        
        for subdir in sorted(cached_dirs):
            subdir_path = os.path.join(dir_path, subdir)
            
            # Check if directory should be ignored
            if self._is_ignored(subdir_path):
                continue
            
            # Process subdirectory
            child_url, _ = self.process_dir(
                subdir_path,
                page_url or parent_url,
                dry_run=dry_run,
                changed_only=changed_only,
                no_dir_update=no_dir_update
            )
            
            if child_url:
                child_links.append((subdir, child_url))
        
        return child_links
    
    def _is_ignored(self, path: str) -> bool:
        """Check if path should be ignored"""
        # This would implement ignore pattern matching
        # For now, return False
        return False
    
    def process_dir(self, dir_path: str, parent_url: str, 
                   create_folder_page: bool = True,
                   dry_run: bool = False, 
                   changed_only: bool = False, no_dir_update: bool = False) -> Tuple[str, bool]:
        """Process directory and return (page_url, has_changes)
        
        Args:
            dir_path: ディレクトリパス
            parent_url: 親ページURL
            create_folder_page: Trueならdir_path自体のフォルダページを作成してその中に配置、
                               Falseならdir_pathの中身だけをparent_urlに直接配置
            dry_run: ドライラン
            changed_only: 変更されたファイルのみ処理
            no_dir_update: ディレクトリ更新をスキップ
        
        Returns:
            (page_url, has_changes): ページURLと変更有無
        """
        if create_folder_page:
            # 従来モード: フォルダページを作成してその中に配置
            title = os.path.basename(dir_path)
            page_url, dir_created, dir_updated = self.setup_directory_page(dir_path, parent_url, dry_run)
            target_url = page_url  # 作成したフォルダページに配置
        else:
            # BUG-009 Fix: フォルダページを作成せず、parent_urlに直接配置
            page_url = parent_url
            target_url = parent_url
        
        # Get directory contents
        cached_dirs, cached_files = self.get_directory_contents(dir_path)
        
        # Process child directories (サブディレクトリは常にフォルダページを作成)
        child_links = self.process_child_directories(
            dir_path, target_url, parent_url, cached_dirs, 
            dry_run, changed_only, no_dir_update
        )
        
        # Process files using FileProcessor
        file_links = self.file_processor.process_directory_files(
            dir_path, target_url, cached_files,
            dry_run=dry_run, changed_only=changed_only
        )
        
        # Combine directory and file links
        all_links = child_links + file_links
        
        # Check if any files were updated
        files_updated = len(file_links) > 0
        
        # Update index page if needed (フォルダページを作成した場合のみ)
        if create_folder_page and all_links and not dry_run and page_url:
            title = os.path.basename(dir_path)
            self._update_index_page(page_url, all_links, keep_title=title)
        
        # Deduplicate child pages (フォルダページを作成した場合のみ)
        if create_folder_page and not dry_run and page_url:
            try:
                self._dedup_child_pages_by_title(page_url, [name for name, _ in all_links])
            except Exception:
                pass
        
        # Return results
        if create_folder_page:
            return page_url, (dir_created or dir_updated or files_updated)
        else:
            return page_url, files_updated
    
    def process_directory(self, dir_path: str, parent_url: str, 
                         create_folder_page: bool = True,
                         dry_run: bool = False, 
                         is_root: bool = False, changed_only: bool = False, no_dir_update: bool = False) -> Tuple[str, bool]:
        """Process directory and return (page_url, has_changes) - alias for process_dir"""
        return self.process_dir(dir_path, parent_url, create_folder_page, dry_run, changed_only, no_dir_update)
    
    def create_directory_structure(self, dir_path: str, parent_url: str, dry_run: bool = False) -> str:
        """Create directory structure in Notion"""
        try:
            # Get relative path from root
            rel_path = os.path.relpath(dir_path, self.root_dir)
            path_parts = rel_path.split(os.sep)
            
            current_url = parent_url
            
            # Create each level of the directory structure
            for i, part in enumerate(path_parts):
                if part == '.':
                    continue
                
                current_path = os.path.join(self.root_dir, *path_parts[:i+1])
                page_url, _, _ = self.setup_directory_page(current_path, current_url, dry_run)
                
                if page_url:
                    current_url = page_url
                else:
                    break
            
            return current_url
        except Exception as e:
            print(f"Failed to create directory structure: {e}")
            return parent_url
    
    def update_directory_metadata(self, dir_path: str, page_url: str) -> None:
        """Update directory metadata"""
        try:
            # ✅ FIX: Fallback to current UTC time if remote_last is None
            import datetime
            remote_last_meta = self._get_remote_last_edited(page_url)
            last_sync_value_meta = remote_last_meta or datetime.datetime.now(datetime.timezone.utc).isoformat()
            # Update metadata for directory
            self.root_meta.setdefault("items", {})
            self.root_meta["items"][dir_path] = {
                "type": "directory",
                "title": os.path.basename(dir_path),
                "page_url": page_url,
                "page_id": extract_id_from_url_strict(page_url),
                "parent_url": page_url,
                "local_mtime_ns": int(time.time() * 1_000_000_000),
                "remote_last_edited": remote_last_meta,
                "last_sync_at": last_sync_value_meta,
                "updated_at": int(time.time()),
            }
        except Exception as e:
            print(f"Failed to update directory metadata: {e}")
    
    def get_directory_children(self, dir_path: str) -> List[str]:
        """Get list of child directories"""
        try:
            contents = os.listdir(dir_path)
            return [item for item in contents if os.path.isdir(os.path.join(dir_path, item)) and not item.startswith('.')]
        except Exception:
            return []
    
    def get_directory_files(self, dir_path: str) -> List[str]:
        """Get list of files in directory"""
        try:
            contents = os.listdir(dir_path)
            return [item for item in contents if os.path.isfile(os.path.join(dir_path, item)) and not item.startswith('.')]
        except Exception:
            return []
    
    def is_directory_empty(self, dir_path: str) -> bool:
        """Check if directory is empty"""
        try:
            contents = os.listdir(dir_path)
            return len(contents) == 0
        except Exception:
            return True
    
    def create_directory_index(self, dir_path: str, page_url: str, child_links: List[Tuple[str, str]]) -> None:
        """Create directory index page"""
        try:
            dir_name = os.path.basename(dir_path)
            
            # Create index content
            index_content = f"# {dir_name}\n\n"
            for name, url in child_links:
                index_content += f"- [{name}]({url})\n"
            
            # Update page with index content
            create_or_update_notion_page(
                title=dir_name,
                blocks=[],  # Would need to convert markdown to blocks
                url=page_url,
                update_mode=True
            )
        except Exception as e:
            print(f"Failed to create directory index: {e}")
    
    def sync_directory_structure(self, dir_path: str, parent_url: str, dry_run: bool = False) -> str:
        """Sync directory structure with Notion"""
        try:
            # Get directory name
            dir_name = os.path.basename(dir_path)
            
            # Check if directory page exists
            existing_item = self.root_meta.get("items", {}).get(dir_path)
            if existing_item and existing_item.get("page_url"):
                return existing_item["page_url"]
            
            # Create new directory page
            page_url = create_or_update_notion_page(
                title=dir_name,
                blocks=[],
                url=parent_url,
                update_mode=False
            )
            
            if page_url:
                # Update metadata
                self.update_directory_metadata(dir_path, page_url)
                
                # Auto-set icon
                self._auto_set_page_icon(page_url, force_update=False, is_folder=True)
            
            return page_url
        except Exception as e:
            print(f"Failed to sync directory structure: {e}")
            return parent_url
