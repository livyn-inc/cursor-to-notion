#!/usr/bin/env python3

"""
File processing for push operations
"""

import os
import time
from typing import List, Tuple, Dict, Any, Optional
from notion_client import Client

from c2n_core.utils import extract_id_from_url_strict
from c2n_core.notion_api.icons import auto_set_page_icon as core_auto_icon
from notion_page_manager import create_or_update_notion_page  # type: ignore
from markdown_converter import convert_markdown_to_notion_blocks  # type: ignore


class FileProcessor:
    """Handles file processing for push operations"""
    
    def __init__(self, client: Client, root_dir: str, root_meta: Dict[str, Any]):
        self.client = client
        self.root_dir = root_dir
        self.root_meta = root_meta
    
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
    
    def _read_file_content(self, file_path: str) -> str:
        """Read file content"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Failed to read file {file_path}: {e}")
            return ""
    
    def _get_file_mtime(self, file_path: str) -> int:
        """Get file modification time in nanoseconds"""
        try:
            stat = os.stat(file_path)
            return int(stat.st_mtime * 1_000_000_000)
        except Exception:
            return 0
    
    def _convert_file_to_blocks(self, file_path: str) -> List[Dict[str, Any]]:
        """Convert file content to Notion blocks"""
        try:
            content = self._read_file_content(file_path)
            if not content:
                return []
            
            # ✅ FIX: コードファイルはコードブロックとして扱う
            ext = os.path.splitext(file_path)[1].lower()
            
            # コード系ファイルのマッピング
            code_lang_map = {
                '.py': 'python',
                '.js': 'javascript',
                '.ts': 'typescript',
                '.json': 'json',
                '.sh': 'bash',
                '.yaml': 'yaml',
                '.yml': 'yaml',
                '.html': 'html',
                '.css': 'css',
                '.java': 'java',
                '.cpp': 'c++',
                '.c': 'c',
                '.go': 'go',
                '.rs': 'rust',
                '.rb': 'ruby',
                '.php': 'php',
                '.sql': 'sql',
                '.xml': 'xml',
            }
            
            # コードファイルの場合、コードブロックとして作成
            if ext in code_lang_map:
                language = code_lang_map[ext]
                # Notionのrich_textの制限対策（1800文字ごとに分割）
                chunk_size = 1800
                rich_text = []
                if content:
                    for i in range(0, len(content), chunk_size):
                        rich_text.append({
                            "type": "text",
                            "text": {"content": content[i:i + chunk_size]}
                        })
                else:
                    rich_text.append({"type": "text", "text": {"content": ""}})
                
                return [{
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": rich_text,
                        "language": language
                    }
                }]
            
            # Markdownファイルの場合、通常のMarkdown変換
            blocks = convert_markdown_to_notion_blocks(content)
            return blocks
        except Exception as e:
            print(f"Failed to convert file to blocks: {e}")
            return []
    
    def _should_update_file(self, file_path: str, existing_item: Dict[str, Any], changed_only: bool = False) -> bool:
        """Check if file should be updated"""
        if not changed_only:
            return True
        
        if not existing_item:
            return True
        
        # Check if file has been modified since last sync
        current_mtime = self._get_file_mtime(file_path)
        last_sync_str = existing_item.get("last_sync_at", None)
        
        # ✅ FIX BUG-011: Convert ISO 8601 string to Unix timestamp
        if last_sync_str:
            from datetime import datetime
            try:
                last_sync_dt = datetime.fromisoformat(last_sync_str.replace('Z', '+00:00'))
                last_sync = int(last_sync_dt.timestamp())
            except Exception:
                # Fallback: If parsing fails, assume file has changed
                return True
        else:
            last_sync = 0
        
        return current_mtime > last_sync
    
    def process_file(self, file_path: str, parent_url: str, dry_run: bool = False, 
                    changed_only: bool = False) -> Tuple[str, bool]:
        """Process file and return (page_url, has_changes)"""
        if dry_run:
            return parent_url, False
        
        try:
            # Get file name without extension
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            
            # Check if file page already exists
            existing_item = self.root_meta.get("items", {}).get(file_path)
            
            # Check if file should be updated
            if not self._should_update_file(file_path, existing_item, changed_only):
                if existing_item and existing_item.get("page_url"):
                    return existing_item["page_url"], False
                else:
                    return parent_url, False
            
            # Convert file to blocks
            blocks = self._convert_file_to_blocks(file_path)
            
            if existing_item and existing_item.get("page_url"):
                # Update existing page
                page_url = existing_item["page_url"]
                
                create_or_update_notion_page(
                    title=file_name,
                    blocks=blocks,
                    url=page_url,
                    update_mode=True
                )
                
                # Auto-set icon
                self._auto_set_page_icon(page_url, force_update=False, is_folder=False)
                
                # Update metadata
                self._update_file_metadata(file_path, page_url, parent_url)
                
                return page_url, True
            else:
                # Create new page
                page_url = create_or_update_notion_page(
                    title=file_name,
                    blocks=blocks,
                    url=parent_url,
                    update_mode=False
                )
                
                if page_url:
                    # Auto-set icon
                    self._auto_set_page_icon(page_url, force_update=False, is_folder=False)
                    
                    # Update metadata
                    self._update_file_metadata(file_path, page_url, parent_url)
                
                return page_url, True
                
        except Exception as e:
            print(f"Failed to process file {file_path}: {e}")
            return parent_url, False
    
    def _update_file_metadata(self, file_path: str, page_url: str, parent_url: str) -> None:
        """Update file metadata"""
        try:
            self.root_meta.setdefault("items", {})
            # ✅ FIX: Fallback to current UTC time if remote_last is None
            import datetime
            remote_last_file = self._get_remote_last_edited(page_url)
            last_sync_value_file = remote_last_file or datetime.datetime.now(datetime.timezone.utc).isoformat()
            self.root_meta["items"][file_path] = {
                "type": "file",
                "title": os.path.splitext(os.path.basename(file_path))[0],
                "page_url": page_url,
                "page_id": extract_id_from_url_strict(page_url),
                "parent_url": parent_url,
                "local_mtime_ns": self._get_file_mtime(file_path),
                "remote_last_edited": remote_last_file,
                "last_sync_at": last_sync_value_file,
                "updated_at": int(time.time()),
            }
        except Exception as e:
            print(f"Failed to update file metadata: {e}")
    
    def process_directory_files(self, dir_path: str, page_url: str, cached_files: List[str], 
                               dry_run: bool = False, changed_only: bool = False) -> List[Tuple[str, str]]:
        """Process files in directory"""
        file_links = []
        
        for filename in sorted(cached_files):
            file_path = os.path.join(dir_path, filename)
            
            # Check if file should be ignored
            if self._is_ignored(file_path):
                continue
            
            # Process file
            child_url, has_changes = self.process_file(
                file_path, page_url, dry_run=dry_run, changed_only=changed_only
            )
            
            if child_url and has_changes:
                file_links.append((filename, child_url))
        
        return file_links
    
    def _is_ignored(self, file_path: str) -> bool:
        """Check if file should be ignored"""
        # This would implement ignore pattern matching
        # For now, return False
        return False
    
    def get_file_content_hash(self, file_path: str) -> str:
        """Get file content hash"""
        try:
            import hashlib
            content = self._read_file_content(file_path)
            return hashlib.md5(content.encode('utf-8')).hexdigest()
        except Exception:
            return ""
    
    def is_file_binary(self, file_path: str) -> bool:
        """Check if file is binary"""
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                return b'\0' in chunk
        except Exception:
            return False
    
    def get_file_size(self, file_path: str) -> int:
        """Get file size in bytes"""
        try:
            return os.path.getsize(file_path)
        except Exception:
            return 0
    
    def create_file_page(self, file_path: str, parent_url: str, dry_run: bool = False) -> str:
        """Create file page in Notion"""
        if dry_run:
            return parent_url
        
        try:
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            blocks = self._convert_file_to_blocks(file_path)
            
            page_url = create_or_update_notion_page(
                title=file_name,
                blocks=blocks,
                url=parent_url,
                update_mode=False
            )
            
            if page_url:
                self._update_file_metadata(file_path, page_url, parent_url)
                self._auto_set_page_icon(page_url, force_update=False, is_folder=False)
            
            return page_url
        except Exception as e:
            print(f"Failed to create file page: {e}")
            return parent_url
    
    def update_file_page(self, file_path: str, page_url: str, dry_run: bool = False) -> bool:
        """Update file page in Notion"""
        if dry_run:
            return False
        
        try:
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            blocks = self._convert_file_to_blocks(file_path)
            
            create_or_update_notion_page(
                title=file_name,
                blocks=blocks,
                url=page_url,
                update_mode=True
            )
            
            # Update metadata
            self._update_file_metadata(file_path, page_url, page_url)
            
            # Auto-set icon
            self._auto_set_page_icon(page_url, force_update=False, is_folder=False)
            
            return True
        except Exception as e:
            print(f"Failed to update file page: {e}")
            return False
    
    def sync_file_with_notion(self, file_path: str, parent_url: str, dry_run: bool = False) -> str:
        """Sync file with Notion"""
        try:
            # Check if file page exists
            existing_item = self.root_meta.get("items", {}).get(file_path)
            if existing_item and existing_item.get("page_url"):
                # Update existing page
                if self.update_file_page(file_path, existing_item["page_url"], dry_run):
                    return existing_item["page_url"]
                else:
                    return parent_url
            else:
                # Create new page
                return self.create_file_page(file_path, parent_url, dry_run)
        except Exception as e:
            print(f"Failed to sync file with Notion: {e}")
            return parent_url
    
    def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """Get file metadata"""
        try:
            return {
                "path": file_path,
                "name": os.path.basename(file_path),
                "size": self.get_file_size(file_path),
                "mtime": self._get_file_mtime(file_path),
                "is_binary": self.is_file_binary(file_path),
                "content_hash": self.get_file_content_hash(file_path),
            }
        except Exception:
            return {}
    
    def validate_file(self, file_path: str) -> bool:
        """Validate file"""
        try:
            # Check if file exists
            if not os.path.isfile(file_path):
                return False
            
            # Check if file is readable
            if not os.access(file_path, os.R_OK):
                return False
            
            # Check file size (max 50MB)
            if self.get_file_size(file_path) > 50 * 1024 * 1024:
                return False
            
            return True
        except Exception:
            return False
    
    def get_supported_file_types(self) -> List[str]:
        """Get list of supported file types"""
        return [
            '.md', '.txt', '.py', '.js', '.ts', '.html', '.css', '.json', '.yaml', '.yml',
            '.xml', '.csv', '.log', '.ini', '.cfg', '.conf', '.sh', '.bash', '.zsh',
            '.sql', '.r', '.rb', '.php', '.java', '.cpp', '.c', '.h', '.hpp',
            '.go', '.rs', '.swift', '.kt', '.scala', '.clj', '.hs', '.ml', '.fs'
        ]
    
    def is_supported_file_type(self, file_path: str) -> bool:
        """Check if file type is supported"""
        try:
            _, ext = os.path.splitext(file_path)
            return ext.lower() in self.get_supported_file_types()
        except Exception:
            return False

