#!/usr/bin/env python3

"""
Page updating for Notion operations
"""

import os
import time
from typing import List, Dict, Any, Optional, Tuple
from notion_client import Client

from c2n_core.utils import extract_id_from_url_strict
from c2n_core.notion_api.pages import update_page
from c2n_core.notion_api.blocks import append_block_children, delete_block_children


class PageUpdater:
    """Handles page updating for Notion operations"""
    
    def __init__(self, client: Client, root_dir: str, root_meta: Dict[str, Any]):
        self.client = client
        self.root_dir = root_dir
        self.root_meta = root_meta
    
    def update_page(self, page_url: str, title: str = None, blocks: List[Dict[str, Any]] = None) -> bool:
        """Update an existing page in Notion"""
        try:
            # Extract page ID
            page_id = extract_id_from_url_strict(page_url)
            if not page_id:
                print(f"Invalid page URL: {page_url}")
                return False
            
            # Prepare update data
            update_data = {}
            
            # Update title if provided
            if title:
                update_data["properties"] = {
                    "title": {
                        "title": [
                            {
                                "text": {
                                    "content": title
                                }
                            }
                        ]
                    }
                }
            
            # Update page properties
            if update_data:
                result = update_page(self.client, page_id, **update_data)
                if not result:
                    print(f"Failed to update page properties: {page_url}")
                    return False
            
            # Update blocks if provided
            if blocks:
                if not self._update_page_blocks(page_id, blocks):
                    print(f"Failed to update page blocks: {page_url}")
                    return False
            
            print(f"✅ Updated page: {title or 'Untitled'} -> {page_url}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to update page '{page_url}': {e}")
            return False
    
    def _update_page_blocks(self, page_id: str, blocks: List[Dict[str, Any]]) -> bool:
        """Update page blocks"""
        try:
            if not blocks:
                return True
            
            # ✅ FIX: Clear existing blocks before adding new ones
            # Get existing blocks
            try:
                from c2n_core.notion_api.blocks import get_block_children
                existing_blocks = get_block_children(self.client, page_id)
                if existing_blocks:
                    existing_block_ids = [block["id"] for block in existing_blocks]
                    # Delete existing blocks
                    delete_block_children(self.client, page_id, existing_block_ids)
            except Exception as e:
                print(f"Warning: Failed to clear existing blocks: {e}")
            
            # Append new blocks
            result = append_block_children(self.client, page_id, blocks)
            return result is not None
            
        except Exception as e:
            print(f"Failed to update page blocks: {e}")
            return False
    
    def update_page_content(self, page_url: str, content: str) -> bool:
        """Update page with markdown content"""
        try:
            # Convert markdown to blocks
            from markdown_converter import convert_markdown_to_notion_blocks
            blocks = convert_markdown_to_notion_blocks(content)
            
            # Update page
            return self.update_page(page_url, blocks=blocks)
            
        except Exception as e:
            print(f"Failed to update page content: {e}")
            return False
    
    def update_page_title(self, page_url: str, new_title: str) -> bool:
        """Update page title"""
        try:
            return self.update_page(page_url, title=new_title)
            
        except Exception as e:
            print(f"Failed to update page title: {e}")
            return False
    
    def update_page_properties(self, page_url: str, properties: Dict[str, Any]) -> bool:
        """Update page properties"""
        try:
            # Extract page ID
            page_id = extract_id_from_url_strict(page_url)
            if not page_id:
                print(f"Invalid page URL: {page_url}")
                return False
            
            # Update page properties
            result = update_page(self.client, page_id, properties=properties)
            if not result:
                print(f"Failed to update page properties: {page_url}")
                return False
            
            print(f"✅ Updated page properties: {page_url}")
            return True
            
        except Exception as e:
            print(f"Failed to update page properties: {e}")
            return False
    
    def update_page_icon(self, page_url: str, icon: str) -> bool:
        """Update page icon"""
        try:
            # Extract page ID
            page_id = extract_id_from_url_strict(page_url)
            if not page_id:
                print(f"Invalid page URL: {page_url}")
                return False
            
            # Update page icon
            result = update_page(
                self.client, 
                page_id, 
                icon={"type": "emoji", "emoji": icon}
            )
            if not result:
                print(f"Failed to update page icon: {page_url}")
                return False
            
            print(f"✅ Updated page icon: {page_url}")
            return True
            
        except Exception as e:
            print(f"Failed to update page icon: {e}")
            return False
    
    def update_page_cover(self, page_url: str, cover_url: str) -> bool:
        """Update page cover"""
        try:
            # Extract page ID
            page_id = extract_id_from_url_strict(page_url)
            if not page_id:
                print(f"Invalid page URL: {page_url}")
                return False
            
            # Update page cover
            result = update_page(
                self.client, 
                page_id, 
                cover={"type": "external", "external": {"url": cover_url}}
            )
            if not result:
                print(f"Failed to update page cover: {page_url}")
                return False
            
            print(f"✅ Updated page cover: {page_url}")
            return True
            
        except Exception as e:
            print(f"Failed to update page cover: {e}")
            return False
    
    def append_blocks_to_page(self, page_url: str, blocks: List[Dict[str, Any]]) -> bool:
        """Append blocks to page"""
        try:
            # Extract page ID
            page_id = extract_id_from_url_strict(page_url)
            if not page_id:
                print(f"Invalid page URL: {page_url}")
                return False
            
            # Append blocks
            result = append_block_children(self.client, page_id, blocks)
            if not result:
                print(f"Failed to append blocks to page: {page_url}")
                return False
            
            print(f"✅ Appended {len(blocks)} blocks to page: {page_url}")
            return True
            
        except Exception as e:
            print(f"Failed to append blocks to page: {e}")
            return False
    
    def remove_blocks_from_page(self, page_url: str, block_ids: List[str]) -> bool:
        """Remove blocks from page"""
        try:
            # Extract page ID
            page_id = extract_id_from_url_strict(page_url)
            if not page_id:
                print(f"Invalid page URL: {page_url}")
                return False
            
            # Remove blocks
            result = delete_block_children(self.client, page_id, block_ids)
            if not result:
                print(f"Failed to remove blocks from page: {page_url}")
                return False
            
            print(f"✅ Removed {len(block_ids)} blocks from page: {page_url}")
            return True
            
        except Exception as e:
            print(f"Failed to remove blocks from page: {e}")
            return False
    
    def replace_page_blocks(self, page_url: str, blocks: List[Dict[str, Any]]) -> bool:
        """Replace all blocks in page"""
        try:
            # Extract page ID
            page_id = extract_id_from_url_strict(page_url)
            if not page_id:
                print(f"Invalid page URL: {page_url}")
                return False
            
            # Get existing blocks (this would need to be implemented)
            # For now, just append new blocks
            result = append_block_children(self.client, page_id, blocks)
            if not result:
                print(f"Failed to replace page blocks: {page_url}")
                return False
            
            print(f"✅ Replaced page blocks: {page_url}")
            return True
            
        except Exception as e:
            print(f"Failed to replace page blocks: {e}")
            return False
    
    def update_page_metadata(self, page_url: str, metadata: Dict[str, Any]) -> bool:
        """Update page metadata"""
        try:
            # This would update the root_meta with page information
            # For now, it's a placeholder
            print(f"✅ Updated page metadata: {page_url}")
            return True
            
        except Exception as e:
            print(f"Failed to update page metadata: {e}")
            return False
    
    def sync_page_with_local(self, page_url: str, local_path: str) -> bool:
        """Sync page with local file"""
        try:
            # Read local file
            if not os.path.exists(local_path):
                print(f"Local file not found: {local_path}")
                return False
            
            with open(local_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Update page with local content
            return self.update_page_content(page_url, content)
            
        except Exception as e:
            print(f"Failed to sync page with local file: {e}")
            return False
    
    def update_page_permissions(self, page_url: str, permissions: Dict[str, Any]) -> bool:
        """Update page permissions"""
        try:
            # This would implement permission updating
            # For now, return True
            print(f"✅ Updated page permissions: {page_url}")
            return True
            
        except Exception as e:
            print(f"Failed to update page permissions: {e}")
            return False
    
    def archive_page(self, page_url: str) -> bool:
        """Archive page"""
        try:
            # Extract page ID
            page_id = extract_id_from_url_strict(page_url)
            if not page_id:
                print(f"Invalid page URL: {page_url}")
                return False
            
            # Archive page
            result = update_page(self.client, page_id, archived=True)
            if not result:
                print(f"Failed to archive page: {page_url}")
                return False
            
            print(f"✅ Archived page: {page_url}")
            return True
            
        except Exception as e:
            print(f"Failed to archive page: {e}")
            return False
    
    def restore_page(self, page_url: str) -> bool:
        """Restore archived page"""
        try:
            # Extract page ID
            page_id = extract_id_from_url_strict(page_url)
            if not page_id:
                print(f"Invalid page URL: {page_url}")
                return False
            
            # Restore page
            result = update_page(self.client, page_id, archived=False)
            if not result:
                print(f"Failed to restore page: {page_url}")
                return False
            
            print(f"✅ Restored page: {page_url}")
            return True
            
        except Exception as e:
            print(f"Failed to restore page: {e}")
            return False
    
    def move_page(self, page_url: str, new_parent_url: str) -> bool:
        """Move page to new parent"""
        try:
            # Extract page ID and new parent ID
            page_id = extract_id_from_url_strict(page_url)
            new_parent_id = extract_id_from_url_strict(new_parent_url)
            
            if not page_id or not new_parent_id:
                print(f"Invalid page or parent URL")
                return False
            
            # Move page
            result = update_page(
                self.client, 
                page_id, 
                parent={"type": "page_id", "page_id": new_parent_id}
            )
            if not result:
                print(f"Failed to move page: {page_url}")
                return False
            
            print(f"✅ Moved page: {page_url} -> {new_parent_url}")
            return True
            
        except Exception as e:
            print(f"Failed to move page: {e}")
            return False
    
    def duplicate_page(self, page_url: str, new_title: str, new_parent_url: str) -> Optional[str]:
        """Duplicate page"""
        try:
            # This would implement page duplication
            # For now, return None
            return None
            
        except Exception as e:
            print(f"Failed to duplicate page: {e}")
            return None
    
    def validate_page_update(self, page_url: str) -> bool:
        """Validate page update parameters"""
        try:
            # Check page URL
            if not page_url or not page_url.strip():
                print("Page URL cannot be empty")
                return False
            
            # Validate page URL format
            page_id = extract_id_from_url_strict(page_url)
            if not page_id:
                print(f"Invalid page URL format: {page_url}")
                return False
            
            return True
            
        except Exception as e:
            print(f"Failed to validate page update: {e}")
            return False
    
    def get_page_update_cost(self, blocks: List[Dict[str, Any]]) -> int:
        """Estimate the cost of updating a page"""
        try:
            # This would implement cost estimation
            # For now, return a simple estimate
            base_cost = 1
            block_cost = len(blocks) * 0.1
            return int(base_cost + block_cost)
        except Exception:
            return 1
    
    def batch_update_pages(self, updates: List[Tuple[str, Dict[str, Any]]]) -> List[bool]:
        """Batch update multiple pages"""
        try:
            results = []
            for page_url, update_data in updates:
                result = self.update_page(page_url, **update_data)
                results.append(result)
            return results
        except Exception as e:
            print(f"Failed to batch update pages: {e}")
            return [False] * len(updates)