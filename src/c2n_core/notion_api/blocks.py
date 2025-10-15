"""Notion blocks helpers (list/append/replace)."""
from __future__ import annotations

from typing import Any, Dict, List


def list_children(notion_client, block_id: str, **kwargs) -> Dict[str, Any]:
    return notion_client.blocks.children.list(block_id=block_id, **kwargs)


def append_children(notion_client, block_id: str, children: List[dict]) -> Dict[str, Any]:
    return notion_client.blocks.children.append(block_id=block_id, children=children)


def replace_children(notion_client, block_id: str, children: List[dict]) -> None:
    # Notion APIにreplaceは無いが、上位側が分割/削除/追加を調整する想定
    return notion_client.blocks.children.append(block_id=block_id, children=children)


def append_block_children(notion_client, block_id: str, children: List[dict]) -> Dict[str, Any]:
    """Append children to a block (alias for append_children)
    
    ✅ FIX: Notion API制限（1リクエスト最大100ブロック）に対応
    ブロック数が100を超える場合は自動的に分割送信する
    """
    if not children:
        return {"results": []}
    
    # ブロック数が100以下の場合は通常送信
    if len(children) <= 100:
        return append_children(notion_client, block_id, children)
    
    # ブロック数が100を超える場合は分割送信
    print(f"ℹ️  ブロック数が多いため分割送信します: {len(children)}個 → {(len(children) + 99) // 100}回に分割")
    
    results = []
    for i in range(0, len(children), 100):
        batch = children[i:i + 100]
        batch_num = (i // 100) + 1
        total_batches = (len(children) + 99) // 100
        
        print(f"   📦 バッチ {batch_num}/{total_batches}: {len(batch)}ブロックを送信中...")
        
        try:
            result = append_children(notion_client, block_id, batch)
            if result:
                results.append(result)
        except Exception as e:
            print(f"   ❌ バッチ {batch_num} の送信に失敗: {e}")
            # 失敗しても次のバッチは試行する
            continue
    
    # 最後のバッチの結果を返す（互換性のため）
    if results:
        print(f"✅ 分割送信完了: {len(results)}バッチ送信成功")
        return results[-1]
    else:
        print(f"❌ すべてのバッチ送信に失敗")
        return {"results": []}


def delete_block_children(notion_client, block_id: str, block_ids: List[str]) -> None:
    """Delete children blocks from a parent block"""
    for child_id in block_ids:
        try:
            notion_client.blocks.delete(block_id=child_id)
        except Exception:
            # Ignore errors for individual block deletions
            pass


def get_block_children(notion_client, block_id: str) -> List[Dict[str, Any]]:
    """Get children blocks from a parent block"""
    response = list_children(notion_client, block_id)
    return response.get("results", [])


def update_block(notion_client, block_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
    """Update a block with new properties"""
    return notion_client.blocks.update(block_id=block_id, **properties)


