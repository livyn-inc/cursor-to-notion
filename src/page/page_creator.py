#!/usr/bin/env python3

"""
Page creation for Notion operations
"""

import os
import time
from typing import List, Dict, Any, Optional, Tuple
from notion_client import Client

from c2n_core.utils import extract_id_from_url_strict
from c2n_core.notion_api.pages import create_page, update_page
from c2n_core.notion_api.blocks import append_block_children


class PageCreator:
    """Handles page creation for Notion operations"""
    
    def __init__(self, client: Client, root_dir: str, root_meta: Dict[str, Any]):
        self.client = client
        self.root_dir = root_dir
        self.root_meta = root_meta
    
    def create_page(self, title: str, blocks: List[Dict[str, Any]], parent_url: str) -> Optional[str]:
        """Create a new page in Notion"""
        try:
            # Extract parent page ID
            parent_id = extract_id_from_url_strict(parent_url)
            if not parent_id:
                print(f"Invalid parent URL: {parent_url}")
                return None
            
            # Create page properties
            properties = {
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
            
            # Create page
            parent = {"page_id": parent_id}
            page = create_page(
                self.client,
                parent=parent,
                properties=properties
            )
            
            if not page:
                print(f"Failed to create page: {title}")
                return None
            
            page_id = page.get("id")
            if not page_id:
                print(f"No page ID returned for: {title}")
                return None
            
            # Convert page ID to URL
            page_url = f"https://www.notion.so/{page_id.replace('-', '')}"
            
            # Add blocks if provided
            if blocks:
                self._add_blocks_to_page(page_id, blocks)
            
            print(f"✅ Created page: {title} -> {page_url}")
            return page_url
            
        except Exception as e:
            print(f"❌ Failed to create page '{title}': {e}")
            return None
    
    def _add_blocks_to_page(self, page_id: str, blocks: List[Dict[str, Any]]) -> bool:
        """Add blocks to a page"""
        try:
            if not blocks:
                return True
            
            # Append blocks to page
            result = append_block_children(self.client, page_id, blocks)
            return result is not None
            
        except Exception as e:
            print(f"Failed to add blocks to page {page_id}: {e}")
            return False
    
    def create_page_with_content(self, title: str, content: str, parent_url: str) -> Optional[str]:
        """Create a page with markdown content"""
        try:
            # Convert markdown to blocks
            from markdown_converter import convert_markdown_to_notion_blocks
            blocks = convert_markdown_to_notion_blocks(content)
            
            # Create page
            return self.create_page(title, blocks, parent_url)
            
        except Exception as e:
            print(f"Failed to create page with content: {e}")
            return None
    
    def create_directory_page(self, dir_name: str, parent_url: str) -> Optional[str]:
        """Create a directory page in Notion"""
        try:
            # Create page with directory name
            page_url = self.create_page(dir_name, [], parent_url)
            
            if page_url:
                # Set directory icon
                self._set_directory_icon(page_url)
                
                # Update metadata
                self._update_directory_metadata(dir_name, page_url, parent_url)
            
            return page_url
            
        except Exception as e:
            print(f"Failed to create directory page: {e}")
            return None
    
    def _set_directory_icon(self, page_url: str) -> bool:
        """Set directory icon for page"""
        try:
            from c2n_core.notion_api.icons import auto_set_page_icon
            return auto_set_page_icon(self.client, page_url, force_update=False, is_folder=True)
        except Exception as e:
            print(f"Failed to set directory icon: {e}")
            return False
    
    def _update_directory_metadata(self, dir_name: str, page_url: str, parent_url: str) -> None:
        """Update directory metadata"""
        try:
            # This would update the root_meta with directory information
            # For now, it's a placeholder
            pass
        except Exception as e:
            print(f"Failed to update directory metadata: {e}")
    
    def create_file_page(self, file_name: str, file_content: str, parent_url: str) -> Optional[str]:
        """Create a file page in Notion"""
        try:
            # Remove file extension from title
            title = os.path.splitext(file_name)[0]
            
            # Create page with file content
            page_url = self.create_page_with_content(title, file_content, parent_url)
            
            if page_url:
                # Set file icon
                self._set_file_icon(page_url)
                
                # Update metadata
                self._update_file_metadata(file_name, page_url, parent_url)
            
            return page_url
            
        except Exception as e:
            print(f"Failed to create file page: {e}")
            return None
    
    def _set_file_icon(self, page_url: str) -> bool:
        """Set file icon for page"""
        try:
            from c2n_core.notion_api.icons import auto_set_page_icon
            return auto_set_page_icon(self.client, page_url, force_update=False, is_folder=False)
        except Exception as e:
            print(f"Failed to set file icon: {e}")
            return False
    
    def _update_file_metadata(self, file_name: str, page_url: str, parent_url: str) -> None:
        """Update file metadata"""
        try:
            # This would update the root_meta with file information
            # For now, it's a placeholder
            pass
        except Exception as e:
            print(f"Failed to update file metadata: {e}")
    
    def create_index_page(self, title: str, child_links: List[Tuple[str, str]], parent_url: str) -> Optional[str]:
        """Create an index page with child links"""
        try:
            # Create index content
            index_content = f"# {title}\n\n"
            for name, url in child_links:
                index_content += f"- [{name}]({url})\n"
            
            # Create page with index content
            page_url = self.create_page_with_content(title, index_content, parent_url)
            
            if page_url:
                # Set index icon
                self._set_index_icon(page_url)
            
            return page_url
            
        except Exception as e:
            print(f"Failed to create index page: {e}")
            return None
    
    def _set_index_icon(self, page_url: str) -> bool:
        """Set index icon for page"""
        try:
            from c2n_core.notion_api.icons import auto_set_page_icon
            return auto_set_page_icon(self.client, page_url, force_update=False, is_folder=True)
        except Exception as e:
            print(f"Failed to set index icon: {e}")
            return False
    
    def create_page_from_template(self, template_name: str, title: str, parent_url: str) -> Optional[str]:
        """Create a page from a template"""
        try:
            # This would implement template-based page creation
            # For now, create a basic page
            return self.create_page(title, [], parent_url)
            
        except Exception as e:
            print(f"Failed to create page from template: {e}")
            return None
    
    def duplicate_page(self, source_url: str, new_title: str, parent_url: str) -> Optional[str]:
        """Duplicate an existing page"""
        try:
            # This would implement page duplication
            # For now, return None
            return None
            
        except Exception as e:
            print(f"Failed to duplicate page: {e}")
            return None
    
    def create_page_with_properties(self, title: str, properties: Dict[str, Any], 
                                  blocks: List[Dict[str, Any]], parent_url: str) -> Optional[str]:
        """Create a page with custom properties"""
        try:
            # Extract parent page ID
            parent_id = extract_id_from_url_strict(parent_url)
            if not parent_id:
                print(f"Invalid parent URL: {parent_url}")
                return None
            
            # Add title to properties
            properties["title"] = {
                "title": [
                    {
                        "text": {
                            "content": title
                        }
                    }
                ]
            }
            
            # Create page
            parent = {"page_id": parent_id}
            page = create_page(
                self.client,
                parent=parent,
                properties=properties
            )
            
            if not page:
                print(f"Failed to create page: {title}")
                return None
            
            page_id = page.get("id")
            if not page_id:
                print(f"No page ID returned for: {title}")
                return None
            
            # Convert page ID to URL
            page_url = f"https://www.notion.so/{page_id.replace('-', '')}"
            
            # Add blocks if provided
            if blocks:
                self._add_blocks_to_page(page_id, blocks)
            
            print(f"✅ Created page with properties: {title} -> {page_url}")
            return page_url
            
        except Exception as e:
            print(f"❌ Failed to create page with properties '{title}': {e}")
            return None
    
    def create_database_page(self, title: str, database_schema: Dict[str, Any], parent_url: str) -> Optional[str]:
        """Create a database page"""
        try:
            # This would implement database creation
            # For now, create a basic page
            return self.create_page(title, [], parent_url)
            
        except Exception as e:
            print(f"Failed to create database page: {e}")
            return None
    
    def create_page_with_cover(self, title: str, cover_url: str, blocks: List[Dict[str, Any]], parent_url: str) -> Optional[str]:
        """Create a page with cover image"""
        try:
            # Extract parent page ID
            parent_id = extract_id_from_url_strict(parent_url)
            if not parent_id:
                print(f"Invalid parent URL: {parent_url}")
                return None
            
            # Create page properties
            properties = {
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
            
            # Create page with cover
            page = create_page(
                self.client,
                parent_id=parent_id,
                properties=properties,
                cover={"type": "external", "external": {"url": cover_url}}
            )
            
            if not page:
                print(f"Failed to create page: {title}")
                return None
            
            page_id = page.get("id")
            if not page_id:
                print(f"No page ID returned for: {title}")
                return None
            
            # Convert page ID to URL
            page_url = f"https://www.notion.so/{page_id.replace('-', '')}"
            
            # Add blocks if provided
            if blocks:
                self._add_blocks_to_page(page_id, blocks)
            
            print(f"✅ Created page with cover: {title} -> {page_url}")
            return page_url
            
        except Exception as e:
            print(f"❌ Failed to create page with cover '{title}': {e}")
            return None
    
    def create_page_with_icon(self, title: str, icon: str, blocks: List[Dict[str, Any]], parent_url: str) -> Optional[str]:
        """Create a page with icon"""
        try:
            # Extract parent page ID
            parent_id = extract_id_from_url_strict(parent_url)
            if not parent_id:
                print(f"Invalid parent URL: {parent_url}")
                return None
            
            # Create page properties
            properties = {
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
            
            # Create page with icon
            page = create_page(
                self.client,
                parent_id=parent_id,
                properties=properties,
                icon={"type": "emoji", "emoji": icon}
            )
            
            if not page:
                print(f"Failed to create page: {title}")
                return None
            
            page_id = page.get("id")
            if not page_id:
                print(f"No page ID returned for: {title}")
                return None
            
            # Convert page ID to URL
            page_url = f"https://www.notion.so/{page_id.replace('-', '')}"
            
            # Add blocks if provided
            if blocks:
                self._add_blocks_to_page(page_id, blocks)
            
            print(f"✅ Created page with icon: {title} -> {page_url}")
            return page_url
            
        except Exception as e:
            print(f"❌ Failed to create page with icon '{title}': {e}")
            return None
    
    def validate_page_creation(self, title: str, parent_url: str) -> bool:
        """Validate page creation parameters"""
        try:
            # Check title
            if not title or not title.strip():
                print("Page title cannot be empty")
                return False
            
            # Check parent URL
            if not parent_url or not parent_url.strip():
                print("Parent URL cannot be empty")
                return False
            
            # Validate parent URL format
            parent_id = extract_id_from_url_strict(parent_url)
            if not parent_id:
                print(f"Invalid parent URL format: {parent_url}")
                return False
            
            return True
            
        except Exception as e:
            print(f"Failed to validate page creation: {e}")
            return False
    
    def get_page_creation_cost(self, blocks: List[Dict[str, Any]]) -> int:
        """Estimate the cost of creating a page"""
        try:
            # This would implement cost estimation
            # For now, return a simple estimate
            base_cost = 1
            block_cost = len(blocks) * 0.1
            return int(base_cost + block_cost)
        except Exception:
            return 1