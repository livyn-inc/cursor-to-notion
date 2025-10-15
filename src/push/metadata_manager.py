#!/usr/bin/env python3

"""
Metadata management for push operations
"""

import os
import time
from typing import Dict, Any, Optional, List
from c2n_core.logging import load_yaml_file, save_yaml_file
from c2n_core.meta_updater import MetaUpdater


class MetadataManager:
    """Manages metadata for push operations"""
    
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.meta_dir = self._meta_dir(root_dir)
        self.meta_path = self._meta_path(root_dir)
        self.config_path = self._config_path(root_dir)
        self.meta_updater = MetaUpdater(root_dir)
    
    def _meta_dir(self, root_dir: str) -> str:
        """Get meta directory path"""
        return os.path.join(root_dir, ".c2n")
    
    def _meta_path(self, root_dir: str) -> str:
        """Get meta file path"""
        return os.path.join(self._meta_dir(root_dir), "index.yaml")
    
    def _config_path(self, root_dir: str) -> str:
        """Get config file path"""
        return os.path.join(self._meta_dir(root_dir), "config.json")
    
    def load_meta(self) -> Dict[str, Any]:
        """Load metadata from index.yaml"""
        default_data = {
            "version": 1, 
            "generated_at": int(time.time()), 
            "items": {}, 
            "ignore": []
        }
        data = load_yaml_file(self.meta_path, default_data)
        data.setdefault("items", {})
        data.setdefault("ignore", [])
        return data
    
    def save_meta(self, meta: Dict[str, Any]) -> None:
        """Save metadata to index.yaml"""
        # Use MetaUpdater to ensure consistency
        self.meta_updater.save_meta(meta)
    
    def get_item(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get metadata item for file path"""
        meta = self.load_meta()
        return meta.get("items", {}).get(file_path)
    
    def set_item(self, file_path: str, item_data: Dict[str, Any]) -> None:
        """Set metadata item for file path"""
        meta = self.load_meta()
        meta.setdefault("items", {})
        meta["items"][file_path] = item_data
        self.save_meta(meta)
    
    def remove_item(self, file_path: str) -> None:
        """Remove metadata item for file path"""
        meta = self.load_meta()
        if "items" in meta and file_path in meta["items"]:
            del meta["items"][file_path]
            self.save_meta(meta)
    
    def get_ignore_patterns(self) -> List[str]:
        """Get ignore patterns"""
        meta = self.load_meta()
        return meta.get("ignore", [])
    
    def add_ignore_pattern(self, pattern: str) -> None:
        """Add ignore pattern"""
        meta = self.load_meta()
        ignore_list = meta.setdefault("ignore", [])
        if pattern not in ignore_list:
            ignore_list.append(pattern)
            self.save_meta(meta)
    
    def remove_ignore_pattern(self, pattern: str) -> None:
        """Remove ignore pattern"""
        meta = self.load_meta()
        ignore_list = meta.get("ignore", [])
        if pattern in ignore_list:
            ignore_list.remove(pattern)
            self.save_meta(meta)
    
    def is_ignored(self, file_path: str) -> bool:
        """Check if file path matches ignore patterns"""
        import fnmatch
        ignore_patterns = self.get_ignore_patterns()
        
        # Convert to relative path for matching
        rel_path = os.path.relpath(file_path, self.root_dir)
        
        for pattern in ignore_patterns:
            if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(os.path.basename(file_path), pattern):
                return True
        return False
    
    def update_last_sync_time(self, file_path: str, sync_time: Optional[int] = None) -> None:
        """Update last sync time for file"""
        if sync_time is None:
            sync_time = int(time.time())
        
        item = self.get_item(file_path) or {}
        item["last_sync_at"] = sync_time
        item["updated_at"] = sync_time
        self.set_item(file_path, item)
    
    def get_file_snapshot(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get file snapshot data"""
        item = self.get_item(file_path)
        if item:
            return {
                "mtime_ns": item.get("local_mtime_ns"),
                "size": item.get("local_size"),
                "sha1": item.get("content_sha1"),
                "page_url": item.get("page_url"),
                "page_id": item.get("page_id")
            }
        return None
    
    def set_file_snapshot(self, file_path: str, snapshot: Dict[str, Any]) -> None:
        """Set file snapshot data"""
        item = self.get_item(file_path) or {}
        item.update({
            "type": "file",
            "title": os.path.splitext(os.path.basename(file_path))[0],
            "local_mtime_ns": snapshot.get("mtime_ns"),
            "local_size": snapshot.get("size"),
            "content_sha1": snapshot.get("sha1"),
            "page_url": snapshot.get("page_url"),
            "page_id": snapshot.get("page_id"),
            "updated_at": int(time.time())
        })
        self.set_item(file_path, item)
    
    def get_directory_snapshot(self, dir_path: str) -> Optional[Dict[str, Any]]:
        """Get directory snapshot data"""
        item = self.get_item(dir_path)
        if item:
            return {
                "mtime_ns": item.get("local_mtime_ns"),
                "page_url": item.get("page_url"),
                "page_id": item.get("page_id"),
                "children": item.get("children", [])
            }
        return None
    
    def set_directory_snapshot(self, dir_path: str, snapshot: Dict[str, Any]) -> None:
        """Set directory snapshot data"""
        item = self.get_item(dir_path) or {}
        item.update({
            "type": "directory",
            "title": os.path.basename(dir_path),
            "local_mtime_ns": snapshot.get("mtime_ns"),
            "page_url": snapshot.get("page_url"),
            "page_id": snapshot.get("page_id"),
            "children": snapshot.get("children", []),
            "updated_at": int(time.time())
        })
        self.set_item(dir_path, item)
    
    def get_remote_last_edited(self, page_url: str) -> Optional[int]:
        """Get remote last edited time for page"""
        # This would typically make an API call to get the last edited time
        # For now, return None as a placeholder
        return None
    
    def update_remote_last_edited(self, file_path: str, last_edited: int) -> None:
        """Update remote last edited time for file"""
        item = self.get_item(file_path) or {}
        item["remote_last_edited"] = last_edited
        item["last_sync_at"] = last_edited
        self.set_item(file_path, item)
    
    def get_all_items(self) -> Dict[str, Any]:
        """Get all metadata items"""
        meta = self.load_meta()
        return meta.get("items", {})
    
    def clear_items(self) -> None:
        """Clear all metadata items"""
        meta = self.load_meta()
        meta["items"] = {}
        self.save_meta(meta)
    
    def get_items_by_type(self, item_type: str) -> Dict[str, Any]:
        """Get items filtered by type"""
        all_items = self.get_all_items()
        return {path: item for path, item in all_items.items() 
                if item.get("type") == item_type}
    
    def get_items_by_page_url(self, page_url: str) -> Dict[str, Any]:
        """Get items filtered by page URL"""
        all_items = self.get_all_items()
        return {path: item for path, item in all_items.items() 
                if item.get("page_url") == page_url}
    
    def get_items_by_page_id(self, page_id: str) -> Dict[str, Any]:
        """Get items filtered by page ID"""
        all_items = self.get_all_items()
        return {path: item for path, item in all_items.items() 
                if item.get("page_id") == page_id}
    
    def get_changed_items(self, since_time: int) -> Dict[str, Any]:
        """Get items changed since specified time"""
        all_items = self.get_all_items()
        return {path: item for path, item in all_items.items() 
                if item.get("updated_at", 0) > since_time}
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get overall sync status"""
        all_items = self.get_all_items()
        total_items = len(all_items)
        synced_items = sum(1 for item in all_items.values() 
                          if item.get("page_url") and item.get("last_sync_at"))
        
        return {
            "total_items": total_items,
            "synced_items": synced_items,
            "unsynced_items": total_items - synced_items,
            "sync_percentage": (synced_items / total_items * 100) if total_items > 0 else 0
        }
    
    def ensure_consistency(self) -> bool:
        """Ensure metadata consistency using MetaUpdater"""
        return self.meta_updater.validate_and_fix()
    
    def get_root_page_url(self) -> Optional[str]:
        """Get root page URL using MetaUpdater's URLResolver"""
        return self.meta_updater.resolver.get_root_url()
    
    def set_root_page_url(self, url: str) -> None:
        """Set root page URL and ensure consistency"""
        meta = self.load_meta()
        meta['root_page_url'] = url
        self.save_meta(meta)
        # Ensure consistency after setting
        self.meta_updater.ensure_root_page_url()

