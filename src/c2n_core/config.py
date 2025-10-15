"""Configuration helpers for the c2n CLI."""
from __future__ import annotations

import json
import os
from typing import Any, Dict

__all__ = ["_load_config"]


def _load_config(target: str) -> Dict[str, Any]:
    cfg_path = os.path.join(target, ".c2n", "config.json")
    config: Dict[str, Any] = {}
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as fh:
                config = json.load(fh) or {}
        except Exception:
            pass
    if "sync_mode" not in config:
        config["sync_mode"] = "hierarchy"
    return config
