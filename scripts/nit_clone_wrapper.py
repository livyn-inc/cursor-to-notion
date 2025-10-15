#!/usr/bin/env python3
"""
Nit Clone Repository Wrapper
URLのクォート問題を解決するためのPythonラッパー
"""
import sys
import subprocess
from pathlib import Path

# パス設定
VENV_PYTHON = "/Users/daisukemiyata/aipm_v3/Stock/programs/Tools/projects/cursor_to_notion/venv_cursor_notion/bin/python"
C2N_PATH = "/Users/daisukemiyata/aipm_v3/Stock/programs/Tools/projects/cursor_to_notion/dev/c2n.py"

def main():
    if len(sys.argv) < 3:
        print("使用方法: nit_clone_wrapper.py <NOTION_URL> <CLONE_DIR> [FOLDER_NAME]")
        sys.exit(1)
    
    notion_url = sys.argv[1]
    clone_dir = sys.argv[2]
    folder_name = sys.argv[3] if len(sys.argv) > 3 else ""
    
    print("🚀 Notionページをクローンしています...")
    print(f"📍 URL: {notion_url}")
    print(f"📂 保存先ディレクトリ: {clone_dir}")
    print(f"📁 フォルダ名: {folder_name if folder_name else '（Notionページタイトルを使用）'}")
    print("")
    
    # コマンドを構築
    cmd = [VENV_PYTHON, C2N_PATH, "repo", "clone", notion_url, "--dir", clone_dir]
    
    if folder_name:
        cmd.extend(["--name", folder_name])
    
    # 実行
    try:
        result = subprocess.run(cmd, check=True)
        print("")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("✅ クローン完了！")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("")
        print("💡 次のステップ:")
        print("   Nit: Push to Notion でNotionに同期")
        print("")
    except subprocess.CalledProcessError as e:
        print(f"❌ エラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()




