"""Shared context building for pull commands."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .cache import CacheManager
from .config import _load_config
from .meta_io import _load_meta
from .url_resolver import URLResolver

__all__ = ["PullContext", "build_pull_context"]


@dataclass
class PullContext:
    target: str
    sync_mode: str
    create_url: Optional[str]
    root_url: Optional[str]
    meta: Dict[str, Any]
    cache_manager: CacheManager
    url_resolver: URLResolver


def build_pull_context(target: str) -> PullContext:
    target = os.path.abspath(target)
    conf_all = _load_config(target)
    sync_mode = (conf_all or {}).get("sync_mode", "hierarchy")

    cfg_path = os.path.join(target, ".c2n", "config.json")
    create_url: Optional[str] = None

    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as fh:
                conf = json.load(fh) or {}
                create_url = conf.get("repo_create_url") or conf.get("default_parent_url")
        except Exception:
            pass

    meta = _load_meta(target) or {}
    
    # Use URLResolver for unified URL resolution
    url_resolver = URLResolver(target)
    root_url = url_resolver.get_root_url()

    cache_manager = CacheManager(target)

    return PullContext(
        target=target,
        sync_mode=sync_mode,
        create_url=create_url,
        root_url=root_url,
        meta=meta,
        cache_manager=cache_manager,
        url_resolver=url_resolver,
    )
