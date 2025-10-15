#!/usr/bin/env python3

"""
Block management for Notion operations
"""

import os
import time
from typing import List, Dict, Any, Optional, Tuple
from notion_client import Client

from c2n_core.utils import extract_id_from_url_strict
from c2n_core.notion_api.blocks import get_block_children, append_block_children, delete_block_children, update_block


class BlockManager:
    """Handles block management for Notion operations"""
    
    def __init__(self, client: Client, root_dir: str, root_meta: Dict[str, Any]):
        self.client = client
        self.root_dir = root_dir
        self.root_meta = root_meta
    
    def get_page_blocks(self, page_url: str) -> List[Dict[str, Any]]:
        """Get all blocks from a page"""
        try:
            # Extract page ID
            page_id = extract_id_from_url_strict(page_url)
            if not page_id:
                print(f"Invalid page URL: {page_url}")
                return []
            
            # Get page blocks
            blocks = get_block_children(self.client, page_id)
            return blocks or []
            
        except Exception as e:
            print(f"Failed to get page blocks: {e}")
            return []
    
    def add_blocks_to_page(self, page_url: str, blocks: List[Dict[str, Any]]) -> bool:
        """Add blocks to a page"""
        try:
            # Extract page ID
            page_id = extract_id_from_url_strict(page_url)
            if not page_id:
                print(f"Invalid page URL: {page_url}")
                return False
            
            # Add blocks
            result = append_block_children(self.client, page_id, blocks)
            if not result:
                print(f"Failed to add blocks to page: {page_url}")
                return False
            
            print(f"✅ Added {len(blocks)} blocks to page: {page_url}")
            return True
            
        except Exception as e:
            print(f"Failed to add blocks to page: {e}")
            return False
    
    def remove_blocks_from_page(self, page_url: str, block_ids: List[str]) -> bool:
        """Remove blocks from a page"""
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
    
    def update_block(self, block_id: str, block_data: Dict[str, Any]) -> bool:
        """Update a specific block"""
        try:
            # Update block
            result = update_block(self.client, block_id, **block_data)
            if not result:
                print(f"Failed to update block: {block_id}")
                return False
            
            print(f"✅ Updated block: {block_id}")
            return True
            
        except Exception as e:
            print(f"Failed to update block: {e}")
            return False
    
    def create_text_block(self, text: str, annotations: Dict[str, bool] = None) -> Dict[str, Any]:
        """Create a text block"""
        try:
            # Prepare rich text
            rich_text = [{
                "type": "text",
                "text": {
                    "content": text
                }
            }]
            
            # Apply annotations if provided
            if annotations:
                rich_text[0]["annotations"] = annotations
            
            return {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": rich_text
                }
            }
            
        except Exception as e:
            print(f"Failed to create text block: {e}")
            return {}
    
    def create_heading_block(self, text: str, level: int = 1) -> Dict[str, Any]:
        """Create a heading block"""
        try:
            if level < 1 or level > 3:
                level = 1
            
            heading_type = f"heading_{level}"
            
            return {
                "type": heading_type,
                heading_type: {
                    "rich_text": [{
                        "type": "text",
                        "text": {
                            "content": text
                        }
                    }]
                }
            }
            
        except Exception as e:
            print(f"Failed to create heading block: {e}")
            return {}
    
    def create_list_item_block(self, text: str, list_type: str = "bulleted") -> Dict[str, Any]:
        """Create a list item block"""
        try:
            if list_type not in ["bulleted", "numbered"]:
                list_type = "bulleted"
            
            list_key = f"{list_type}_list_item"
            
            return {
                "type": list_key,
                list_key: {
                    "rich_text": [{
                        "type": "text",
                        "text": {
                            "content": text
                        }
                    }]
                }
            }
            
        except Exception as e:
            print(f"Failed to create list item block: {e}")
            return {}
    
    def create_code_block(self, code: str, language: str = "") -> Dict[str, Any]:
        """Create a code block"""
        try:
            return {
                "type": "code",
                "code": {
                    "rich_text": [{
                        "type": "text",
                        "text": {
                            "content": code
                        }
                    }],
                    "language": language
                }
            }
            
        except Exception as e:
            print(f"Failed to create code block: {e}")
            return {}
    
    def create_quote_block(self, text: str) -> Dict[str, Any]:
        """Create a quote block"""
        try:
            return {
                "type": "quote",
                "quote": {
                    "rich_text": [{
                        "type": "text",
                        "text": {
                            "content": text
                        }
                    }]
                }
            }
            
        except Exception as e:
            print(f"Failed to create quote block: {e}")
            return {}
    
    def create_divider_block(self) -> Dict[str, Any]:
        """Create a divider block"""
        try:
            return {
                "type": "divider",
                "divider": {}
            }
            
        except Exception as e:
            print(f"Failed to create divider block: {e}")
            return {}
    
    def create_image_block(self, image_url: str, caption: str = "") -> Dict[str, Any]:
        """Create an image block"""
        try:
            block = {
                "type": "image",
                "image": {
                    "type": "external",
                    "external": {
                        "url": image_url
                    }
                }
            }
            
            if caption:
                block["image"]["caption"] = [{
                    "type": "text",
                    "text": {
                        "content": caption
                    }
                }]
            
            return block
            
        except Exception as e:
            print(f"Failed to create image block: {e}")
            return {}
    
    def create_link_block(self, url: str, text: str = None) -> Dict[str, Any]:
        """Create a link block"""
        try:
            if not text:
                text = url
            
            return {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {
                            "content": text,
                            "link": {
                                "url": url
                            }
                        }
                    }]
                }
            }
            
        except Exception as e:
            print(f"Failed to create link block: {e}")
            return {}
    
    def create_todo_block(self, text: str, checked: bool = False) -> Dict[str, Any]:
        """Create a todo block"""
        try:
            return {
                "type": "to_do",
                "to_do": {
                    "rich_text": [{
                        "type": "text",
                        "text": {
                            "content": text
                        }
                    }],
                    "checked": checked
                }
            }
            
        except Exception as e:
            print(f"Failed to create todo block: {e}")
            return {}
    
    def create_toggle_block(self, text: str) -> Dict[str, Any]:
        """Create a toggle block"""
        try:
            return {
                "type": "toggle",
                "toggle": {
                    "rich_text": [{
                        "type": "text",
                        "text": {
                            "content": text
                        }
                    }]
                }
            }
            
        except Exception as e:
            print(f"Failed to create toggle block: {e}")
            return {}
    
    def create_callout_block(self, text: str, icon: str = "💡") -> Dict[str, Any]:
        """Create a callout block"""
        try:
            return {
                "type": "callout",
                "callout": {
                    "rich_text": [{
                        "type": "text",
                        "text": {
                            "content": text
                        }
                    }],
                    "icon": {
                        "type": "emoji",
                        "emoji": icon
                    }
                }
            }
            
        except Exception as e:
            print(f"Failed to create callout block: {e}")
            return {}
    
    def create_table_block(self, table_data: List[List[str]]) -> Dict[str, Any]:
        """Create a table block"""
        try:
            if not table_data:
                return {}
            
            # Create table structure
            table = {
                "type": "table",
                "table": {
                    "table_width": len(table_data[0]) if table_data else 0,
                    "has_column_header": True,
                    "has_row_header": False
                }
            }
            
            # Add table rows
            table["table"]["children"] = []
            for row_data in table_data:
                row = {
                    "type": "table_row",
                    "table_row": {
                        "cells": []
                    }
                }
                
                for cell_data in row_data:
                    cell = [{
                        "type": "text",
                        "text": {
                            "content": str(cell_data)
                        }
                    }]
                    row["table_row"]["cells"].append(cell)
                
                table["table"]["children"].append(row)
            
            return table
            
        except Exception as e:
            print(f"Failed to create table block: {e}")
            return {}
    
    def convert_markdown_to_blocks(self, markdown_content: str) -> List[Dict[str, Any]]:
        """Convert markdown content to Notion blocks"""
        try:
            from markdown_converter import convert_markdown_to_notion_blocks
            return convert_markdown_to_notion_blocks(markdown_content)
        except Exception as e:
            print(f"Failed to convert markdown to blocks: {e}")
            return []
    
    def convert_blocks_to_markdown(self, blocks: List[Dict[str, Any]]) -> str:
        """Convert Notion blocks to markdown"""
        try:
            markdown = ""
            for block in blocks:
                block_markdown = self._convert_single_block_to_markdown(block)
                if block_markdown:
                    markdown += block_markdown + "\n"
            return markdown
        except Exception as e:
            print(f"Failed to convert blocks to markdown: {e}")
            return ""
    
    def _convert_single_block_to_markdown(self, block: Dict[str, Any]) -> str:
        """Convert a single block to markdown"""
        try:
            block_type = block.get("type", "")
            
            if block_type == "paragraph":
                return self._convert_paragraph_to_markdown(block)
            elif block_type == "heading_1":
                return self._convert_heading_to_markdown(block, 1)
            elif block_type == "heading_2":
                return self._convert_heading_to_markdown(block, 2)
            elif block_type == "heading_3":
                return self._convert_heading_to_markdown(block, 3)
            elif block_type == "bulleted_list_item":
                return self._convert_list_item_to_markdown(block, "bulleted")
            elif block_type == "numbered_list_item":
                return self._convert_list_item_to_markdown(block, "numbered")
            elif block_type == "to_do":
                return self._convert_todo_to_markdown(block)
            elif block_type == "code":
                return self._convert_code_to_markdown(block)
            elif block_type == "quote":
                return self._convert_quote_to_markdown(block)
            elif block_type == "divider":
                return "---"
            else:
                return f"<!-- Unknown block type: {block_type} -->"
        except Exception as e:
            print(f"Failed to convert block to markdown: {e}")
            return ""
    
    def _convert_paragraph_to_markdown(self, block: Dict[str, Any]) -> str:
        """Convert paragraph block to markdown"""
        try:
            paragraph = block.get("paragraph", {})
            rich_text = paragraph.get("rich_text", [])
            
            if not rich_text:
                return ""
            
            text_content = ""
            for item in rich_text:
                if isinstance(item, dict) and "text" in item:
                    text_content += item["text"].get("content", "")
            
            return text_content
        except Exception:
            return ""
    
    def _convert_heading_to_markdown(self, block: Dict[str, Any], level: int) -> str:
        """Convert heading block to markdown"""
        try:
            heading_key = f"heading_{level}"
            heading = block.get(heading_key, {})
            rich_text = heading.get("rich_text", [])
            
            if not rich_text:
                return ""
            
            text_content = ""
            for item in rich_text:
                if isinstance(item, dict) and "text" in item:
                    text_content += item["text"].get("content", "")
            
            return f"{'#' * level} {text_content}"
        except Exception:
            return ""
    
    def _convert_list_item_to_markdown(self, block: Dict[str, Any], list_type: str) -> str:
        """Convert list item block to markdown"""
        try:
            list_key = f"{list_type}_list_item"
            list_item = block.get(list_key, {})
            rich_text = list_item.get("rich_text", [])
            
            if not rich_text:
                return ""
            
            text_content = ""
            for item in rich_text:
                if isinstance(item, dict) and "text" in item:
                    text_content += item["text"].get("content", "")
            
            prefix = "-" if list_type == "bulleted" else "1."
            return f"{prefix} {text_content}"
        except Exception:
            return ""
    
    def _convert_todo_to_markdown(self, block: Dict[str, Any]) -> str:
        """Convert todo block to markdown"""
        try:
            to_do = block.get("to_do", {})
            rich_text = to_do.get("rich_text", [])
            checked = to_do.get("checked", False)
            
            if not rich_text:
                return ""
            
            text_content = ""
            for item in rich_text:
                if isinstance(item, dict) and "text" in item:
                    text_content += item["text"].get("content", "")
            
            checkbox = "- [x]" if checked else "- [ ]"
            return f"{checkbox} {text_content}"
        except Exception:
            return ""
    
    def _convert_code_to_markdown(self, block: Dict[str, Any]) -> str:
        """Convert code block to markdown"""
        try:
            code = block.get("code", {})
            rich_text = code.get("rich_text", [])
            language = code.get("language", "")
            
            if not rich_text:
                return ""
            
            text_content = ""
            for item in rich_text:
                if isinstance(item, dict) and "text" in item:
                    text_content += item["text"].get("content", "")
            
            return f"```{language}\n{text_content}\n```"
        except Exception:
            return ""
    
    def _convert_quote_to_markdown(self, block: Dict[str, Any]) -> str:
        """Convert quote block to markdown"""
        try:
            quote = block.get("quote", {})
            rich_text = quote.get("rich_text", [])
            
            if not rich_text:
                return ""
            
            text_content = ""
            for item in rich_text:
                if isinstance(item, dict) and "text" in item:
                    text_content += item["text"].get("content", "")
            
            return f"> {text_content}"
        except Exception:
            return ""
    
    def get_block_count(self, page_url: str) -> int:
        """Get the number of blocks in a page"""
        try:
            blocks = self.get_page_blocks(page_url)
            return len(blocks)
        except Exception:
            return 0
    
    def get_block_types(self, page_url: str) -> Dict[str, int]:
        """Get the count of each block type in a page"""
        try:
            blocks = self.get_page_blocks(page_url)
            block_types = {}
            
            for block in blocks:
                block_type = block.get("type", "unknown")
                block_types[block_type] = block_types.get(block_type, 0) + 1
            
            return block_types
        except Exception:
            return {}
    
    def validate_blocks(self, blocks: List[Dict[str, Any]]) -> List[str]:
        """Validate blocks and return list of errors"""
        try:
            errors = []
            
            for i, block in enumerate(blocks):
                if not isinstance(block, dict):
                    errors.append(f"Block {i} is not a dictionary")
                    continue
                
                if "type" not in block:
                    errors.append(f"Block {i} missing 'type' field")
                    continue
                
                block_type = block["type"]
                if not isinstance(block_type, str):
                    errors.append(f"Block {i} has invalid 'type' field")
                    continue
            
            return errors
        except Exception as e:
            return [f"Failed to validate blocks: {e}"]
    
    def merge_blocks(self, blocks1: List[Dict[str, Any]], blocks2: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge two lists of blocks"""
        try:
            return blocks1 + blocks2
        except Exception as e:
            print(f"Failed to merge blocks: {e}")
            return blocks1
    
    def filter_blocks_by_type(self, blocks: List[Dict[str, Any]], block_type: str) -> List[Dict[str, Any]]:
        """Filter blocks by type"""
        try:
            return [block for block in blocks if block.get("type") == block_type]
        except Exception:
            return []
    
    def get_block_ids(self, blocks: List[Dict[str, Any]]) -> List[str]:
        """Get all block IDs from a list of blocks"""
        try:
            return [block.get("id") for block in blocks if block.get("id")]
        except Exception:
            return []