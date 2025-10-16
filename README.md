# Nit - Notion ⇄ Markdown 双方向同期ツール v2.1 🚧 BETA

> ⚠️ **【重要】このツールはベータ版です**
> 
> - 現在活発に開発中であり、**予期しない動作や不具合が発生する可能性があります**
> - **必ず重要なデータはバックアップしてください**
> - コマンドや仕様は予告なく変更される可能性があります
> - 使用は自己責任でお願いします

---

このツールは、ローカルのMarkdownファイルとNotionページを双方向で同期し、Git風のワークフローでコラボレーションを可能にします。

## 🚀 できること

- **📁 Clone**: Notionページをローカルフォルダとして取得（`nit clone`）
- **⬆️ Push**: ローカルの変更をNotionに反映（差分検出・自動ブロック置換）
- **⬇️ Pull**: Notionの変更をローカルに取得（タイムスタンプベース差分検出・自動マージ）
- **🔀 Auto Merge**: Git風のコンフリクトマーカーで自動解決
- **📂 Folder Conversion**: Notion上でフォルダ化されたページを自動でローカルディレクトリに変換
- **🎯 2つの同期モード**: Hierarchy（階層構造）とFlat（全ファイル）を選択可能
- **👀 Status**: 同期状態確認・URL設定の自動修復（`--fix`オプション）
- **⚡ 高速化**: SHA1ハッシュ・タイムスタンプ差分・キャッシュ・並列処理による最適化
- **🔧 URL統合管理**: 統一されたURL解決ロジックで設定の一貫性を保証

## 🏃‍♂️ クイックスタート

### 1. インストール（nitエイリアス設定）

```bash
# インストールスクリプトを実行
chmod +x scripts/install.sh
./scripts/install.sh
```

**インストール内容**:
- Python仮想環境の作成・設定
- 依存関係の自動インストール
- `nit` エイリアスの自動登録
- 動作テストの実行

### 2. 新規プロジェクトの開始

```bash
# 1) Notionページをローカルにクローン（インタラクティブ）
nit clone

# または、URLとフォルダを直接指定
nit clone <notion_url> <local_folder>

# 2) ローカルで編集後、Notionに反映
nit push <local_folder>

# 3) Notionで他の人が編集した内容を取得（新規＋変更＋自動マージ）
nit pull <local_folder>
```

### 3. 既存フォルダの初期化

```bash
# 1) 既存フォルダを初期化（インタラクティブでURL入力）
nit init <folder>

# または、ワークスペースURLを直接指定
nit init <folder> --workspace-url <url>

# 2) 初回同期
nit push <folder>
```

---

### Step 1: プロジェクト初期化 🚀

田中さんは新しいプロジェクト「awesome-app」を開始しました。

```bash
# Notionワークスペース内にプロジェクトフォルダを作成
nit init awesome-app --workspace-url "https://www.notion.so/my-workspace/OKR-abc123"

# 出力例:
# ✅ プロジェクトフォルダを作成しました
# 📋 Project URL: https://www.notion.so/awesome-app-def456
# 💾 設定を保存しました: .c2n/config.json
```

**Notionを確認すると...**
- OKRページの下に「awesome-app」フォルダページが作成されている ✅
- フォルダアイコンが自動設定されている 📁

---

### Step 2: ローカルでドキュメント作成 📝

```bash
cd awesome-app

# README作成
cat > README.md << 'EOF'
# Awesome App

最高のアプリケーションです。

## 機能
- ユーザー認証
- データ分析
- レポート生成
EOF

# 設計書作成
mkdir docs
cat > docs/design.md << 'EOF'
# システム設計

## アーキテクチャ
- フロントエンド: React
- バックエンド: FastAPI
- データベース: PostgreSQL
EOF

# API仕様書（YAMLファイル）
cat > docs/api.yaml << 'EOF'
openapi: 3.0.0
info:
  title: Awesome App API
  version: 1.0.0
paths:
  /users:
    get:
      summary: ユーザー一覧取得
EOF
```

---

### Step 3: Notionに初回Push ⬆️

```bash
# まず実行計画を確認（安全確認）
nit push . --dry-run

# 出力例:
# 📤 Push Plan:
#   ✅ README.md → Create new page
#   ✅ docs/design.md → Create new page
#   ✅ docs/api.yaml → Create new page (as code block)
#   📊 Total: 3 files to upload

# 問題なければ実際にPush
nit push .

# 出力例:
# ⬆️  Pushing to Notion...
# ✅ Created: README.md
# ✅ Created: docs/design.md
# ✅ Created: docs/api.yaml (as YAML code block)
# 🎉 Push completed: 3 files
```

**Notionを確認すると...**
- README、design、api.yaml が Notionページとして作成されている ✅
- api.yaml は YAML のコードブロックとして表示されている 💻
- docs フォルダはフォルダページになっている 📁

---

### Step 4: Notionで編集 ✏️

田中さんの同僚がNotionで README を編集しました：

```markdown
# Awesome App

最高のアプリケーションです。

## 機能
- ユーザー認証
- データ分析
- レポート生成
- **📊 リアルタイムダッシュボード** ← 追加
```

---

### Step 5: ローカルに変更を取得 ⬇️

```bash
# 5分待機（Notion APIのタイムスタンプ反映待ち）
sleep 300

# 変更をPull
nit pull .

# 出力例:
# ⬇️  Pulling from Notion...
# 🔍 Checking for changes...
#   - README.md: Changed (remote: 2025-10-16 10:30, local: 2025-10-16 10:00)
#   - docs/design.md: No changes
#   - docs/api.yaml: No changes
# 📥 Downloading changed files...
# ✅ Updated: README.md
# 🎉 Pull completed: 1 file updated
```

**ローカルのREADME.mdを確認すると...**
- 同僚が追加した「リアルタイムダッシュボード」が反映されている ✅

---

### Step 6: コンフリクト発生時の対応 🔀

田中さんも同時に README を編集していました：

```bash
# ローカルで編集
echo "- 多言語対応" >> README.md

# Pushしようとすると...
nit push .

# 出力例:
# ⚠️  Conflict detected: README.md
#   Local:  2025-10-16 10:35
#   Remote: 2025-10-16 10:30
# 
# 🔀 Auto-merging with conflict markers...
# ⚠️  Please resolve conflicts manually
```

**README.mdを開くと...**
```markdown
# Awesome App

最高のアプリケーションです。

## 機能
- ユーザー認証
- データ分析
- レポート生成
<<<<<<< LOCAL
- 多言語対応
=======
- 📊 リアルタイムダッシュボード
>>>>>>> REMOTE
```

**コンフリクト解決**:
```bash
# マーカーを削除して両方の変更をマージ
cat > README.md << 'EOF'
# Awesome App

最高のアプリケーションです。

## 機能
- ユーザー認証
- データ分析
- レポート生成
- 📊 リアルタイムダッシュボード
- 多言語対応
EOF

# 再度Push
nit push .

# 出力例:
# ✅ Updated: README.md
# 🎉 Push completed
```

---

### Step 7: 継続的な同期 🔄

田中さんの日常的なワークフロー：

```bash
# 朝：作業開始前
cd awesome-app
nit pull .  # チームの変更を取得

# 作業中：ローカルで編集
vim docs/design.md

# 夕方：作業終了後
nit push .  # 自分の変更をNotionに反映
```


## 🛠️ 環境セットアップ

### 1. 自動インストール（推奨）

```bash
chmod +x install.sh
./install.sh
```

### 2. 手動セットアップ

```bash
# 依存関係のインストール
pip install -r requirements.txt
```

### 3. Notion APIトークンの設定

以下の優先順位で `.env` ファイルからトークンを自動読み込みします：

1. `<対象プロジェクト>/.c2n/.env`（最優先）
2. `<対象プロジェクト>/.env`
3. `cursor_to_notion/` ツール直下の `.env`
#### `.env` ファイルサンプル

プロジェクトルートまたは `.c2n/` ディレクトリに以下のファイルを作成してください：

```bash
# .env
# ==========================================
# Nit - Notion API 設定ファイル
# ==========================================

# 必須: Notion Integration トークン
# Notionで Integration を作成し、トークンを取得してください
# https://www.notion.so/my-integrations
NOTION_TOKEN=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# オプション: ワークスペースのデフォルトURL
# 新規プロジェクト作成時のデフォルト親ページ
WORKSPACE_URL=https://www.notion.so/my-workspace/parent-page-abc123

```

**手動設定（環境変数）**:
```bash
# シェルで直接設定する場合
export NOTION_TOKEN="secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export WORKSPACE_URL="https://www.notion.so/my-workspace/parent-page-abc123"
```

## 📋 コマンドリファレンス

### `nit init`
既存フォルダをNotionプロジェクトとして初期化

```bash
nit init [<folder>] [--workspace-url <url>] [--root-url <url>]
```

**オプション**:
- `<folder>`: 初期化するフォルダパス（省略時は対話的に入力）
- `--workspace-url <url>`: ワークスペースURL（プロジェクトページ作成先）
- `--root-url <url>`: ルートページURL（レガシー互換）

**インタラクティブ例**:
```bash
$ nit init
🔍 Notionワークスペースのページを開いてURLをコピーしてください
📋 ワークスペースURL（または親ページURL）を入力してください: 
> https://www.notion.so/workspace/my-workspace-page-abc123
✅ プロジェクトフォルダを作成しました
```

### `nit clone`
NotionページをローカルにClone

```bash
nit clone [<notion_url>] [<local_folder>] [--workspace-url <url>]
```

**オプション**:
- `<notion_url>`: CloneするNotionページURL（省略時は対話的に入力）
- `<local_folder>`: Clone先のローカルフォルダ（省略時は対話的に入力）
- `--workspace-url <url>`: 親ワークスペースURL（自動検出される場合は不要）

**インタラクティブ例**:
```bash
$ nit clone
📋 CloneするNotionページURLを入力してください: 
> https://www.notion.so/my-project-page-abc123
📁 Clone先のフォルダ名を入力してください [my-project-page]: 
> my-project
✅ プロジェクトをCloneしました: ./my-project
```

**レガシー互換**:
- 旧コマンド `nit repo clone` も引き続き使用可能（内部で`nit clone`にリダイレクト）

### `nit push`
ローカルの変更をNotionに反映

```bash
nit push <folder> [--force-all] [--dry-run] [--verbose]
```

**オプション**:
- `--force-all`: 全ファイルを強制的にPush（差分検出を無視）
- `--dry-run`: 実行計画のみ表示（実際のPushは行わない）
- `--verbose`: 詳細ログを表示

**動作**:
- 変更されたファイルのみを自動検出してNotionに送信
- 既存のNotionブロックを削除してから新ブロックを追加（内容重複を防止）
- コードファイル（`.yaml`, `.py`, `.json`等）はコードブロックとして配置
- 長いコード（1800文字超）は自動分割して送信

### `nit pull`
Notionの変更をローカルに取得

```bash
nit pull <folder> [--new-only] [--existing-only] [--dry-run] [--verbose]
```

**オプション**:
- `--new-only`: 新規ページのみ取得
- `--existing-only`: 既存ページの更新のみ取得
- `--dry-run`: 実行計画のみ表示
- `--verbose`: 詳細ログを表示

**動作**:
- タイムスタンプベースの差分検出
- 変更されたページのみダウンロード
- コンフリクト発生時はGit風マーカーで自動解決

**削除されたオプション（v2.1）**:
- `--full`（削除: `--force-all`に統合）
- `--cleanup-folders`（削除: 不要になった）
- `--auto`（名称変更: `--existing-only`に）
- `--snapshot`（削除: 内部で自動処理）

### `nit status`
プロジェクトの同期状態を確認

```bash
nit status <folder> [--fix]
```

**オプション**:
- `--fix`: URL設定の不整合を自動修復

**出力例**:
```
📋 プロジェクト状態: /path/to/project
   同期済みページ: 45
   変更あり: 3
   新規: 1
   ✅ 状態: 正常
```

## 🎯 同期モード

### Hierarchy Mode（階層モード）- デフォルト

**特徴**:
- Notionのページ階層をローカルのディレクトリ構造として再現
- フォルダページ → ローカルディレクトリ
- ファイルページ → `.md` ファイル

**適用例**:
- プロジェクトドキュメント管理
- 階層的なナレッジベース

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
- 全てのNotionページを単一階層の `.md` ファイルとして保存
- 階層構造はMarkdown内のFrontmatterとリンクで表現

**適用例**:
- OKR・会議録などの大量ページ管理
- ページ間の関連性を視覚化したい場合

**ローカル構造例**:
```
okr/
├── OKR_FY25.md
├── OKR_Q3_目標1.md
├── OKR_Q3_目標2.md
└── 振り返り.md
```

### モード切り替え

`.c2n/config.json` の `sync_mode` を編集：

```json
{
  "sync_mode": "hierarchy"  // または "flat"
}
```

## 💻 コードファイル同期（v2.1新機能）

### 対応ファイル形式

以下のファイルは自動的にNotionのコードブロックとして同期されます：

- `.py` (Python)
- `.js` (JavaScript)
- `.ts` (TypeScript)
- `.json` (JSON)
- `.yaml`, `.yml` (YAML)
- `.sh` (Bash)
- `.html` (HTML)
- `.css` (CSS)
- `.java` (Java)
- `.cpp`, `.c` (C/C++)
- `.go` (Go)
- `.rs` (Rust)
- `.rb` (Ruby)
- `.php` (PHP)
- `.sql` (SQL)
- `.xml` (XML)

### 長いコードの自動分割

1800文字を超えるコードファイルは、自動的に複数の`rich_text`ブロックに分割されます。

**実装詳細**:
```python
# file_processor.py (Lines 97-107)
chunk_size = 1800
for i in range(0, len(content), chunk_size):
    rich_text.append({
        "type": "text",
        "text": {"content": content[i:i + chunk_size]}
    })
```

**例**:
- 3,631文字のYAMLファイル → 2ブロック（1800 + 1831文字）
- 4,523文字のPythonファイル → 3ブロック（1800 + 1800 + 923文字）

### 使用例

```bash
# コードファイルを含むプロジェクトをPush
$ nit push ./my-project

✅ Created page: config.yaml -> https://www.notion.so/abc123
✅ Created page: script.py -> https://www.notion.so/def456
✅ Created page: data.json -> https://www.notion.so/ghi789
```

Notionページで確認すると：
- 各ファイルが適切な言語のコードブロックとして表示
- シンタックスハイライトが自動適用
- 長いコードも完全に表示される

## 🖼️ 画像ファイルの扱い（v2.1）

### 画像ファイル除外機能

以下の画像ファイルは自動的にPush対象から除外されます：

- `.png`, `.jpg`, `.jpeg`
- `.gif`, `.bmp`
- `.svg`, `.webp`
- `.ico`, `.tiff`, `.tif`

**理由**: 画像アップロード機能は将来的に実装予定のため、一時的に除外

**実装詳細**:
```python
# directory_processor.py (Lines 203-224)
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', ...}
files = [item for item in contents 
         if os.path.isfile(os.path.join(dir_path, item)) 
         and os.path.splitext(item.lower())[1] not in IMAGE_EXTENSIONS]
```

**将来的な復活**: コメントアウトされたコードを有効化することで、画像アップロード機能を復活できます。

## 🔧 URL統一管理システム

### 概要

v2.1では、NotionページURLの設定と解決が **`default_parent_url`に統一** され、シンプルで一貫した動作が保証されます。

### URL解決の優先順位

1. **`default_parent_url`** (`.c2n/config.json`) - プライマリソース
2. **`NOTION_ROOT_URL`** (環境変数) - 初期設定時のフォールバック

**従来の問題**: 4つの異なるURLソース（`root_page_url`, `parent_url`, `default_parent_url`, `NOTION_ROOT_URL`）が混在し、どのURLが使用されるかが不明確でした。

**解決策**: `default_parent_url`を唯一のソースとして使用する統一システム。

### `nit status --fix` による自動修復

URL設定の不整合を自動検出・修復します：

```bash
$ nit status /path/to/project --fix

🔍 URL整合性チェック中...
⚠️  不整合を検出: 3件
   - item1: root_url不一致
   - item2: parent_url不一致
🔧 自動修復を実行...
✅ 3件の不整合を修復しました
```

## 🗂️ .c2nディレクトリの理解

### ディレクトリ構造

```
project/
├── .c2n/
│   ├── config.json       # プロジェクト設定
│   ├── index.yaml        # 同期メタデータ（ページID、URL、タイムスタンプ）
│   ├── .cache.json       # キャッシュデータ
│   └── pull/
│       └── latest/       # Pull結果の一時保存
├── .c2n_ignore           # 除外パターン
└── ...
```

### 主要ファイルの説明

#### `config.json`
プロジェクト全体の設定ファイル：

```json
{
  "project_url": "https://www.notion.so/project-abc123",
  "default_parent_url": "https://www.notion.so/workspace-def456",
  "sync_mode": "hierarchy",
  "pull_apply_default": true,
  "push_changed_only_default": true
}
```

#### `index.yaml`
各ページの同期状態を管理：

```yaml
items:
  README.md:
    page_id: "abc123def456"
    page_url: "https://www.notion.so/README-abc123"
    local_mtime_ns: 1729000000000000000
    remote_last_edited: "2025-10-16T10:00:00.000Z"
    last_sync_at: "2025-10-16T10:01:00.000Z"
```

**重要フィールド**:
- `last_sync_at`: 最後に同期した時刻（差分検出に使用）
- `remote_last_edited`: Notion側の最終編集時刻
- `local_mtime_ns`: ローカルファイルの最終更新時刻（ナノ秒）

#### `.c2n_ignore`
Gitの`.gitignore`と同様の除外パターン：

```
# 除外例
*.tmp
.DS_Store
node_modules/
```

## ⚠️ よくある質問とエラー

### Q1: `NOTION_TOKEN`が設定されていないエラー

**エラー**:
```
Error: NOTION_TOKEN が設定されていません
```

**解決方法**:
1. `.env`ファイルを作成
2. `NOTION_TOKEN=secret_xxxxx`を記述
3. または環境変数を設定: `export NOTION_TOKEN="secret_xxxxx"`

### Q2: `nit: command not found`

**解決方法**:
```bash
# エイリアス設定を確認
alias nit

# なければ再設定
./install.sh

# または手動で設定
alias nit='python /path/to/cursor_to_notion/dev/src/nit_cli.py'
```

### Q3: Pushしたファイルがコードブロックにならない

**確認事項**:
- ファイル拡張子が対応形式か？（`.py`, `.yaml`, `.json`等）
- `file_processor.py`の`code_lang_map`に定義されているか？

**デバッグ**:
```bash
# 詳細ログでPush実行
nit push <folder> --verbose
```

### Q4: 画像ファイルがNotionに同期されない

**説明**: v2.1では画像ファイルは一時的に除外されています（将来的に実装予定）

**回避策**: 画像は手動でNotionページにアップロードしてください

### Q5: 長いコードが途中で切れる

**確認**: 1800文字を超えるコードは自動分割されるはずです

**デバッグ**:
1. `file_processor.py`の`chunk_size`を確認（Line 98）
2. Notionページで完全に表示されているか確認

### Q6: Pullでコンフリクトが発生した

**説明**: Git風のコンフリクトマーカーが自動挿入されます：

```markdown
<<<<<<< LOCAL
ローカルの内容
=======
Notionの内容
>>>>>>> REMOTE
```

**解決方法**:
1. ファイルを開いてコンフリクトマーカーを確認
2. 必要な内容を選択・マージ
3. マーカーを削除
4. `nit push`で反映

## 🎬 リアルな使用例：プロジェクトドキュメント管理

### シナリオ: 新規プロジェクトのドキュメント同期

**登場人物**: 田中さん（エンジニア、Notion愛用者）

**目標**: プロジェクトドキュメント（README、設計書、API仕様）をNotionとローカルで双方向同期させたい


---

## 💡 ベストプラクティス

### 1. 定期的な同期

```bash
# 作業開始前にPull
nit pull <folder>

# 作業終了後にPush
nit push <folder>
```

### 2. `--dry-run`で事前確認

```bash
# 実行計画を確認
nit push <folder> --dry-run
nit pull <folder> --dry-run
```

### 3. `.c2n_ignore`の活用

```
# ビルド成果物を除外
dist/
build/
*.pyc

# 一時ファイルを除外
*.tmp
*.swp
```

### 4. バックアップ

```bash
# .c2nディレクトリをバックアップ
cp -r project/.c2n project/.c2n.backup
```

### 5. コンフリクト回避のコツ

```bash
# 編集前に必ずPull
nit pull .

# Notion側で編集した場合は5分待ってからPull
# （Notion APIのタイムスタンプ反映待ち）

# 大きな変更は事前にチームに連絡
```

## ⚠️ 免責事項・注意事項

### 重要な免責事項

このソフトウェアは「現状のまま」提供され、**いかなる保証もありません**。

**開発者・貢献者は以下について一切の責任を負いません**:

1. **データ損失**: 
   - Notionページの削除・上書き
   - ローカルファイルの削除・破損
   - 同期エラーによるコンテンツの欠損

2. **システムへの影響**:
   - Notion APIレート制限による制約
   - 予期しないシステム挙動
   - パフォーマンスの低下

3. **ビジネスへの影響**:
   - 業務停止・遅延
   - 機会損失
   - 間接的・派生的損害

4. **その他**:
   - 本ツールの使用から生じるあらゆる損害
   - データ復旧・修復コスト
   - 第三者への損害

### 使用前の必須事項

✅ **必ず以下を実行してください**:

1. **バックアップ作成**
   ```bash
   # Notionページをエクスポート
   # Notion設定 → エクスポート → Markdown & CSV
   
   # ローカルファイルをバックアップ
   cp -r /path/to/project /path/to/project.backup
   ```

2. **テスト環境で試用**
   - 本番データでは絶対に使用しない
   - テスト用のNotionワークスペースで動作確認
   - 小規模なプロジェクトから開始

3. **重要データは手動確認**
   - `--dry-run` オプションで実行計画を確認
   - 同期後に必ずNotionとローカルを目視確認
   - コンフリクト発生時は慎重に解決

4. **定期的なバックアップ**
   - 作業前後に必ずバックアップ
   - `.c2n/` ディレクトリもバックアップ対象

### 既知の問題・制限事項

#### 🐛 既知のバグ

1. **コンテンツ重複**（v2.1で修正済み）
   - 問題: `nit push` 実行時にNotionページのコンテンツが重複
   - 対策: 既存ブロックを削除してから新ブロックを追加する実装に変更
   - 状態: ✅ 修正済み（v2.1）

2. **長いコードの制限**
   - 問題: 1800文字を超えるコードが途中で切れる可能性
   - 対策: 自動分割ロジックを実装
   - 状態: ✅ 修正済み（v2.1）、但し極端に長い場合は要注意

3. **画像ファイルの扱い**
   - 問題: 画像ファイルのアップロードが未実装
   - 対策: 一時的に画像ファイルを除外
   - 状態: ⚠️ 将来のバージョンで実装予定

4. **タイムスタンプ同期の遅延**
   - 問題: Notion側の `last_edited_time` が即座に反映されない場合がある
   - 対策: 5分程度の待機後に `nit pull` を実行
   - 状態: ⚠️ Notion API仕様による制約

5. **大量ページの処理**
   - 問題: 100ページ以上の同期でパフォーマンス低下
   - 対策: `--new-only` や `--existing-only` で分割実行
   - 状態: ⚠️ パフォーマンス最適化は今後の課題

#### 🚫 サポート外の機能

以下の機能は現在サポートされていません：

- ❌ **Notionデータベース**: 表形式・リレーション・ロールアップ等
- ❌ **高度なブロック**: トグルリスト・カラム・埋め込み等
- ❌ **添付ファイル**: PDF・動画等のバイナリファイル
- ❌ **リアルタイム同期**: 変更検知は手動実行のみ
- ❌ **複数人の同時編集**: コンフリクト解決は手動
- ❌ **ページ削除の自動検出**: Notion側で削除したページの自動削除

#### 📊 パフォーマンスの制約

- **Notion APIレート制限**: 3リクエスト/秒
- **大きなファイル**: 10MB超のMarkdownは処理が遅い
- **階層が深い構造**: 5階層以上は推奨しない
- **並列処理の制限**: 同時接続数に制限あり

### トラブル発生時の対応

1. **すぐに操作を停止**
   ```bash
   # プロセスを強制終了（Ctrl+Cが効かない場合）
   pkill -f nit_cli.py
   ```

2. **バックアップから復元**
   ```bash
   # ローカルファイルを復元
   rm -rf /path/to/project
   cp -r /path/to/project.backup /path/to/project
   
   # Notionページを復元
   # Notion → 設定 → ゴミ箱 から復元
   ```

3. **状態確認**
   ```bash
   # プロジェクト状態を確認
   nit status /path/to/project
   
   # ログを確認
   nit push /path/to/project --verbose
   ```

4. **Issue報告**
   - GitHubのIssuesで報告
   - 実行コマンド、エラーメッセージ、環境情報を記載
   - 可能であれば再現手順も記載

### 推奨される使用環境

✅ **推奨**:
- Python 3.8以上
- macOS / Linux
- テスト用Notionワークスペース
- 定期的なバックアップ体制

⚠️ **非推奨**:
- Windows（一部機能が未検証）
- 本番環境での直接使用
- 大規模プロジェクト（100ページ超）
- 複数人の同時編集が頻繁なプロジェクト

## 📖 詳細ドキュメント

より詳細な情報は以下をご参照ください：

- **[USER_GUIDE_COMPREHENSIVE.md](USER_GUIDE_COMPREHENSIVE.md)**: 完全ガイド（トラブルシューティング、ベストプラクティス）
- **[URL_UNIFICATION_GUIDE.md](src/URL_UNIFICATION_GUIDE.md)**: URL統一システムの詳細
- **[.env_setup_guide.md](.env_setup_guide.md)**: 環境変数セットアップガイド

## 🤝 コントリビューション

バグ報告や機能リクエストは、GitHubのIssuesでお願いします。

**貢献方法**:
1. Fork このリポジトリ
2. Feature branchを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をCommit (`git commit -m 'Add amazing feature'`)
4. Branchにpush (`git push origin feature/amazing-feature`)
5. Pull Requestを作成

**バグ報告時の必須情報**:
- 実行したコマンド
- エラーメッセージ全文
- 環境情報（OS、Pythonバージョン等）
- 再現手順
- 期待される動作と実際の動作

## 📄 ライセンス

MIT License

**本ソフトウェアは無保証で提供されます。使用によるいかなる損害についても、著作権者および貢献者は責任を負いません。**

詳細は [LICENSE](LICENSE) ファイルをご参照ください。

---

**v2.1 BETA** - 2025-10-16 更新

🚧 **このツールはベータ版です。本番環境での使用は避け、必ずバックアップを取ってからご使用ください。**
