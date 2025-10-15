#!/usr/bin/env python3
"""
Notion MCP Client - PythonからNotion MCPサーバーをstdio経由で呼び出す
"""
import subprocess
import json
import sys
from typing import Dict, Any, Optional

class NotionMCPClient:
    def __init__(self, notion_token: str):
        self.notion_token = notion_token
        self.process = None
        
    def start_server(self):
        """MCPサーバーをstdio経由で起動"""
        env = {
            'NOTION_API_TOKEN': self.notion_token,
            'PATH': subprocess.os.environ.get('PATH', '')
        }
        
        self.process = subprocess.Popen(
            ['npx', '-y', '@notionhq/notion-mcp-server'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            bufsize=1
        )
        
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict]:
        """MCPツールを呼び出す"""
        if not self.process:
            self.start_server()
            
        # JSON-RPC 2.0 リクエスト形式
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        try:
            # リクエスト送信
            self.process.stdin.write(json.dumps(request) + '\n')
            self.process.stdin.flush()
            
            # レスポンス受信
            response_line = self.process.stdout.readline()
            response = json.loads(response_line)
            
            return response.get('result')
        except Exception as e:
            print(f"Error calling MCP tool: {e}", file=sys.stderr)
            return None
            
    def get_page(self, page_id: str) -> Optional[str]:
        """NotionページをMarkdownで取得"""
        result = self.call_tool('fetch_page_content', {'page_id': page_id})
        if result and 'content' in result:
            return result['content']
        return None
        
    def close(self):
        """MCPサーバーを終了"""
        if self.process:
            self.process.terminate()
            self.process.wait()

# 使用例
if __name__ == '__main__':
    import os
    
    # 環境変数からトークン取得
    token = os.environ.get('NOTION_TOKEN')
    if not token:
        print("Error: NOTION_TOKEN environment variable not set")
        sys.exit(1)
    
    # コマンドライン引数からページID取得
    if len(sys.argv) < 2:
        print("Usage: python mcp_notion_client.py <page_id>")
        sys.exit(1)
        
    page_id = sys.argv[1]
    
    # MCPクライアント実行
    client = NotionMCPClient(token)
    try:
        content = client.get_page(page_id)
        if content:
            print(content)
        else:
            print("Failed to fetch page content")
    finally:
        client.close()






