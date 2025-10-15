#!/usr/bin/env python3
"""
Notion APIを使用してテストページを作成するスクリプト
"""

import argparse
import json
import os
import sys
from datetime import datetime

try:
    from notion_client import Client
except ImportError:
    print("Error: notion-client package not found. Please install it with: pip install notion-client")
    sys.exit(1)

def create_test_page(notion_token, title, content, parent_url, output_file):
    """Notion APIを使用してテストページを作成"""
    
    # Notionクライアント初期化
    notion = Client(auth=notion_token)
    
    # 親ページIDを抽出
    parent_id = extract_page_id(parent_url)
    if not parent_id:
        raise ValueError(f"Invalid parent URL: {parent_url}")
    
    # ページ作成
    try:
        page = notion.pages.create(
            parent={"page_id": parent_id},
            properties={
                "title": {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                }
            },
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": content
                                }
                            }
                        ]
                    }
                }
            ]
        )
        
        # 結果をファイルに保存
        result = {
            "page_id": page["id"],
            "page_url": page["url"],
            "title": title,
            "created_at": datetime.now().isoformat(),
            "parent_url": parent_url
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"✅ テストページ作成完了: {page['url']}")
        return page["url"]
        
    except Exception as e:
        print(f"❌ ページ作成失敗: {e}")
        raise

def extract_page_id(url):
    """Notion URLからページIDを抽出"""
    if not url:
        return None
    
    # URLからページIDを抽出
    if "notion.so/" in url:
        parts = url.split("notion.so/")
        if len(parts) > 1:
            page_part = parts[1]
            # ハイフンで区切られた部分からページIDを抽出
            if "-" in page_part:
                page_id = page_part.split("-")[-1]
                # 32文字のページIDを確認
                if len(page_id) == 32:
                    return page_id
    
    return None

def main():
    parser = argparse.ArgumentParser(description="Create a test page in Notion")
    parser.add_argument("--title", required=True, help="Page title")
    parser.add_argument("--content", required=True, help="Page content")
    parser.add_argument("--parent-url", required=True, help="Parent page URL")
    parser.add_argument("--output-file", required=True, help="Output JSON file")
    
    args = parser.parse_args()
    
    # 環境変数からNotionトークンを取得
    notion_token = os.getenv("NOTION_TOKEN")
    if not notion_token:
        print("❌ NOTION_TOKEN environment variable not set")
        sys.exit(1)
    
    try:
        page_url = create_test_page(
            notion_token=notion_token,
            title=args.title,
            content=args.content,
            parent_url=args.parent_url,
            output_file=args.output_file
        )
        print(f"📄 作成されたページ: {page_url}")
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()





