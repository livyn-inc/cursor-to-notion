#!/usr/bin/env python3

"""
nit CLI - Main entry point for cursor_to_notion tool
"""

import os
import sys
import argparse
import json
import subprocess
import time
import re
import shutil
import difflib
import datetime
from typing import Optional, Dict, Any

from c2n_core.cache import CacheManager
from c2n_core.meta import ensure_meta
from c2n_core.meta_io import _load_meta, _save_meta
from c2n_core.logging import ensure_dependency
from c2n_core.pull_context import build_pull_context
from c2n_core.push_context import build_push_context
from c2n_core.utils import load_config_for_folder, save_config_for_folder, extract_id_from_url
from c2n_core.env import _load_env_file as _core_load_env_file, _ensure_notion_env_bridge as _core_ensure_notion_env_bridge
from c2n_core.error import exit_with_error, print_error
from c2n_core.url_resolver import URLResolver, ensure_root_url_consistency
from c2n_core.meta_updater import MetaUpdater, ensure_meta_consistency
from c2n_core.error_improved import print_url_error, print_warning
from notion_client import Client

# Import CLI components
from cli.command_handlers import CommandHandlers
from cli.config_manager import ConfigManager
from cli.merge_handler import MergeHandler
from cli.argument_parser import create_argument_parser

ROOT = os.path.dirname(os.path.abspath(__file__))

# Ensure line-buffered stdout/stderr even when piped (e.g., `| cat`)
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass

# Backward-compatible wrapper for tests expecting _load_env_file in this module
def _load_env_file(path: str):
    """Load .env style file and export into os.environ.
    Only set variables not already present. Strip surrounding single/double quotes.
    """
    _core_load_env_file(path)

def _prepare_pull_output_base(target_folder: str, snapshot: bool) -> str:
    base = os.path.join(target_folder, '.c2n', 'pull')
    latest = os.path.join(base, 'latest')
    if os.path.isdir(latest):
        if snapshot:
            hist_root = os.path.join(base, 'history')
            os.makedirs(hist_root, exist_ok=True)
            dst = os.path.join(hist_root, str(int(time.time())))
            try:
                shutil.move(latest, dst)
            except Exception:
                pass
        else:
            try:
                shutil.rmtree(latest, ignore_errors=True)
            except Exception:
                pass
    os.makedirs(latest, exist_ok=True)
    return latest

def _read_text(path: str) -> str:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return ''

def _write_text(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

# Delegate to MergeHandler
def _merge_two_way(dst_txt: str, src_txt: str) -> str:
    """Git風のコンフリクトマーカーで行レベルマージを実行"""
    return MergeHandler.merge_two_way(dst_txt, src_txt)

# Delegate to MergeHandler
def _apply_direct_merge(src_path: str, dst_path: str) -> str:
    """ファイルを直接マージして結果を返す"""
    return MergeHandler.apply_direct_merge(src_path, dst_path)


# Additional imports already included above

def _ensure_notion_env_bridge():
    _core_ensure_notion_env_bridge()

def _load_env_for_target(target_folder: str):
    from c2n_core.env import _load_env_for_target as _core_load_env_for_target
    _core_load_env_for_target(target_folder)

def ensure_meta(dir_path: str) -> str:
    c2n = os.path.join(dir_path, '.c2n')
    os.makedirs(c2n, exist_ok=True)
    return c2n

def load_config(target: str) -> Dict[str, Any]:
    target = os.path.abspath(target)
    config = load_config_for_folder(target)
    if 'sync_mode' not in config:
        config['sync_mode'] = 'hierarchy'
    return config

def _prompt_parent_url(default: str = "") -> str:
    try:
        prompt = "Enter Notion parent page URL for this workspace (required): "
        value = input(prompt).strip()
        if not value and default:
            return default
        return value
    except EOFError:
        return default


def cmd_init(target: str, workspace_url: str = "", root_url: str = ""):
    """
    Initialize a project for Notion sync (v2.1).
    
    Args:
        target: Folder path to initialize
        workspace_url: Notion workspace URL (parent of project folder) - v2.1 recommended
        root_url: Notion project page URL (legacy, for backward compatibility)
    
    v2.1 behavior:
    - If workspace_url is provided, create a folder page under it for this project
    - If root_url is provided (legacy), use it directly as project_url
    - If neither is provided, prompt interactively
    """
    from c2n_core.project_init import initialize_project
    from c2n_core.prompt import prompt_for_url
    import os
    
    target = os.path.abspath(target)
    project_name = os.path.basename(target)
    
    # Check if already initialized
    cfg_path = os.path.join(target, '.c2n', 'config.json')
    if os.path.exists(cfg_path):
        print(f'✅ 既に初期化済みです: {cfg_path}')
        print(f'💡 設定を変更する場合は、ファイルを直接編集してください')
        return
    
    # Determine which URL to use
    project_url = None
    final_workspace_url = workspace_url
    
    if workspace_url:
        # v2.1: Create folder page under workspace
        print(f"\n📦 ワークスペース配下にプロジェクトフォルダを作成中...")
        print(f"   ワークスペース: {workspace_url}")
        print(f"   プロジェクト名: {project_name}")
        
        try:
            from c2n_core import notion_hierarchy
            from notion_client import Client
            
            _ensure_notion_env_bridge()
            token = os.getenv('NOTION_TOKEN')
            if not token:
                exit_with_error("NOTION_TOKENが設定されていません")
            
            client = Client(auth=token)
            
            # Create folder page for this project
            result = notion_hierarchy.create_folder_page(
                parent_url=workspace_url,
                title=project_name,
                notion_client=client
            )
            project_url = result['url']
            
            print(f"\n✅ プロジェクトフォルダを作成しました")
            print(f"   📁 プロジェクトURL: {project_url}")
            
        except Exception as e:
            exit_with_error(f"プロジェクトフォルダの作成に失敗しました: {e}")
    
    elif root_url:
        # Legacy: Use root_url directly
        print(f"\n⚠️  レガシーモード: root_urlを直接使用します")
        print(f"   今後は --workspace-url の使用を推奨します")
        project_url = root_url
        
        # Try to detect workspace_url from root_url
        try:
            from c2n_core import notion_hierarchy
            from notion_client import Client
            from c2n_core.utils import extract_id_from_url
            
            _ensure_notion_env_bridge()
            token = os.getenv('NOTION_TOKEN')
            if token:
                client = Client(auth=token)
                page_id = extract_id_from_url(root_url)
                detected_workspace = notion_hierarchy.get_parent_page_url(page_id, client)
                if detected_workspace:
                    final_workspace_url = detected_workspace
                    print(f"   🔍 ワークスペースURL検出: {final_workspace_url}")
        except Exception:
            pass  # Workspace detection is optional
    
    else:
        # Interactive prompt
        try:
            from c2n_core import notion_hierarchy
            from notion_client import Client
            from c2n_core.utils import extract_id_from_url
            
            print("\n📝 プロジェクト初期化")
            print("━" * 40)
            print("\nNotion URLを指定してください:")
            print("  1. ワークスペースURL（推奨）: プロジェクトフォルダを自動作成")
            print("  2. プロジェクトURL（レガシー）: 直接使用")
            print("")
            
            project_url = prompt_for_url()
            
            # Try to detect if this is a workspace or project URL
            # If it has children, assume it's a workspace; create folder page
            # Otherwise, use it directly as project URL
            try:
                _ensure_notion_env_bridge()
                token = os.getenv('NOTION_TOKEN')
                if token:
                    client = Client(auth=token)
                    
                    # Try to create a folder page under the provided URL
                    print(f"\n🔍 URL種別を判定中...")
                    result = notion_hierarchy.create_folder_page(
                        parent_url=project_url,
                        title=project_name,
                        notion_client=client
                    )
                    
                    # Success - it was a workspace URL
                    final_workspace_url = project_url
                    project_url = result['url']
                    print(f"✅ ワークスペースURLと判定し、プロジェクトフォルダを作成しました")
                    print(f"   📁 プロジェクトURL: {project_url}")
            
            except Exception:
                # Failed to create folder - assume it's already a project URL
                print(f"ℹ️  プロジェクトURLとして使用します")
                # Try to detect parent
                try:
                    page_id = extract_id_from_url(project_url)
                    detected_parent = notion_hierarchy.get_parent_page_url(page_id, client)
                    if detected_parent:
                        final_workspace_url = detected_parent
                        print(f"   🔍 親ワークスペースURL検出: {final_workspace_url}")
                except Exception:
                    pass
        
        except ValueError as e:
            exit_with_error(str(e))
        except KeyboardInterrupt:
            print("\n\n❌ 初期化をキャンセルしました")
            sys.exit(1)
    
    # Initialize project using common logic
    if not project_url:
        exit_with_error("プロジェクトURLの取得に失敗しました")
    
    try:
        initialize_project(target, project_url, workspace_url=final_workspace_url)
        print(f"""
✅ プロジェクトを初期化しました: {target}

📁 作成されたファイル:
   - .c2n/config.json (project_url: {project_url})
   - .c2n/index.yaml
   - .c2n_ignore

次のステップ:
1. ローカルでMarkdownファイルを作成
2. nit push {target}  # Notionに初回同期

または、既存のNotionページを取得する場合:
  nit pull {target}
""")
    except Exception as e:
        exit_with_error(f"初期化に失敗しました: {e}")


def cmd_clone(notion_url: str = "", local_folder: str = "", workspace_url: str = "", verbose: bool = False):
    """
    Clone Notion pages to local folder (v2.1).
    
    Args:
        notion_url: Notion project page URL (optional, interactive if not provided)
        local_folder: Local folder path (optional, interactive if not provided)
        workspace_url: Notion workspace URL (auto-detected if not provided)
        verbose: Show detailed logs
    
    v2.1 behavior:
    - Auto-detects workspace_url from notion_url's parent if not provided
    - Stores both project_url and workspace_url in config.json
    """
    from c2n_core.project_init import initialize_project
    from c2n_core.prompt import prompt_for_url, prompt_for_folder
    from c2n_core import notion_hierarchy
    from c2n_core.utils import extract_id_from_url
    from notion_client import Client
    
    # Interactive prompt if notion_url not provided
    if not notion_url:
        try:
            print("\n📦 Notionページのクローン")
            print("━" * 40)
            notion_url = prompt_for_url()
        except ValueError as e:
            exit_with_error(str(e))
        except KeyboardInterrupt:
            print("\n\n❌ クローンをキャンセルしました")
            sys.exit(1)
    
    # Interactive prompt if local_folder not provided
    if not local_folder:
        try:
            local_folder = prompt_for_folder()
        except ValueError as e:
            exit_with_error(str(e))
        except KeyboardInterrupt:
            print("\n\n❌ クローンをキャンセルしました")
            sys.exit(1)
    
    local_folder = os.path.abspath(local_folder)
    
    # v2.1: Auto-detect workspace_url if not provided
    detected_workspace_url = workspace_url
    if not detected_workspace_url:
        try:
            print(f"\n🔍 ワークスペースURLを自動検出中...")
            _ensure_notion_env_bridge()
            token = os.getenv('NOTION_TOKEN')
            if token:
                client = Client(auth=token)
                page_id = extract_id_from_url(notion_url)
                detected_workspace_url = notion_hierarchy.get_parent_page_url(page_id, client)
                if detected_workspace_url:
                    print(f"   ✅ ワークスペースURL検出: {detected_workspace_url}")
                else:
                    print(f"   ℹ️  親ページが見つかりませんでした（トップレベルページの可能性）")
        except Exception as e:
            print(f"   ⚠️  ワークスペースURL自動検出に失敗: {e}")
            print(f"   ℹ️  workspace_url なしで初期化を続行します")
    
    # 1. Initialize project using common logic
    print(f"\n[c2n] 📁 プロジェクトを初期化中...")
    try:
        initialize_project(local_folder, notion_url, workspace_url=detected_workspace_url)
    except Exception as e:
        exit_with_error(f"初期化に失敗しました: {e}")
    
    # 2. Pull all pages from Notion
    print(f"[c2n] 📥 Notionページを取得中...")
    try:
        cmd_pull(target=local_folder, snapshot=False, apply=True)
        
        workspace_info = f"\n   🏢 ワークスペース: {detected_workspace_url}" if detected_workspace_url else ""
        
        print(f"""
✅ クローンが完了しました: {local_folder}

📁 Notionページがローカルに保存されました
   🔗 プロジェクト: {notion_url}{workspace_info}

次のステップ:
1. cd {local_folder}
2. ファイルを編集
3. nit push .  # 変更をNotionに反映
4. nit pull .  # Notionからの変更を取得
""")
    except Exception as e:
        exit_with_error(f"Pullに失敗しました: {e}")

def _run_folder_to_notion(folder: str, parent_url: str = None, dryrun: bool = False, log_file: str = None, changed_only: bool = False, no_dir_update: bool = False, stream: bool = True, flat_mode: bool = False, cache_file: Optional[str] = None):
    # Immediate user feedback before spawning child process
    try:
        mode = 'dryrun' if dryrun else 'push'
        print(f"[c2n] Start: {mode} (preparing env/config...)")
        sys.stdout.flush()
    except Exception:
        pass
    args = [sys.executable, '-u', os.path.join(ROOT, 'notion_push.py'), folder]
    if parent_url:
        args += ['--parent-url', parent_url]
    if dryrun:
        args += ['--dry-run']
    if log_file:
        args += ['--log-file', log_file]
    if changed_only:
        args += ['--changed-only']
    if no_dir_update:
        args += ['--no-dir-update']
    if flat_mode:
        args += ['--flat-mode']
    try:
        print("[c2n] Spawning folder_to_notion...")
        sys.stdout.flush()
    except Exception:
        pass
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    if cache_file:
        env['C2N_CACHE_FILE'] = cache_file
    if not stream:
        result = subprocess.run(args, check=False, env=env)
        if result.returncode != 0:
            print_error(f"Subprocess failed with exit code {result.returncode}")
            sys.exit(result.returncode)
        return
    # streaming mode: print child stdout in real-time
    proc = subprocess.Popen(args, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    assert proc.stdout is not None
    # Heartbeat until first output arrives
    try:
        import select  # Unix: ok (darwin)
        first_output = False
        start_ts = time.time()
        last_beat = 0.0
        while True:
            if proc.poll() is not None:
                break
            r, _, _ = select.select([proc.stdout], [], [], 0.2)
            if r:
                chunk = proc.stdout.readline()
                if chunk:
                    print(chunk, end='')
                    first_output = True
                    break
            now = time.time()
            if now - last_beat >= 0.5:  # print every 500ms
                elapsed_ms = int((now - start_ts) * 1000)
                print(f"[c2n] waiting child output... ({elapsed_ms}ms)")
                last_beat = now
        # stream remaining lines
        if first_output:
            for line in proc.stdout:
                # HTTPリクエストログを抑制
                if 'HTTP Request:' not in line and 'httpx' not in line and 'httpcore' not in line:
                    print(line, end='')
    finally:
        proc.wait()
    if proc.returncode != 0:
        print_error(f"Subprocess failed with exit code {proc.returncode}")
        sys.exit(proc.returncode)
    
    # 成功時は処理されたアイテム数を返す（簡易実装）
    return 1

def cmd_push(target: str, force_all: bool = False, dry_run: bool = False, verbose: bool = False):
    """
    Push local changes to Notion (v2.1).
    
    Args:
        target: Folder to push
        force_all: Force push all files (ignore change detection)
        dry_run: Preview changes without pushing
        verbose: Show detailed logs
    
    Default behavior (v2.1):
        - Only push changed files (unless --force-all)
        - Update directory structure
        - Use project_url from config.json (v2.1)
    """
    # v2.0: Map new options to internal implementation
    # changed_only is now the default (inverted by force_all)
    changed_only = not force_all
    no_dir_update = False  # v2.0: Always update directory structure
    
    ctx = build_push_context(target)
    _load_env_for_target(ctx.target)
    
    # v2.1: Use URLResolver.get_project_url() for unified URL resolution
    resolver = URLResolver(target)
    root_url = resolver.get_project_url()
    
    if not root_url:
        print_url_error(target, "missing")
        return

    log_path = os.path.join(ctx.target, '.c2n', 'run.log')
    final_changed_only = True if changed_only is None else bool(changed_only)
    final_no_dir_update = ctx.no_dir_update_default if no_dir_update is None else bool(no_dir_update)

    cache_mgr = ctx.cache_manager

    if ctx.sync_mode == 'flat':
        print("[c2n] Flat Mode: Pushing with --flat-mode flag")
        _run_folder_to_notion(
            ctx.target,
            parent_url=root_url,
            dryrun=False,
            log_file=log_path,
            changed_only=final_changed_only,
            no_dir_update=final_no_dir_update,
            cache_file=cache_mgr.cache_path if cache_mgr else None,
            flat_mode=True,
        )
    else:
        _run_folder_to_notion(
            ctx.target,
            parent_url=root_url,
            dryrun=False,
            log_file=log_path,
            changed_only=final_changed_only,
            no_dir_update=final_no_dir_update,
            cache_file=cache_mgr.cache_path if cache_mgr else None,
        )

    # URLResolverを使用してルートURLを取得し、index.yamlを更新
    resolver = URLResolver(ctx.target)
    root_url = resolver.get_root_url()
    if root_url:
        meta = _load_meta(ctx.target)
        meta['root_page_url'] = root_url
        _save_meta(ctx.target, meta)

    # ensure cache data persisted if modified downstream
    cache_mgr.ensure_saved()

def cmd_dryrun(target: str, no_dir_update: Optional[bool] = None):
    target = os.path.abspath(target)
    _load_env_for_target(target)
    
    # Use URLResolver for unified URL resolution
    resolver = URLResolver(target)
    root_url = resolver.get_root_url()
    
    if not root_url:
        print_url_error(target, "missing")
        return
    
    # Load config with backward-compatible sync_mode
    conf_all = load_config(target)
    sync_mode = (conf_all or {}).get('sync_mode', 'hierarchy')
    
    cfg = os.path.join(target, '.c2n', 'config.json')
    no_dir_update_default: bool = True
    if os.path.exists(cfg):
        try:
            with open(cfg, 'r', encoding='utf-8') as f:
                conf = (json.load(f) or {})
                if 'no_dir_update_default' in conf:
                    no_dir_update_default = bool(conf.get('no_dir_update_default'))
        except Exception:
            pass
    log_path = os.path.join(target, '.c2n', 'dryrun.log')
    final_no_dir_update = no_dir_update_default if no_dir_update is None else bool(no_dir_update)
    
    # Flat mode分岐
    if sync_mode == 'flat':
        print("[c2n] Flat Mode: Dryrun with --flat-mode flag")
        _run_folder_to_notion(target, parent_url=root_url, dryrun=True, log_file=log_path, 
                             no_dir_update=final_no_dir_update, flat_mode=True)
    else:
        _run_folder_to_notion(target, parent_url=root_url, dryrun=True, log_file=log_path, 
                             no_dir_update=final_no_dir_update)

def cmd_pull(target: str, snapshot: bool = False, apply: bool = True):
    """
    Pull changes from Notion (v2.1).
    
    Args:
        target: Folder to pull
        snapshot: If True, only check existing pages; if False, discover new pages too
        apply: If True, apply changes; if False, only show what would change
    
    v2.1 changes:
        - Use project_url from config.json instead of root_page_url from index.yaml
    """
    ctx = build_pull_context(target)
    _load_env_for_target(ctx.target)
    
    # v2.1: Use URLResolver.get_project_url() for unified URL resolution
    resolver = URLResolver(target)
    root_url = resolver.get_project_url()
    
    if not root_url:
        print_url_error(target, "missing")
        return

    if ctx.sync_mode == 'flat':
        try:
            parent = root_url
            if not parent:
                raise ValueError("Parent page URL is required for flat mode.")
            out_dir = _prepare_pull_output_base(ctx.target, snapshot=snapshot)
            cmd = [
                sys.executable,
                os.path.join(ROOT, 'notion_pull.py'),
                parent,
                '-o', out_dir,
                '--flat-mode'
            ]
            print('[c2n] Start: pull (flat mode) ...')
            _ensure_notion_env_bridge()
            subprocess.run(cmd, check=False)
            if apply:
                _apply_merge_from_pull_latest(ctx.target)
            return
        except Exception as e:
            print_error(f"[c2n] Flat mode pull failed: {e}")

    use_fast_check = False
    changed_pages = []
    # ✅ FIX: Reload meta to ensure we have the latest index.yaml (especially after a push)
    meta = _load_meta(target) or {}
    print(f"[c2n] DEBUG: Reloaded meta, items count: {len(meta.get('items', {}))}")
    # DEBUG: Print last_sync_at for first 3 items
    if isinstance(meta.get('items'), dict):
        for i, (path, info) in enumerate(list(meta['items'].items())[:3]):
            if isinstance(info, dict):
                print(f"[c2n] DEBUG:   [{i}] {os.path.basename(path)}: last_sync_at={info.get('last_sync_at')}")
    cache_mgr = ctx.cache_manager
    try:
        from notion_client import Client  # type: ignore
        token = os.environ.get('NOTION_TOKEN') or os.environ.get('NOTION_API_KEY')
        
        # 🔍 DEBUG: Log diff check conditions
        print(f"[c2n] DEBUG: token exists: {bool(token)}")
        print(f"[c2n] DEBUG: meta is dict: {isinstance(meta, dict)}")
        print(f"[c2n] DEBUG: meta.get('items'): {bool(meta.get('items') if isinstance(meta, dict) else False)}")
        if isinstance(meta, dict) and meta.get('items'):
            print(f"[c2n] DEBUG: items count: {len(meta.get('items', {}))}")
        
        if token and isinstance(meta, dict) and meta.get('items'):
            use_fast_check = True
            print("[c2n] Start: pull (optimized with diff check)")
            notion = Client(auth=token)
            prev_snapshot = cache_mgr.get_remote_snapshot()
            items = meta.get('items') or {}
            candidates = []
            for path, info in items.items():
                if not isinstance(info, dict) or info.get('type') not in ('file', 'directory'):
                    continue
                pid = info.get('page_id') or extract_id_from_url(info.get('page_url') or '')
                if pid:
                    candidates.append((path, pid, info))

            if candidates:
                print(f"[c2n] Checking {len(candidates)} existing pages for changes...")
                from concurrent.futures import ThreadPoolExecutor, as_completed
                remote_snapshot = {}
                def _fetch(pid: str):
                    try:
                        page = notion.pages.retrieve(page_id=pid)
                        return page.get('last_edited_time')
                    except Exception:
                        return None

                with ThreadPoolExecutor(max_workers=6) as ex:
                    fut_map = {ex.submit(_fetch, pid): (path, pid, info) for (path, pid, info) in candidates}
                    for fut in as_completed(fut_map):
                        path, pid, info = fut_map[fut]
                        last_edited = fut.result()
                        remote_snapshot[pid] = last_edited
                        try:
                            if isinstance(meta.get('items'), dict) and path in meta['items'] and isinstance(meta['items'][path], dict):
                                meta['items'][path]['remote_last_edited'] = last_edited
                            # 🔍 DEBUG: Log info content before accessing last_sync_at
                            print(f"[c2n] DEBUG: {path}")
                            # ✅ FIX: Read last_sync_at from the reloaded meta, not from the old info snapshot
                            current_info = meta.get('items', {}).get(path, {}) if isinstance(meta.get('items'), dict) else {}
                            print(f"[c2n] DEBUG:   current_info keys: {list(current_info.keys()) if isinstance(current_info, dict) else 'NOT A DICT'}")
                            print(f"[c2n] DEBUG:   current_info.get('last_sync_at'): {current_info.get('last_sync_at')}")
                            last_sync_at = current_info.get('last_sync_at') if isinstance(current_info, dict) else None
                            # 🔍 DEBUG: Log timestamp comparison
                            print(f"[c2n] DEBUG:   last_edited={last_edited}, last_sync_at={last_sync_at}")
                            # ✅ FIX: Use strict comparison (>) to avoid unnecessary pulls when timestamps are identical
                            if last_edited and (not last_sync_at or last_edited > last_sync_at):
                                print(f"[c2n] DEBUG:   → CHANGED")
                                changed_pages.append((info.get('page_url'), path, last_edited))
                            else:
                                print(f"[c2n] DEBUG:   → NO CHANGE")
                        except Exception as e:
                            print(f"[c2n] DEBUG:   → EXCEPTION: {e}")
                            changed_pages.append((info.get('page_url'), path, last_edited))

                cache_mgr.set_remote_snapshot(remote_snapshot)

                # 🔍 DEBUG: Log fallback conditions
                print(f"[c2n] DEBUG: changed_pages count: {len(changed_pages)}")
                print(f"[c2n] DEBUG: remote_snapshot == prev_snapshot: {remote_snapshot == prev_snapshot}")
                
                # ✅ FIX: If no changes detected, skip pull entirely (don't fallback to full sync)
                # Full sync should only happen if we can't perform diff check at all
                # if not changed_pages and remote_snapshot == prev_snapshot:
                #     print("[c2n] No changes detected via snapshot diff; falling back to full sync")
                #     use_fast_check = False

    except Exception as e:
        print(f"[c2n] Warning: diff check disabled ({e})")
        print(f"[c2n] DEBUG: Exception details: {type(e).__name__}: {str(e)}")
        use_fast_check = False
        changed_pages = []

    # 取得先を .c2n/pull/latest に直接指定
    out_dir = _prepare_pull_output_base(target, snapshot=snapshot)

    # ✅ FIX BUG-010: 差分検出モードで changed_pages を個別にダウンロード
    if use_fast_check and changed_pages:
        print(f"[c2n] Start: pull (fast check - {len(changed_pages)} changed pages)")
        for page_url, path, last_edited in changed_pages:
            if not page_url:
                print(f"[c2n] Warning: Skipping {path} (no page_url)")
                continue
            print(f"[c2n] Pulling changed page: {path}")
            
            # ✅ FIX BUG-010: Extract relative path from target directory and pass to notion_pull.py
            # This ensures the file is saved with the correct path structure in .c2n/pull/latest/
            rel_path = os.path.relpath(path, target) if os.path.isabs(path) else path
            
            single_args = [sys.executable, os.path.join(ROOT, 'notion_pull.py'), page_url, '-o', out_dir, '--target-relpath', rel_path]
            try:
                subprocess.run(single_args, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                print(f"[c2n] Warning: Failed to pull {path}: {e.stderr}")
    elif not use_fast_check:
        print(f"[c2n] Start: pull (full sync)")
        url = root_url
        args = [sys.executable, os.path.join(ROOT, 'notion_pull.py'), url, '-o', out_dir]
        # when using scoped root_url, also fetch children recursively
        if root_url:
            args.append('-c')

        # Streaming with heartbeat (mirrors push behavior)
        try:
            print("[c2n] Spawning notion2md...")
            sys.stdout.flush()
        except Exception:
            pass

        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        assert proc.stdout is not None
        try:
            import select
            first_output = False
            start_ts = time.time()
            last_beat = 0.0
            while True:
                if proc.poll() is not None:
                    break
                r, _, _ = select.select([proc.stdout], [], [], 0.2)
                if r:
                    chunk = proc.stdout.readline()
                    if chunk:
                        print(chunk, end='')
                        first_output = True
                        break
                now = time.time()
                if now - last_beat >= 0.5:
                    elapsed_ms = int((now - start_ts) * 1000)
                    print(f"[c2n] waiting child output... ({elapsed_ms}ms)")
                    last_beat = now
            if first_output:
                for line in proc.stdout:
                    # HTTPリクエストログを抑制
                    if 'HTTP Request:' not in line and 'httpx' not in line and 'httpcore' not in line:
                        print(line, end='')
        finally:
            proc.wait()

        if proc.returncode != 0:
            print_error(f"Subprocess failed with exit code {proc.returncode}")
            sys.exit(proc.returncode)
    else:
        # use_fast_check=True だが changed_pages が空の場合
        print("[c2n] No changes detected (fast check). Skipping pull.")
    
    # ✅ FIX IMP-010: Apply merge after pull (default behavior)
    if apply:
        print('--- Apply Merge (Notion -> working tree) ---')
        applied = _apply_merge_from_pull_latest(target)
        if applied == 0:
            print('no files to merge (already up-to-date)')
        else:
            print(f'merge applied: {applied} files. review conflict markers if any.')
            # メタデータ更新(変更されたページの同期時刻を更新)
            if use_fast_check and changed_pages:
                # ✅ FIX IMP-012: Preserve root_page_url before updating
                root_page_url_backup = meta.get('root_page_url')
                for _, changed_path, last_edited in changed_pages:
                    if isinstance(meta.get('items'), dict) and changed_path in meta['items']:
                        if isinstance(meta['items'][changed_path], dict):
                            meta['items'][changed_path]['last_sync_at'] = last_edited
                # ✅ FIX IMP-012: Restore root_page_url before saving
                if root_page_url_backup:
                    meta['root_page_url'] = root_page_url_backup
                _save_meta(target, meta)
    else:
        print('[c2n] Skipping auto-merge (--no-apply). Files are in .c2n/pull/latest/')
    cache_mgr.ensure_saved()
    return True


def _get_existing_page_ids(target: str) -> tuple[set[str], dict[str, str]]:
    """既存のページIDとパスのマッピングを取得"""
    meta = _load_meta(target) or {}
    existing_page_ids = set()
    existing_paths = {}
    
    if isinstance(meta, dict) and meta.get('items'):
        for path, info in meta['items'].items():
            if isinstance(info, dict):
                pid = info.get('page_id') or extract_id_from_url(info.get('page_url') or '')
                if pid:
                    existing_page_ids.add(pid)
                    existing_paths[pid] = path
    
    # 既知ページ（過去にnew-onlyで取得済みだがindex未反映の可能性があるもの）をキャッシュから統合
    cache_mgr = build_pull_context(target).cache_manager
    cached_known = set(cache_mgr.get_known_page_ids())
    if cached_known:
        existing_page_ids |= cached_known
    
    return existing_page_ids, existing_paths


def _get_changed_pages(target: str, existing_page_ids: set[str], client) -> list[str]:
    """最後のpull以降に変更されたページを特定"""
    changed_pages = []
    
    # 最後のpull時刻を取得
    last_pull_time = None
    last_pull_iso = None
    try:
        pull_dir = os.path.join(target, '.c2n', 'pull', 'latest')
        if os.path.exists(pull_dir):
            manifest_path = os.path.join(pull_dir, 'manifest.json')
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                    last_pull_time = manifest.get('pulled_at')
        
        if last_pull_time:
            # Unix timestamp to ISO format
            import datetime
            last_pull_dt = datetime.datetime.fromtimestamp(last_pull_time, tz=datetime.timezone.utc)
            last_pull_iso = last_pull_dt.isoformat()
            print(f"[c2n] Last pull: {last_pull_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        else:
            print("[c2n] No previous pull found, checking all pages")
    except Exception as e:
        print(f"[c2n] Warning: Could not determine last pull time: {e}")
        last_pull_iso = None
    
    # 変更されたページを特定（最後のpull以降のみ）
    print("[c2n] Checking for pages changed since last pull...")
    
    # 並列でlast_edited_timeを取得
    from concurrent.futures import ThreadPoolExecutor
    def get_last_edited(page_id):
        try:
            page = client.pages.retrieve(page_id=page_id)
            return page_id, page.get('last_edited_time')
        except Exception:
            return page_id, None
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(get_last_edited, existing_page_ids))
    
    for page_id, last_edited in results:
        if not last_edited:
            continue
        
        # 最後のpull以降に変更されたかチェック
        if last_pull_iso and last_edited <= last_pull_iso:
            continue  # 最後のpull以前の変更なのでスキップ
            
        changed_pages.append(page_id)
    
    print(f"[c2n] Found {len(changed_pages)} pages changed since last pull")
    return changed_pages


def _scan_for_new_pages(changed_pages: list[str], existing_page_ids: set[str], client, meta: dict) -> set[str]:
    """新規ページをスキャンして候補IDを取得"""
    candidate_page_ids = set()
    
    if changed_pages:
        print("[c2n] Scanning children of changed pages for new pages...")
        
        def scan_children(page_id, depth=0):
            if depth > 3:  # 深さ制限
                return
            try:
                response = client.blocks.children.list(block_id=page_id)
                for block in response.get('results', []):
                    if block.get('type') == 'child_page':
                        child_id = block.get('id')
                        if child_id:
                            candidate_page_ids.add(child_id)
                            # 新規ページの子も確認（浅く）
                            if child_id not in existing_page_ids and depth < 2:
                                scan_children(child_id, depth + 1)
            except Exception as e:
                print_warning(f"Failed to scan children of {page_id}: {e}")
        
        for page_id in changed_pages:
            scan_children(page_id)
    else:
        # 変更がない場合でも、ルート配下を多段で探索して新規ページを検出（深さ3）
        print("[c2n] No recent changes, scanning root page tree (depth<=3)...")
        root_url = meta.get('root_page_url')
        if root_url:
            root_page_id = extract_id_from_url(root_url)
            if root_page_id:
                def scan_root_tree(page_id: str, depth: int = 0):
                    if depth > 3:
                        return
                    try:
                        resp = client.blocks.children.list(block_id=page_id)
                        for blk in resp.get('results', []):
                            if blk.get('type') == 'child_page':
                                cid = blk.get('id')
                                if cid:
                                    candidate_page_ids.add(cid)
                                    # 新規の可能性がある子も辿る
                                    scan_root_tree(cid, depth + 1)
                    except Exception as e:
                        print_warning(f"Failed to scan root tree at {page_id}: {e}")

                scan_root_tree(root_page_id, 0)
    
    # 新規ページIDを特定
    new_page_ids = candidate_page_ids - existing_page_ids
    print(f"[c2n] Detected {len(new_page_ids)} new pages from incremental scan")
    return new_page_ids


def cmd_pull_new_only(target: str, snapshot: bool = False, update_time: bool = True, cleanup_folders: bool = False) -> bool:
    """新規ページのみを効率的に取得（増分スキャン方式）"""
    print("[c2n] Start: pull --new-only (incremental scan for new pages)")
    
    target = os.path.abspath(target)
    _load_env_for_target(target)
    
    # 既存のページIDを取得
    existing_page_ids, existing_paths = _get_existing_page_ids(target)
    print(f"[c2n] Found {len(existing_page_ids)} existing pages in local index")
    
    # 1. 変更されたページを特定
    from notion_client import Client
    token = os.environ.get('NOTION_TOKEN') or os.environ.get('NOTION_API_KEY')
    if not token:
        exit_with_error("NOTION_TOKEN not found")
    
    client = Client(auth=token)
    meta = _load_meta(target) or {}
    
    changed_pages = _get_changed_pages(target, existing_page_ids, client)
    
    # 2. 新規ページをスキャン
    new_page_ids = _scan_for_new_pages(changed_pages, existing_page_ids, client, meta)
    
    if not new_page_ids:
        print("[c2n] No new pages to pull")
        # 新規ページがない場合は時刻を更新しない（既存ページの変更検出に影響するため）
        return False
    
    # 3. 新規ページを取得
    out_dir = _pull_new_pages(target, new_page_ids, snapshot)
    
    # 4. 作業ディレクトリにコピー
    copied_count = _copy_pages_to_working_dir(target, out_dir, new_page_ids, existing_paths, client)
    
    # 5. インデックス更新
    if copied_count > 0:
        _update_index_with_new_pages(target, out_dir, new_page_ids, client, meta)
    
    # 6. キャッシュ更新
    cache_mgr_new = build_pull_context(target).cache_manager
    known = set(cache_mgr_new.get_known_page_ids())
    known |= set(new_page_ids)
    cache_mgr_new.set_known_page_ids(sorted(list(known)))
    cache_mgr_new.ensure_saved()
    
    # 7. 最後のpull時刻を更新
    if update_time:
        _update_last_pull_time(target, "new-only")

    # 8. （オプション）file→dir変換クリーンアップ
    if cleanup_folders:
        try:
            print("[c2n] Cleanup: checking file pages that became folders...")
            converted = _convert_file_entries_to_dir(target, client)
            if converted > 0:
                print(f"[c2n] Converted {converted} file entries to folder directories")
            else:
                print("[c2n] No file→folder conversions needed")
        except Exception:
            pass

    return True  # 新規ページを取得した


def _pull_new_pages(target: str, new_page_ids: set[str], snapshot: bool) -> str:
    """新規ページをnotion2mdで取得"""
    out_dir = _prepare_pull_output_base(target, snapshot=snapshot)
    print(f"[c2n] Pulling {len(new_page_ids)} new pages...")

    # 新規ページIDをカンマ区切りで渡す
    page_ids_str = ','.join(new_page_ids)

    # notion2mdを新規ページIDのみで実行
    cmd = [
        sys.executable,
        os.path.join(os.path.dirname(__file__), 'notion_pull.py'),
        '--page-ids', page_ids_str,
        '-o', out_dir
    ]

    # notion2md がローカルの .c2n/index.yaml を参照できるように cwd を target に設定
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, bufsize=1, universal_newlines=True, cwd=target)

    try:
        for line in proc.stdout:
            if 'HTTP Request:' not in line and 'httpx' not in line and 'httpcore' not in line:
                print(line, end='')
    finally:
        proc.wait()

    if proc.returncode != 0:
        print_error(f"Subprocess failed with exit code {proc.returncode}")
        sys.exit(proc.returncode)
    
    return out_dir


def _copy_pages_to_working_dir(target: str, out_dir: str, new_page_ids: set[str], existing_paths: dict[str, str], client) -> int:
    """新規ページを作業ディレクトリにコピー"""
    print("[c2n] Copying new pages to working directory...")
    copied_count = 0
    
    # notion2md が出力した manifest から {rel_path -> page_id} を取得
    manifest_map = {}
    try:
        mf = os.path.join(out_dir, 'manifest.json')
        if os.path.exists(mf):
            with open(mf, 'r', encoding='utf-8') as f:
                man = json.load(f) or {}
                for p in (man.get('pages') or []):
                    pid = p.get('page_id')
                    fp = p.get('file_path')
                    if pid and fp:
                        manifest_map[fp] = pid
    except Exception:
        manifest_map = {}
    
    for root, _, files in os.walk(out_dir):
        for fn in files:
            if fn == 'manifest.json':
                continue
            src = os.path.join(root, fn)
            rel = os.path.relpath(src, out_dir)
            # 可能なら親ディレクトリのローカルパスへ配置
            dst = os.path.join(target, rel)
            try:
                # rel (e.g., "Parent/Child.md") があればそのまま使う。
                # 軽量モードで親階層が付与されていない場合は manifest と meta から補正。
                if os.sep not in rel or rel.startswith('..'):
                    pid = manifest_map.get(rel)
                    if pid:
                        # 親IDを取得
                        par_id = None
                        try:
                            pg = client.pages.retrieve(page_id=pid)
                            par = pg.get('parent') or {}
                            par_id = par.get('page_id')
                        except Exception:
                            par_id = None
                        # 既存メタにある親のローカルパスへ
                        if par_id and par_id in existing_paths:
                            parent_local = existing_paths.get(par_id)
                            if parent_local and os.path.isdir(parent_local):
                                dst = os.path.join(parent_local, os.path.basename(rel))
            except Exception:
                pass
            
            # ディレクトリ作成
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            
            # 既存と同一ならスキップ表示（混乱防止）
            def _sha1(p):
                import hashlib
                h = hashlib.sha1()
                with open(p, 'rb') as f:
                    for chunk in iter(lambda: f.read(8192), b''):
                        h.update(chunk)
                return h.hexdigest()
            existed = os.path.exists(dst)
            same = False
            if existed:
                try:
                    same = (_sha1(src) == _sha1(dst))
                except Exception:
                    same = False
            
            import shutil
            if not existed:
                shutil.copy2(src, dst)
                print(f"  NEW: {rel}")
                copied_count += 1
            elif not same:
                shutil.copy2(src, dst)
                print(f"  UPDATED: {rel}")
                copied_count += 1
            else:
                print(f"  (same-file) {rel}")
    
    print(f"[c2n] Successfully pulled {copied_count} new pages")
    return copied_count


def _update_index_with_new_pages(target: str, out_dir: str, new_page_ids: set[str], client, meta: dict):
    """index.yamlを更新（新規ページを追加）"""
    print("[c2n] Updating local index...")
    
    # manifest.jsonからpage_idとファイルの対応関係を取得
    manifest_path = os.path.join(out_dir, 'manifest.json')
    page_file_mapping = {}
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
                for page_info in manifest.get('pages', []):
                    page_id = page_info.get('page_id')
                    file_path = page_info.get('file_path')
                    if page_id and file_path:
                        page_file_mapping[file_path] = page_id
        except Exception as e:
            print(f"[c2n] Warning: Could not read manifest.json: {e}")
    
    # 実際に取得したページの詳細情報をindexに追加
    for root, _, files in os.walk(out_dir):
        for fn in files:
            if fn == 'manifest.json':
                continue
            src = os.path.join(root, fn)
            rel = os.path.relpath(src, out_dir)
            dst = os.path.join(target, rel)
            
            # manifest.jsonからpage_idを取得（なければURLタグから抽出）
            if fn.endswith('.md'):
                page_id = page_file_mapping.get(rel)
                if not page_id:
                    # URLタグから抽出
                    try:
                        with open(dst, 'r', encoding='utf-8') as rf:
                            lines = rf.read().splitlines()
                        for line in reversed(lines[-5:]):
                            if line.strip().startswith('//url:'):
                                url = line.split(':', 1)[1].strip()
                                # URL末尾からID抽出
                                m = re.search(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$', url)
                                if m:
                                    page_id = m.group(1)
                                    break
                    except Exception:
                        pass
                if not page_id:
                    # フォールバック：ファイル名から推測
                    for pid in new_page_ids:
                        if pid in fn or fn.replace('.md', '') in fn:
                            page_id = pid
                            break
                
                if page_id:
                    # Notion APIからURLとlast_editedを取得してメタ精度を上げる
                    page_url = None
                    remote_last_edited = None
                    try:
                        page = client.pages.retrieve(page_id=page_id)
                        page_url = page.get('url')
                        remote_last_edited = page.get('last_edited_time')
                    except Exception:
                        pass
                    # indexにエントリを追加
                    if 'items' not in meta:
                        meta['items'] = {}
                    
                    meta['items'][dst] = {
                        'page_id': page_id,
                        'type': 'file',
                        'title': fn.replace('.md', ''),
                        'updated_at': int(time.time()),
                        'page_url': page_url,
                        'remote_last_edited': remote_last_edited,
                        'last_sync_at': remote_last_edited or datetime.datetime.now(datetime.timezone.utc).isoformat()
                    }
    
    # ✅ FIX IMP-012: Preserve root_page_url before saving
    # Note: meta was loaded at the start of cmd_pull_new_only, so root_page_url should be present
    # But we explicitly preserve it to ensure consistency
    _save_meta(target, meta)

def cmd_pull_auto(target: str, snapshot: bool = False, update_time: bool = True) -> bool:
    target = os.path.abspath(target)
    _load_env_for_target(target)
    cfg = os.path.join(target, '.c2n', 'config.json')
    create_url = None
    if os.path.exists(cfg):
        try:
            with open(cfg, 'r', encoding='utf-8') as f:
                conf = (json.load(f) or {})
                create_url = conf.get('repo_create_url') or conf.get('default_parent_url')
        except Exception:
            pass
    if not create_url:
        exit_with_error('repo_create_url/default_parent_url is not set in .c2n/config.json')
    if not ensure_dependency('notion_client', 'notion-client'):
        print('フルPullにフォールバックします。')
        return cmd_pull(target)
    token = os.environ.get('NOTION_TOKEN') or os.environ.get('NOTION_API_KEY')
    if not token:
        print('NOTION_TOKEN または NOTION_API_KEY が環境変数にありません。フルPullにフォールバックします。')
        return cmd_pull(target)
    notion = Client(auth=token)
    meta = _load_meta(target)
    items = (meta.get('items') or {}) if isinstance(meta, dict) else {}
    print("[c2n] Start: pull --auto (local files only, no new pages)...")

    # 事前整合性チェック（共通関数）: file→dir変換
    try:
        _convert_file_entries_to_dir(target, notion)
    except Exception:
        pass

    # load previous remote snapshot from cache
    cache_mgr_auto = build_pull_context(target).cache_manager
    prev_snapshot = cache_mgr_auto.get_remote_snapshot()

    # build candidates with page_id (only existing local files)
    candidates = []
    for path, info in items.items():
        if not isinstance(info, dict):
            continue
        # 既存ローカルの対象: ファイルページに加えてディレクトリページも監視
        if info.get('type') not in ('file', 'dir'):
            continue
        # ローカルファイルが存在するもののみ対象
        if not os.path.exists(path):
            continue
        pid = info.get('page_id') or extract_id_from_url(info.get('page_url') or '')
        if not pid:
            continue
        candidates.append((path, pid, info))

    # parallel retrieve last_edited
    from concurrent.futures import ThreadPoolExecutor, as_completed
    changed = []
    remote_snapshot = {}
    def _fetch(pid: str):
        try:
            page = notion.pages.retrieve(page_id=pid)
            return page.get('last_edited_time')
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=6) as ex:
        fut_map = {ex.submit(_fetch, pid): (path, pid, info) for (path, pid, info) in candidates}
        for fut in as_completed(fut_map):
            path, pid, info = fut_map[fut]
            last_edited = fut.result()
            remote_snapshot[pid] = last_edited
            try:
                # update meta.remote_last_edited always
                if isinstance(meta.get('items'), dict) and path in meta['items'] and isinstance(meta['items'][path], dict):
                    meta['items'][path]['remote_last_edited'] = last_edited
                # diff check vs last_sync_at (strict datetime compare)
                def _iso_to_dt(s: str):
                    if not s:
                        return None
                    try:
                        # normalize Z to +00:00 for fromisoformat
                        ss = s.replace('Z', '+00:00')
                        return datetime.datetime.fromisoformat(ss)
                    except Exception:
                        return None
                led = _iso_to_dt(last_edited) if last_edited else None
                lsa = _iso_to_dt(info.get('last_sync_at')) if info.get('last_sync_at') else None
                if led and (not lsa or led > lsa):
                    changed.append((info.get('page_url') or pid, path, last_edited))
            except Exception:
                changed.append((info.get('page_url'), path, last_edited))
    print(f"[c2n] Pull targets: {len(changed)}")
    if not changed:
        if remote_snapshot != prev_snapshot:
            print('[c2n] Snapshot changed but no per-item diff found; falling back to full pull')
            return cmd_pull(target, snapshot=snapshot, apply=update_time)
        print('差分はありません（auto pull 対象なし）')
        # 差分がない場合は時刻を更新しない（新規ページの検出に影響するため）
        return False
    out_dir = _prepare_pull_output_base(target, snapshot)
    for page_url, path, last_edited in changed:
        # アイテムのローカル相対ディレクトリに合わせて出力先を分岐
        try:
            rel = os.path.relpath(path, target)
        except Exception:
            rel = os.path.basename(path)
        # ディレクトリページは、その相対ディレクトリ直下に出力
        if os.path.isdir(path):
            item_out = os.path.join(out_dir, rel)
        else:
            rel_dir = os.path.dirname(rel)
            item_out = os.path.join(out_dir, rel_dir) if rel_dir else out_dir
        os.makedirs(item_out, exist_ok=True)
        args = [sys.executable, os.path.join(ROOT, 'notion_pull.py'), page_url, '-o', item_out]
        try:
            print(f"[c2n] Pulling: {rel} -> {item_out}")
            sys.stdout.flush()
        except Exception:
            pass
        # stream each notion2md
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        assert proc.stdout is not None
        try:
            for line in proc.stdout:
                # HTTPリクエストログを抑制
                if 'HTTP Request:' not in line and 'httpx' not in line and 'httpcore' not in line:
                    print(line, end='')
        finally:
            proc.wait()
        if proc.returncode != 0:
            print(f'pull失敗: {page_url}')
        else:
            # メタ更新
            if isinstance(meta.get('items'), dict) and path in meta['items']:
                if isinstance(meta['items'][path], dict):
                    meta['items'][path]['remote_last_edited'] = last_edited or meta['items'][path].get('remote_last_edited')
                    # 最終同期時刻を現在値（=取得時のlast_edited）で更新
                    meta['items'][path]['last_sync_at'] = last_edited
    # ✅ FIX IMP-012: Preserve root_page_url before saving
    # Note: meta was loaded at the start of cmd_pull_auto, so root_page_url should be present
    _save_meta(target, meta)
    # save remote snapshot to cache
    try:
        cache_mgr_auto.set_remote_snapshot(remote_snapshot)
        cache_mgr_auto.ensure_saved()
    except Exception:
        pass
    # manifest
    try:
        manifest = {
            'mode': 'auto',
            'pulled_at': int(time.time()),
        }
        with open(os.path.join(out_dir, 'manifest.json'), 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    # 自動マージ適用（既定/フラグは main から渡す）
    if changed:
        print('--- Apply Merge (pull auto -> working tree) ---')
        applied = _apply_merge_from_pull_latest(target)
        if applied == 0:
            print('no files to merge (already up-to-date)')
    
    # 最後のpull時刻を更新
    if update_time:
        _update_last_pull_time(target, "auto")
    
    return True  # 既存ページの変更を取得した

def _update_last_pull_time(target: str, mode: str):
    """最後のpull時刻を更新"""
    try:
        import time
        pull_dir = os.path.join(target, '.c2n', 'pull', 'latest')
        os.makedirs(pull_dir, exist_ok=True)
        
        manifest_path = os.path.join(pull_dir, 'manifest.json')
        current_time = int(time.time())
        
        manifest = {
            'mode': mode,
            'pulled_at': current_time
        }
        
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        
        # 時刻を人間が読める形式でログ出力
        import datetime
        dt = datetime.datetime.fromtimestamp(current_time, tz=datetime.timezone.utc)
        print(f"[c2n] Updated last pull time: {dt.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
    except Exception as e:
        print_warning(f"[c2n] Failed to update last pull time: {e}")

def _convert_file_entries_to_dir(target: str, notion_client) -> int:
    """Notion上で子ページを持つページ（フォルダ扱い）に変わったものを
    ローカルで .md → ディレクトリ へ変換し、index.yamlを更新する。
    戻り値は変換数。
    """
    try:
        meta = _load_meta(target)
        items = (meta.get('items') or {}) if isinstance(meta, dict) else {}
        to_convert = []
        for path, info in list(items.items()):
            if not isinstance(info, dict):
                continue
            if info.get('type') != 'file':
                continue
            pid = info.get('page_id') or extract_id_from_url(info.get('page_url') or '')
            if not pid:
                continue
            if not os.path.isfile(path) or not path.endswith('.md'):
                continue
            try:
                res = notion_client.blocks.children.list(block_id=pid)
                has_child_page = any(b.get('type') == 'child_page' for b in (res.get('results') or []))
            except Exception:
                has_child_page = False
            if has_child_page:
                new_dir = path[:-3]
                to_convert.append((path, new_dir))
        converted = 0
        for old_path, new_dir in to_convert:
            try:
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                        print(f"[c2n] Converted to folder (removed file): {old_path}")
                    except Exception:
                        pass
                try:
                    os.makedirs(new_dir, exist_ok=True)
                except Exception:
                    pass
                try:
                    entry = items.pop(old_path, None)
                    if isinstance(entry, dict):
                        entry['type'] = 'dir'
                        entry['updated_at'] = int(time.time())
                        items[new_dir] = entry
                        converted += 1
                except Exception:
                    pass
            finally:
                pass
        if converted > 0:
            meta['items'] = items
            # ✅ FIX IMP-012: Preserve root_page_url before saving
            # Note: meta was loaded at the start of _convert_file_entries_to_dir, so root_page_url should be present
            _save_meta(target, meta)
        return converted
    except Exception:
        return 0

def _apply_merge_from_pull_latest(target: str) -> int:
    """Merge files from .c2n/pull/latest into working tree using direct merge.
    Returns number of files applied (ADD/REPLACE/UPDATE counted)."""
    try:
        pull_latest = os.path.join(target, '.c2n', 'pull', 'latest')
        if not os.path.isdir(pull_latest):
            print("[c2n] No pull artifacts to apply (missing .c2n/pull/latest)")
            return 0
        meta = _load_meta(target)
        # ✅ FIX IMP-012: Preserve root_page_url and other top-level keys
        root_page_url = meta.get('root_page_url')
        
        applied = 0
        for root, _, files in os.walk(pull_latest):
            for fn in files:
                if fn == 'manifest.json':
                    continue
                src = os.path.join(root, fn)
                rel = os.path.relpath(src, pull_latest)
                
                # ✅ FIX BUG-010: Files in .c2n/pull/latest/ now maintain correct directory structure
                # Simply use the relative path as the destination
                dst = os.path.join(target, rel)
                
                status = _apply_direct_merge(src, dst)
                if status in ('ADD', 'REPLACE', 'UPDATE'):
                    applied += 1
                print(f"{status:7}  {rel}")
                
                # best-effort: update last_sync_at if meta entry exists
                try:
                    if isinstance(meta.get('items'), dict) and dst in meta['items'] and isinstance(meta['items'][dst], dict):
                        meta['items'][dst]['last_sync_at'] = meta['items'][dst].get('remote_last_edited') or datetime.datetime.now(datetime.timezone.utc).isoformat()
                except Exception:
                    pass
        if applied:
            # ✅ FIX IMP-012: Restore root_page_url before saving
            if root_page_url:
                meta['root_page_url'] = root_page_url
            _save_meta(target, meta)
        return applied
    except Exception:
        return 0

def _get_pull_apply_default(target: str):
    try:
        cfg = os.path.join(os.path.abspath(target), '.c2n', 'config.json')
        if os.path.exists(cfg):
            with open(cfg, 'r', encoding='utf-8') as f:
                conf = json.load(f) or {}
                val = conf.get('pull_apply_default')
                if isinstance(val, bool):
                    return val
    except Exception:
        pass
    return False

# Delegate to argument parser
def parse_args():
    """Parse command line arguments"""
    parser = create_argument_parser()
    return parser.parse_args()

# Delegate to CommandHandlers
def _handle_repo_create(args):
    """repo create コマンドの処理"""
    handlers = CommandHandlers()
    handlers.handle_repo_create(args)


# Delegate to CommandHandlers
def _handle_repo_clone(args):
    """repo clone コマンドの処理"""
    handlers = CommandHandlers()
    handlers.handle_repo_clone(args)


# Delegate to CommandHandlers
def _handle_push(args):
    """push コマンドの処理"""
    handlers = CommandHandlers()
    handlers.handle_push(args)


# Delegate to CommandHandlers
def _handle_pull(args):
    """pull コマンドの処理"""
    handlers = CommandHandlers()
    handlers.handle_pull(args)


def main():
    """メイン関数 - コマンドルーティング (v2.1)"""
    args = parse_args()
    handlers = CommandHandlers()
    
    # v2.1: Main commands
    if args.cmd == 'init':
        workspace_url = getattr(args, 'workspace_url', '')
        root_url = getattr(args, 'root_url', '')
        folder = getattr(args, 'folder', '.')
        cmd_init(target=folder, workspace_url=workspace_url, root_url=root_url)
    elif args.cmd == 'clone':
        notion_url = getattr(args, 'notion_url', '')
        local_folder = getattr(args, 'local_folder', '')
        workspace_url = getattr(args, 'workspace_url', '')
        verbose = getattr(args, 'verbose', False)
        cmd_clone(notion_url=notion_url, local_folder=local_folder, workspace_url=workspace_url, verbose=verbose)
    elif args.cmd == 'push':
        folder = getattr(args, 'folder', '.')
        force_all = getattr(args, 'force_all', False)
        dry_run = getattr(args, 'dry_run', False)
        verbose = getattr(args, 'verbose', False)
        cmd_push(target=folder, force_all=force_all, dry_run=dry_run, verbose=verbose)
    elif args.cmd == 'pull':
        folder = getattr(args, 'folder', '.')
        new_only = getattr(args, 'new_only', False)
        existing_only = getattr(args, 'existing_only', False)
        dry_run = getattr(args, 'dry_run', False)
        verbose = getattr(args, 'verbose', False)
        # Determine pull mode based on options
        if new_only:
            snapshot = False
            apply = False  # Only show new pages
        elif existing_only:
            snapshot = True
            apply = True  # Only update existing pages
        else:
            snapshot = False
            apply = True  # Default: pull all (new + changed)
        cmd_pull(target=folder, snapshot=snapshot, apply=apply)
    elif args.cmd == 'status':
        handlers.handle_dryrun(args)
    elif args.cmd == 'dryrun':
        handlers.handle_dryrun(args)
    # Legacy: repo subcommands
    elif args.cmd == 'repo' and getattr(args, 'repo_cmd', None) == 'create':
        _handle_repo_create(args)
    elif args.cmd == 'repo' and getattr(args, 'repo_cmd', None) == 'clone':
        _handle_repo_clone(args)
    else:
        exit_with_error('Usage: nit {init|clone|push|pull|status} <folder>')

if __name__ == '__main__':
    main()


