# cursor_to_notion モジュール化改善案

## 現状の課題

### 巨大単一ファイル問題
- `c2n.py`: 1,547行 - CLIエントリーポイント＋全コマンド実装
- `folder_to_notion.py`: 1,395行 - アップロード処理＋メタデータ管理

### 主な問題点
1. **保守性の低下**: 1つのファイルに複数の責務が混在
2. **テストの困難性**: 単体テストが書きにくい構造
3. **再利用性の欠如**: コマンド間で重複コードが多数存在
4. **可読性の低下**: 関数が長く、依存関係が複雑

---

## 提案するモジュール構造

```
cursor_to_notion/
├── c2n.py                    # CLIエントリーポイント（最小限）
├── core/                     # 共通コア機能
│   ├── __init__.py
│   ├── env_loader.py         # 環境変数・設定読み込み
│   ├── meta_manager.py       # index.yaml メタデータ管理
│   ├── cache_manager.py      # .cache.json キャッシュ管理
│   ├── notion_client.py      # Notion API クライアント統合
│   └── file_utils.py         # ファイル操作・SHA計算・mtime
├── commands/                 # コマンド別モジュール
│   ├── __init__.py
│   ├── init.py               # c2n init
│   ├── push.py               # c2n push / dryrun
│   ├── pull.py               # c2n pull / pull --auto / --new-only
│   └── repo.py               # c2n repo create / clone
├── upload/                   # アップロード処理
│   ├── __init__.py
│   ├── markdown.py           # Markdownアップロード
│   ├── media.py              # メディアアップロード
│   ├── directory.py          # ディレクトリ処理
│   └── walker.py             # ファイルツリー走査
├── download/                 # ダウンロード処理
│   ├── __init__.py
│   ├── notion2md.py          # Notion→Markdown変換
│   ├── merger.py             # マージ処理
│   └── diff_detector.py      # 差分検出
└── utils/                    # ユーティリティ
    ├── __init__.py
    ├── url_parser.py         # Notion URL/ID 抽出
    ├── logger.py             # ログ出力（統一インターフェース）
    └── progress.py           # プログレスバー
```

---

## 各モジュールの詳細設計

### 1. `core/env_loader.py`
**責務**: 環境変数と設定ファイルの読み込み

```python
def load_env_for_target(target_folder: str) -> None:
    """Load .env files in priority order"""

def load_config(target_folder: str) -> dict:
    """Load .c2n/config.json with defaults"""

def ensure_notion_env_bridge() -> None:
    """Bridge NOTION_TOKEN <-> NOTION_API_KEY"""
```

**抽出元**:
- `c2n.py`: `_load_env_for_target()`, `_load_config()`, `_ensure_notion_env_bridge()`
- `folder_to_notion.py`: `_load_env_for_folder()`, `load_folder_config()`

---

### 2. `core/meta_manager.py`
**責務**: `index.yaml` メタデータの読み書き・アイテム管理

```python
class MetaManager:
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.meta: dict = {}
    
    def load(self) -> dict:
        """Load .c2n/index.yaml"""
    
    def save(self) -> None:
        """Save .c2n/index.yaml (preserve root_page_url)"""
    
    def get_item(self, abs_path: str) -> Optional[dict]:
        """Get metadata for a file/dir"""
    
    def set_item(self, abs_path: str, item: dict) -> None:
        """Set metadata for a file/dir"""
    
    def is_ignored(self, path: str) -> bool:
        """Check if path matches ignore patterns"""
```

**抽出元**:
- `c2n.py`: `_load_meta()`, `_save_meta()`
- `folder_to_notion.py`: `load_meta()`, `save_meta()`, `get_item()`, `set_item()`, `is_ignored()`

---

### 3. `core/cache_manager.py`
**責務**: `.cache.json` の読み書き・スナップショット管理

```python
class CacheManager:
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.cache: dict = {}
    
    def load(self) -> dict:
        """Load .c2n/.cache.json"""
    
    def save(self) -> None:
        """Save .c2n/.cache.json"""
    
    def get_remote_snapshot(self) -> dict:
        """Get remote_tree_snapshot"""
    
    def set_remote_snapshot(self, snapshot: dict) -> None:
        """Update remote_tree_snapshot"""
```

**抽出元**:
- `c2n.py`: `_load_cache()`, `_save_cache()`
- `folder_to_notion.py`: `_load_cache()`, `_save_cache()`

---

### 4. `core/notion_client.py`
**責務**: Notion API クライアントの統合・共通操作

```python
class NotionClientWrapper:
    def __init__(self, token: str):
        self.client = Client(auth=token)
    
    def retrieve_page(self, page_id: str) -> dict:
        """Retrieve page with error handling"""
    
    def find_child_page(self, parent_url: str, title: str) -> Optional[str]:
        """Find child page by title (with pagination)"""
    
    def set_page_icon(self, page_url: str, emoji: str) -> bool:
        """Set page icon"""
    
    def archive_page(self, page_id: str) -> None:
        """Archive a page"""
```

**抽出元**:
- `folder_to_notion.py`: `_find_child_page_url()`, `_set_page_icon()`, `_archive_page()`
- `c2n.py`: Notion API呼び出し部分

---

### 5. `core/file_utils.py`
**責務**: ファイル操作・ハッシュ計算・mtime取得

```python
def sha1_file(path: str) -> str:
    """Calculate SHA-1 hash of file"""

def mtime_ns(path: str) -> int:
    """Get mtime in nanoseconds"""

def is_markdown_file(path: str) -> bool:
    """Check if file is markdown/code file"""

def is_media_file(path: str) -> bool:
    """Check if file is media file"""

def read_text(path: str) -> str:
    """Read text file with error handling"""

def write_text(path: str, content: str) -> None:
    """Write text file"""
```

**抽出元**:
- `folder_to_notion.py`: `_sha1_file()`, `_mtime_ns()`, `is_markdown_file()`, `is_media_file()`
- `c2n.py`: `_read_text()`, `_write_text()`

---

### 6. `commands/init.py`
**責務**: `c2n init` コマンド

```python
def cmd_init(target: str) -> None:
    """Initialize .c2n folder with config.json, .c2n_ignore, index.yaml"""
```

**抽出元**: `c2n.py` の `cmd_init()`

---

### 7. `commands/push.py`
**責務**: `c2n push` / `c2n dryrun` コマンド

```python
def cmd_push(target: str, changed_only: bool = None, no_dir_update: bool = None) -> None:
    """Push local changes to Notion"""

def cmd_dryrun(target: str, no_dir_update: bool = None) -> None:
    """Dry-run push and save log"""
```

**抽出元**: `c2n.py` の `cmd_push()`, `cmd_dryrun()`

---

### 8. `commands/pull.py`
**責務**: `c2n pull` 系コマンド

```python
def cmd_pull(target: str, snapshot: bool = False, apply: bool = True) -> None:
    """Pull changes from Notion to local"""

def cmd_pull_auto(target: str, snapshot: bool = False, update_time: bool = True) -> bool:
    """Pull changed pages only"""

def cmd_pull_new_only(target: str, snapshot: bool = False, update_time: bool = True, cleanup_folders: bool = False) -> bool:
    """Pull new pages only"""
```

**抽出元**: `c2n.py` の `cmd_pull()`, `cmd_pull_auto()`, `cmd_pull_new_only()`

---

### 9. `commands/repo.py`
**責務**: `c2n repo create` / `c2n repo clone` コマンド

```python
def cmd_repo_create(name: str, parent_url: str, base_dir: str) -> None:
    """Create local repo and Notion child page"""

def cmd_repo_clone(root_page_url: str, base_dir: str, name: str = None, apply: bool = True) -> None:
    """Clone from existing Notion root page"""
```

**抽出元**: `c2n.py` の `main()` 内の repo 処理部分

---

### 10. `upload/markdown.py`
**責務**: Markdownファイルのアップロード

```python
def upload_markdown(
    parent_url: str,
    md_path: str,
    *,
    update_page_url: Optional[str] = None,
    dry_run: bool = False
) -> str:
    """Upload markdown file to Notion"""

def apply_markdown_to_existing_page(
    page_url: str,
    md_path: str,
    *,
    keep_title: str = None,
    dry_run: bool = False
) -> None:
    """Apply markdown to existing page"""
```

**抽出元**: `folder_to_notion.py` の `upload_markdown()`, `apply_markdown_to_existing_page()`

---

### 11. `upload/media.py`
**責務**: メディアファイルのアップロード

```python
def upload_media(
    parent_url: str,
    file_path: str,
    *,
    dry_run: bool = False
) -> str:
    """Upload media file via Node helper"""
```

**抽出元**: `folder_to_notion.py` の `upload_media()`

---

### 12. `upload/directory.py`
**責務**: ディレクトリページの処理

```python
def process_directory(
    dir_path: str,
    parent_url: str,
    *,
    meta_manager: MetaManager,
    root_dir: str,
    dry_run: bool = False,
    is_root: bool = False,
    changed_only: bool = False,
    no_dir_update: bool = False
) -> Tuple[str, bool]:
    """Process directory and create/update Notion page"""
```

**抽出元**: `folder_to_notion.py` の `process_dir()`

---

### 13. `upload/walker.py`
**責務**: ファイルツリー走査とアップロード制御

```python
def walk_and_upload(
    root_dir: str,
    root_parent_url: str,
    *,
    dry_run: bool = False,
    changed_only: bool = False,
    no_dir_update: bool = False
) -> None:
    """Walk directory tree and upload to Notion"""
```

**抽出元**: `folder_to_notion.py` の `walk_and_upload()`

---

### 14. `download/merger.py`
**責務**: Pull後のマージ処理

```python
def merge_two_way(dst_txt: str, src_txt: str) -> str:
    """Git-style conflict marker merge"""

def apply_merge_from_pull_latest(target: str) -> int:
    """Merge files from .c2n/pull/latest into working tree"""
```

**抽出元**: `c2n.py` の `_merge_two_way()`, `_apply_merge_from_pull_latest()`

---

### 15. `download/diff_detector.py`
**責務**: リモート差分検出

```python
def detect_changed_pages(
    target: str,
    meta_manager: MetaManager,
    notion_client: NotionClientWrapper
) -> List[Tuple[str, str, str]]:
    """Detect changed pages by comparing last_edited_time"""
```

**抽出元**: `c2n.py` の `cmd_pull_auto()` 内の差分検出ロジック

---

### 16. `utils/url_parser.py`
**責務**: Notion URL/ID の抽出

```python
def extract_page_id_from_url(url: str) -> Optional[str]:
    """Extract page ID from Notion URL"""

def extract_id_from_url(url: str) -> str:
    """Extract and normalize page ID"""
```

**抽出元**:
- `c2n.py`: `_extract_page_id_from_url()`
- `folder_to_notion.py`: `_extract_id_from_url()`

---

### 17. `utils/logger.py`
**責務**: ログ出力の統一インターフェース

```python
class Logger:
    def __init__(self, log_file: Optional[str] = None):
        self.log_fp = None
        if log_file:
            self.log_fp = open(log_file, 'w', encoding='utf-8')
    
    def log_row(self, action: str, kind: str, title: str, url: str, rel_path: str, reason: str = None) -> None:
        """Log table row"""
    
    def log(self, msg: str) -> None:
        """Log message"""
    
    def close(self) -> None:
        """Close log file"""
```

**抽出元**: `folder_to_notion.py` の `log_row()`, `log()`

---

### 18. `utils/progress.py`
**責務**: プログレス表示

```python
class Progress:
    def __init__(self, total: int, no_progress: bool = False):
        self.total = total
        self.done = 0
        self.no_progress = no_progress
    
    def tick(self, rel_path: str) -> None:
        """Increment progress and print"""
    
    def note(self, msg: str) -> None:
        """Print progress note"""
```

**抽出元**: `folder_to_notion.py` の `_progress_tick()`, `_progress_note()`

---

## 移行手順

### Phase 1: コア機能の抽出（優先度: 高）
1. `core/env_loader.py` を作成
2. `core/meta_manager.py` を作成（最重要: 全コマンドで使用）
3. `core/cache_manager.py` を作成
4. `core/file_utils.py` を作成
5. `utils/url_parser.py` を作成

### Phase 2: ユーティリティの抽出（優先度: 中）
1. `utils/logger.py` を作成
2. `utils/progress.py` を作成
3. `core/notion_client.py` を作成

### Phase 3: コマンド別モジュール化（優先度: 高）
1. `commands/init.py` を作成（最もシンプル）
2. `commands/push.py` を作成
3. `commands/pull.py` を作成
4. `commands/repo.py` を作成

### Phase 4: アップロード処理のモジュール化（優先度: 中）
1. `upload/markdown.py` を作成
2. `upload/media.py` を作成
3. `upload/directory.py` を作成
4. `upload/walker.py` を作成

### Phase 5: ダウンロード処理のモジュール化（優先度: 低）
1. `download/merger.py` を作成
2. `download/diff_detector.py` を作成

### Phase 6: 統合とテスト（優先度: 高）
1. `c2n.py` を最小限のエントリーポイントに書き換え
2. `folder_to_notion.py` を `upload/walker.py` からインポートするラッパーに変更
3. 既存の統合テストを実行
4. 後方互換性の確認

---

## テスト戦略

### 単体テスト
各モジュールに対応する `tests/` ディレクトリを作成:

```
tests/
├── core/
│   ├── test_env_loader.py
│   ├── test_meta_manager.py
│   ├── test_cache_manager.py
│   └── test_file_utils.py
├── commands/
│   ├── test_init.py
│   ├── test_push.py
│   └── test_pull.py
├── upload/
│   ├── test_markdown.py
│   └── test_directory.py
└── utils/
    ├── test_url_parser.py
    └── test_logger.py
```

### 統合テスト
既存の `documents/11_QA実行/` 内のテストを活用:
- `unit_tests/`: 各モジュールの単体テスト
- `integration_tests/`: コマンド全体の統合テスト

---

## 期待される効果

### 1. 保守性の向上
- **単一責任原則**: 各モジュールが1つの責務のみを持つ
- **変更の局所化**: 機能追加・修正が特定モジュール内で完結

### 2. テスト性の向上
- **モック化の容易化**: 依存関係が明確で単体テストが書きやすい
- **テストカバレッジの向上**: 小さなモジュールは網羅的テストが可能

### 3. 再利用性の向上
- **コード重複の削減**: 共通処理が `core/` に集約される
- **他プロジェクトでの利用**: `core/meta_manager.py` などを他ツールで再利用可能

### 4. 可読性の向上
- **モジュール境界の明確化**: 責務が分離され、理解しやすい
- **インポート文で依存関係が可視化**: どのモジュールが何を使うか一目瞭然

### 5. チーム開発の促進
- **並行作業の容易化**: モジュール間の衝突が減る
- **新メンバーの理解促進**: 小さなモジュールから学習可能

---

## 互換性の保証

### 既存のエントリーポイントを維持
```python
# c2n.py (新版)
from commands.init import cmd_init
from commands.push import cmd_push, cmd_dryrun
from commands.pull import cmd_pull, cmd_pull_auto, cmd_pull_new_only
from commands.repo import cmd_repo_create, cmd_repo_clone

def main():
    # 既存のCLI引数解析を維持
    # 対応するコマンドモジュールを呼び出し
    ...
```

```python
# folder_to_notion.py (新版)
from upload.walker import walk_and_upload

def main():
    # 既存のCLI引数解析を維持
    # upload.walker.walk_and_upload() を呼び出し
    ...
```

---

## 参考: 既存の重複コード例

### 環境変数読み込み（3箇所に重複）
- `c2n.py`: `_load_env_for_target()`
- `folder_to_notion.py`: `_load_env_for_folder()`
- `md2notion.py`: 独自実装

→ **`core/env_loader.py`** に統一

### メタデータ管理（2箇所に重複）
- `c2n.py`: `_load_meta()`, `_save_meta()`
- `folder_to_notion.py`: `load_meta()`, `save_meta()`

→ **`core/meta_manager.py`** に統一

### キャッシュ管理（2箇所に重複）
- `c2n.py`: `_load_cache()`, `_save_cache()`
- `folder_to_notion.py`: `_load_cache()`, `_save_cache()`

→ **`core/cache_manager.py`** に統一

### URL/ID抽出（2箇所に重複）
- `c2n.py`: `_extract_page_id_from_url()`
- `folder_to_notion.py`: `_extract_id_from_url()`

→ **`utils/url_parser.py`** に統一

---

## 次のステップ

### 即座に開始可能なタスク
1. **Phase 1 の実施**: コア機能の抽出から開始
2. **単体テストの作成**: 抽出したモジュールごとにテストを追加
3. **ドキュメントの整備**: 各モジュールの docstring を充実

### 長期的なタスク
1. **型ヒントの追加**: すべてのモジュールに型アノテーションを追加
2. **エラーハンドリングの統一**: 例外処理を共通化
3. **ログレベルの導入**: DEBUG/INFO/WARNING/ERROR の4段階

---

## まとめ

この改善案により、**3000行の巨大単一ファイル** から **明確な責務を持つ18のモジュール** へと移行します。これにより、保守性・テスト性・再利用性・可読性・チーム開発のすべてが向上します。

**最優先で実施すべき項目**:
1. `core/meta_manager.py` の作成（全コマンドで使用）
2. `core/env_loader.py` の作成（初期化で必須）
3. `commands/init.py` の作成（最もシンプルで効果検証に最適）

これらを実施することで、今後の機能追加・バグ修正が劇的に容易になります。
