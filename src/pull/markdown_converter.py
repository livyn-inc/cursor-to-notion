#!/usr/bin/env python3

"""
Markdown conversion for pull operations
"""

import os
import re
from typing import List, Dict, Any, Optional, Tuple
from notion_client import Client

from c2n_core.utils import extract_id_from_url_strict
from c2n_core.notion_api.blocks import get_block_children


class MarkdownConverter:
    """Handles markdown conversion for pull operations"""
    
    def __init__(self, client: Client, root_dir: str, root_meta: Dict[str, Any]):
        self.client = client
        self.root_dir = root_dir
        self.root_meta = root_meta
    
    def convert_page_to_markdown(self, page_url: str, include_children: bool = True) -> str:
        """Convert Notion page to markdown"""
        try:
            # Fetch page info
            page_info = self._fetch_page_info(page_url)
            if not page_info:
                return ""
            
            # ✅ FIX: Skip page title - only keep content
            # Page title is managed by filename, not markdown content
            markdown = ""
            
            # ✅ FIX: Skip page properties metadata (only keep content)
            # properties = page_info.get("properties", {})
            # if properties:
            #     markdown += self._convert_properties_to_markdown(properties)
            #     markdown += "\n"
            
            # Convert page blocks to markdown
            blocks = self._fetch_page_blocks(page_url)
            if blocks:
                markdown += self._convert_blocks_to_markdown(blocks)
            
            # Add child pages if requested
            if include_children:
                child_pages = self._fetch_child_pages(page_url)
                if child_pages:
                    markdown += "\n## Child Pages\n\n"
                    for child in child_pages:
                        child_title = child.get("title", "Untitled")
                        child_url = child.get("url", "")
                        markdown += f"- [{child_title}]({child_url})\n"
            
            return markdown
        except Exception as e:
            print(f"Failed to convert page to markdown: {e}")
            return ""
    
    def _fetch_page_info(self, page_url: str) -> Optional[Dict[str, Any]]:
        """Fetch page information"""
        try:
            page_id = extract_id_from_url_strict(page_url)
            if not page_id:
                return None
            
            from c2n_core.notion_api.pages import get_page
            page = get_page(self.client, page_id)
            return page
        except Exception:
            return None
    
    def _fetch_page_blocks(self, page_url: str) -> List[Dict[str, Any]]:
        """Fetch page blocks"""
        try:
            page_id = extract_id_from_url_strict(page_url)
            if not page_id:
                return []
            
            blocks = get_block_children(self.client, page_id)
            return blocks or []
        except Exception:
            return []
    
    def _fetch_child_pages(self, page_url: str) -> List[Dict[str, Any]]:
        """Fetch child pages"""
        try:
            page_id = extract_id_from_url_strict(page_url)
            if not page_id:
                return []
            
            from c2n_core.notion_api.pages import get_page_children
            children = get_page_children(self.client, page_id)
            if not children:
                return []
            
            # Filter for pages only
            pages = []
            for child in children:
                if child.get("object") == "page":
                    pages.append({
                        "title": self._extract_page_title(child),
                        "url": f"https://www.notion.so/{child.get('id', '').replace('-', '')}",
                    })
            
            return pages
        except Exception:
            return []
    
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
    
    def _convert_properties_to_markdown(self, properties: Dict[str, Any]) -> str:
        """Convert page properties to markdown"""
        try:
            markdown = ""
            
            for prop_name, prop_value in properties.items():
                if prop_name in ["title", "Name", "名前", "Title"]:
                    continue  # Skip title properties
                
                markdown += f"**{prop_name}**: "
                
                if isinstance(prop_value, dict):
                    if "rich_text" in prop_value:
                        rich_text = prop_value["rich_text"]
                        if isinstance(rich_text, list):
                            text_content = ""
                            for item in rich_text:
                                if isinstance(item, dict) and "text" in item:
                                    text_content += item["text"]["content"]
                            markdown += text_content
                        else:
                            markdown += str(rich_text)
                    elif "title" in prop_value:
                        title = prop_value["title"]
                        if isinstance(title, list):
                            text_content = ""
                            for item in title:
                                if isinstance(item, dict) and "text" in item:
                                    text_content += item["text"]["content"]
                            markdown += text_content
                        else:
                            markdown += str(title)
                    elif "select" in prop_value:
                        select = prop_value["select"]
                        if isinstance(select, dict) and "name" in select:
                            markdown += select["name"]
                        else:
                            markdown += str(select)
                    elif "multi_select" in prop_value:
                        multi_select = prop_value["multi_select"]
                        if isinstance(multi_select, list):
                            names = [item.get("name", "") for item in multi_select if isinstance(item, dict)]
                            markdown += ", ".join(names)
                        else:
                            markdown += str(multi_select)
                    elif "date" in prop_value:
                        date = prop_value["date"]
                        if isinstance(date, dict) and "start" in date:
                            markdown += date["start"]
                        else:
                            markdown += str(date)
                    elif "checkbox" in prop_value:
                        checkbox = prop_value["checkbox"]
                        markdown += "✓" if checkbox else "✗"
                    elif "number" in prop_value:
                        number = prop_value["number"]
                        markdown += str(number)
                    elif "url" in prop_value:
                        url = prop_value["url"]
                        markdown += f"[{url}]({url})"
                    elif "email" in prop_value:
                        email = prop_value["email"]
                        markdown += email
                    elif "phone_number" in prop_value:
                        phone = prop_value["phone_number"]
                        markdown += phone
                    else:
                        markdown += str(prop_value)
                else:
                    markdown += str(prop_value)
                
                markdown += "\n"
            
            return markdown
        except Exception as e:
            print(f"Failed to convert properties to markdown: {e}")
            return ""
    
    def _convert_blocks_to_markdown(self, blocks: List[Dict[str, Any]]) -> str:
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
        """Convert a single Notion block to markdown"""
        try:
            block_type = block.get("type", "")
            
            if block_type == "paragraph":
                return self._convert_paragraph_block(block)
            elif block_type == "heading_1":
                return self._convert_heading_block(block, 1)
            elif block_type == "heading_2":
                return self._convert_heading_block(block, 2)
            elif block_type == "heading_3":
                return self._convert_heading_block(block, 3)
            elif block_type == "bulleted_list_item":
                return self._convert_bulleted_list_item(block)
            elif block_type == "numbered_list_item":
                return self._convert_numbered_list_item(block)
            elif block_type == "to_do":
                return self._convert_todo_block(block)
            elif block_type == "toggle":
                return self._convert_toggle_block(block)
            elif block_type == "code":
                return self._convert_code_block(block)
            elif block_type == "quote":
                return self._convert_quote_block(block)
            elif block_type == "callout":
                return self._convert_callout_block(block)
            elif block_type == "divider":
                return "---"
            elif block_type == "table":
                return self._convert_table_block(block)
            elif block_type == "image":
                return self._convert_image_block(block)
            elif block_type == "video":
                return self._convert_video_block(block)
            elif block_type == "file":
                return self._convert_file_block(block)
            elif block_type == "bookmark":
                return self._convert_bookmark_block(block)
            elif block_type == "link_preview":
                return self._convert_link_preview_block(block)
            elif block_type == "equation":
                return self._convert_equation_block(block)
            elif block_type == "child_page":
                return self._convert_child_page_block(block)
            elif block_type == "child_database":
                return self._convert_child_database_block(block)
            else:
                return f"<!-- Unknown block type: {block_type} -->"
        except Exception as e:
            print(f"Failed to convert block to markdown: {e}")
            return ""
    
    def _convert_paragraph_block(self, block: Dict[str, Any]) -> str:
        """Convert paragraph block to markdown"""
        try:
            paragraph = block.get("paragraph", {})
            rich_text = paragraph.get("rich_text", [])
            
            if not rich_text:
                return ""
            
            text_content = ""
            for item in rich_text:
                if isinstance(item, dict) and "text" in item:
                    text_item = item["text"]
                    content = text_item.get("content", "")
                    
                    # Apply formatting
                    annotations = text_item.get("annotations", {})
                    if annotations.get("bold"):
                        content = f"**{content}**"
                    if annotations.get("italic"):
                        content = f"*{content}*"
                    if annotations.get("strikethrough"):
                        content = f"~~{content}~~"
                    if annotations.get("underline"):
                        content = f"<u>{content}</u>"
                    if annotations.get("code"):
                        content = f"`{content}`"
                    
                    # Handle links
                    if "link" in text_item and text_item["link"]:
                        link_url = text_item["link"].get("url", "")
                        content = f"[{content}]({link_url})"
                    
                    text_content += content
            
            return text_content
        except Exception:
            return ""
    
    def _convert_heading_block(self, block: Dict[str, Any], level: int) -> str:
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
    
    def _convert_bulleted_list_item(self, block: Dict[str, Any]) -> str:
        """Convert bulleted list item to markdown"""
        try:
            bulleted_list_item = block.get("bulleted_list_item", {})
            rich_text = bulleted_list_item.get("rich_text", [])
            
            if not rich_text:
                return ""
            
            text_content = ""
            for item in rich_text:
                if isinstance(item, dict) and "text" in item:
                    text_content += item["text"].get("content", "")
            
            return f"- {text_content}"
        except Exception:
            return ""
    
    def _convert_numbered_list_item(self, block: Dict[str, Any]) -> str:
        """Convert numbered list item to markdown"""
        try:
            numbered_list_item = block.get("numbered_list_item", {})
            rich_text = numbered_list_item.get("rich_text", [])
            
            if not rich_text:
                return ""
            
            text_content = ""
            for item in rich_text:
                if isinstance(item, dict) and "text" in item:
                    text_content += item["text"].get("content", "")
            
            return f"1. {text_content}"
        except Exception:
            return ""
    
    def _convert_todo_block(self, block: Dict[str, Any]) -> str:
        """Convert to-do block to markdown"""
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
    
    def _convert_toggle_block(self, block: Dict[str, Any]) -> str:
        """Convert toggle block to markdown"""
        try:
            toggle = block.get("toggle", {})
            rich_text = toggle.get("rich_text", [])
            
            if not rich_text:
                return ""
            
            text_content = ""
            for item in rich_text:
                if isinstance(item, dict) and "text" in item:
                    text_content += item["text"].get("content", "")
            
            return f"<details>\n<summary>{text_content}</summary>\n\n</details>"
        except Exception:
            return ""
    
    def _convert_code_block(self, block: Dict[str, Any]) -> str:
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
    
    def _convert_quote_block(self, block: Dict[str, Any]) -> str:
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
    
    def _convert_callout_block(self, block: Dict[str, Any]) -> str:
        """Convert callout block to markdown"""
        try:
            callout = block.get("callout", {})
            rich_text = callout.get("rich_text", [])
            icon = callout.get("icon", {})
            
            if not rich_text:
                return ""
            
            text_content = ""
            for item in rich_text:
                if isinstance(item, dict) and "text" in item:
                    text_content += item["text"].get("content", "")
            
            # Extract icon emoji if available
            icon_emoji = ""
            if isinstance(icon, dict) and "emoji" in icon:
                icon_emoji = icon["emoji"]
            
            return f"> {icon_emoji} **Callout**: {text_content}"
        except Exception:
            return ""
    
    def _convert_table_block(self, block: Dict[str, Any]) -> str:
        """Convert table block to markdown"""
        try:
            table = block.get("table", {})
            # This would require fetching table rows
            # For now, return a placeholder
            return "<!-- Table content would be here -->"
        except Exception:
            return ""
    
    def _convert_image_block(self, block: Dict[str, Any]) -> str:
        """Convert image block to markdown"""
        try:
            image = block.get("image", {})
            caption = image.get("caption", [])
            
            # Extract image URL
            image_url = ""
            if "external" in image:
                image_url = image["external"].get("url", "")
            elif "file" in image:
                image_url = image["file"].get("url", "")
            
            # Extract caption text
            caption_text = ""
            for item in caption:
                if isinstance(item, dict) and "text" in item:
                    caption_text += item["text"].get("content", "")
            
            if caption_text:
                return f"![{caption_text}]({image_url})"
            else:
                return f"![]({image_url})"
        except Exception:
            return ""
    
    def _convert_video_block(self, block: Dict[str, Any]) -> str:
        """Convert video block to markdown"""
        try:
            video = block.get("video", {})
            caption = video.get("caption", [])
            
            # Extract video URL
            video_url = ""
            if "external" in video:
                video_url = video["external"].get("url", "")
            elif "file" in video:
                video_url = video["file"].get("url", "")
            
            # Extract caption text
            caption_text = ""
            for item in caption:
                if isinstance(item, dict) and "text" in item:
                    caption_text += item["text"].get("content", "")
            
            if caption_text:
                return f"[{caption_text}]({video_url})"
            else:
                return f"[Video]({video_url})"
        except Exception:
            return ""
    
    def _convert_file_block(self, block: Dict[str, Any]) -> str:
        """Convert file block to markdown"""
        try:
            file_block = block.get("file", {})
            caption = file_block.get("caption", [])
            
            # Extract file URL
            file_url = ""
            if "external" in file_block:
                file_url = file_block["external"].get("url", "")
            elif "file" in file_block:
                file_url = file_block["file"].get("url", "")
            
            # Extract caption text
            caption_text = ""
            for item in caption:
                if isinstance(item, dict) and "text" in item:
                    caption_text += item["text"].get("content", "")
            
            if caption_text:
                return f"[{caption_text}]({file_url})"
            else:
                return f"[File]({file_url})"
        except Exception:
            return ""
    
    def _convert_bookmark_block(self, block: Dict[str, Any]) -> str:
        """Convert bookmark block to markdown"""
        try:
            bookmark = block.get("bookmark", {})
            caption = bookmark.get("caption", [])
            url = bookmark.get("url", "")
            
            # Extract caption text
            caption_text = ""
            for item in caption:
                if isinstance(item, dict) and "text" in item:
                    caption_text += item["text"].get("content", "")
            
            if caption_text:
                return f"[{caption_text}]({url})"
            else:
                return f"[Bookmark]({url})"
        except Exception:
            return ""
    
    def _convert_link_preview_block(self, block: Dict[str, Any]) -> str:
        """Convert link preview block to markdown"""
        try:
            link_preview = block.get("link_preview", {})
            url = link_preview.get("url", "")
            
            return f"[Link Preview]({url})"
        except Exception:
            return ""
    
    def _convert_equation_block(self, block: Dict[str, Any]) -> str:
        """Convert equation block to markdown"""
        try:
            equation = block.get("equation", {})
            expression = equation.get("expression", "")
            
            return f"$${expression}$$"
        except Exception:
            return ""
    
    def _convert_child_page_block(self, block: Dict[str, Any]) -> str:
        """Convert child page block to markdown"""
        try:
            child_page = block.get("child_page", {})
            title = child_page.get("title", "Untitled")
            
            return f"[[{title}]]"
        except Exception:
            return ""
    
    def _convert_child_database_block(self, block: Dict[str, Any]) -> str:
        """Convert child database block to markdown"""
        try:
            child_database = block.get("child_database", {})
            title = child_database.get("title", "Untitled Database")
            
            return f"[[Database: {title}]]"
        except Exception:
            return ""