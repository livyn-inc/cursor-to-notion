#!/usr/bin/env python3

"""
notion_push.py - Push operations for cursor_to_notion tool
"""

import os
import sys
import time
import io
import argparse
from typing import List, Tuple, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from notion_client import Client
import fnmatch
import mimetypes
import hashlib
import json
import subprocess
import shutil

from notion_client import Client
# Removed unused import: APIResponseError

from c2n_core.env import _ensure_notion_env_bridge, _load_env_file
from c2n_core.cache import CacheManager
from c2n_core.utils import load_config_for_folder, extract_id_from_url_strict
from c2n_core.notion_api.icons import set_page_icon as core_set_icon, get_page_icon as core_get_icon, auto_set_page_icon as core_auto_icon
from c2n_core.logging import load_yaml_file, save_yaml_file, check_yaml_available, parse_yaml_frontmatter
from c2n_core.error import run_subprocess_with_env, handle_subprocess_error, exit_with_error, print_error

# Import push components
from push.directory_processor import DirectoryProcessor
from push.file_processor import FileProcessor
from push.metadata_manager import MetadataManager
from push.snapshot_manager import SnapshotManager
from notion_page_manager import create_or_update_notion_page  # type: ignore

# Delegate to c2n_core.env
def _load_env_for_folder(folder: str):
    from c2n_core.env import _load_env_for_target as _core_load_env_for_target
    _core_load_env_for_target(folder)

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
# 下部Indexを生成するか（既定: False = 生成しない）
GENERATE_INDEX = False
 
# 差分アップロード用メタ管理（.c2n/index.yaml）

MetaType = Dict[str, Any]

def _meta_dir(root_dir: str) -> str:
    return os.path.join(root_dir, ".c2n")

def _meta_path(root_dir: str) -> str:
    return os.path.join(_meta_dir(root_dir), "index.yaml")

def _config_path(root_dir: str) -> str:
    return os.path.join(_meta_dir(root_dir), "config.json")

def load_meta(root_dir: str) -> MetaType:
    path = _meta_path(root_dir)
    default_data = {"version": 1, "generated_at": int(time.time()), "items": {}, "ignore": []}
    data = load_yaml_file(path, default_data)
    data.setdefault("items", {})
    data.setdefault("ignore", [])
    return data

def load_folder_config(root_dir: str) -> Dict[str, Any]:
    """[Deprecated] Kept for backward compatibility. Use load_config_for_folder directly."""
    tool_root = os.path.dirname(os.path.abspath(__file__))
    return load_config_for_folder(root_dir, script_dir=tool_root)

def save_meta(root_dir: str, meta: MetaType) -> None:
    path = _meta_path(root_dir)
    # ✅ FIX IMP-012: Preserve root_page_url before saving
    # Load existing meta to preserve top-level keys
    existing_meta = load_meta(root_dir)
    if existing_meta and 'root_page_url' in existing_meta:
        meta['root_page_url'] = existing_meta['root_page_url']
    save_yaml_file(path, meta)

def _path_mtime(path: str) -> Optional[int]:
    try:
        return int(os.path.getmtime(path))
    except Exception:
        return None

def _collect_env_chain(root_dir: str) -> List[Dict[str, Any]]:
    # Simplified version - just return the main env files
    chain: List[str] = []
    chain.append(os.path.join(root_dir, '.c2n', '.env'))
    chain.append(os.path.join(root_dir, '.env'))
    # normalize unique existing
    norm: List[str] = []
    for p in chain:
        if p and os.path.exists(p) and p not in norm:
            norm.append(p)
    return [{"path": p, "mtime": _path_mtime(p)} for p in norm]


def _key(abs_path: str) -> str:
    return os.path.normpath(abs_path)

def get_item(meta: MetaType, abs_path: str) -> Optional[Dict[str, Any]]:
    return meta.get("items", {}).get(_key(abs_path))

def set_item(meta: MetaType, abs_path: str, item: Dict[str, Any]) -> None:
    meta.setdefault("items", {})[_key(abs_path)] = item

def is_ignored(meta: MetaType, path: str, root_dir: str) -> bool:
    rel = os.path.relpath(path, root_dir)
    patterns = (meta.get("ignore", []) or []) + _IGNORE_PATTERNS
    for pat in patterns:
        if fnmatch.fnmatch(rel, pat):
            return True
    return False
notion = Client(auth=NOTION_TOKEN)

# 簡易ログ（標準出力 + 任意ファイル）
_LOG_FP: Optional[io.TextIOBase] = None
_LOG_HEADER_EMITTED: bool = False
_IGNORE_PATTERNS: List[str] = []
_PROG_TOTAL: int = 0
_PROG_DONE: int = 0
_NO_PROGRESS: bool = False
_VERBOSE: bool = False
_CACHE_MANAGER: Optional[CacheManager] = None
_DIR_SNAPSHOT: Dict[str, Any] = {}
_FILE_SNAPSHOT: Dict[str, Any] = {}
_PREV_DIR_SNAPSHOT: Dict[str, Any] = {}
_PREV_FILE_SNAPSHOT: Dict[str, Any] = {}

def _emit_log_header_once() -> None:
    global _LOG_HEADER_EMITTED
    if _LOG_HEADER_EMITTED:
        return
    _LOG_HEADER_EMITTED = True
    # ACT: N(new)/U(update)/-(no-op), TYPE: DIR/FILE, PATH: relative path from root
    hdr = f"{'ACT':<3}  {'TYPE':<4}  {'PATH':<40}  {'TITLE':<32}  URL"
    sep = f"{'-'*3}  {'-'*4}  {'-'*40}  {'-'*32}  {'-'*3}"
    print(hdr)
    if _LOG_FP is not None:
        try:
            _LOG_FP.write(hdr + "\n")
            _LOG_FP.write(sep + "\n")
            _LOG_FP.flush()
        except Exception:
            pass

def log_row(action: str, kind: str, title: str, url: str, rel_path: str, reason: Optional[str] = None) -> None:
    _emit_log_header_once()
    safe_title = (title[:29] + '...') if len(title) > 32 else title
    safe_path = (rel_path[:37] + '...') if len(rel_path) > 40 else rel_path
    act = action if not reason else f"{action}({reason})"
    line = f"{act:<3}  {kind:<4}  {safe_path:<40}  {safe_title:<32}  {url or '-'}"
    print(line)
    if _LOG_FP is not None:
        try:
            _LOG_FP.write(line + "\n")
            _LOG_FP.flush()
        except Exception:
            pass

def log(msg: str) -> None:
    print(msg)
    if _LOG_FP is not None:
        try:
            _LOG_FP.write(msg + "\n")
            _LOG_FP.flush()
        except Exception:
            pass

def is_markdown_file(path: str) -> bool:
    name = os.path.basename(path)
    if name.startswith('.'):
        return False
    lower = name.lower()
    # push対象拡張子: .md, .mdc, .py, .sh, .json, .js, .yaml, .yml
    return (
        lower.endswith('.md') or lower.endswith('.mdc') or
        lower.endswith('.py') or lower.endswith('.sh') or
        lower.endswith('.json') or lower.endswith('.js') or
        lower.endswith('.yaml') or lower.endswith('.yml')
    )

def is_media_file(path: str) -> bool:
    name = os.path.basename(path)
    if name.startswith('.'):
        return False
    lower = name.lower()
    return (
        lower.endswith('.png') or lower.endswith('.jpg') or lower.endswith('.jpeg') or
        lower.endswith('.gif') or lower.endswith('.webp') or lower.endswith('.svg') or
        lower.endswith('.pdf')
    )

def _sha1_file(path: str) -> str:
    try:
        h = hashlib.sha1()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ''

def _mtime_ns(path: str) -> int:
    try:
        return int(os.stat(path).st_mtime_ns)
    except Exception:
        # フォールバック（精度低下）
        try:
            return int(os.path.getmtime(path)) * 1_000_000_000
        except Exception:
            return 0

def _parse_frontmatter(md_path: str) -> dict:
    """
    Markdownファイルからfrontmatterを抽出
    """
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # frontmatter検出（---で囲まれた部分）
        if not content.startswith('---\n'):
            return {}
        
        parts = content.split('---\n', 2)
        if len(parts) < 3:
            return {}
        
        frontmatter_text = parts[1]
        
        # YAML解析（統一版）
        return parse_yaml_frontmatter(content)
    except Exception:
        return {}

def _progress_tick(rel_path: str) -> None:
    global _PROG_DONE
    if _NO_PROGRESS:
        return
    if _PROG_TOTAL <= 0:
        return
    _PROG_DONE += 1
    try:
        pct = int((_PROG_DONE / _PROG_TOTAL) * 100)
    except Exception:
        pct = 100
    print(f"Upload [{_PROG_DONE}/{_PROG_TOTAL}] ({pct}%) {rel_path}")

from contextlib import contextmanager

@contextmanager
def _suppress_io():
    if _VERBOSE:
        yield
        return
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        yield
    finally:
        sys.stdout = old_out
        sys.stderr = old_err

def _progress_note(msg: str) -> None:
    if _NO_PROGRESS:
        return
    print(msg)

def _find_child_page_url(parent_url: str, title: str) -> Optional[str]:
    """親ページ直下でタイトル一致の子ページURLを返す（なければNone）。ページネーション対応。"""
    parent_id = extract_id_from_url_strict(parent_url)
    try:
        cursor = None
        while True:
            kwargs = {"block_id": parent_id}
            if cursor:
                kwargs["start_cursor"] = cursor
            res = notion.blocks.children.list(**kwargs)
            for b in res.get('results', []):
                if b.get('type') == 'child_page' and b.get('child_page', {}).get('title') == title:
                    page = notion.pages.retrieve(b['id'])
                    return page['url']
            cursor = res.get('next_cursor')
            if not res.get('has_more'):
                break
    except Exception:
        return None
    return None

def _set_page_icon(page_url: str, icon_emoji: str) -> bool:
    """Notionページにアイコン（絵文字）を設定する"""
    try:
        page_id = extract_id_from_url_strict(page_url)
        if not page_id:
            return False
        
        return core_set_icon(notion, page_id, icon_emoji)
    except Exception as e:
        log(f"Failed to set icon for {page_url}: {e}")
        return False

def _get_page_icon(page_url: str) -> Optional[str]:
    """Notionページの現在のアイコンを取得する"""
    try:
        page_id = extract_id_from_url_strict(page_url)
        if not page_id:
            return None
        
        return core_get_icon(notion, page_id)
    except Exception as e:
        log(f"Failed to get icon for {page_url}: {e}")
        return None

def _is_folder_page_by_url(page_url: str) -> bool:
    """ページが子ページを持つフォルダページかどうかを判定"""
    try:
        page_id = extract_id_from_url_strict(page_url)
        if not page_id:
            return False
        
        response = notion.blocks.children.list(block_id=page_id)
        blocks = response.get('results', [])
        
        # 子ページ（child_page）があるかチェック
        for block in blocks:
            if block.get('type') == 'child_page':
                return True
        
        return False
    except Exception as e:
        log(f"Failed to check if folder page {page_url}: {e}")
        return False

def _auto_set_page_icon(page_url: str, force_update: bool = False, is_folder: bool = None) -> bool:
    """ページの種類に応じて自動的にアイコンを設定する"""
    try:
        # 既にアイコンが設定されている場合はスキップ（force_updateがFalseの場合）
        if not force_update:
            current_icon = _get_page_icon(page_url)
            if current_icon:
                return True  # 既にアイコンが設定されている
        
        # フォルダページかファイルページかを判定
        if is_folder is None:
            is_folder = _is_folder_page_by_url(page_url)
        
        success = core_auto_icon(notion, extract_id_from_url_strict(page_url), force_update=force_update, is_folder=is_folder)
        if success:
            page_type = "folder" if is_folder else "file"
            log(f"Auto-set icon for {page_type} page: {page_url}")
        
        return success
        
    except Exception as e:
        log(f"Failed to auto-set icon for {page_url}: {e}")
        return False

def _get_remote_last_edited(page_url: str) -> Optional[str]:
    try:
        pid = extract_id_from_url_strict(page_url)
        if not pid:
            return None
        page = notion.pages.retrieve(pid)
        return page.get('last_edited_time')
    except Exception:
        return None

def ensure_page(parent_url: str, title: str, *, known_url: Optional[str] = None, dry_run: bool = False) -> str:
    """親URL配下にtitleの子ページを確保しURLを返す。dry_run時は作成せず既存が無ければ空文字。"""
    if known_url:
        return known_url
    existing = _find_child_page_url(parent_url, title)
    if existing:
        return existing
    if dry_run:
        return ""  # 作成しない
    # 409 Conflict対策: 競合時は再検索して取得
    try:
        return create_or_update_notion_page(title=title, blocks=[], url=parent_url, update_mode=False)
    except Exception as e:
        msg = str(e)
        code = getattr(e, 'code', '')
        if 'Conflict' in msg or 'conflict' in msg.lower() or code == 'conflict_error':
            try:
                import time as _time
            except Exception:
                _time = None
            # 短い待機を挟みつつ再検索
            for _ in range(3):
                if _time:
                    try:
                        _time.sleep(0.3)
                    except Exception:
                        pass
                again = _find_child_page_url(parent_url, title)
                if again:
                    return again
        # その他はそのまま投げる
        raise

def upload_markdown(parent_url: str, md_path: str, *, update_page_url: Optional[str] = None, dry_run: bool = False) -> str:
    # デフォルトページタイトルは拡張子なし
    base_name = os.path.basename(md_path)
    title = os.path.splitext(base_name)[0]
    ext = os.path.splitext(base_name)[1].lower()
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # コード系ファイルは1コードブロックとして扱う
    def _make_code_block(language: str, body: str) -> dict:
        chunk_size = 1800  # Notionのtextノード制限対策（余裕を持たせて分割）
        rich_text = []
        if body:
            for i in range(0, len(body), chunk_size):
                rich_text.append({
                    "type": "text",
                    "text": {"content": body[i:i + chunk_size]}
                })
        else:
            rich_text.append({"type": "text", "text": {"content": ""}})
        return {
            "object": "block",
            "type": "code",
            "code": {
                "rich_text": rich_text,
                "language": language
            }
        }

    code_lang_map = {
        '.py': ('python', False),
        '.js': ('javascript', False),
        '.json': ('json', False),
        '.sh': ('bash', False),
        '.yaml': ('yaml', True),
        '.yml': ('yaml', True),
    }
    if ext in code_lang_map:
        language, keep_extension_title = code_lang_map[ext]
        if keep_extension_title:
            title = base_name  # 拡張子込み
        else:
            title = os.path.splitext(base_name)[0]
        blocks = [_make_code_block(language, content)]
    else:
        # Markdown/MDX相当は通常のMarkdown変換
        from markdown_converter import convert_markdown_to_notion_blocks  # type: ignore
        _progress_note(f"Converting markdown -> blocks: {os.path.basename(md_path)}")
        with _suppress_io():
            blocks = convert_markdown_to_notion_blocks(content)
    if dry_run:
        return update_page_url or ""
    # 既存ページは一度本文を空にしてから上書き（重複防止）
    if update_page_url:
        try:
            pid = extract_id_from_url_strict(update_page_url)
            if pid:
                _replace_children(pid, [])
        except Exception:
            pass
    with _suppress_io():
        if update_page_url:
            return create_or_update_notion_page(title=title, blocks=blocks, url=update_page_url, update_mode=True)
        return create_or_update_notion_page(title=title, blocks=blocks, url=parent_url, update_mode=False)

def upload_media(parent_url: str, file_path: str, *, dry_run: bool = False) -> str:
    """Create a page titled by file name and upload media via Node helper for native Notion upload."""
    base_name = os.path.basename(file_path)
    title = os.path.splitext(base_name)[0]
    if dry_run:
        return ""
    # 1) ページ作成（親URL直下）
    page_url = create_or_update_notion_page(title=title, blocks=[], url=parent_url, update_mode=False)

    # 2) Node.js helper 経由でネイティブアップロードを実行
    node_path = shutil.which("node")
    if not node_path:
        log("[media] node command not available; skipping native upload")
        return page_url

    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "node_upload_media.js")
    if not os.path.exists(script_path):
        log("[media] node_upload_media.js not found; skipping native upload")
        return page_url

    env = os.environ.copy()
    if not env.get("NOTION_API_KEY") and env.get("NOTION_TOKEN"):
        env["NOTION_API_KEY"] = env["NOTION_TOKEN"]

    try:
        result = run_subprocess_with_env(
            [node_path, script_path, page_url, file_path],
            capture_output=True,
            text=True,
            extra_env={"NOTION_API_KEY": env.get("NOTION_API_KEY", "")},
        )
        if result.stdout:
            log(result.stdout.strip())
        if result.returncode != 0:
            handle_subprocess_error(result, [node_path, script_path, page_url, file_path], prefix="Node helper")
            log("[media] Node helper failed; native upload not applied")
    except Exception as e:
        log(f"[media] Node helper exception: {e}")

    return page_url

def apply_markdown_to_existing_page(page_url: str, md_path: str, *, keep_title: Optional[str] = None, dry_run: bool = False) -> None:
    """与えられたMarkdownを既存ページ本文としてそのまま反映（同期ブロック不使用）"""
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()
    from markdown_converter import convert_markdown_to_notion_blocks  # type: ignore
    _progress_note(f"Converting markdown -> blocks: {os.path.basename(md_path)}")
    with _suppress_io():
        blocks = convert_markdown_to_notion_blocks(content)
    if dry_run:
        return
    title_to_keep = keep_title or os.path.splitext(os.path.basename(md_path))[0]
    with _suppress_io():
        create_or_update_notion_page(title=title_to_keep, blocks=blocks, url=page_url, update_mode=True)

def _link_item(text: str, url: str) -> dict:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": text, "link": {"url": url}}
                }
            ]
        }
    }

def _update_index_page(page_url: str, links: List[Tuple[str, str]], keep_title: str):
    # 見出し＋リンク一覧を生成（タイトルは保持）
    blocks: List[dict] = []
    blocks.append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Index"}}]}
    })
    for name, url in links:
        blocks.append(_link_item(name, url))
    # ページを更新モードで上書き（本文のみ）
    create_or_update_notion_page(title=keep_title, blocks=blocks, url=page_url, update_mode=True)

def _list_children_blocks(page_url: str) -> List[dict]:
    """ページ直下のブロック一覧（ページネーション対応）を返す"""
    blocks: List[dict] = []
    try:
        pid = extract_id_from_url_strict(page_url)
        if not pid:
            return []
        cursor = None
        while True:
            kwargs = {"block_id": pid}
            if cursor:
                kwargs["start_cursor"] = cursor
            res = notion.blocks.children.list(**kwargs)
            blocks.extend(res.get('results', []))
            cursor = res.get('next_cursor')
            if not res.get('has_more'):
                break
    except Exception:
        return []
    return blocks

def _find_child_pages_by_title(page_url: str, title: str) -> List[str]:
    """ページ直下の child_page のうち、指定タイトルと一致するページID一覧を返す"""
    result: List[str] = []
    try:
        for b in _list_children_blocks(page_url):
            if b.get('type') == 'child_page':
                t = (b.get('child_page') or {}).get('title') or ''
                if t == title:
                    pid = b.get('id')
                    if pid:
                        result.append(pid)
    except Exception:
        pass
    return result

def _archive_page(page_id: str) -> None:
    try:
        notion.pages.update(page_id=page_id, archived=True)
    except Exception:
        pass

def _dedup_child_pages_by_title(page_url: str, titles_to_keep: List[str]) -> None:
    """同一タイトルの child_page が複数ある場合、最新以外をアーカイブする"""
    try:
        for t in titles_to_keep:
            ids = _find_child_pages_by_title(page_url, t)
            if len(ids) <= 1:
                continue
            # 取得したIDの last_edited_time でソートし、最新だけ残す
            def _last_edit(pid: str) -> int:
                try:
                    pg = notion.pages.retrieve(page_id=pid)
                    ts = (pg or {}).get('last_edited_time') or '1970-01-01T00:00:00.000Z'
                    import datetime
                    return int(datetime.datetime.fromisoformat(ts.replace('Z','+00:00')).timestamp())
                except Exception:
                    return 0
            ids_sorted = sorted(ids, key=_last_edit, reverse=True)
            for old in ids_sorted[1:]:
                _archive_page(old)
    except Exception:
        pass

def _text_rich(text: str) -> List[dict]:
    return [{
        "type": "text",
        "text": {"content": text}
    }]

def _upsert_c2n_settings_block(root_page_url: str, settings: Dict[str, Any]) -> None:
    """[Deprecated] C2N Settings埋め込みは廃止。互換のため空実装。"""
    return

def _wrap_as_synced_block(children_blocks: List[dict]) -> dict:
    # NOTE: Notion APIではsynced_blockのchildrenは作成後に別APIでappendする必要がある
    return {
        "object": "block",
        "type": "synced_block",
        "synced_block": {
            "synced_from": None
        }
    }

def _find_synced_block_id_in_page(page_url: str) -> Optional[str]:
    try:
        for b in _list_children_blocks(page_url):
            if b.get('type') == 'synced_block':
                return b.get('id')
    except Exception:
        pass
    return None

def _ensure_synced_block_in_page(page_url: str) -> Optional[str]:
    """ページ本文直下にsynced_blockを1つ確保し、そのblock_idを返す"""
    sid = _find_synced_block_id_in_page(page_url)
    if sid:
        return sid
    try:
        pid = extract_id_from_url_strict(page_url)
        if not pid:
            return None
        notion.blocks.children.append(block_id=pid, children=[{
            "object": "block",
            "type": "synced_block",
            "synced_block": {"synced_from": None}
        }])
        # fetch again
        return _find_synced_block_id_in_page(page_url)
    except Exception:
        return None

def _replace_children(block_id: str, children: List[dict]) -> None:
    try:
        # collect existing child ids
        child_ids: List[str] = []
        cursor = None
        while True:
            kw = {"block_id": block_id}
            if cursor:
                kw['start_cursor'] = cursor
            res = notion.blocks.children.list(**kw)
            for ch in res.get('results', []):
                cid = ch.get('id')
                if cid:
                    child_ids.append(cid)
            if not res.get('has_more'):
                break
            cursor = res.get('next_cursor')
        # concurrent delete
        if child_ids:
            _progress_note(f"Clearing children: {len(child_ids)} blocks")
            with ThreadPoolExecutor(max_workers=5) as ex:
                futs = [ex.submit(notion.blocks.delete, block_id=cid) for cid in child_ids]
                for _ in as_completed(futs):
                    pass
        # append new children
        if children:
            notion.blocks.children.append(block_id=block_id, children=children)
    except Exception:
        pass

def _cleanup_stale_synced_refs(dir_page_url: str, valid_synced_block_id: str) -> None:
    try:
        pid = extract_id_from_url_strict(dir_page_url)
        if not pid:
            return
        ch = _list_children_blocks(dir_page_url)
        for b in ch:
            if b.get('type') == 'synced_block':
                src = (b.get('synced_block') or {}).get('synced_from') or {}
                bid = src.get('block_id')
                if bid and bid != valid_synced_block_id:
                    try:
                        notion.blocks.delete(block_id=b.get('id'))
                    except Exception:
                        pass
    except Exception:
        return

def upload_readme_with_synced(parent_url: str, md_path: str, *, update_page_url: Optional[str], dry_run: bool) -> Tuple[str, Optional[str]]:
    """Deprecated: Treat README like any other file page (no special handling)."""
    url = upload_markdown(parent_url, md_path, update_page_url=update_page_url, dry_run=dry_run)
    return (url or update_page_url or parent_url, None)

def _ensure_dir_has_synced_preview(dir_page_url: str, source_synced_block_id: str, source_page_url: Optional[str] = None) -> bool:
    """[Deprecated] synced_block撤廃: プレビュー挿入は常にスキップ"""
    return False

def _setup_directory_page(dir_path: str, parent_url: str, root_meta: MetaType, root_dir: str, dry_run: bool) -> tuple[str, bool, bool]:
    """ディレクトリページのセットアップ"""
    title = os.path.basename(os.path.abspath(dir_path))
    known = get_item(root_meta, dir_path)
    before_url = (known or {}).get("page_url") if known else None
    page_url = ensure_page(parent_url, title, known_url=before_url, dry_run=dry_run)
    
    # このディレクトリページ自体を編集・作成したか（親DIR更新の対象）
    dir_created = False
    dir_updated = False
    if not before_url and page_url:
        dir_created = True
        # 新規作成されたディレクトリページにフォルダアイコンを設定
        _auto_set_page_icon(page_url, force_update=False, is_folder=True)

    if not dry_run:
        # ✅ FIX: Set last_sync_at for directory pages
        remote_last_dir_page = _get_remote_last_edited(page_url) if page_url else None
        import datetime
        last_sync_value_dir_page = remote_last_dir_page or datetime.datetime.now(datetime.timezone.utc).isoformat()
        print(f"[c2n] DEBUG PUSH: Dir {title}: remote_last={remote_last_dir_page}, last_sync_value={last_sync_value_dir_page}")
        set_item(root_meta, dir_path, {
            "type": "dir",
            "title": title,
            "page_url": page_url or "",
            "page_id": extract_id_from_url_strict(page_url or ""),
            "parent_url": parent_url,
            "remote_last_edited": remote_last_dir_page,
            "last_sync_at": last_sync_value_dir_page,
            "updated_at": int(time.time()),
        })
        save_meta(root_dir, root_meta)
    
    return page_url, dir_created, dir_updated


def _get_directory_contents(dir_path: str, root_dir: str) -> tuple[List[str], List[str]]:
    """ディレクトリ内容を取得（キャッシュ利用）"""
    rel_dir = os.path.relpath(dir_path, root_dir)
    try:
        cur_dir_mtime_ns = _mtime_ns(dir_path)
    except Exception:
        cur_dir_mtime_ns = 0
    
    cached_dirs: List[str] = []
    cached_files: List[str] = []
    snap_hit = False
    
    try:
        prev = _PREV_DIR_SNAPSHOT.get(rel_dir)
        if prev and prev.get('mtime_ns') == cur_dir_mtime_ns:
            cached_dirs = list(prev.get('dirs') or [])
            cached_files = list(prev.get('files') or [])
            snap_hit = True
    except Exception:
        snap_hit = False
    
    if not snap_hit:
        # fresh listing
        try:
            for x in os.listdir(dir_path):
                if x.startswith('.'):
                    continue
                p = os.path.join(dir_path, x)
                if os.path.isdir(p):
                    cached_dirs.append(x)
                elif os.path.isfile(p) and (is_markdown_file(x) or is_media_file(x)):
                    cached_files.append(x)
        except Exception:
            cached_dirs = []
            cached_files = []
    
    # 保存用スナップショット
    _DIR_SNAPSHOT[rel_dir] = {"mtime_ns": cur_dir_mtime_ns, "dirs": sorted(cached_dirs), "files": sorted(cached_files)}
    
    return cached_dirs, cached_files


def _process_child_directories(dir_path: str, page_url: str, parent_url: str, cached_dirs: List[str], root_meta: MetaType, root_dir: str, dry_run: bool, changed_only: bool, no_dir_update: bool) -> List[Tuple[str, str]]:
    """子ディレクトリを処理"""
    child_links: List[Tuple[str, str]] = []
    
    # ディレクトリ先に
    for d in sorted(cached_dirs):
        child_dir = os.path.join(dir_path, d)
        if is_ignored(root_meta, child_dir, root_dir):
            continue
        child_url, _child_dir_updated = process_dir(child_dir, page_url or parent_url, root_meta=root_meta, root_dir=root_dir, dry_run=dry_run, changed_only=changed_only, no_dir_update=no_dir_update)
        child_links.append((d, child_url))
    
    return child_links


# Delegate to DirectoryProcessor
def process_dir(dir_path: str, parent_url: str, *, root_meta: MetaType, root_dir: str, dry_run: bool = False, is_root: bool = False, changed_only: bool = False, no_dir_update: bool = False) -> Tuple[str, bool]:
    """dir_path を親 parent_url 配下にページ化し、子要素を再帰で作成してリンクIndexを生成
    戻り値: (このディレクトリのページURL, このディレクトリ配下で変更があったか)
    """
    # Get Notion client
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        _load_env_for_folder(root_dir)
        token = os.environ.get("NOTION_TOKEN")
    
    client = Client(auth=token) if token else None
    if not client:
        raise Exception("Notion client not available")
    
    processor = DirectoryProcessor(client, root_dir, root_meta)
    return processor.process_directory(dir_path, parent_url, dry_run=dry_run, is_root=is_root, changed_only=changed_only, no_dir_update=no_dir_update)


def _process_directory_files(dir_path: str, page_url: str, parent_url: str, cached_files: List[str], root_meta: MetaType, root_dir: str, title: str, dry_run: bool, changed_only: bool) -> List[Tuple[str, str]]:
    """ディレクトリ内のファイルを処理"""
    file_links: List[Tuple[str, str]] = []
    
    for fn in sorted(cached_files):
        file_path = os.path.join(dir_path, fn)
        if is_ignored(root_meta, file_path, root_dir):
            continue
        # ファイルスナップショット検証（mtime/size一致ならsha再計算を省略）
        cur_stat = None
        try:
            st = os.stat(file_path)
            cur_stat = {"mtime_ns": int(st.st_mtime_ns), "size": int(st.st_size)}
        except Exception:
            cur_stat = {"mtime_ns": _mtime_ns(file_path), "size": None}
        prev_snap = _PREV_FILE_SNAPSHOT.get(os.path.relpath(file_path, root_dir)) if _PREV_FILE_SNAPSHOT else None
        if prev_snap and prev_snap.get('mtime_ns') == cur_stat.get('mtime_ns') and prev_snap.get('size') == cur_stat.get('size'):
            cur_mtime_ns = cur_stat.get('mtime_ns') or 0
            cur_mtime = int(cur_mtime_ns/1_000_000_000)
            cur_sha = prev_snap.get('sha1') or ''
        else:
            cur_mtime_ns = cur_stat.get('mtime_ns') or _mtime_ns(file_path)
            cur_mtime = int(cur_mtime_ns/1_000_000_000)
            cur_sha = _sha1_file(file_path)
        # スナップショット保存
        _FILE_SNAPSHOT[os.path.relpath(file_path, root_dir)] = {"mtime_ns": cur_mtime_ns, "size": cur_stat.get('size'), "sha1": cur_sha}
        known = get_item(root_meta, file_path)
        if changed_only:
            # 変更なしは完全スキップ（SHA一致 or mtime一致）
            k_ns = (known or {}).get("local_mtime_ns") if known else None
            k_s = (known or {}).get("local_mtime") if known else None
            k_sha = (known or {}).get("content_sha1") if known else None
            if known and known.get("page_url") and (k_sha == cur_sha or (k_ns is not None and k_ns == cur_mtime_ns) or (k_ns is None and k_s == int(cur_mtime_ns/1_000_000_000))):
                if dry_run:
                    relp_skip = os.path.relpath(file_path, root_dir)
                    log_row('-(same-hash)' if k_sha == cur_sha else '-', 'FILE', os.path.splitext(fn)[0], known.get("page_url", ""), relp_skip)
                continue
        # 方針判定（SHA一致ならスキップ）
        if known and known.get("page_url") and (known.get("content_sha1") == cur_sha):
            if dry_run:
                child_url = known.get("page_url", "")
                relp = os.path.relpath(file_path, root_dir)
                log_row('-(same-hash)', 'FILE', os.path.splitext(fn)[0], child_url, relp)
            # push時はログを出さずスキップ
        else:
            update_url = (known or {}).get("page_url")
            relp = os.path.relpath(file_path, root_dir)
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            # ディレクトリ名と同名の.mdのみ「ディレクトリ本文」として扱う（README特別扱いは廃止）
            if base_name == title:
                # 変更なしはスキップ（SHA一致 or mtime一致）
                k_ns = (known or {}).get("local_mtime_ns") if known else None
                k_s = (known or {}).get("local_mtime") if known else None
                k_sha = (known or {}).get("content_sha1") if known else None
                if known and (k_sha == cur_sha or (k_ns is not None and k_ns == cur_mtime_ns) or (k_ns is None and k_s == int(cur_mtime_ns/1_000_000_000))):
                    if dry_run:
                        log_row('-(same-hash)', 'FILE', os.path.splitext(fn)[0], (known or {}).get('page_url',''), relp, reason='dir-body')
                    continue
                # ログ（dir-body反映）
                action_ch = 'U' if (known and known.get('page_url')) else 'N'
                log_row(action_ch, 'FILE', os.path.splitext(fn)[0], (known or {}).get('page_url',''), relp, reason='dir-body')
                if not dry_run and (page_url or parent_url):
                    target_url = (page_url or parent_url)
                    apply_markdown_to_existing_page(target_url, file_path, keep_title=title, dry_run=False)
                    dir_updated = True
                    # メタを更新（次回の差分判定用）
                    remote_last_dir = _get_remote_last_edited(target_url)
                    # ✅ FIX: Fallback to current UTC time if remote_last is None (新規作成直後など)
                    import datetime
                    last_sync_value_dir = remote_last_dir or datetime.datetime.now(datetime.timezone.utc).isoformat()
                    set_item(root_meta, file_path, {
                        "type": "file",
                        "title": os.path.splitext(fn)[0],
                        "page_url": target_url,
                        "page_id": extract_id_from_url_strict(target_url or ""),
                        "parent_url": target_url,
                        "local_mtime": int(cur_mtime_ns/1_000_000_000),
                        "local_mtime_ns": cur_mtime_ns,
                        "content_sha1": cur_sha,
                        "remote_last_edited": remote_last_dir,
                        "last_sync_at": last_sync_value_dir,
                        "updated_at": int(time.time()),
                    })
                    save_meta(root_dir, root_meta)
                # ディレクトリ本文用MDはリンク一覧に含めない
                continue
            else:
                # メディアは専用処理、その他はMarkdown/コードとして処理
                if is_media_file(file_path):
                    action_ch = 'U' if update_url else 'N'
                    log_row(action_ch, 'FILE', os.path.splitext(fn)[0], update_url or '', relp)
                    child_url = upload_media(page_url or parent_url, file_path, dry_run=dry_run)
                else:
                    action_ch = 'U' if update_url else 'N'
                    log_row(action_ch, 'FILE', os.path.splitext(fn)[0], update_url or '', relp)
                    child_url = upload_markdown(page_url or parent_url, file_path, update_page_url=update_url, dry_run=dry_run)
                # 新規作成されたファイルページにファイルアイコンを設定
                if not update_url and child_url:
                    _auto_set_page_icon(child_url, force_update=False, is_folder=False)
            if not dry_run:
                remote_last = _get_remote_last_edited(child_url) if child_url else None
                # ✅ FIX: Fallback to current UTC time if remote_last is None (新規作成直後など)
                import datetime
                last_sync_value = remote_last or datetime.datetime.now(datetime.timezone.utc).isoformat()
                print(f"[c2n] DEBUG PUSH: File {os.path.splitext(fn)[0]}: remote_last={remote_last}, last_sync_value={last_sync_value}")
                set_item(root_meta, file_path, {
                    "type": "file",
                    "title": os.path.splitext(fn)[0],
                    "page_url": child_url,
                    "page_id": extract_id_from_url_strict(child_url or ""),
                    "parent_url": page_url or parent_url,
                    "local_mtime": int(cur_mtime_ns/1_000_000_000),
                    "local_mtime_ns": cur_mtime_ns,
                    "content_sha1": cur_sha,
                    "remote_last_edited": remote_last,
                    "last_sync_at": last_sync_value,  # 初期同期待ちを防ぎ、初回auto pullで差分のみになる
                    "updated_at": int(time.time()),
                })
                save_meta(root_dir, root_meta)
            # progress
            _progress_tick(os.path.relpath(file_path, root_dir))
            # ファイル本文更新はDIRの更新には含めない
        child_title = os.path.splitext(fn)[0]
        file_links.append((child_title, child_url))

    return file_links

def _count_targets(dir_path: str, *, meta: MetaType, root_dir: str, changed_only: bool) -> int:
    if is_ignored(meta, dir_path, root_dir):
        return 0
    total = 0
    # subdirs
    for d in [x for x in os.listdir(dir_path) if os.path.isdir(os.path.join(dir_path, x)) and not x.startswith('.')]:
        total += _count_targets(os.path.join(dir_path, d), meta=meta, root_dir=root_dir, changed_only=changed_only)
    # files
    for fn in [x for x in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, x)) and is_markdown_file(x)]:
        p = os.path.join(dir_path, fn)
        if is_ignored(meta, p, root_dir):
            continue
        mtime_ns = _mtime_ns(p)
        known = get_item(meta, p)
        k_ns = (known or {}).get('local_mtime_ns') if known else None
        k_s = (known or {}).get('local_mtime') if known else None
        if changed_only and known and known.get('page_url') and ((k_ns is not None and k_ns == mtime_ns) or (k_ns is None and k_s == int(mtime_ns/1_000_000_000))):
            continue
        total += 1
    return total

def _push_flat_mode(folder: str, root_parent_url: str, args) -> None:
    """
    Flat Mode専用Push処理: フォルダ内の全.mdファイルをNotionページとして作成/更新
    frontmatterから親子関係を読み取り、階層構造を再構築
    """
    import glob
    import subprocess
    
    dry_run = getattr(args, 'dry_run', False)
    changed_only = getattr(args, 'changed_only', False)
    
    # 1. 全.mdファイルを収集
    md_files = []
    for f in glob.glob(os.path.join(folder, '*.md')):
        if os.path.isfile(f):
            md_files.append(f)
    
    if not md_files:
        print("[c2n] No .md files found in flat mode directory.")
        return
    
    print(f"[c2n] Found {len(md_files)} .md files to process")
    
    # 2. frontmatter解析してpage_id, parent_id, titleを抽出
    page_map = {}  # {page_id: {'path': ..., 'parent_id': ..., 'title': ..., 'frontmatter': ...}}
    
    for md_path in md_files:
        fm = _parse_frontmatter(md_path)
        page_id = fm.get('page_id', '').strip()
        parent_id = fm.get('parent_id', '').strip()
        
        # titleはファイル名から抽出（拡張子除外、ID suffix除外）
        filename = os.path.basename(md_path)
        title = filename.replace('.md', '')
        
        # タイトル末尾のID suffix除去（例: "title_27db..." → "title"）
        if '_' in title and len(title.split('_')[-1]) >= 10:
            title = '_'.join(title.split('_')[:-1])
        
        page_map[page_id] = {
            'path': md_path,
            'parent_id': parent_id,
            'title': title,
            'frontmatter': fm,
            'page_url': fm.get('page_url', '').strip()
        }
    
    # 3. ルートページ特定（parent_idがroot_parent_urlのpage_id）
    try:
        root_page_id = extract_id_from_url_strict(root_parent_url)
    except Exception:
        root_page_id = ''
    
    # 4. 階層順にソート（親→子）
    def get_depth(pid: str, visited=None) -> int:
        if visited is None:
            visited = set()
        if pid in visited:
            return 999  # 循環参照防止
        visited.add(pid)
        info = page_map.get(pid, {})
        parent_id = info.get('parent_id', '')
        if not parent_id or parent_id == root_page_id:
            return 0
        return 1 + get_depth(parent_id, visited)
    
    sorted_pages = sorted(page_map.items(), key=lambda x: get_depth(x[0]))
    
    # 5. 各ページをNotion push（親→子順）- md2notion.py CLI呼び出し
    md2notion_path = os.path.join(os.path.dirname(__file__), 'notion_page_manager.py')
    
    for i, (page_id, info) in enumerate(sorted_pages, 1):
        md_path = info['path']
        title = info['title']
        parent_id = info['parent_id']
        page_url = info['page_url']
        
        print(f"[{i}/{len(sorted_pages)}] Processing: {title}")
        
        # 親URLの解決
        if parent_id == root_page_id:
            parent_url = root_parent_url
        elif parent_id in page_map:
            parent_url = page_map[parent_id].get('page_url', '')
            if not parent_url:
                print(f"  ⚠️ Parent page_url not found for parent_id={parent_id}, skipping")
                continue
        else:
            parent_url = root_parent_url
        
        if dry_run:
            if page_url:
                print(f"  [DRY] Would update: {title} -> {page_url}")
            else:
                print(f"  [DRY] Would create: {title} under {parent_url}")
            continue
        
        # notion_page_manager.py呼び出し
        cmd = [sys.executable, md2notion_path, md_path, parent_url, '-t', title]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                # 出力からURLを抽出（簡易実装）
                output = result.stdout + result.stderr
                if 'https://notion.so/' in output or 'https://www.notion.so/' in output:
                    # 新規作成の場合、返却URLを page_map に記録
                    if not page_url:
                        for line in output.split('\n'):
                            if 'notion.so/' in line:
                                url_part = line.split('notion.so/')[-1].strip()
                                new_url = f"https://www.notion.so/{url_part}"
                                page_map[page_id]['page_url'] = new_url
                                break
                if page_url:
                    print(f"  U(updated): {title}")
                else:
                    print(f"  +(created): {title}")
            else:
                handle_subprocess_error(result, cmd, prefix="Flat mode")
        except Exception as e:
            print_error(f"Flat mode exception: {str(e)[:100]}")
    
    print("[c2n] ✅ Flat Mode Push completed")

# Delegate to DirectoryProcessor
def walk_and_upload(root_dir: str, root_parent_url: str, *, dry_run: bool = False, changed_only: bool = False, no_dir_update: bool = False, precount_total: Optional[int] = None) -> None:
    """Walk directory tree and upload to Notion"""
    # Get Notion client
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        _load_env_for_folder(root_dir)
        token = os.environ.get("NOTION_TOKEN")
    
    client = Client(auth=token) if token else None
    if not client:
        raise Exception("Notion client not available")
    
    # Load metadata
    meta = load_meta(root_dir)
    
    # Create processor and execute
    processor = DirectoryProcessor(client, root_dir, meta)
    processor.walk_and_upload(root_dir, root_parent_url, dry_run=dry_run, changed_only=changed_only, no_dir_update=no_dir_update, precount_total=precount_total)

def parse_args():
    parser = argparse.ArgumentParser(description='Upload a folder hierarchy to Notion pages.')
    parser.add_argument('folder', help='Path to the source folder')
    parser.add_argument('--parent-url', help='Notion parent page URL (default: config.json default_parent_url)')
    parser.add_argument('--dry-run', action='store_true', help='Plan only. Show actions without writing to Notion or meta')
    parser.add_argument('--log-file', help='Path to save plan/execution logs (optional)')
    parser.add_argument('--changed-only', action='store_true', help='Upload only changed/new files using .c2n/index.yaml mtimes')
    parser.add_argument('--no-dir-update', action='store_true', help='Do not modify directory pages (disable preview insertion and body edits)')
    parser.add_argument('--no-progress', action='store_true', help='Disable progress percentage output')
    parser.add_argument('--verbose', action='store_true', help='Show detailed conversion logs (disable suppression)')
    parser.add_argument('--flat-mode', action='store_true', help='Flat mode: upload all .md files as pages, reconstruct hierarchy from frontmatter')
    return parser.parse_args()

def main():
    args = parse_args()
    folder = os.path.abspath(args.folder)
    if not os.path.isdir(folder):
        exit_with_error(f'Folder not found: {folder}')

    # try load .env for this folder
    print("[c2n] Loading env/config for target...")
    _load_env_for_folder(folder)
    print("[c2n] Env loaded. Ensuring token bridge...")
    global NOTION_TOKEN, notion
    if not (os.environ.get('NOTION_TOKEN') or os.environ.get('NOTION_API_KEY')):
        exit_with_error('NOTION_TOKEN is not set')
    # refresh client with possibly newly loaded token
    NOTION_TOKEN = os.environ.get('NOTION_TOKEN') or os.environ.get('NOTION_API_KEY')
    notion = Client(auth=NOTION_TOKEN)
    print("[c2n] Notion client initialized.")

    # Cache manager
    global _CACHE_MANAGER, _PREV_DIR_SNAPSHOT, _PREV_FILE_SNAPSHOT
    cache_file_env = os.environ.get('C2N_CACHE_FILE')
    if cache_file_env:
        cache_root = os.path.dirname(os.path.dirname(cache_file_env))
    else:
        cache_root = folder
    _CACHE_MANAGER = CacheManager(cache_root)
    cache_prev = _CACHE_MANAGER.load()
    env_chain = _collect_env_chain(folder)
    cfg_path = _config_path(folder)
    ign_path = os.path.join(folder, '.c2n_ignore')
    idx_path = _meta_path(folder)
    probe = {
        'config_path': cfg_path,
        'config_mtime': _path_mtime(cfg_path),
        'ignore_path': ign_path,
        'ignore_mtime': _path_mtime(ign_path),
        'index_path': idx_path,
        'index_mtime': _path_mtime(idx_path),
        'env_chain': env_chain,
    }

    # .c2n/config.json → parent_url
    parent_url = args.parent_url
    config: Dict[str, Any] = {}
    if not parent_url:
        # try cache
        if cache_prev and cache_prev.get('probe') == {
            'config_path': probe['config_path'], 'config_mtime': probe['config_mtime']
        } and cache_prev.get('parent_url'):
            parent_url = cache_prev.get('parent_url')
        else:
            print("[c2n] Reading .c2n/config.json (if any)...")
            config = load_folder_config(folder)
            parent_url = config.get('default_parent_url')
    if not parent_url:
        exit_with_error('parent URL is required (pass --parent-url or set in config.json)')

    global _LOG_FP, _NO_PROGRESS, _VERBOSE
    try:
        if args.log_file:
            os.makedirs(os.path.dirname(os.path.abspath(args.log_file)), exist_ok=True)
            _LOG_FP = open(args.log_file, 'w', encoding='utf-8')
        _NO_PROGRESS = bool(getattr(args, 'no_progress', False))
        _VERBOSE = bool(getattr(args, 'verbose', False))
        # load .c2n_ignore from root folder (with cache)
        ignore_file = os.path.join(folder, '.c2n_ignore')
        if cache_prev and cache_prev.get('probe', {}).get('ignore_path') == probe['ignore_path'] \
           and cache_prev.get('probe', {}).get('ignore_mtime') == probe['ignore_mtime'] \
           and isinstance(cache_prev.get('ignore_patterns'), list):
            _IGNORE_PATTERNS[:] = cache_prev.get('ignore_patterns')
        elif os.path.exists(ignore_file):
            print("[c2n] Reading .c2n_ignore...")
            loaded: List[str] = []
            with open(ignore_file, 'r', encoding='utf-8') as f:
                for raw in f:
                    line = raw.strip()
                    if not line or line.startswith('#'):
                        continue
                    if line.startswith('/'):
                        line = line[1:]
                    if line.endswith('/'):
                        base = line.rstrip('/')
                        if base:
                            loaded.append(base)
                            loaded.append(base + '/**')
                    else:
                        loaded.append(line)
            _IGNORE_PATTERNS[:] = loaded
            print(f"[c2n] Loaded ignore patterns: {len(_IGNORE_PATTERNS)}")
        print("[c2n] Scanning filesystem and counting items...")
        precount = None
        try:
            if cache_prev and cache_prev.get('probe') == probe:
                # reuse last total and previous snapshots
                if isinstance(cache_prev.get('last_prog_total'), int):
                    precount = cache_prev.get('last_prog_total')
                if isinstance(cache_prev.get('dir_snapshot'), dict):
                    _PREV_DIR_SNAPSHOT = dict(cache_prev.get('dir_snapshot'))
                if isinstance(cache_prev.get('file_snapshot'), dict):
                    _PREV_FILE_SNAPSHOT = dict(cache_prev.get('file_snapshot'))
        except Exception:
            precount = None
        
        # Flat mode分岐
        if getattr(args, 'flat_mode', False):
            print("[c2n] 🎯 Flat Mode: Pushing all .md files as flat pages...")
            _push_flat_mode(folder, parent_url, args)
        else:
            walk_and_upload(folder, parent_url, dry_run=args.dry_run, changed_only=getattr(args, 'changed_only', False), no_dir_update=getattr(args, 'no_dir_update', False), precount_total=precount)
    finally:
        # save cache snapshot
        if _CACHE_MANAGER:
            _CACHE_MANAGER.update_probe(**probe)
            data = _CACHE_MANAGER.data
            data['parent_url'] = parent_url
            data['ignore_patterns'] = list(_IGNORE_PATTERNS)
            data['last_prog_total'] = _PROG_TOTAL
            _CACHE_MANAGER.set_dir_snapshot(_DIR_SNAPSHOT)
            _CACHE_MANAGER.set_file_snapshot(_FILE_SNAPSHOT)
            _CACHE_MANAGER.ensure_saved()
        if _LOG_FP is not None:
            try:
                _LOG_FP.close()
            except Exception:
                pass

if __name__ == '__main__':
    main()


