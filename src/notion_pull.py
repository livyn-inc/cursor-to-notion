#!/usr/bin/env python3

"""
notion_pull.py - Pull operations for cursor_to_notion tool
"""

import os
import json
import argparse
from notion_client import Client, APIResponseError
from typing import List, Dict, Any, Optional
import re
import logging
from c2n_core.utils import load_config_for_folder, extract_id_from_url_strict
from c2n_core.env import _load_env_file as core_load_env_file, _ensure_notion_env_bridge as core_env_bridge
from c2n_core.notion_api.icons import set_page_icon as core_set_icon, get_page_icon as core_get_icon, auto_set_page_icon as core_auto_icon
from c2n_core.notion_api.pages import get_page as core_get_page, get_database as core_get_database, get_database_entries as core_get_database_entries
from c2n_core.notion_api.blocks import list_children as core_list_children
from c2n_core.logging import load_yaml_file, check_yaml_available

# Import pull components
from pull.page_fetcher import PageFetcher
from pull.markdown_converter import MarkdownConverter

# HTTPリクエストログを抑制するため、notion-clientのログレベルを上げる
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)

# Initialize environment and client
from c2n_core.env import _load_env_for_target as _core_load_env_for_target
_core_load_env_for_target(os.getcwd())
NOTION_TOKEN = os.environ.get("NOTION_TOKEN") or os.environ.get("NOTION_API_KEY")
notion = Client(auth=NOTION_TOKEN)

def load_config():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return load_config_for_folder(os.getcwd(), prefer_c2n=False, script_dir=script_dir)

def _is_folder_page(page_id: str) -> bool:
    """ページが子ページを持つフォルダページかどうかを判定"""
    try:
        response = core_list_children(notion, page_id)
        blocks = response.get('results', [])

        # 子ページ（child_page）があるかチェック
        for block in blocks:
            if block.get('type') == 'child_page':
                return True

        return False
    except Exception as e:
        logging.warning(f"Failed to check if page {page_id} is folder: {e}")
        return False

def _set_page_icon(page_id: str, icon_emoji: str) -> bool:
    return core_set_icon(notion, page_id, icon_emoji)

def _get_page_icon(page_id: str) -> str:
    return core_get_icon(notion, page_id) or None

def _auto_set_page_icon(page_id: str, force_update: bool = False, is_folder: bool = None) -> bool:
    return core_auto_icon(notion, page_id, force_update=force_update, is_folder=is_folder)

def _build_page_hierarchy_path(page_id: str, base_output_dir: str) -> str:
    """ページIDから親ページの階層構造を辿って、適切なディレクトリパスを構築"""
    try:
        # ローカルのルートページIDを取得（.c2n/index.yamlから）
        local_root_page_id = None
        try:
            index_path = os.path.join(os.getcwd(), '.c2n', 'index.yaml')
            if os.path.exists(index_path):
                index = load_yaml_file(index_path, {})
                root_url = index.get('root_page_url', '')
                if root_url:
                        # URLからページIDを抽出
                        match = re.search(r"([a-f0-9]{32}|[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})", root_url)
                        if match:
                            local_root_page_id = match.group(1).replace("-", "")
                            logging.info(f"ローカルルートページID: {local_root_page_id}")
        except Exception as e:
            logging.warning(f"Failed to load root page ID: {e}")
        
        # 親ページの階層を辿る
        hierarchy = []
        current_page_id = page_id
        
        while current_page_id and len(hierarchy) < 10:  # 無限ループ防止
            try:
                page = core_get_page(notion, current_page_id)
                
                # ページタイトルを取得
                title = ""
                props = page.get('properties', {})
                for prop in props.values():
                    if prop.get('type') == 'title':
                        title_array = prop.get('title', [])
                        title = ''.join([t.get('plain_text', '') for t in title_array])
                        break
                
                if title:
                    # ファイル名として安全な文字に変換
                    safe_title = re.sub(r'[<>:"/\\|?*]', '_', title).strip()
                    hierarchy.insert(0, safe_title)
                
                # ローカルルートに到達したら停止
                if local_root_page_id and current_page_id.replace("-", "") == local_root_page_id:
                    logging.info(f"ローカルルートページに到達: {title}")
                    break
                
                # 親ページを取得
                parent = page.get('parent', {})
                if parent.get('type') == 'page_id':
                    current_page_id = parent.get('page_id')
                elif parent.get('type') == 'database_id':
                    # データベースの場合は、そのデータベースの親を確認
                    db_id = parent.get('database_id')
                    try:
                        db = core_get_database(notion, db_id)
                        db_parent = db.get('parent', {})
                        if db_parent.get('type') == 'page_id':
                            current_page_id = db_parent.get('page_id')
                        else:
                            break
                    except Exception:
                        break
                else:
                    break
                    
            except Exception as e:
                logging.warning(f"Failed to retrieve parent for page {current_page_id}: {e}")
                break
        
        # ローカルルートより下の階層のみを使用
        if local_root_page_id and len(hierarchy) > 1:
            # ローカルルートページを階層から除外
            # 最初の要素がローカルルートページの場合は除外
            relative_hierarchy = hierarchy[1:-1] if len(hierarchy) > 2 else []
            
            if relative_hierarchy:
                dir_path = os.path.join(base_output_dir, *relative_hierarchy)
                logging.info(f"相対階層パス構築: {' > '.join(hierarchy)} -> 相対パス: {' > '.join(relative_hierarchy)} -> {dir_path}")
                return dir_path
        
        # フォールバック：ベースディレクトリを返す
        logging.info(f"フォールバック: ベースディレクトリを使用 -> {base_output_dir}")
        return base_output_dir
            
    except Exception as e:
        logging.warning(f"Failed to build hierarchy path for page {page_id}: {e}")
        return None

def _get_page_metadata_flat(page_id: str) -> dict:
    """
    Flat Mode用: ページのメタデータ（親、子、タイトル等）を取得
    """
    try:
        page = core_get_page(notion, page_id)
        
        # タイトル取得
        title = ""
        props = page.get('properties', {})
        for prop in props.values():
            if prop.get('type') == 'title':
                title_array = prop.get('title', [])
                title = ''.join([t.get('plain_text', '') for t in title_array])
                break
        
        # 親ページID取得
        parent_id = None
        parent_type = None
        parent = page.get('parent', {})
        if parent.get('type') == 'page_id':
            parent_id = parent.get('page_id')
            parent_type = 'page'
        elif parent.get('type') == 'database_id':
            parent_id = parent.get('database_id')
            parent_type = 'database'
        
        # 子ページとブロック取得
        children_ids = []
        all_blocks = []
        try:
            children = core_list_children(notion, page_id)
            blocks_list = children.get('results', [])
            logging.debug(f"[Flat Mode] Page {page_id}: Found {len(blocks_list)} blocks")
            for block in blocks_list:
                block_type = block.get('type')
                logging.debug(f"  - Block type: {block_type}, ID: {block.get('id')}")
                if block_type == 'child_page':
                    child_id = block.get('id')
                    children_ids.append(child_id)
                    logging.info(f"  ✓ Found child page: {child_id}")
                else:
                    # 子ページ以外のブロックを保存（コンテンツ用）
                    all_blocks.append(block)
        except Exception as e:
            logging.warning(f"[Flat Mode] Failed to get children for {page_id}: {e}")
        
        return {
            'page_id': page_id,
            'title': title,
            'parent_id': parent_id,
            'parent_type': parent_type,
            'children_ids': children_ids,
            'page_url': f"https://notion.so/{page_id.replace('-', '')}",
            'blocks': all_blocks  # ブロック情報を追加
        }
    except Exception as e:
        logging.warning(f"Failed to get page metadata for {page_id}: {e}")
        return None


def get_block_children(block_id: str, start_cursor: str = None) -> Dict[str, Any]:
    return core_list_children(notion, block_id, start_cursor=start_cursor)

def get_page_content(page_id: str) -> List[Dict[str, Any]]:
    blocks = []
    start_cursor = None

    while True:
        try:
            response = get_block_children(page_id, start_cursor)
            logging.debug(f"[get_page_content] page_id={page_id}, got {len(response.get('results', []))} blocks")
            blocks.extend(response["results"])
            if not response["has_more"]:
                break
            start_cursor = response["next_cursor"]
        except Exception as e:
            logging.error(f"[get_page_content] Error fetching blocks for {page_id}: {e}")
            break

    logging.info(f"[get_page_content] Total blocks for {page_id}: {len(blocks)}")
    return blocks

def block_to_markdown(block: Dict[str, Any], depth: int = 0) -> str:
    block_type = block["type"]
    indent = "  " * depth

    if block_type == "paragraph":
        return f"{indent}{text_to_markdown(block['paragraph']['rich_text'])}\n"
    elif block_type.startswith("heading_"):
        level = int(block_type[-1])
        return f"{indent}{'#' * level} {text_to_markdown(block[block_type]['rich_text'])}\n"
    # H4以下の代替: (h_4) マーカー付き太字段落を見つけたら見出しに復元
    elif block_type == "paragraph":
        text_md = text_to_markdown(block['paragraph']['rich_text'])
        m = re.match(r"\(h_(\d+)\)\s+(.*)", text_md)
        if m:
            lvl = int(m.group(1))
            content = m.group(2)
            # 安全のため4以上のみを対象
            if lvl >= 4:
                return f"{indent}{'#' * lvl} {content}\n"
        return f"{indent}{text_md}\n"
    elif block_type == "to_do":
        checked = "x" if block["to_do"]["checked"] else " "
        return f"{indent}- [{checked}] {text_to_markdown(block['to_do']['rich_text'])}\n"
    elif block_type == "code":
        language = block["code"]["language"]
        code = text_to_markdown(block["code"]["rich_text"])
        return f"{indent}```{language}\n{code}\n```\n"
    elif block_type == "quote":
        return f"{indent}> {text_to_markdown(block['quote']['rich_text'])}\n"
    elif block_type == "divider":
        return f"{indent}---\n"
    elif block_type == "image":
        caption = text_to_markdown(block["image"].get("caption", []))
        url = block["image"]["file"]["url"]
        return f"{indent}![{caption}]({url})\n"
    elif block_type in ["numbered_list_item", "bulleted_list_item"]:
        if block_type == "numbered_list_item":
            return f"{indent}1. {text_to_markdown(block[block_type]['rich_text'])}\n"
        else:
            return f"{indent}- {text_to_markdown(block[block_type]['rich_text'])}\n"
    else:
        return ""

def text_to_markdown(rich_text: List[Dict[str, Any]]) -> str:
    markdown = ""
    for text in rich_text:
        content = text["plain_text"]
        if text.get("href"):
            content = f"[{content}]({text['href']})"
        if text["annotations"]["bold"]:
            content = f"**{content}**"
        if text["annotations"]["italic"]:
            content = f"*{content}*"
        if text["annotations"]["strikethrough"]:
            content = f"~~{content}~~"
        if text["annotations"]["code"]:
            content = f"`{content}`"
        markdown += content
    return markdown

def get_page_title(page_id: str) -> str:
    try:
        page = core_get_page(notion, page_id)
        for prop_name, prop_value in page["properties"].items():
            if prop_value["type"] == "title":
                if prop_value["title"]:
                    return prop_value["title"][0]["plain_text"]
    except APIResponseError as e:
        if "Could not find page" in str(e):
            try:
                database = core_get_database(notion, page_id)
                if database["title"]:
                    return database["title"][0]["plain_text"]
            except APIResponseError:
                pass
        logging.error(f"APIエラー: {str(e)}")
    except Exception as e:
        logging.error(f"予期せぬエラー: {str(e)}")
    return "Untitled"

def get_database_entries(database_id: str) -> List[Dict[str, Any]]:
    return core_get_database_entries(notion, database_id)

def process_blocks(blocks: List[Dict[str, Any]], depth: int = 0) -> str:
    markdown = ""
    list_type = None
    list_depth = 0

    for block in blocks:
        block_type = block["type"]
        
        # child_pageブロックはスキップ（fetch_childrenで別途処理される）
        if block_type == "child_page":
            continue

        if block_type in ["numbered_list_item", "bulleted_list_item"]:
            if list_type != block_type:
                list_type = block_type
                list_depth = depth
            indent = "  " * depth
            if block_type == "numbered_list_item":
                markdown += f"{indent}1. {text_to_markdown(block[block_type]['rich_text'])}\n"
            else:
                markdown += f"{indent}- {text_to_markdown(block[block_type]['rich_text'])}\n"

            if block.get("has_children"):
                child_blocks = get_page_content(block["id"])
                markdown += process_blocks(child_blocks, depth + 1)
        else:
            list_type = None
            markdown += block_to_markdown(block, depth)

            if block.get("has_children"):
                child_blocks = get_page_content(block["id"])
                markdown += process_blocks(child_blocks, depth + 1)

    return markdown

def notion_to_md_flat(page_id: str, output_dir: str, metadata: dict = None):
    """
    Flat Mode: ページを単一のMarkdownファイルとして保存（Frontmatter付き）
    """
    page_id = page_id.replace("-", "")
    
    # メタデータ取得（渡されていない場合は取得）
    if not metadata:
        metadata = _get_page_metadata_flat(page_id)
    
    if not metadata:
        logging.error(f"Failed to get metadata for page {page_id}")
        return None
    
    try:
        page = core_get_page(notion, page_id)
        is_database = False
    except APIResponseError:
        page = core_get_database(notion, page_id)
        is_database = True
    
    page_title = metadata['title'] or "Untitled"
    safe_title = re.sub(r'[<>:"/\\|?*]', '_', page_title)
    output_file = os.path.join(output_dir, f"{safe_title}.md")
    
    # 重複ファイル名対策
    if os.path.exists(output_file):
        output_file = os.path.join(output_dir, f"{safe_title}_{page_id[:8]}.md")
    
    with open(output_file, "w", encoding="utf-8") as f:
        # Frontmatter書き込み
        f.write("---\n")
        f.write(f"page_id: {page_id}\n")
        f.write(f"page_url: {metadata['page_url']}\n")
        if metadata['parent_id']:
            f.write(f"parent_id: {metadata['parent_id']}\n")
            f.write(f"parent_type: {metadata['parent_type']}\n")
        if metadata['children_ids']:
            f.write("children_ids:\n")
            for child_id in metadata['children_ids']:
                f.write(f"  - {child_id}\n")
        f.write(f"sync_mode: flat\n")
        f.write("---\n\n")
        
        # 本文（自動見出しは付与しない）
        
        if is_database:
            entries = get_database_entries(page_id)
            for entry in entries:
                entry_title = entry["properties"].get("Name", {}).get("title", [{}])[0].get("plain_text", "Untitled")
                entry_id = entry["id"]
                f.write(f"- [{entry_title}](https://www.notion.so/{entry_id.replace('-', '')})\n")
        else:
            # メタデータに既にブロック情報がある場合はそれを使用（API呼び出しを削減）
            if metadata and 'blocks' in metadata and metadata['blocks']:
                logging.debug(f"[notion_to_md_flat] Using cached blocks from metadata ({len(metadata['blocks'])} blocks)")
                blocks = metadata['blocks']
            else:
                logging.debug(f"[notion_to_md_flat] Fetching content for page {page_id}")
                blocks = get_page_content(page_id)
            
            logging.debug(f"[notion_to_md_flat] Got {len(blocks)} blocks, processing...")
            markdown = process_blocks(blocks)
            logging.debug(f"[notion_to_md_flat] Markdown length: {len(markdown)} chars")
            f.write(markdown)
    
    logging.info(f"Flat Mode: {os.path.relpath(output_file, output_dir)} を作成")
    return output_file

# Delegate to PageFetcher and MarkdownConverter
def notion_to_md(page_id: str, output_dir: str, fetch_children: bool = False, with_url_tag: bool = False, is_root_page: bool = False, target_filename: str = None):
    """Convert Notion page to Markdown
    
    Args:
        page_id: Notion page ID
        output_dir: Output directory for markdown file
        fetch_children: Whether to fetch child pages
        with_url_tag: Whether to include URL tags
        is_root_page: Whether this is the root page
        target_filename: Optional target filename (without extension). If provided, uses this instead of page title.
    """
    # Get current working directory for root_dir
    root_dir = os.getcwd()
    
    # Create fetcher and converter
    fetcher = PageFetcher(notion, root_dir, {})
    converter = MarkdownConverter(notion, root_dir, {})
    
    # Fetch page information
    page_info = fetcher.fetch_page_info(page_id)
    if not page_info:
        raise Exception(f"Failed to fetch page {page_id}")
    
    # Convert to markdown
    markdown_content = converter.convert_page_to_markdown(page_id, include_children=fetch_children)
    
    # Save to file
    # ✅ FIX BUG-010: Use target_filename if provided, otherwise fallback to page title
    if target_filename:
        filename = f"{target_filename}.md" if not target_filename.endswith('.md') else target_filename
    else:
        page_title = page_info.get("title", "Untitled")
        safe_title = re.sub(r'[^\w\s-]', '', page_title).strip()
        safe_title = re.sub(r'[-\s]+', '-', safe_title)
        filename = f"{safe_title}.md" if safe_title else "page.md"
    
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    logging.info(f"Saved: {filepath}")
    return filepath

def main():
    config = load_config()
    parser = argparse.ArgumentParser(description="Convert Notion page to Markdown file")
    parser.add_argument("url", nargs='?', help="URL of the Notion page or database")
    parser.add_argument("-o", "--output", help="Output directory for Markdown files")
    parser.add_argument("-c", "--children", action="store_true", help="Fetch child pages")
    parser.add_argument("--with-url-tag", action="store_true", help="Append //url:... at the end of files")
    parser.add_argument("--page-ids", help="Comma-separated list of page IDs to fetch (lightweight mode)")
    parser.add_argument("--flat-mode", action="store_true", help="Flat mode: all pages as files, no directory structure")
    parser.add_argument("--target-filename", help="Target filename (without extension) for the output file")
    parser.add_argument("--target-relpath", help="Target relative path (with directories) for the output file")
    args = parser.parse_args()

    output_dir = args.output or os.getcwd()
    os.makedirs(output_dir, exist_ok=True)
    logging.info(f"出力ディレクトリ: {output_dir}")

    try:
        # --page-idsオプションが指定された場合の軽量モード
        if args.page_ids:
            page_ids = [pid.strip() for pid in args.page_ids.split(',') if pid.strip()]
            logging.info(f"軽量モード: {len(page_ids)}個のページIDを処理します")
            
            # manifest出力用のリスト
            manifest_pages = []
            
            # 各ページIDに対して、親ページの階層構造を考慮して処理
            for i, page_id in enumerate(page_ids, 1):
                logging.info(f"[{i}/{len(page_ids)}] ページID {page_id} を処理中...")
                try:
                    # フォルダページ（子ページを持つページ）かどうかをチェック
                    if _is_folder_page(page_id):
                        logging.info(f"フォルダページをスキップ: {page_id}")
                        # フォルダページにもアイコンを設定（ただしファイルは保存しない）
                        _auto_set_page_icon(page_id, force_update=False, is_folder=True)
                        continue
                    
                    # 親ページの階層構造を取得してディレクトリパスを構築
                    page_path = _build_page_hierarchy_path(page_id, output_dir)
                    # 出力先ディレクトリ決定（manifest用に後でスキャン）
                    dir_to_check = page_path if page_path else output_dir
                    if page_path:
                        # 階層構造を考慮したディレクトリに出力
                        os.makedirs(page_path, exist_ok=True)
                        notion_to_md(page_id, page_path, False, args.with_url_tag)
                    else:
                        # フォールバック：ルートディレクトリに出力
                        notion_to_md(page_id, output_dir, False, args.with_url_tag)
                    
                    # ファイルページにアイコンを設定
                    _auto_set_page_icon(page_id, force_update=False, is_folder=False)
                    
                    # 出力ディレクトリ内で最新更新の.mdをmanifestとして記録（上書きケースも対応）
                    try:
                        import glob, time as _t
                        md_files = glob.glob(os.path.join(dir_to_check, '*.md'))
                        if md_files:
                            latest = max(md_files, key=lambda p: os.path.getmtime(p))
                            rel_dir = os.path.relpath(dir_to_check, output_dir)
                            rel_path = os.path.basename(latest) if rel_dir == '.' else os.path.join(rel_dir, os.path.basename(latest))
                            manifest_pages.append({'page_id': page_id, 'file_path': rel_path})
                    except Exception:
                        pass
                except Exception as e:
                    logging.warning(f"ページID {page_id} の処理に失敗: {e}")
            
            # manifest.json を出力（c2nがindex更新に使用）
            try:
                manifest = { 'pages': manifest_pages }
                with open(os.path.join(output_dir, 'manifest.json'), 'w', encoding='utf-8') as f:
                    json.dump(manifest, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logging.warning(f"manifest.jsonの出力に失敗: {e}")

            logging.info(f"軽量モード完了: {len(page_ids)}個のページを処理しました")
            return

        # 通常モード（従来の処理）
        if not args.url:
            args.url = config.get("default_parent_url")
            if not args.url:
                logging.error("エラー: URLが指定されておらず、config.jsonにも定義されていません。")
                return

        page_id = extract_id_from_url_strict(args.url)
        if not page_id:
            logging.error("エラー: 有効なNotionページIDがURLから抽出できませんでした。")
            return

        # Flat Mode処理
        if args.flat_mode:
            logging.info("🔄 Flat Mode: 全ページをフラット構造で保存します")
            # ルートページから全子孫ページを再帰的に取得
            def collect_all_pages(root_id, collected=None):
                if collected is None:
                    collected = []
                if root_id in collected:
                    return collected
                collected.append(root_id)
                try:
                    children = core_list_children(notion, root_id)
                    for block in children.get('results', []):
                        if block.get('type') == 'child_page':
                            child_id = block.get('id')
                            collect_all_pages(child_id, collected)
                except Exception as e:
                    logging.warning(f"Failed to get children for {root_id}: {e}")
                return collected
            
            all_page_ids = collect_all_pages(page_id)
            logging.info(f"📄 合計 {len(all_page_ids)} ページを検出")
            
            # シーケンシャル処理（デバッグ用）
            completed = 0
            failed = 0
            
            logging.info(f"⚡ シーケンシャル処理開始")
            
            for pid in all_page_ids:
                try:
                    logging.debug(f"Processing page: {pid}")
                    metadata = _get_page_metadata_flat(pid)
                    if metadata:
                        notion_to_md_flat(pid, output_dir, metadata)
                    completed += 1
                    if completed % 5 == 0 or completed == len(all_page_ids):
                        logging.info(f"📊 進捗: {completed}/{len(all_page_ids)} ページ完了")
                except Exception as e:
                    failed += 1
                    logging.error(f"✗ {pid} の取得に失敗: {e}")
            
            logging.info(f"✅ Flat Mode完了: 成功 {completed}件, 失敗 {failed}件")
            return
        
        # Hierarchy Mode（既存の処理）
        # ✅ FIX BUG-010: Handle target_relpath or target_filename
        if args.target_relpath:
            # target_relpath includes directory structure (e.g., "docs/api.md")
            target_file = os.path.join(output_dir, args.target_relpath)
            target_dir = os.path.dirname(target_file)
            if target_dir:
                os.makedirs(target_dir, exist_ok=True)
            # Extract filename without extension
            basename = os.path.basename(args.target_relpath)
            target_filename = os.path.splitext(basename)[0] if basename.endswith('.md') else basename
            notion_to_md(page_id, target_dir if target_dir else output_dir, args.children, args.with_url_tag, is_root_page=True, target_filename=target_filename)
        else:
            # Fallback to target_filename or default behavior
            notion_to_md(page_id, output_dir, args.children, args.with_url_tag, is_root_page=True, target_filename=args.target_filename)
    except Exception as e:
        logging.error(f"エラーが発生しました: {str(e)}")

if __name__ == "__main__":
    main()