"""index.yaml load/save helpers."""
from __future__ import annotations

import os
import time
from typing import Any, Dict

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore

__all__ = ["_load_meta", "_save_meta"]


def _load_meta(target: str) -> Dict[str, Any]:
    try:
        mpath = os.path.join(target, ".c2n", "index.yaml")
        if yaml and os.path.exists(mpath):
            with open(mpath, "r", encoding="utf-8") as fh:
                return yaml.safe_load(fh) or {}
    except Exception:
        pass
    return {}


def _save_meta(target: str, meta: Dict[str, Any]) -> None:
    try:
        mdir = os.path.join(target, ".c2n")
        os.makedirs(mdir, exist_ok=True)
        mpath = os.path.join(mdir, "index.yaml")
        meta = meta or {}
        meta["generated_at"] = int(time.time())
        if yaml:
            with open(mpath, "w", encoding="utf-8") as fh:
                yaml.safe_dump(meta, fh, allow_unicode=True, sort_keys=False)
        else:
            with open(mpath, "w", encoding="utf-8") as fh:
                fh.write(str(meta))
    except Exception:
        pass
