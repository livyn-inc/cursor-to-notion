"""Meta directory helpers."""
from __future__ import annotations

import os

__all__ = ["ensure_meta"]


def ensure_meta(dir_path: str) -> str:
    c2n_dir = os.path.join(dir_path, ".c2n")
    os.makedirs(c2n_dir, exist_ok=True)
    return c2n_dir
