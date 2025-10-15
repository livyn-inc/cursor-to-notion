#!/usr/bin/env python3

"""
Snapshot management for push operations
"""

import os
import time
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from c2n_core.cache import CacheManager


class SnapshotManager:
    """Manages file and directory snapshots for change detection"""
    
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.cache_manager = CacheManager(root_dir)
        self._file_snapshot: Dict[str, Dict[str, Any]] = {}
        self._prev_file_snapshot: Dict[str, Dict[str, Any]] = {}
        self._dir_snapshot: Dict[str, List[str]] = {}
    
    def _mtime_ns(self, path: str) -> int:
        """Get modification time in nanoseconds"""
        try:
            return int(os.path.getmtime(path) * 1_000_000_000)
        except Exception:
            return 0
    
    def _sha1_file(self, path: str) -> str:
        """Calculate SHA1 hash of file"""
        try:
            with open(path, 'rb') as f:
                return hashlib.sha1(f.read()).hexdigest()
        except Exception:
            return ''
    
    def get_file_snapshot(self, file_path: str) -> Dict[str, Any]:
        """Get current file snapshot"""
        rel_path = os.path.relpath(file_path, self.root_dir)
        
        # Check if we already have this snapshot
        if rel_path in self._file_snapshot:
            return self._file_snapshot[rel_path]
        
        # Calculate snapshot
        try:
            st = os.stat(file_path)
            mtime_ns = int(st.st_mtime_ns)
            size = int(st.st_size)
        except Exception:
            mtime_ns = self._mtime_ns(file_path)
            size = None
        
        # Check previous snapshot for optimization
        prev_snap = self._prev_file_snapshot.get(rel_path)
        if prev_snap and prev_snap.get('mtime_ns') == mtime_ns and prev_snap.get('size') == size:
            # Use cached SHA1 if mtime and size match
            sha1 = prev_snap.get('sha1', '')
        else:
            # Calculate new SHA1
            sha1 = self._sha1_file(file_path)
        
        snapshot = {
            "mtime_ns": mtime_ns,
            "size": size,
            "sha1": sha1
        }
        
        self._file_snapshot[rel_path] = snapshot
        return snapshot
    
    def get_directory_snapshot(self, dir_path: str) -> List[str]:
        """Get current directory snapshot (list of contents)"""
        rel_path = os.path.relpath(dir_path, self.root_dir)
        
        # Check if we already have this snapshot
        if rel_path in self._dir_snapshot:
            return self._dir_snapshot[rel_path]
        
        # Calculate snapshot
        try:
            contents = sorted(os.listdir(dir_path))
            # Filter out hidden files and directories
            contents = [item for item in contents if not item.startswith('.')]
        except Exception:
            contents = []
        
        self._dir_snapshot[rel_path] = contents
        return contents
    
    def has_file_changed(self, file_path: str, since_snapshot: Optional[Dict[str, Any]] = None) -> bool:
        """
        Check if file has changed since snapshot (v2.0: hash-only detection).
        
        Change detection logic:
        - Primary: SHA1 hash comparison (content-based)
        - Optimization: mtime_ns and size for quick checks
        
        Returns True only if SHA1 hash differs.
        """
        current_snapshot = self.get_file_snapshot(file_path)
        
        if since_snapshot is None:
            # Compare with previous snapshot
            rel_path = os.path.relpath(file_path, self.root_dir)
            since_snapshot = self._prev_file_snapshot.get(rel_path)
        
        if since_snapshot is None:
            return True  # No previous snapshot means new/changed
        
        # v2.0: Hash-only change detection
        # Only compare SHA1 hash for actual change detection
        current_sha1 = current_snapshot.get('sha1', '')
        previous_sha1 = since_snapshot.get('sha1', '')
        
        # If SHA1 differs, file has changed
        return current_sha1 != previous_sha1
    
    def has_directory_changed(self, dir_path: str, since_snapshot: Optional[List[str]] = None) -> bool:
        """Check if directory has changed since snapshot"""
        current_snapshot = self.get_directory_snapshot(dir_path)
        
        if since_snapshot is None:
            # Compare with previous snapshot
            rel_path = os.path.relpath(dir_path, self.root_dir)
            since_snapshot = self._dir_snapshot.get(rel_path)
        
        if since_snapshot is None:
            return True  # No previous snapshot means changed
        
        # Compare snapshots
        return current_snapshot != since_snapshot
    
    def load_previous_snapshots(self) -> None:
        """Load previous snapshots from cache"""
        try:
            cache_data = self.cache_manager.load_cache()
            self._prev_file_snapshot = cache_data.get('file_snapshot', {})
            self._dir_snapshot = cache_data.get('dir_snapshot', {})
        except Exception:
            self._prev_file_snapshot = {}
            self._dir_snapshot = {}
    
    def save_current_snapshots(self) -> None:
        """Save current snapshots to cache"""
        try:
            cache_data = self.cache_manager.load_cache()
            cache_data['file_snapshot'] = self._file_snapshot
            cache_data['dir_snapshot'] = self._dir_snapshot
            cache_data['last_snapshot_time'] = int(time.time())
            self.cache_manager.save_cache(cache_data)
        except Exception:
            pass
    
    def get_changed_files(self, file_paths: List[str]) -> List[str]:
        """Get list of changed files"""
        changed_files = []
        for file_path in file_paths:
            if self.has_file_changed(file_path):
                changed_files.append(file_path)
        return changed_files
    
    def get_changed_directories(self, dir_paths: List[str]) -> List[str]:
        """Get list of changed directories"""
        changed_dirs = []
        for dir_path in dir_paths:
            if self.has_directory_changed(dir_path):
                changed_dirs.append(dir_path)
        return changed_dirs
    
    def get_file_hash(self, file_path: str) -> str:
        """Get file hash for change detection"""
        snapshot = self.get_file_snapshot(file_path)
        return snapshot.get('sha1', '')
    
    def get_file_mtime(self, file_path: str) -> int:
        """Get file modification time"""
        snapshot = self.get_file_snapshot(file_path)
        return snapshot.get('mtime_ns', 0)
    
    def get_file_size(self, file_path: str) -> Optional[int]:
        """Get file size"""
        snapshot = self.get_file_snapshot(file_path)
        return snapshot.get('size')
    
    def is_media_file(self, file_path: str) -> bool:
        """Check if file is a media file"""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type:
            return mime_type.startswith(('image/', 'video/', 'audio/'))
        return False
    
    def get_file_type(self, file_path: str) -> str:
        """Get file type category"""
        if self.is_media_file(file_path):
            return 'media'
        elif file_path.endswith('.md'):
            return 'markdown'
        elif file_path.endswith(('.py', '.js', '.ts', '.html', '.css', '.json', '.yaml', '.yml')):
            return 'code'
        else:
            return 'text'
    
    def get_snapshot_summary(self) -> Dict[str, Any]:
        """Get summary of current snapshots"""
        return {
            "file_count": len(self._file_snapshot),
            "dir_count": len(self._dir_snapshot),
            "total_size": sum(snap.get('size', 0) for snap in self._file_snapshot.values() 
                            if snap.get('size') is not None),
            "last_snapshot_time": int(time.time())
        }
    
    def clear_snapshots(self) -> None:
        """Clear all snapshots"""
        self._file_snapshot.clear()
        self._dir_snapshot.clear()
        self._prev_file_snapshot.clear()
    
    def get_snapshot_diff(self) -> Dict[str, Any]:
        """Get diff between current and previous snapshots"""
        current_files = set(self._file_snapshot.keys())
        prev_files = set(self._prev_file_snapshot.keys())
        
        added_files = current_files - prev_files
        removed_files = prev_files - current_files
        modified_files = []
        
        for file_path in current_files & prev_files:
            if self._file_snapshot[file_path] != self._prev_file_snapshot[file_path]:
                modified_files.append(file_path)
        
        return {
            "added": list(added_files),
            "removed": list(removed_files),
            "modified": modified_files,
            "total_changes": len(added_files) + len(removed_files) + len(modified_files)
        }

