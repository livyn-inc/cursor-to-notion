"""Cache helpers (.c2n/.cache.json)."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, MutableMapping, Optional

__all__ = [
    "CacheManager", 
    "_cache_path", 
    "_load_cache", 
    "_save_cache",
    "clear_cache_file",
]


def _cache_path(target: str) -> str:
    return os.path.join(target, '.c2n', '.cache.json')


def _load_cache(target: str) -> Dict[str, Any]:
    try:
        path = _cache_path(target)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as fh:
                return json.load(fh) or {}
    except Exception:
        pass
    return {}


def _save_cache(target: str, data: Dict[str, Any]) -> None:
    try:
        os.makedirs(os.path.join(target, '.c2n'), exist_ok=True)
        path = _cache_path(target)
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(data or {}, fh, ensure_ascii=False, indent=2)
    except Exception:
        pass


def clear_cache_file(target: str) -> bool:
    """Clear cache file completely (useful for IMP-008 resolution)."""
    try:
        path = _cache_path(target)
        if os.path.exists(path):
            os.remove(path)
            return True
    except Exception:
        pass
    return False


class CacheManager:
    """High-level accessor for .c2n/.cache.json"""

    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self._data: Optional[Dict[str, Any]] = None
        self._dirty: bool = False

    # ------------------------------------------------------------------
    # basic lifecycle
    # ------------------------------------------------------------------
    def load(self) -> Dict[str, Any]:
        if self._data is None:
            # copy so in-memory mutations do not leak into callers that reuse dicts
            self._data = dict(_load_cache(self.root_dir))
        return self._data

    @property
    def data(self) -> Dict[str, Any]:
        return self.load()

    def save(self, force: bool = False) -> None:
        if force or self._dirty:
            _save_cache(self.root_dir, self.data)
            self._dirty = False

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _get_section(self, key: str, *, default: Any) -> Any:
        data = self.data
        value = data.get(key)
        if isinstance(default, dict):
            if not isinstance(value, MutableMapping):
                value = dict(default)
                data[key] = value
                self._dirty = True
            return value
        if isinstance(default, list):
            if not isinstance(value, list):
                value = list(default)
                data[key] = value
                self._dirty = True
            return value
        if value is None:
            data[key] = default
            self._dirty = True
            return default
        return value

    # ------------------------------------------------------------------
    # remote snapshot / diff detection helpers
    # ------------------------------------------------------------------
    def get_remote_snapshot(self) -> Dict[str, Any]:
        return self._get_section('remote_tree_snapshot', default={})

    def set_remote_snapshot(self, snapshot: Dict[str, Any]) -> None:
        self.data['remote_tree_snapshot'] = dict(snapshot)
        self._dirty = True

    # ------------------------------------------------------------------
    # known page ids helpers
    # ------------------------------------------------------------------
    def get_known_page_ids(self) -> List[str]:
        return self._get_section('known_page_ids', default=[])

    def set_known_page_ids(self, ids: List[str]) -> None:
        self.data['known_page_ids'] = list(ids)
        self._dirty = True

    def add_known_page_id(self, pid: str) -> None:
        ids = self.get_known_page_ids()
        if pid not in ids:
            ids.append(pid)
            self._dirty = True

    # ------------------------------------------------------------------
    # directory / file snapshot helpers (used by push)
    # ------------------------------------------------------------------
    def get_dir_snapshot(self) -> Dict[str, Any]:
        return self._get_section('dir_snapshot', default={})

    def set_dir_snapshot(self, snapshot: Dict[str, Any]) -> None:
        self.data['dir_snapshot'] = dict(snapshot)
        self._dirty = True

    def get_file_snapshot(self) -> Dict[str, Any]:
        return self._get_section('file_snapshot', default={})

    def set_file_snapshot(self, snapshot: Dict[str, Any]) -> None:
        self.data['file_snapshot'] = dict(snapshot)
        self._dirty = True

    # ------------------------------------------------------------------
    # misc helpers
    # ------------------------------------------------------------------
    def get_probe(self) -> Dict[str, Any]:
        return self._get_section('probe', default={})

    def update_probe(self, **kwargs: Any) -> None:
        probe = self.get_probe()
        changed = False
        for key, value in kwargs.items():
            if probe.get(key) != value:
                probe[key] = value
                changed = True
        if changed:
            self._dirty = True

    def ensure_saved(self) -> None:
        """Persist in-memory state if dirty."""
        self.save()

    @property
    def cache_path(self) -> str:
        return _cache_path(self.root_dir)

    # ------------------------------------------------------------------
    # cache management helpers
    # ------------------------------------------------------------------
    def clear_cache(self) -> None:
        """Clear all cache data and save empty cache."""
        self._data = {}
        self._dirty = True
        self.save(force=True)

    def clear_section(self, section: str) -> None:
        """Clear a specific cache section."""
        if self._data is None:
            self.load()
        if section in self._data:
            del self._data[section]
            self._dirty = True

    def clear_remote_snapshot(self) -> None:
        """Clear remote snapshot cache (useful for IMP-008 resolution)."""
        self.clear_section('remote_tree_snapshot')

    def clear_known_page_ids(self) -> None:
        """Clear known page IDs cache."""
        self.clear_section('known_page_ids')

    def clear_file_snapshots(self) -> None:
        """Clear file and directory snapshots."""
        self.clear_section('file_snapshot')
        self.clear_section('dir_snapshot')

    def is_cache_valid(self) -> bool:
        """Check if cache file exists and is readable."""
        try:
            path = self.cache_path
            return os.path.exists(path) and os.access(path, os.R_OK)
        except Exception:
            return False

    def get_cache_size(self) -> int:
        """Get cache file size in bytes."""
        try:
            path = self.cache_path
            if os.path.exists(path):
                return os.path.getsize(path)
        except Exception:
            pass
        return 0
