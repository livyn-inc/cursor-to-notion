#!/usr/bin/env python3
"""
Notion MCPレスポンスをMarkdownファイルとして保存するヘルパースクリプト
"""

import sys
import re
from pathlib import Path
from datetime import datetime

def sanitize_filename(title: str) -> str:
    """ファイル名として使える文字列に変換"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        title = title.replace(char, '_')
    return title.strip()

def mcp_to_markdown(mcp_text: str, output_path: Path) -> str:
    """MCPレスポンスをMarkdownファイルに変換"""
    
    # タイトル抽出
    title_match = re.search(r'title="([^"]+)"', mcp_text)
    title = title_match.group(1) if title_match else "Untitled"
    
    # ページID抽出
    url_match = re.search(r'https://www\.notion\.so/([a-f0-9-]+)', mcp_text)
    page_id = url_match.group(1) if url_match else ""
    
    # 親ページID抽出
    parent_match = re.search(r'<parent-page url="{{https://www\.notion\.so/([a-f0-9-]+)}}"', mcp_text)
    parent_id = parent_match.group(1) if parent_match else ""
    
    # コンテンツ抽出
    content_match = re.search(r'<content>(.*?)</content>', mcp_text, re.DOTALL)
    content = content_match.group(1).strip() if content_match else ""
    
    # Frontmatter作成
    frontmatter = f"""---
page_id: {page_id}
page_url: https://notion.so/{page_id.replace('-', '')}
parent_id: {parent_id}
parent_type: page
sync_mode: flat
via: notion_mcp
fetched_at: {datetime.now().isoformat()}
---

"""
    
    # ファイル名生成
    filename = sanitize_filename(title) + '.md'
    filepath = output_path / filename
    
    # ファイル書き込み
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(frontmatter)
        f.write(f"# {title}\n\n")
        f.write(content)
    
    file_size = filepath.stat().st_size
    print(f"✅ Created: {filename} ({file_size:,} bytes)")
    
    return str(filepath)

def main():
    """メイン処理"""
    if len(sys.argv) < 3:
        print("Usage: python save_mcp_content.py <output_dir> <mcp_response_text>")
        print("または標準入力からMCPレスポンスを渡す:")
        print("  echo '<mcp response>' | python save_mcp_content.py <output_dir>")
        sys.exit(1)
    
    output_dir = Path(sys.argv[1])
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # MCPレスポンステキストの取得
    if len(sys.argv) >= 3:
        mcp_text = sys.argv[2]
    else:
        mcp_text = sys.stdin.read()
    
    # 変換実行
    saved_file = mcp_to_markdown(mcp_text, output_dir)
    print(f"📁 Saved to: {saved_file}")

if __name__ == '__main__':
    main()






