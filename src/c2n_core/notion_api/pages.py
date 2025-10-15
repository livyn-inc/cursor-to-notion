"""Lightweight wrappers around Notion pages/databases APIs.

These helpers make it easier to mock in unit tests and to keep call sites clean.
"""
from __future__ import annotations

from typing import Any, Dict, List


def get_page(notion_client, page_id: str) -> Dict[str, Any]:
    """Retrieve a page object by ID."""
    return notion_client.pages.retrieve(page_id=page_id)


def get_database(notion_client, database_id: str) -> Dict[str, Any]:
    """Retrieve a database object by ID."""
    return notion_client.databases.retrieve(database_id=database_id)


def get_database_entries(notion_client, database_id: str) -> List[Dict[str, Any]]:
    """Retrieve all entries from a Notion database with pagination."""
    results = []
    has_more = True
    next_cursor = None
    while has_more:
        response = notion_client.databases.query(
            database_id=database_id,
            start_cursor=next_cursor
        )
        results.extend(response["results"])
        has_more = response["has_more"]
        next_cursor = response["next_cursor"]
    return results


def create_page(notion_client, parent: Dict[str, Any], properties: Dict[str, Any], 
                children: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a new page in Notion."""
    page_data = {
        "parent": parent,
        "properties": properties
    }
    if children:
        page_data["children"] = children
    return notion_client.pages.create(**page_data)


def update_page(notion_client, page_id: str, properties: Dict[str, Any] = None,
                archived: bool = None) -> Dict[str, Any]:
    """Update an existing page in Notion."""
    update_data = {}
    if properties is not None:
        update_data["properties"] = properties
    if archived is not None:
        update_data["archived"] = archived
    return notion_client.pages.update(page_id=page_id, **update_data)


def get_page_children(notion_client, page_id: str) -> List[Dict[str, Any]]:
    """Retrieve all child pages/blocks from a Notion page with pagination."""
    results = []
    has_more = True
    next_cursor = None
    while has_more:
        response = notion_client.blocks.children.list(
            block_id=page_id,
            start_cursor=next_cursor
        )
        results.extend(response["results"])
        has_more = response["has_more"]
        next_cursor = response["next_cursor"]
    return results


