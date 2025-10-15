# Git クリーンアップ手順

## 🎯 目的

機密情報や不要な開発ファイルをリポジトリから削除し、適切な `.gitignore` を設定します。

## 📝 削除対象

### 機密情報
- `config.json` - Notion APIトークンを含む設定ファイル

### 開発・テスト用ファイル
- `docs/archive/` - 開発履歴・アーカイブ
- `docs/archive/tests/` - テストデータ
- `test_markdown_converter.py` - テストスクリプト
- `test_walkthrough_*/` - 統合テスト一時ディレクトリ

### ビルド成果物
- `.venv/`, `venv/`, `venv_cursor_notion/` - Python仮想環境
- `node_modules/` - Node.jsパッケージ
- `package-lock.json` - Node.jsロックファイル
- `__pycache__/` - Pythonキャッシュ
- `*.pyc` - Pythonバイトコード

### Playwright関連
- `.auth/` - 認証情報
- `debug-*.png`, `screenshot-*.png` - スクリーンショット

## 🚀 実行手順

### ステップ1: スクリプトに実行権限を付与

```bash
chmod +x cleanup_git.sh
```

### ステップ2: スクリプトを実行

```bash
./cleanup_git.sh
```

### ステップ3: 変更内容を確認

```bash
git status
git diff --cached
```

### ステップ4: コミット＆プッシュ

```bash
# コミット
git commit -m "chore: add comprehensive .gitignore and remove sensitive/dev files

- Add comprehensive .gitignore with all necessary exclusions
- Remove config.json (contains API tokens)
- Remove docs/archive/ (development history)
- Remove all virtual environments (.venv, venv_*)
- Remove node_modules and package-lock.json
- Remove Python cache (__pycache__, *.pyc)
- Remove Playwright auth and test screenshots
- Keep config_sample.json as reference"

# プッシュ
git push origin main
```

## ⚠️ 注意事項

1. **バックアップ推奨**
   - 実行前に重要なファイルをバックアップしてください
   
2. **config.json**
   - ローカルの `config.json` は削除されません（Gitから除外されるだけ）
   - 引き続きローカルで使用できます
   
3. **仮想環境**
   - ローカルの `.venv/` も削除されません
   - `install.sh` で再作成できます

4. **二度と戻せません**
   - Git履歴から完全に削除されるわけではありません
   - 機密情報が既にプッシュされている場合は別途対応が必要です

## 🔍 確認コマンド

### 削除されたファイルを確認

```bash
git diff --cached --name-status
```

### 追跡対象外になったファイルを確認

```bash
git ls-files --others --exclude-standard
```

## 📚 参考

- `.gitignore` の内容: `cat .gitignore`
- Git status: `git status`

