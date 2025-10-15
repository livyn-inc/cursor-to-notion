#!/usr/bin/env python3
"""
last_sync_atを現在時刻に一括更新するスクリプト
pull時刻更新ロジックの修正により発生した問題を解決
"""
import os
import sys
import yaml
from datetime import datetime, timezone

def fix_sync_times(target_dir: str):
    """index.yamlのlast_sync_atを現在時刻に更新"""
    index_path = os.path.join(target_dir, '.c2n', 'index.yaml')
    
    if not os.path.exists(index_path):
        print(f"Error: {index_path} not found")
        return False
    
    # 現在時刻をISO形式で取得
    current_time = datetime.now(timezone.utc).isoformat()
    
    print(f"Loading {index_path}...")
    with open(index_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    if not data or 'items' not in data:
        print("Error: Invalid index.yaml format")
        return False
    
    updated_count = 0
    for path, item in data['items'].items():
        if isinstance(item, dict) and item.get('type') == 'file':
            # ファイルアイテムのlast_sync_atを更新
            if 'last_sync_at' in item:
                old_time = item['last_sync_at']
                item['last_sync_at'] = current_time
                print(f"Updated: {os.path.basename(path)} ({old_time} -> {current_time})")
                updated_count += 1
    
    if updated_count == 0:
        print("No files to update")
        return True
    
    # バックアップを作成
    backup_path = f"{index_path}.backup"
    os.rename(index_path, backup_path)
    print(f"Backup created: {backup_path}")
    
    # 更新されたデータを保存
    with open(index_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    print(f"Successfully updated {updated_count} files' sync times")
    return True

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python fix_sync_times.py <target_directory>")
        sys.exit(1)
    
    target = os.path.abspath(sys.argv[1])
    success = fix_sync_times(target)
    sys.exit(0 if success else 1)












