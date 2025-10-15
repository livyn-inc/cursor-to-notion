#!/usr/bin/env python3

"""
Page fetching for pull operations
"""

import os
import time
from typing import List, Dict, Any, Optional, Tuple
from notion_client import Client

from c2n_core.utils import extract_id_from_url_strict
from c2n_core.notion_api.pages import get_page, get_page_children
from c2n_core.notion_api.blocks import get_block_children


class PageFetcher:
    """Handles page fetching for pull operations"""
    
    def __init__(self, client: Client, root_dir: str, root_meta: Dict[str, Any]):
        self.client = client
        self.root_dir = root_dir
        self.root_meta = root_meta
    
    def fetch_page_info(self, page_url: str) -> Optional[Dict[str, Any]]:
        """Fetch page information from Notion"""
        try:
            page_id = extract_id_from_url_strict(page_url)
            if not page_id:
                return None
            
            # Get page properties
            page = get_page(self.client, page_id)
            if not page:
                return None
            
            return {
                "id": page_id,
                "url": page_url,
                "title": self._extract_page_title(page),
                "properties": page.get("properties", {}),
                "created_time": page.get("created_time"),
                "last_edited_time": page.get("last_edited_time"),
                "parent": page.get("parent"),
                "archived": page.get("archived", False),
                "icon": page.get("icon"),
                "cover": page.get("cover"),
            }
        except Exception as e:
            print(f"Failed to fetch page info for {page_url}: {e}")
            return None
    
    def _extract_page_title(self, page: Dict[str, Any]) -> str:
        """Extract page title from page object"""
        try:
            properties = page.get("properties", {})
            
            # Try different title properties
            title_props = ["title", "Name", "名前", "Title"]
            for prop in title_props:
                if prop in properties:
                    title_obj = properties[prop]
                    if isinstance(title_obj, dict):
                        if "title" in title_obj:
                            title_array = title_obj["title"]
                            if isinstance(title_array, list) and len(title_array) > 0:
                                title_item = title_array[0]
                                if isinstance(title_item, dict) and "text" in title_item:
                                    return title_item["text"]["content"]
                        elif "rich_text" in title_obj:
                            rich_text = title_obj["rich_text"]
                            if isinstance(rich_text, list) and len(rich_text) > 0:
                                text_item = rich_text[0]
                                if isinstance(text_item, dict) and "text" in text_item:
                                    return text_item["text"]["content"]
            
            # Fallback to page ID
            return page.get("id", "Untitled")
        except Exception:
            return "Untitled"
    
    def fetch_page_blocks(self, page_url: str) -> List[Dict[str, Any]]:
        """Fetch page blocks from Notion"""
        try:
            page_id = extract_id_from_url_strict(page_url)
            if not page_id:
                return []
            
            # Get page children (blocks)
            blocks = get_block_children(self.client, page_id)
            return blocks or []
        except Exception as e:
            print(f"Failed to fetch page blocks for {page_url}: {e}")
            return []
    
    def fetch_child_pages(self, page_url: str) -> List[Dict[str, Any]]:
        """Fetch child pages from Notion"""
        try:
            page_id = extract_id_from_url_strict(page_url)
            if not page_id:
                return []
            
            # Get page children (blocks)
            children = get_page_children(self.client, page_id)
            if not children:
                return []
            
            # Filter for child_page blocks and full page objects
            pages = []
            for child in children:
                # Check if this is a child_page block
                if child.get("type") == "child_page":
                    child_page_id = child.get("id")
                    child_page_title = child.get("child_page", {}).get("title", "Untitled")
                    
                    # Fetch full page info for the child page
                    try:
                        full_page = get_page(self.client, child_page_id)
                        pages.append({
                            "id": child_page_id,
                            "url": f"https://www.notion.so/{child_page_id.replace('-', '')}",
                            "title": child_page_title,
                            "properties": full_page.get("properties", {}),
                            "created_time": full_page.get("created_time"),
                            "last_edited_time": full_page.get("last_edited_time"),
                            "parent": full_page.get("parent"),
                            "archived": full_page.get("archived", False),
                            "icon": full_page.get("icon"),
                            "cover": full_page.get("cover"),
                        })
                    except Exception as e:
                        print(f"Failed to fetch full page info for child {child_page_id}: {e}")
                        # Fallback: use basic info from child_page block
                        pages.append({
                            "id": child_page_id,
                            "url": f"https://www.notion.so/{child_page_id.replace('-', '')}",
                            "title": child_page_title,
                            "properties": {},
                            "created_time": None,
                            "last_edited_time": None,
                            "parent": {"type": "page_id", "page_id": page_id},
                            "archived": False,
                            "icon": None,
                            "cover": None,
                        })
                # Also check for full page objects (for compatibility)
                elif child.get("object") == "page":
                    pages.append({
                        "id": child.get("id"),
                        "url": f"https://www.notion.so/{child.get('id', '').replace('-', '')}",
                        "title": self._extract_page_title(child),
                        "properties": child.get("properties", {}),
                        "created_time": child.get("created_time"),
                        "last_edited_time": child.get("last_edited_time"),
                        "parent": child.get("parent"),
                        "archived": child.get("archived", False),
                        "icon": child.get("icon"),
                        "cover": child.get("cover"),
                    })
            
            return pages
        except Exception as e:
            print(f"Failed to fetch child pages for {page_url}: {e}")
            return []
    
    def fetch_page_hierarchy(self, root_url: str, max_depth: int = 10) -> Dict[str, Any]:
        """Fetch page hierarchy recursively"""
        try:
            hierarchy = {
                "root": root_url,
                "pages": {},
                "children": {},
                "depth": 0,
            }
            
            self._fetch_hierarchy_recursive(root_url, hierarchy, 0, max_depth)
            return hierarchy
        except Exception as e:
            print(f"Failed to fetch page hierarchy: {e}")
            return {"root": root_url, "pages": {}, "children": {}, "depth": 0}
    
    def _fetch_hierarchy_recursive(self, page_url: str, hierarchy: Dict[str, Any], 
                                  current_depth: int, max_depth: int) -> None:
        """Recursively fetch page hierarchy"""
        if current_depth >= max_depth:
            return
        
        try:
            # Fetch page info
            page_info = self.fetch_page_info(page_url)
            if not page_info:
                return
            
            # Add to hierarchy
            hierarchy["pages"][page_url] = page_info
            hierarchy["children"][page_url] = []
            
            # Fetch child pages
            child_pages = self.fetch_child_pages(page_url)
            for child in child_pages:
                child_url = child["url"]
                hierarchy["children"][page_url].append(child_url)
                
                # Recursively fetch children
                self._fetch_hierarchy_recursive(child_url, hierarchy, current_depth + 1, max_depth)
        except Exception as e:
            print(f"Failed to fetch hierarchy for {page_url}: {e}")
    
    def get_page_last_edited_time(self, page_url: str) -> Optional[int]:
        """Get page last edited time"""
        try:
            page_info = self.fetch_page_info(page_url)
            if not page_info:
                return None
            
            last_edited = page_info.get("last_edited_time")
            if last_edited:
                # Convert to timestamp
                import datetime
                if isinstance(last_edited, str):
                    dt = datetime.datetime.fromisoformat(last_edited.replace('Z', '+00:00'))
                    return int(dt.timestamp() * 1_000_000_000)
                elif isinstance(last_edited, (int, float)):
                    return int(last_edited * 1_000_000_000)
            
            return None
        except Exception as e:
            print(f"Failed to get last edited time for {page_url}: {e}")
            return None
    
    def is_page_modified_since(self, page_url: str, since_time: int) -> bool:
        """Check if page was modified since given time"""
        try:
            last_edited = self.get_page_last_edited_time(page_url)
            if not last_edited:
                return True  # Assume modified if we can't determine
            
            return last_edited > since_time
        except Exception:
            return True  # Assume modified on error
    
    def get_page_metadata(self, page_url: str) -> Dict[str, Any]:
        """Get page metadata"""
        try:
            page_info = self.fetch_page_info(page_url)
            if not page_info:
                return {}
            
            return {
                "url": page_url,
                "title": page_info.get("title", "Untitled"),
                "id": page_info.get("id"),
                "created_time": page_info.get("created_time"),
                "last_edited_time": page_info.get("last_edited_time"),
                "archived": page_info.get("archived", False),
                "icon": page_info.get("icon"),
                "cover": page_info.get("cover"),
                "parent": page_info.get("parent"),
            }
        except Exception as e:
            print(f"Failed to get page metadata for {page_url}: {e}")
            return {}
    
    def search_pages(self, query: str, parent_url: str = None) -> List[Dict[str, Any]]:
        """Search for pages"""
        try:
            # This would implement Notion search API
            # For now, return empty list
            return []
        except Exception as e:
            print(f"Failed to search pages: {e}")
            return []
    
    def get_page_by_title(self, title: str, parent_url: str = None) -> Optional[Dict[str, Any]]:
        """Get page by title"""
        try:
            # This would implement title-based page lookup
            # For now, return None
            return None
        except Exception as e:
            print(f"Failed to get page by title: {e}")
            return None
    
    def validate_page_url(self, page_url: str) -> bool:
        """Validate page URL"""
        try:
            page_id = extract_id_from_url_strict(page_url)
            if not page_id:
                return False
            
            # Try to fetch page info
            page_info = self.fetch_page_info(page_url)
            return page_info is not None
        except Exception:
            return False
    
    def get_page_permissions(self, page_url: str) -> Dict[str, Any]:
        """Get page permissions"""
        try:
            page_info = self.fetch_page_info(page_url)
            if not page_info:
                return {}
            
            # This would implement permission checking
            # For now, return basic info
            return {
                "can_read": True,
                "can_write": True,
                "can_comment": True,
                "can_share": True,
            }
        except Exception as e:
            print(f"Failed to get page permissions for {page_url}: {e}")
            return {}
    
    def archive_page(self, page_url: str) -> bool:
        """Archive page"""
        try:
            page_id = extract_id_from_url_strict(page_url)
            if not page_id:
                return False
            
            # This would implement page archiving
            # For now, return False
            return False
        except Exception as e:
            print(f"Failed to archive page {page_url}: {e}")
            return False
    
    def restore_page(self, page_url: str) -> bool:
        """Restore archived page"""
        try:
            page_id = extract_id_from_url_strict(page_url)
            if not page_id:
                return False
            
            # This would implement page restoration
            # For now, return False
            return False
        except Exception as e:
            print(f"Failed to restore page {page_url}: {e}")
            return False
    
    def get_page_history(self, page_url: str) -> List[Dict[str, Any]]:
        """Get page history"""
        try:
            # This would implement page history retrieval
            # For now, return empty list
            return []
        except Exception as e:
            print(f"Failed to get page history for {page_url}: {e}")
            return []
    
    def get_page_comments(self, page_url: str) -> List[Dict[str, Any]]:
        """Get page comments"""
        try:
            # This would implement comment retrieval
            # For now, return empty list
            return []
        except Exception as e:
            print(f"Failed to get page comments for {page_url}: {e}")
            return []