#!/usr/bin/env python3
"""
Notion MCPを使って複数ページを一括取得するスクリプト
cursor-agent CLIの代替として、直接MCPツールを呼び出す
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
import re

def sanitize_filename(title: str) -> str:
    """ファイル名として使える文字列に変換"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        title = title.replace(char, '_')
    # スラッシュを_に
    title = title.replace('/', '_')
    return title.strip()

def extract_from_mcp_response(mcp_response: str) -> dict:
    """MCPレスポンスからメタデータとコンテンツを抽出"""
    result = {
        'title': 'Untitled',
        'page_id': '',
        'parent_id': '',
        'content': ''
    }
    
    # タイトル抽出
    title_match = re.search(r'title="([^"]+)"', mcp_response)
    if title_match:
        result['title'] = title_match.group(1)
    
    # ページID抽出（最初のURL）
    url_match = re.search(r'<page url="{{https://www\.notion\.so/([a-f0-9-]+)}}"', mcp_response)
    if url_match:
        result['page_id'] = url_match.group(1)
    
    # 親ページID抽出
    parent_match = re.search(r'<parent-page url="{{https://www\.notion\.so/([a-f0-9-]+)}}"', mcp_response)
    if parent_match:
        result['parent_id'] = parent_match.group(1)
    
    # コンテンツ抽出
    content_match = re.search(r'<content>(.*?)</content>', mcp_response, re.DOTALL)
    if content_match:
        result['content'] = content_match.group(1).strip()
    
    return result

def call_mcp_notion_fetch(page_id: str) -> str:
    """
    MCPツールを直接呼び出す（Cursor内から実行される想定）
    実際の実装では、Cursor APIを使用する必要がある
    """
    # ここではプレースホルダー
    # 実際にはCursor APIまたはMCPプロトコルを使用
    print(f"⚠️ この関数は Cursor環境内でのみ動作します")
    print(f"   ページID: {page_id}")
    return ""

def save_as_markdown(page_data: dict, output_dir: Path) -> str:
    """取得したページデータをMarkdownファイルとして保存"""
    
    # ファイル名生成
    filename = sanitize_filename(page_data['title']) + '.md'
    filepath = output_dir / filename
    
    # Frontmatter作成
    frontmatter = f"""---
page_id: {page_data['page_id'].replace('-', '')}
page_url: https://notion.so/{page_data['page_id'].replace('-', '')}
parent_id: {page_data['parent_id'].replace('-', '')}
parent_type: page
sync_mode: flat
via: mcp_batch
fetched_at: {datetime.now().isoformat()}
---

"""
    
    # ファイル書き込み
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(frontmatter)
        f.write(f"# {page_data['title']}\n\n")
        f.write(page_data['content'])
    
    file_size = filepath.stat().st_size
    print(f"✅ Saved: {filename} ({file_size:,} bytes)")
    
    return str(filepath)

def main():
    """メイン処理"""
    
    print("""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 Notion MCP Batch Pull Tool
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

使用方法：
1. Cursor環境内で実行
2. MCPレスポンスを標準入力から渡す
3. 出力ディレクトリを指定

例：
  echo '<mcp_response>' | python mcp_batch_pull.py /path/to/output

⚠️ 注意：
このスクリプトは、Cursor環境の外では動作しません。
MCPツールへのアクセスが必要です。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
    
    if len(sys.argv) < 2:
        print("Error: 出力ディレクトリを指定してください")
        print("Usage: python mcp_batch_pull.py <output_dir>")
        sys.exit(1)
    
    output_dir = Path(sys.argv[1])
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 標準入力からMCPレスポンスを読み込み
    print("📥 MCPレスポンスを読み込み中...")
    mcp_response = sys.stdin.read()
    
    if not mcp_response:
        print("Error: MCPレスポンスが空です")
        sys.exit(1)
    
    # データ抽出
    print("🔍 メタデータとコンテンツを抽出中...")
    page_data = extract_from_mcp_response(mcp_response)
    
    if not page_data['page_id']:
        print("Error: ページIDが抽出できませんでした")
        sys.exit(1)
    
    # ファイル保存
    print("💾 Markdownファイルとして保存中...")
    saved_file = save_as_markdown(page_data, output_dir)
    
    print(f"\n✅ 完了！")
    print(f"📁 保存先: {saved_file}")
    print(f"📊 ページID: {page_data['page_id']}")
    print(f"📝 タイトル: {page_data['title']}")

if __name__ == '__main__':
    main()






