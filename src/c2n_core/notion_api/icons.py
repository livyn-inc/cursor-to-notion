"""Notion icon helpers (shared).

All functions expect a `notion_client` instance from `notion_client.Client`.
"""
from __future__ import annotations

from typing import Optional


def set_page_icon(notion_client, page_id: str, icon_emoji: str) -> bool:
    try:
        notion_client.pages.update(
            page_id=page_id,
            icon={"type": "emoji", "emoji": icon_emoji},
        )
        return True
    except Exception:
        return False


def get_page_icon(notion_client, page_id: str) -> Optional[str]:
    try:
        page = notion_client.pages.retrieve(page_id=page_id)
        icon = page.get("icon")
        if icon and icon.get("type") == "emoji":
            return icon.get("emoji")
        return None
    except Exception:
        return None


def _detect_is_folder(notion_client, page_id: str) -> bool:
    try:
        children = notion_client.blocks.children.list(block_id=page_id)
        for block in children.get("results", []):
            if block.get("type") == "child_page":
                return True
        return False
    except Exception:
        return False


def auto_set_page_icon(
    notion_client,
    page_id: str,
    *,
    force_update: bool = False,
    is_folder: Optional[bool] = None,
) -> bool:
    try:
        if not force_update:
            current = get_page_icon(notion_client, page_id)
            if current:
                return True
        if is_folder is None:
            is_folder = _detect_is_folder(notion_client, page_id)
        icon = "📁" if is_folder else "📄"
        return set_page_icon(notion_client, page_id, icon)
    except Exception:
        return False







