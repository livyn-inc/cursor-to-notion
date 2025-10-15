#!/usr/bin/env python3
"""
Notion MCP を使ってページをMarkdownファイルとして取得するスクリプト
notion2md.py の代替として、MCP経由でコンテンツを取得する
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def sanitize_filename(title: str) -> str:
    """ファイル名として使える文字列に変換"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        title = title.replace(char, '_')
    return title.strip()

def parse_mcp_response(mcp_output: str) -> dict:
    """MCP出力からページ情報を抽出"""
    # MCPレスポンスからタイトルとコンテンツを抽出
    title = "Untitled"
    content = mcp_output
    page_id = ""
    
    # タイトル抽出（<page title="...">）
    if '<page url="{{https://www.notion.so/' in mcp_output:
        start = mcp_output.find('title="') + 7
        end = mcp_output.find('"', start)
        if start > 6 and end > start:
            title = mcp_output[start:end]
        
        # ページID抽出
        url_start = mcp_output.find('https://www.notion.so/') + 22
        url_end = mcp_output.find('}}"', url_start)
        if url_start > 21 and url_end > url_start:
            page_id = mcp_output[url_start:url_end]
    
    # コンテンツ部分を抽出（<content>...</content>）
    content_start = mcp_output.find('<content>')
    content_end = mcp_output.find('</content>')
    if content_start != -1 and content_end != -1:
        content = mcp_output[content_start + 9:content_end].strip()
    
    return {
        'title': title,
        'content': content,
        'page_id': page_id
    }

def collect_child_page_ids(mcp_output: str) -> list:
    """MCP出力から子ページIDを抽出"""
    child_ids = []
    
    # <page url="{{https://www.notion.so/...}}"> パターンを検索
    import re
    pattern = r'<page url="{{https://www\.notion\.so/([a-f0-9-]+)}}">'
    matches = re.findall(pattern, mcp_output)
    
    for page_id in matches:
        # ダッシュなしIDに正規化
        normalized_id = page_id.replace('-', '')
        child_ids.append(normalized_id)
    
    return child_ids

def fetch_page_via_mcp(page_url: str) -> str:
    """Notion MCPでページを取得（実際はMCP呼び出しをシミュレート）"""
    # 実際にはMCPツールを呼び出す必要があるが、ここではプレースホルダー
    # 実運用ではmcp_Notion_notion-fetchツールを使用
    logging.info(f"Fetching page via MCP: {page_url}")
    return ""

def create_markdown_file(page_data: dict, output_dir: Path, flat_mode: bool = True):
    """Markdownファイルを作成"""
    title = page_data['title']
    content = page_data['content']
    page_id = page_data['page_id']
    
    # ファイル名生成
    filename = sanitize_filename(title) + '.md'
    filepath = output_dir / filename
    
    # Frontmatter作成（Flat Mode用）
    frontmatter = f"""---
page_id: {page_id}
page_url: https://notion.so/{page_id}
sync_mode: flat
fetched_at: {datetime.now().isoformat()}
via: notion_mcp
---

"""
    
    # ファイル書き込み
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(frontmatter)
        f.write(f"# {title}\n\n")
        f.write(content)
    
    file_size = filepath.stat().st_size
    logging.info(f"✅ Created: {filename} ({file_size} bytes)")
    
    return str(filepath)

def main():
    parser = argparse.ArgumentParser(description='Notion MCP経由でページをMarkdownに変換')
    parser.add_argument('page_url', help='NotionページのURL')
    parser.add_argument('-o', '--output', default='.', help='出力ディレクトリ')
    parser.add_argument('--flat-mode', action='store_true', help='Flat Mode（全ページを1階層に）')
    parser.add_argument('--recursive', action='store_true', help='子ページも再帰的に取得')
    
    args = parser.parse_args()
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logging.info(f"📄 Output directory: {output_dir}")
    logging.info(f"🔄 Mode: {'Flat' if args.flat_mode else 'Hierarchy'}")
    
    # このスクリプトはMCPツールと連携して使用する必要があることを通知
    print("""
⚠️ このスクリプトはNotion MCPツールと連携して動作します。

使用方法：
1. Cursor/AIエージェントから、mcp_Notion_notion-fetch ツールでページを取得
2. 取得したMCP出力をこのスクリプトに渡す

または、直接AIエージェントに以下のように依頼してください：
「Notion MCP を使って {page_url} をMarkdownファイルとして保存して」
""")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())






