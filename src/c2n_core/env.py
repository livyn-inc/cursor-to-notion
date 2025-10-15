"""Environment loading and token bridge helpers."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Set

__all__ = [
    "_load_env_file",
    "_ensure_notion_env_bridge",
    "_load_env_for_target",
]

ROOT = Path(__file__).resolve().parents[1]


def _load_env_file(path: str) -> None:
    if not path or not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip()
            # Strip surrounding quotes if present
            if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                v = v[1:-1]
            os.environ.setdefault(k, v)


def _ensure_notion_env_bridge() -> None:
    token = os.environ.get("NOTION_TOKEN")
    api_key = os.environ.get("NOTION_API_KEY")
    if not token and api_key:
        os.environ["NOTION_TOKEN"] = api_key
    if not api_key and token:
        os.environ["NOTION_API_KEY"] = token


def _load_env_for_target(target_folder: str) -> None:
    try:
        target_folder = os.path.abspath(target_folder)
        
        # IMP-004: 仮想環境の検出と環境変数継承
        venv_path = os.environ.get('VIRTUAL_ENV')
        if venv_path:
            # 仮想環境のactivateスクリプトから環境変数を読み込み
            activate_script = os.path.join(venv_path, 'bin', 'activate')
            if os.path.exists(activate_script):
                print(f"✓ 仮想環境検出: {venv_path}")
        
        _load_env_file(os.path.join(target_folder, ".c2n", ".env"))
        _load_env_file(os.path.join(target_folder, ".env"))
        try:
            cur = target_folder
            seen: Set[str] = set()
            while cur and cur not in seen:
                seen.add(cur)
                env_path = os.path.join(cur, ".env")
                if os.path.exists(env_path):
                    _load_env_file(env_path)
                    break
                parent = os.path.dirname(cur)
                if parent == cur:
                    break
                cur = parent
        except Exception:
            pass
        _load_env_file(str(ROOT / ".env"))
        _ensure_notion_env_bridge()
    except Exception:
        pass
