# test_pull_merge.py - テスト実装サマリー

## 概要

`c2n.py` の `cmd_pull()`, `_merge_two_way()`, `_apply_direct_merge()` 関数を対象とした包括的なユニットテストを実装しました。

## テスト構成

### テストファイル
- **ファイル名**: `test_pull_merge.py`
- **テストケース数**: 23個
- **テスト実行結果**: 全テスト合格 ✅

### テストクラス構成

#### 1. TestMergeTwoWay (10テストケース)
`_merge_two_way()` 関数のGit風コンフリクトマーカーによる2方向マージロジックをテスト

- ✅ `test_merge_identical_content` - 同一コンテンツのマージ（コンフリクトなし）
- ✅ `test_merge_empty_files` - 空ファイル同士のマージ
- ✅ `test_merge_insert_only_remote` - リモートのみに新規行追加（insertオペレーション）
- ✅ `test_merge_delete_only_local` - ローカルで行削除（remoteが採用される）
- ✅ `test_merge_delete_local_only_lines` - ローカルのみに存在する行（コンフリクト発生）
- ✅ `test_merge_replace_conflict` - 同じ行が異なる内容に変更（replaceコンフリクト）
- ✅ `test_merge_multiple_conflicts` - 複数箇所でのコンフリクト
- ✅ `test_merge_mixed_operations` - equal, insert, delete, replaceの混合ケース
- ✅ `test_merge_trailing_newlines` - 末尾改行処理の確認
- ✅ `test_merge_single_line_change` - 1行のみの変更

#### 2. TestApplyDirectMerge (5テストケース)
`_apply_direct_merge()` 関数のファイルマージと状態管理をテスト

- ✅ `test_apply_merge_same_content` - 同一内容の場合、SAMEステータス
- ✅ `test_apply_merge_add_new_file` - 新規ファイル追加（ADD/REPLACEステータス）
- ✅ `test_apply_merge_replace_empty_file` - 空ファイル置換（REPLACEステータス）
- ✅ `test_apply_merge_update_with_conflict` - コンフリクト付きUPDATE
- ✅ `test_apply_merge_preserves_original_on_same` - 同一内容の場合はファイル不変

#### 3. TestCmdPullIntegration (3テストケース)
`cmd_pull()` 関数の統合テスト（モック使用）

- ✅ `test_cmd_pull_basic_execution` - cmd_pull基本実行フロー（モック）
- ✅ `test_read_write_text_helpers` - _read_text/_write_textヘルパー関数
- ✅ `test_read_text_nonexistent_file` - 存在しないファイル読み込み

#### 4. TestEdgeCases (5テストケース)
エッジケースと例外的なシナリオをテスト

- ✅ `test_merge_very_long_lines` - 非常に長い行（10,000文字）を含むマージ
- ✅ `test_merge_unicode_characters` - ユニコード文字（日本語、中国語、韓国語）
- ✅ `test_merge_only_whitespace_changes` - 空白のみの差異
- ✅ `test_apply_merge_with_permission_error` - 書き込み権限エラー処理（Unix系）
- ✅ `test_merge_binary_like_content` - 制御文字を含むコンテンツ

## コンフリクト解決ロジックの重点テスト

### difflib.SequenceMatcher のオペレーションタイプ

1. **equal** - 同一行: そのまま採用
2. **insert** - リモートのみに存在: リモートを採用（コンフリクトなし）
3. **delete** - ローカルのみに存在: コンフリクトマーカー付き
4. **replace** - 両方で異なる内容: コンフリクトマーカー付き

### コンフリクトマーカー形式
```
<<<<<<< LOCAL
ローカルの内容
=======
リモートの内容
>>>>>>> REMOTE
```

## テスト実行方法

```bash
# 基本実行
python3 test_pull_merge.py

# 詳細出力
python3 test_pull_merge.py -v

# 特定のテストクラスのみ実行
python3 test_pull_merge.py TestMergeTwoWay

# 特定のテストケースのみ実行
python3 test_pull_merge.py TestMergeTwoWay.test_merge_replace_conflict
```

## テスト結果

```
----------------------------------------------------------------------
Ran 23 tests in 0.006s

OK
```

全23テストケースが正常に実行され、コンフリクト解決ロジックの正確性が検証されました。

## カバレッジ

- ✅ 2方向マージアルゴリズム（difflib.SequenceMatcher）
- ✅ コンフリクトマーカーの生成
- ✅ ファイル状態管理（SAME, ADD, REPLACE, UPDATE）
- ✅ ユニコード文字処理
- ✅ エッジケース（長い行、空白のみの差異、制御文字）
- ✅ エラーハンドリング（権限エラー、存在しないファイル）

## 実装の特徴

1. **一時ディレクトリ使用**: 各テストで独立した環境を構築
2. **setUp/tearDown**: 適切なリソース管理
3. **モック使用**: 外部依存（subprocess, notion API）を排除
4. **エッジケース網羅**: 実用的な境界条件を包括的にテスト

## 今後の拡張可能性

- より複雑な入れ子構造のコンフリクトテスト
- パフォーマンステスト（巨大ファイルのマージ）
- 並行実行時の競合状態テスト
- エンコーディングエラーハンドリング
