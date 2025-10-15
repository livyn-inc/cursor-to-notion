"""Shared utility helpers for config loading and URL handling."""
from __future__ import annotations

import json
import os
import re
from typing import Dict, Any, Iterable, Optional

__all__ = ["load_config_for_folder", "save_config_for_folder", "extract_id_from_url", "extract_id_from_url_strict"]


def _first_existing(paths: Iterable[str]) -> Optional[str]:
    for path in paths:
        if path and os.path.exists(path):
            return path
    return None


def load_config_for_folder(
    folder: str,
    *,
    prefer_c2n: bool = True,
    script_dir: Optional[str] = None,
    filename: str = "config.json",
) -> Dict[str, Any]:
    """Load config.json for the given folder with common fallbacks.

    Search order:
        1. <folder>/.c2n/config.json (if prefer_c2n)
        2. <folder>/config.json
        3. <script_dir>/config.json (when provided)
    Returns an empty dict when no config is found or parsing fails.
    """

    search_paths = []
    if prefer_c2n:
        search_paths.append(os.path.join(folder, ".c2n", filename))
    search_paths.append(os.path.join(folder, filename))
    if script_dir:
        search_paths.append(os.path.join(script_dir, filename))

    target = _first_existing(search_paths)
    if not target:
        return {}

    try:
        with open(target, "r", encoding="utf-8") as fh:
            return json.load(fh) or {}
    except Exception:
        return {}


def extract_id_from_url(url: str) -> Optional[str]:
    """Extract a Notion page/database UUID (32 hex) from the given URL or string."""
    if not url:
        return None
    match = re.search(r"([a-f0-9]{32}|[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})", url, re.IGNORECASE)
    if not match:
        return None
    return match.group(1).replace("-", "").lower()


def extract_id_from_url_strict(url: str) -> str:
    """Return extracted ID or empty string for callers expecting a string."""
    value = extract_id_from_url(url)
    return value or ""


def save_config_for_folder(
    folder: str,
    config: Dict[str, Any],
    *,
    filename: str = "config.json",
) -> None:
    """Persist config dictionary to <folder>/.c2n/config.json."""
    meta_dir = os.path.join(folder, ".c2n")
    os.makedirs(meta_dir, exist_ok=True)
    cfg_path = os.path.join(meta_dir, filename)
    
    # IMP-003: default_parent_urlが未設定の場合は環境変数から設定
    if not config:
        config = {}
    if 'default_parent_url' not in config or not config['default_parent_url']:
        config['default_parent_url'] = os.environ.get('NOTION_ROOT_URL', '')
    
    with open(cfg_path, "w", encoding="utf-8") as fh:
        json.dump(config, fh, ensure_ascii=False, indent=2)
