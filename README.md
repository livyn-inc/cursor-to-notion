# cursor\_to\_notion (nit) - Notion ⇄ Markdown 双方向同期ツール v2.1

このツールは、ローカルのMarkdownファイルとNotionページを双方向で同期し、Git風のワークフローでコラボレーションを可能にします。

## 🆕 v2.1の主な改善点

*   **🎯 インタラクティブプロンプト**: 引数を省略可能、対話的にセットアップ
*   **🔍 ワークスペース自動検出**: プロジェクトページから親ワークスペースを自動取得
*   **✨ コマンド簡素化**: `nit clone`など、よりシンプルなコマンド体系
*   **📝 オプション名の統一**: `--force-all`, `--existing-only`など、より直感的な名称

## 🚀 できること

*   **📁 Clone**: Notionページをローカルフォルダとして取得（`nit clone`）
*   **⬆️ Push**: ローカルの変更をNotionに反映（差分検出・自動ブロック置換）
*   **⬇️ Pull**: Notionの変更をローカルに取得（タイムスタンプベース差分検出・自動マージ）
*   **🔀 Auto Merge**: Git風のコンフリクトマーカーで自動解決
*   **📂 Folder Conversion**: Notion上でフォルダ化されたページを自動でローカルディレクトリに変換
*   **🎯 2つの同期モード**: Hierarchy（階層構造）とFlat（全ファイル）を選択可能
*   **👀 Status**: 同期状態確認・URL設定の自動修復（`--fix`オプション）
*   **⚡ 高速化**: SHA1ハッシュ・タイムスタンプ差分・キャッシュ・並列処理による最適化
*   **🔧 URL統合管理**: 統一されたURL解決ロジックで設定の一貫性を保証

## 🏃‍♂️ クイックスタート

### 1\. インストール（nitエイリアス設定）

```
# インストールスクリプトを実行
chmod +x install.sh
./install.sh
```

**インストール内容**:

*   Python仮想環境の作成・設定
*   依存関係の自動インストール
*   `nit` エイリアスの自動登録
*   動作テストの実行

### 2\. 新規プロジェクトの開始

```
# 1) Notionページをローカルにクローン（インタラクティブ）
nit clone

# または、URLとフォルダを直接指定
nit clone https://notion.so/your-project-page-url /path/to/local/folder

# 2) ローカルで編集後、Notionに反映
nit push /path/to/local/folder

# 3) Notionで他の人が編集した内容を取得（新規＋変更＋自動マージ）
nit pull /path/to/local/folder
```

### 3\. 既存フォルダの初期化

```
# 1) 既存フォルダを初期化（インタラクティブでURL入力）
nit init /path/to/existing/folder

# または、ワークスペースURLを直接指定
nit init /path/to/existing/folder --workspace-url https://notion.so/workspace-url

# 2) 初回同期
nit push /path/to/existing/folder
```

## 🛠️ 環境セットアップ

### 1\. 自動インストール（推奨）

```
# インストールスクリプトを実行
chmod +x install.sh
./install.sh
```

### 2\. 手動セットアップ

```
# 依存関係のインストール
pip install -r dev/requirements.txt
```

### 3\. Notion APIトークンの設定

以下の優先順位で `.env` ファイルからトークンを自動読み込みします：

1.  `<対象プロジェクト>/.c2n/.env`（最優先）
2.  `<対象プロジェクト>/.env`
3.  `cursor_to_notion/` ツール直下の `.env`

```
# .env ファイルの例
NOTION_TOKEN=secret_xxxxxxxxxxxxx
# または
NOTION_API_KEY=secret_xxxxxxxxxxxxx
```

**手動設定（環境変数）**:

```
export NOTION_TOKEN="your_notion_api_key_here"
```

### 4\. NotionページURLの取得方法

**NotionページURLとは**:
- Notionページの完全なURL（例: `https://www.notion.so/your-workspace/Page-Title-abc123def456`)
- `nit` コマンドで親ページとして指定するURL
- `default_parent_url` 設定や `--parent-url` オプションで使用

**URL取得手順**:

1. **Notionでページを開く**
   - ブラウザでNotionにログイン
   - 対象のページを開く

2. **URLをコピー**
   - ブラウザのアドレスバーからURLをコピー
   - 例: `https://www.notion.so/your-workspace/Project-Docs-abc123def456`

3. **URL形式の確認**
   - ✅ 正しい形式: `https://www.notion.so/workspace/Page-Title-32文字のID`
   - ❌ 間違った形式: `https://notion.so/Page-Title` (IDなし)

**URL形式の例**:
```
# 正しい形式（32文字のIDが含まれる）
https://www.notion.so/your-workspace/Project-Docs-abc123def456ghi789jkl012mno345pqr678stu901vwx234yz

# 間違った形式（IDが含まれない）
https://notion.so/Project-Docs
```

**設定方法**:

1. **config.jsonで設定**:
   ```json
   {
     "default_parent_url": "https://www.notion.so/your-workspace/Project-Docs-abc123def456ghi789jkl012mno345pqr678stu901vwx234yz"
   }
   ```

2. **コマンドラインで指定**:
   ```bash
   nit init /path/to/folder --parent-url "https://www.notion.so/your-workspace/Project-Docs-abc123def456ghi789jkl012mno345pqr678stu901vwx234yz"
   ```

**トラブルシューティング**:
- URLに32文字のIDが含まれているか確認
- ページがNotionで正常に表示できるか確認
- ワークスペースの権限があるか確認

### 5\. 設定ファイル（.c2n/config.json）

`nit init` で自動生成される設定ファイル：

```
{
    "default_parent_url": "https://www.notion.so/your_root_page_url",
    "default_title_column": "名前",
    "pull_apply_default": true,
    "push_changed_only_default": true,
    "no_dir_update_default": true,
    "sync_mode": "hierarchy"
}
```

**設定項目の説明**:

*   `pull_apply_default`: Pull後に自動マージするか（デフォルト: true）
*   `push_changed_only_default`: 変更ファイルのみPushするか（デフォルト: true）
*   `no_dir_update_default`: ディレクトリページの更新を抑制するか（デフォルト: true）
*   `sync_mode`: 同期モード - `"hierarchy"` または `"flat"` （デフォルト: `"hierarchy"`）

## 🎯 同期モード

### Hierarchy Mode（階層モード）- デフォルト

**特徴**:

*   Notionのページ階層をローカルのディレクトリ構造として再現
*   フォルダページ → ローカルディレクトリ
*   ファイルページ → `.md` ファイル
*   ファイルシステムとの親和性が高い

**適用例**:

*   プロジェクトドキュメント管理
*   階層的なナレッジベース
*   ファイルエクスプローラーでの閲覧が必要な場合

**ローカル構造例**:

```
project/
├── documents/
│   ├── planning/
│   │   ├── roadmap.md
│   │   └── requirements.md
│   └── design/
│       └── wireframe.md
└── README.md
```

### Flat Mode（フラットモード）

**特徴**:

*   全てのNotionページを単一階層の `.md` ファイルとして保存
*   階層構造はMarkdown内のFrontmatterとリンクで表現
*   ローカルはフラット（全ファイルが同一ディレクトリ）
*   検索性・一覧性が高い

**適用例**:

*   OKR・会議録などの大量ページ管理
*   ページ間の関連性を視覚化したい場合
*   エディタの検索機能を活用したい場合

**ローカル構造例**:

```
okr/
├── OKR_FY25.md
├── OKR_Q3_目標1.md
├── OKR_Q3_目標2.md
├── OKR_Q4_目標1.md
└── 振り返り.md
```

**Frontmatter形式**:

```
---
page_id: abc123...
page_url: https://notion.so/abc123
parent_id: def456...
parent_type: page
children_ids:
  - ghi789...
  - jkl012...
sync_mode: flat
---

# ページタイトル

本文...
```

### モード切り替え

`.c2n/config.json` の `sync_mode` を編集：

```
{
  "sync_mode": "hierarchy"  // または "flat"
}
```

## 🔧 URL統一管理システム

### 概要

v1.2から導入されたURL統一管理システムにより、NotionページURLの設定と解決が**`default_parent_url`に統一**され、シンプルで一貫した動作が保証されます。

### 統一されたURL解決システム

**従来の問題**: 4つの異なるURLソース（`root_page_url`、`parent_url`、`default_parent_url`、`NOTION_ROOT_URL`）が混在し、どのURLが使用されるかが不明確でした。

**解決策**: `default_parent_url`を唯一のソースとして使用するシンプルなシステムに統一しました。

### URL解決の優先順位（統一後）

1. **`default_parent_url`** (`.c2n/config.json`) - プライマリソース
2. **`NOTION_ROOT_URL`** (環境変数) - 初期設定時のフォールバック

### 新しいコマンド

#### `nit status <folder>`
プロジェクトのURL解決状況と整合性を表示します。

```bash
nit status /path/to/project
```

**出力例**:
```
📋 URL Resolution Status for: /path/to/project
   Root URL: https://www.notion.so/workspace/Project-Page-12345678901234567890123456789012
   Source: default_parent_url (config.json)
   Items: 5
   Issues: 0
   ✅ No issues found
✅ プロジェクト状態: 正常
```

#### `nit fix-urls <folder>`
URL設定の不整合を自動修復します。

```bash
nit fix-urls /path/to/project
```

**修復内容**:
- `index.yaml`の`root_page_url`を`default_parent_url`に統一
- メタデータ構造の標準化
- 整合性チェックと自動修復

### 移行サポート

既存プロジェクトを新しい統一システムに移行するには:

```bash
# 移行スクリプトの実行
python3 src/c2n_core/migration.py /path/to/project --dry-run

# 実際の移行実行
python3 src/c2n_core/migration.py /path/to/project
```

**移行内容**:
- `root_page_url` → `default_parent_url`へのコピー
- `index.yaml`構造の標準化
- レガシー設定の互換性保持

### 自動修復機能

プロジェクト初期化時や`nit push`/`nit pull`実行時に、以下の問題が自動的に修復されます：

1. **`root_page_url`の欠如**: `config.json`や環境変数から自動設定
2. **メタデータ構造の不整合**: 標準形式に自動変換
3. **URL解決の失敗**: フォールバック処理で適切なURLを取得

### トラブルシューティング

#### URL設定エラーが発生した場合

```bash
# 1. 現在の状況を確認
nit status /path/to/project

# 2. 自動修復を実行
nit fix-urls /path/to/project

# 3. 修復結果を確認
nit status /path/to/project
```

#### 手動でのURL設定

```bash
# プロジェクト初期化時にURLを指定
nit init /path/to/project --parent-url "https://www.notion.so/workspace/Page-12345678901234567890123456789012"

# 既存プロジェクトのURLを更新
nit fix-urls /path/to/project
```

### 環境変数での設定

```bash
# 環境変数でデフォルトURLを設定
export NOTION_ROOT_URL="https://www.notion.so/workspace/Default-Page-12345678901234567890123456789012"

# プロジェクト初期化（環境変数が自動使用される）
nit init /path/to/project
```

**注意事項**:

*   モード変更後は `nit pull --full` で全ページを再取得推奨
*   既存ファイルは手動削除が必要（データ損失防止のため自動削除なし）

## 📚 コマンドリファレンス

### `nit init` - プロジェクト初期化

```
nit init "/path/to/your/folder"
```

**実行内容**:

*   `.c2n/config.json` の雛形生成（デフォルト設定付き）
*   `.c2n_ignore` の雛形生成（gitignore風の除外ルール）

### `nit clone` - Notionからクローン

```
# インタラクティブ（引数なし）
nit clone

# URLとフォルダを指定
nit clone https://notion.so/your-project-page-url /path/to/local/folder

# ワークスペースURLも明示的に指定
nit clone https://notion.so/your-project-page-url /path/to/local/folder --workspace-url https://notion.so/workspace-url
```

**実行内容**:

*   Notionページ階層をローカルフォルダ構造として複製
*   `.c2n/index.yaml` で同期状態を管理
*   ワークスペースURL（親ページ）を自動検出して設定

**v2.1新機能**:
*   引数省略時はインタラクティブプロンプトで入力
*   ワークスペースURLの自動検出

**レガシー**: `nit repo clone`も引き続き使用可能（下位互換性維持）

### `nit push` - ローカル → Notion

```
# 変更ファイルのみ（デフォルト、高速）
nit push "/path/to/your/folder"

# 全ファイル強制同期
nit push "/path/to/your/folder" --force-all

# 実行計画の事前確認
nit push "/path/to/your/folder" --dry-run

# 詳細ログ付き
nit push "/path/to/your/folder" --verbose
```

**特徴**:

*   SHA1ハッシュによる差分検出（高速化）
*   既存ブロックを削除してから新ブロックを追加（内容重複を防止）
*   並列API処理による最適化
*   詳細な起動ログ表示

### `nit pull` - Notion → ローカル（自動マージ）

```
# 新規ページ＋変更ページ取得＋自動マージ（デフォルト、推奨）
nit pull "/path/to/your/folder"

# 新規ページのみ取得（既存ページの変更は無視）
nit pull "/path/to/your/folder" --new-only

# 既存ページの変更のみ取得（新規ページは無視）
nit pull "/path/to/your/folder" --existing-only

# 実行計画の事前確認
nit pull "/path/to/your/folder" --dry-run

# 詳細ログ付き
nit pull "/path/to/your/folder" --verbose
```

**特徴**:

*   **デフォルト**: 新規ページ + 変更ページを自動マージ
*   **\--new-only**: 新規ページのみ高速取得（増分スキャン方式）
*   **\--existing-only**: 既存ページの変更のみ取得
*   **タイムスタンプ差分検出**: `last_sync_at`と`remote_last_edited`を比較
*   並列 `last_edited_time` 取得による高速化
*   Git風コンフリクトマーカーによる行粒度のコンフリクト解決

**高速化の仕組み**:

*   前回同期時刻（`last_sync_at`）と比較して変更されたページのみ処理
*   変更されていないファイルはスキップ
*   並列取得による最適化
*   リモートスナップショットをキャッシュ（`.c2n/.cache.json`）

### `nit status` - 同期状態確認

```
# 現在の同期状態を確認
nit status "/path/to/your/folder"

# URL設定の問題を自動修復
nit status "/path/to/your/folder" --fix
```

**機能**:
*   URL設定の確認と整合性チェック
*   同期メタデータの解析
*   `--fix`オプションで設定の自動修復

## ⚡ パフォーマンス最適化

### 高速化の仕組み

**SHA1ハッシュによる差分検出**

*   ファイル内容のSHA1ハッシュを `.c2n/index.yaml` に保存
*   内容が変更されていないファイルはスキップ

**ファイルシステムキャッシュ（.c2n/.cache.json）**

*   ディレクトリ構造とファイルメタデータをキャッシュ
*   `mtime_ns`（ナノ秒精度）による変更検出
*   起動時のスキャン処理を大幅高速化

**並列API処理**

*   `last_edited_time` の並列取得（ThreadPoolExecutor）
*   Notionブロック削除の並列実行
*   リモートメタデータキャッシュ（`remote_tree_snapshot`）

**ログ最適化**

*   変更のないファイル・ディレクトリのログ出力を抑制
*   内部処理ログの冗長性削減（`--verbose` で詳細表示可能）

### キャッシュファイル

```
# キャッシュクリア（パフォーマンス問題時）
rm /path/to/project/.c2n/.cache.json
```

## 📊 ログ仕様

### 起動ログ

```
[c2n] Start: push /path/to/project (changed-only mode)...
[c2n] Spawning folder_to_notion...
[c2n] Python startup: 0.2s
[c2n] Config loading: 0.1s
[c2n] Notion client init: 0.3s
[c2n] Scanning filesystem: 0.5s
```

### 進捗表示

```
Converting markdown -> blocks: documents/README.md
[████████████████████████████████] 85% (17/20 files)
Clearing children: /notion/page/abc123
U(updated): documents/guide.md -> https://notion.so/guide-xyz
```

### ハートビート（長時間処理中）

```
[c2n] ♥ (waiting for child process output...)
```

## 🔧 トラブルシューティング

### よくあるエラー

**1.** `**401 Unauthorized**`

```
# トークン設定を確認
echo $NOTION_TOKEN
cat .c2n/.env
```

**2.** `**repo_create_url/default_parent_url is not set**`

```
# config.json を確認・編集
cat .c2n/config.json
```

**3\. 重複したコンテンツが表示される**

*   Notion側でページを手動削除後、`nit push --full` で再同期

**4\. パフォーマンスが遅い**

```
# キャッシュクリア
rm .c2n/.cache.json
# 変更ファイルのみ同期
nit push /path/to/project --changed-only
```

### デバッグオプション

```
# 詳細ログ表示
nit push /path/to/project --verbose

# 実行計画の事前確認
nit dryrun /path/to/project
```

## ❓ よくある質問

**Q: ディレクトリページが頻繁に更新されるのを止めたい**  
A: `--no-dir-update` フラグまたは `no_dir_update_default: true` 設定を使用

**Q: Synced Blockとは？**  
A: NotionのREADMEプレビュー機能。親ディレクトリページに子のREADME.mdの内容を埋め込み表示

**Q: 変更検出の仕組みは？**  
A: SHA1ハッシュ + `mtime_ns` + `last_edited_time` の組み合わせで高精度な差分検出

**Q: コンフリクトマーカーの解決方法は？**  
A: Git風マーカー（`<<<<<<< LOCAL` / `>>>>>>> REMOTE`）を手動編集後、再度 `nit push`

**Q:** `**.c2n_ignore**` **の書き方は？**  
A: gitignore風の記法。`temp/`, `*.log`, `**/cache/**` など

**Q: --new-only と --existing-only の使い分けは？**  
A: デフォルト（オプションなし）は新規+変更の両方を取得。--new-only は新規ページのみ、--existing-only は既存ページの変更のみを高速取得

**Q: Hierarchy ModeとFlat Modeはどう使い分ける？**  
A:

*   **Hierarchy**: プロジェクト文書など階層的に管理したいコンテンツ向け
*   **Flat**: OKR・会議録など大量のページを一覧性高く管理したい場合向け

**Q: Flat Modeで親子関係はどう表現される？**  
A: 各`.md`ファイルのFrontmatterに`parent_id`と`children_ids`が記録されます。これにより階層構造を維持しつつフラットに保存

## 📎 レガシーツール（notion2md.py / md2notion.py）

nit CLIの導入前に使用していた単体ツール。基本的にはnitの使用を推奨。

### notion2md.py - 単体プル

```
python notion2md.py https://notion.so/page-url -o output_dir -c
```

### md2notion.py - 単体プッシュ

```
python md2notion.py file.md https://notion.so/parent-url -t "Title"
```

**制限事項**: 差分検出・キャッシュ・並列処理なし