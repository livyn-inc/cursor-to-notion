"""
Notion階層構造の取得・操作

このモジュールは、Notionのページ階層を操作するための関数を提供します。
v2.1のworkspace自動検出機能の中核となります。
"""
from __future__ import annotations

from notion_client import Client
from typing import Optional, Dict, Any
import os
import datetime


def get_parent_page_url(page_id: str, notion_client: Optional[Client] = None) -> Optional[str]:
    """
    指定されたページの親ページURLを取得
    
    Args:
        page_id: 対象ページのID（ハイフンあり・なし両対応）
        notion_client: Notion APIクライアント（省略時は自動生成）
    
    Returns:
        親ページのURL（親がページでない場合はNone）
    
    Raises:
        ValueError: NOTION_TOKENが設定されていない、またはページの取得に失敗
    """
    if notion_client is None:
        token = os.environ.get('NOTION_TOKEN') or os.environ.get('NOTION_API_KEY')
        if not token:
            raise ValueError("NOTION_TOKEN が環境変数に設定されていません")
        notion_client = Client(auth=token)
    
    try:
        # ページ情報を取得
        page = notion_client.pages.retrieve(page_id=page_id)
        
        # 親情報を確認
        parent = page.get('parent', {})
        parent_type = parent.get('type')
        
        if parent_type == 'page_id':
            parent_id = parent.get('page_id')
            # 親ページのURLを取得
            parent_page = notion_client.pages.retrieve(page_id=parent_id)
            return parent_page.get('url')
        elif parent_type == 'workspace':
            # ワークスペース直下の場合
            return None
        elif parent_type == 'database_id':
            # データベース配下の場合（稀なケース）
            return None
        else:
            return None
            
    except Exception as e:
        raise ValueError(f"親ページの取得に失敗しました: {e}")


def get_page_hierarchy(page_id: str, notion_client: Optional[Client] = None) -> Dict[str, Any]:
    """
    ページの階層情報を詳細に取得
    
    Args:
        page_id: 対象ページのID
        notion_client: Notion APIクライアント（省略時は自動生成）
    
    Returns:
        {
            'page_id': str,
            'page_url': str,
            'page_title': str,
            'parent_id': Optional[str],
            'parent_url': Optional[str],
            'parent_type': str,  # 'page_id', 'workspace', 'database_id'
            'icon': Optional[Dict],
            'created_time': str,
            'last_edited_time': str,
        }
    
    Raises:
        ValueError: ページ情報の取得に失敗
    """
    if notion_client is None:
        token = os.environ.get('NOTION_TOKEN') or os.environ.get('NOTION_API_KEY')
        if not token:
            raise ValueError("NOTION_TOKEN が環境変数に設定されていません")
        notion_client = Client(auth=token)
    
    try:
        page = notion_client.pages.retrieve(page_id=page_id)
        parent = page.get('parent', {})
        parent_type = parent.get('type')
        
        # タイトルを取得（複数のプロパティ名から試行）
        title = 'Untitled'
        properties = page.get('properties', {})
        
        # よくあるプロパティ名をチェック
        for prop_name in ['title', 'Title', 'Name', '名前', 'タイトル']:
            if prop_name in properties:
                title_prop = properties[prop_name]
                if title_prop.get('type') == 'title' and title_prop.get('title'):
                    title_array = title_prop['title']
                    if title_array and len(title_array) > 0:
                        title = title_array[0].get('plain_text', 'Untitled')
                        break
        
        # 結果を構築
        result = {
            'page_id': page_id,
            'page_url': page.get('url'),
            'page_title': title,
            'parent_type': parent_type,
            'parent_id': None,
            'parent_url': None,
            'icon': page.get('icon'),
            'created_time': page.get('created_time'),
            'last_edited_time': page.get('last_edited_time'),
        }
        
        # 親ページ情報を取得
        if parent_type == 'page_id':
            parent_id = parent.get('page_id')
            result['parent_id'] = parent_id
            
            # 親ページのURLを取得
            try:
                parent_page = notion_client.pages.retrieve(page_id=parent_id)
                result['parent_url'] = parent_page.get('url')
            except Exception:
                # 親ページの取得に失敗しても続行
                pass
        
        return result
        
    except Exception as e:
        raise ValueError(f"ページ階層情報の取得に失敗しました: {e}")


def create_folder_page(
    parent_url: str, 
    title: str, 
    icon_emoji: str = "📁",
    notion_client: Optional[Client] = None
) -> Dict[str, Any]:
    """
    親ページ配下に新規フォルダページを作成
    
    Args:
        parent_url: 親ページのURL
        title: 作成するフォルダページのタイトル
        icon_emoji: フォルダアイコン（デフォルト: 📁）
        notion_client: Notion APIクライアント（省略時は自動生成）
    
    Returns:
        {
            'id': str,
            'url': str,
            'title': str,
        }
    
    Raises:
        ValueError: フォルダページの作成に失敗
    """
    if notion_client is None:
        token = os.environ.get('NOTION_TOKEN') or os.environ.get('NOTION_API_KEY')
        if not token:
            raise ValueError("NOTION_TOKEN が環境変数に設定されていません")
        notion_client = Client(auth=token)
    
    try:
        # URLから親ページIDを抽出
        from c2n_core.utils import extract_id_from_url
        parent_id = extract_id_from_url(parent_url)
        if not parent_id:
            raise ValueError(f"無効な親ページURL: {parent_url}")
        
        # 新規ページを作成
        new_page = notion_client.pages.create(
            parent={"page_id": parent_id},
            properties={
                "title": {
                    "title": [{"text": {"content": title}}]
                }
            },
            icon={"type": "emoji", "emoji": icon_emoji}
        )
        
        return {
            'id': new_page['id'],
            'url': new_page['url'],
            'title': title,
        }
        
    except Exception as e:
        raise ValueError(f"フォルダページの作成に失敗しました: {e}")


def get_page_title(page_id: str, notion_client: Optional[Client] = None) -> str:
    """
    ページのタイトルを取得
    
    Args:
        page_id: 対象ページのID
        notion_client: Notion APIクライアント（省略時は自動生成）
    
    Returns:
        ページタイトル
    
    Raises:
        ValueError: ページ情報の取得に失敗
    """
    hierarchy = get_page_hierarchy(page_id, notion_client)
    return hierarchy['page_title']


def validate_page_exists(page_url: str, notion_client: Optional[Client] = None) -> bool:
    """
    ページが存在するか確認
    
    Args:
        page_url: ページのURL
        notion_client: Notion APIクライアント（省略時は自動生成）
    
    Returns:
        True if page exists, False otherwise
    """
    if notion_client is None:
        token = os.environ.get('NOTION_TOKEN') or os.environ.get('NOTION_API_KEY')
        if not token:
            return False
        notion_client = Client(auth=token)
    
    try:
        from c2n_core.utils import extract_id_from_url
        page_id = extract_id_from_url(page_url)
        if not page_id:
            return False
        
        # ページを取得してみる
        notion_client.pages.retrieve(page_id=page_id)
        return True
        
    except Exception:
        return False

