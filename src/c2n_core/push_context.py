"""Shared context building for push/pull commands."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .cache import CacheManager
from .config import _load_config
from .meta_io import _load_meta
from .url_resolver import URLResolver

__all__ = ["PushContext", "build_push_context"]


@dataclass
class PushContext:
    target: str
    sync_mode: str
    create_url: Optional[str]
    root_url: Optional[str]
    push_changed_default: bool
    no_dir_update_default: bool
    meta: Dict[str, Any]
    cache_manager: CacheManager
    url_resolver: URLResolver


def build_push_context(target: str) -> PushContext:
    target = os.path.abspath(target)
    conf_all = _load_config(target)
    sync_mode = (conf_all or {}).get("sync_mode", "hierarchy")

    cfg_path = os.path.join(target, ".c2n", "config.json")
    create_url: Optional[str] = None
    push_changed_default = True
    no_dir_update_default = True

    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as fh:
                conf = json.load(fh) or {}
                create_url = conf.get("repo_create_url") or conf.get("default_parent_url")
                if "push_changed_only_default" in conf:
                    push_changed_default = bool(conf.get("push_changed_only_default"))
                if "no_dir_update_default" in conf:
                    no_dir_update_default = bool(conf.get("no_dir_update_default"))
        except Exception:
            pass

    meta = _load_meta(target) or {}
    
    # Use URLResolver for unified URL resolution
    url_resolver = URLResolver(target)
    root_url = url_resolver.get_root_url()

    cache_manager = CacheManager(target)

    return PushContext(
        target=target,
        sync_mode=sync_mode,
        create_url=create_url,
        root_url=root_url,
        push_changed_default=push_changed_default,
        no_dir_update_default=no_dir_update_default,
        meta=meta,
        cache_manager=cache_manager,
        url_resolver=url_resolver,
    )
