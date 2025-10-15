#!/usr/bin/env python3

"""
Merge and conflict handling for nit CLI
"""

import os
import difflib
import shutil
import time
from typing import List, Tuple, Optional


class MergeHandler:
    """Handles file merging and conflict resolution"""
    
    @staticmethod
    def merge_two_way(dst_txt: str, src_txt: str) -> str:
        """Git-style conflict markers for line-level merge"""
        dst_lines = dst_txt.splitlines()
        src_lines = src_txt.splitlines()
        sm = difflib.SequenceMatcher(a=dst_lines, b=src_lines)
        out: List[str] = []
        
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'equal':
                out.extend(dst_lines[i1:i2])
            elif tag == 'replace':
                out.append('<<<<<<< LOCAL')
                out.extend(dst_lines[i1:i2])
                out.append('=======')
                out.extend(src_lines[j1:j2])
                out.append('>>>>>>> REMOTE')
            elif tag == 'delete':
                # Present only in LOCAL
                out.append('<<<<<<< LOCAL')
                out.extend(dst_lines[i1:i2])
                out.append('=======')
                # Nothing on remote side
                out.append('>>>>>>> REMOTE')
            elif tag == 'insert':
                # Present only in REMOTE → take remote
                out.extend(src_lines[j1:j2])
        
        return '\n'.join(out) + ('\n' if out else '')
    
    @staticmethod
    def apply_direct_merge(src_path: str, dst_path: str) -> str:
        """Apply direct merge and return status
        
        ✅ FIX BUG-007: Actually write files to disk (not just return status)
        """
        try:
            with open(src_path, 'r', encoding='utf-8') as f:
                src_content = f.read()
        except Exception:
            src_content = ''
        
        try:
            with open(dst_path, 'r', encoding='utf-8') as f:
                dst_content = f.read()
        except Exception:
            dst_content = ''
        
        # Determine status based on content comparison
        # Check if destination file exists (not just content)
        dst_exists = os.path.exists(dst_path)
        
        if not dst_exists and src_content:
            # ✅ FIX BUG-007: Create new file
            os.makedirs(os.path.dirname(dst_path) or '.', exist_ok=True)
            with open(dst_path, 'w', encoding='utf-8') as f:
                f.write(src_content)
            return 'ADD'
        elif dst_exists and not src_content:
            # ✅ FIX BUG-007: Delete file
            try:
                os.remove(dst_path)
            except Exception:
                pass
            return 'DELETE'
        elif dst_content == src_content:
            # No changes needed
            return 'SAME'
        elif not dst_content and not src_content:
            # Both empty
            return 'SAME'
        else:
            # Content differs - need to merge
            merged_content = MergeHandler.merge_two_way(dst_content, src_content)
            
            # ✅ FIX BUG-007: Write merged content to file
            os.makedirs(os.path.dirname(dst_path) or '.', exist_ok=True)
            with open(dst_path, 'w', encoding='utf-8') as f:
                f.write(merged_content)
            
            # Check if there are conflict markers
            if '<<<<<<<' in merged_content or '=======' in merged_content or '>>>>>>>' in merged_content:
                return 'UPDATE'
            else:
                return 'REPLACE'
    
    @staticmethod
    def read_text(path: str) -> str:
        """Read text file safely"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return ''
    
    @staticmethod
    def write_text(path: str, content: str) -> None:
        """Write text file safely"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    @staticmethod
    def apply_merge_from_pull_latest(target_folder: str) -> int:
        """Apply merge from .c2n/pull/latest to working directory"""
        pull_latest = os.path.join(target_folder, '.c2n', 'pull', 'latest')
        if not os.path.isdir(pull_latest):
            return 0
        
        applied_count = 0
        
        # Walk through pull_latest and apply changes
        for root, dirs, files in os.walk(pull_latest):
            rel_root = os.path.relpath(root, pull_latest)
            if rel_root == '.':
                target_root = target_folder
            else:
                target_root = os.path.join(target_folder, rel_root)
            
            # Ensure target directory exists
            os.makedirs(target_root, exist_ok=True)
            
            # Process files
            for file in files:
                src_file = os.path.join(root, file)
                dst_file = os.path.join(target_root, file)
                
                # Skip if source is not a regular file
                if not os.path.isfile(src_file):
                    continue
                
                # Apply merge
                merged_content = MergeHandler.apply_direct_merge(src_file, dst_file)
                MergeHandler.write_text(dst_file, merged_content)
                applied_count += 1
        
        return applied_count
    
    @staticmethod
    def prepare_pull_output_base(target_folder: str, snapshot: bool) -> str:
        """Prepare pull output base directory"""
        base = os.path.join(target_folder, '.c2n', 'pull')
        latest = os.path.join(base, 'latest')
        
        if os.path.isdir(latest):
            if snapshot:
                hist_root = os.path.join(base, 'history')
                os.makedirs(hist_root, exist_ok=True)
                dst = os.path.join(hist_root, str(int(time.time())))
                try:
                    shutil.move(latest, dst)
                except Exception:
                    pass
            else:
                try:
                    shutil.rmtree(latest, ignore_errors=True)
                except Exception:
                    pass
        
        os.makedirs(latest, exist_ok=True)
        return latest
    
    @staticmethod
    def cleanup_empty_directories(target_folder: str) -> int:
        """Clean up empty directories after merge"""
        cleaned_count = 0
        
        def remove_empty_dirs(path: str) -> bool:
            """Remove empty directories recursively"""
            nonlocal cleaned_count
            
            if not os.path.isdir(path):
                return False
            
            # Check if directory is empty
            try:
                if not os.listdir(path):
                    os.rmdir(path)
                    cleaned_count += 1
                    return True
            except Exception:
                return False
            
            # Recursively check subdirectories
            try:
                for item in os.listdir(path):
                    item_path = os.path.join(path, item)
                    if os.path.isdir(item_path):
                        if remove_empty_dirs(item_path):
                            # Try to remove this directory if it's now empty
                            try:
                                if not os.listdir(path):
                                    os.rmdir(path)
                                    cleaned_count += 1
                                    return True
                            except Exception:
                                pass
            except Exception:
                pass
            
            return False
        
        remove_empty_dirs(target_folder)
        return cleaned_count
    
    @staticmethod
    def detect_conflicts(content: str) -> List[Tuple[int, str]]:
        """Detect conflict markers in content"""
        conflicts = []
        lines = content.splitlines()
        
        for i, line in enumerate(lines):
            if line.startswith('<<<<<<<') or line.startswith('=======') or line.startswith('>>>>>>>'):
                conflicts.append((i + 1, line))
        
        return conflicts
    
    @staticmethod
    def resolve_conflicts(content: str, strategy: str = 'manual') -> str:
        """Resolve conflicts using specified strategy"""
        if strategy == 'manual':
            return content  # Return as-is for manual resolution
        
        lines = content.splitlines()
        resolved_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            if line.startswith('<<<<<<<'):
                # Start of conflict
                conflict_start = i
                i += 1
                
                # Find separator
                while i < len(lines) and not lines[i].startswith('======='):
                    i += 1
                
                if i < len(lines):
                    i += 1  # Skip separator
                    local_lines = lines[conflict_start + 1:i - 1]
                    
                    # Find end marker
                    while i < len(lines) and not lines[i].startswith('>>>>>>>'):
                        i += 1
                    
                    if i < len(lines):
                        i += 1  # Skip end marker
                        remote_lines = lines[conflict_start + len(local_lines) + 2:i - 1]
                        
                        # Apply resolution strategy
                        if strategy == 'local':
                            resolved_lines.extend(local_lines)
                        elif strategy == 'remote':
                            resolved_lines.extend(remote_lines)
                        elif strategy == 'both':
                            resolved_lines.extend(local_lines)
                            resolved_lines.extend(remote_lines)
                        else:
                            # Keep conflict markers for manual resolution
                            resolved_lines.extend(lines[conflict_start:i])
                    else:
                        resolved_lines.extend(lines[conflict_start:i])
                else:
                    resolved_lines.append(line)
                    i += 1
            else:
                resolved_lines.append(line)
                i += 1
        
        return '\n'.join(resolved_lines) + ('\n' if resolved_lines else '')
