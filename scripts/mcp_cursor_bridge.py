#!/usr/bin/env python3
"""
Cursor MCP Bridge - CursorのMCP設定を使ってPythonから呼び出す
"""
import subprocess
import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional

def load_cursor_mcp_config() -> Dict:
    """CursorのMCP設定を読み込む"""
    config_path = Path.home() / 'Library/Application Support/Cursor/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json'
    
    if not config_path.exists():
        raise FileNotFoundError(f"Cursor MCP config not found: {config_path}")
    
    with open(config_path) as f:
        return json.load(f)

def find_notion_mcp_command() -> tuple[str, Dict[str, str]]:
    """Notion MCPのコマンドと環境変数を取得"""
    config = load_cursor_mcp_config()
    
    # Notion MCPサーバーを探す
    for server_name, server_config in config.get('mcpServers', {}).items():
        if 'notion' in server_name.lower():
            command = server_config.get('command', 'npx')
            args = server_config.get('args', [])
            env = server_config.get('env', {})
            
            # コマンドライン構築
            if args:
                full_command = f"{command} {' '.join(args)}"
            else:
                full_command = command
                
            return full_command, env
    
    # デフォルト: Notion公式MCPサーバー
    return 'npx -y @notionhq/notion-mcp-server', {}

def call_mcp_stdio(page_id: str, output_file: str):
    """stdio経由でMCPサーバーを呼び出してページを保存"""
    
    # コマンドと環境変数を取得
    try:
        command, mcp_env = find_notion_mcp_command()
    except FileNotFoundError:
        # Cursor設定がない場合はデフォルト
        command = 'npx -y @notionhq/notion-mcp-server'
        mcp_env = {}
    
    # 環境変数にNOTION_TOKENを追加
    env = os.environ.copy()
    env.update(mcp_env)
    
    if 'NOTION_TOKEN' in os.environ:
        env['NOTION_API_TOKEN'] = os.environ['NOTION_TOKEN']
    
    print(f"[MCP] Starting server: {command}", file=sys.stderr)
    print(f"[MCP] Environment: {list(env.keys())}", file=sys.stderr)
    
    # MCPサーバー起動
    process = subprocess.Popen(
        command,
        shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True
    )
    
    # JSON-RPC 2.0リクエスト
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "notion-fetch",
            "arguments": {
                "id": page_id
            }
        }
    }
    
    try:
        # リクエスト送信
        stdout, stderr = process.communicate(
            input=json.dumps(request) + '\n',
            timeout=30
        )
        
        print(f"[MCP] Response received ({len(stdout)} chars)", file=sys.stderr)
        
        # レスポンス解析
        for line in stdout.split('\n'):
            if not line.strip():
                continue
            try:
                response = json.loads(line)
                if 'result' in response:
                    content = response['result'].get('content', [])
                    if content:
                        # Markdown内容を保存
                        markdown = content[0].get('text', '')
                        with open(output_file, 'w', encoding='utf-8') as f:
                            f.write(markdown)
                        print(f"[MCP] Saved to: {output_file}", file=sys.stderr)
                        return True
            except json.JSONDecodeError:
                continue
        
        print(f"[MCP] No valid response. stderr: {stderr}", file=sys.stderr)
        return False
        
    except subprocess.TimeoutExpired:
        process.kill()
        print("[MCP] Timeout!", file=sys.stderr)
        return False
    finally:
        process.terminate()

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python mcp_cursor_bridge.py <page_id> <output_file>")
        sys.exit(1)
    
    page_id = sys.argv[1]
    output_file = sys.argv[2]
    
    success = call_mcp_stdio(page_id, output_file)
    sys.exit(0 if success else 1)






