# test_pull_merge.py - ユニットテストガイド

## クイックスタート

```bash
# テスト実行
python3 test_pull_merge.py

# 詳細表示
python3 test_pull_merge.py -v
```

## テスト対象関数

### 1. `_merge_two_way(dst_txt: str, src_txt: str) -> str`
**目的**: Git風のコンフリクトマーカーで行レベルマージを実行

**テスト観点**:
- 同一コンテンツのマージ（コンフリクトなし）
- insert/delete/replace オペレーション
- 複数コンフリクトの処理
- エッジケース（空ファイル、長い行、ユニコード文字）

### 2. `_apply_direct_merge(src_path: str, dst_path: str) -> str`
**目的**: ファイルを直接マージして結果を返す

**戻り値**:
- `SAME`: 内容が同一
- `ADD`: 新規ファイル追加
- `REPLACE`: 空ファイル置換
- `UPDATE`: コンフリクト付きマージ

**テスト観点**:
- 各ステータスの正確性
- ファイルI/O操作
- コンフリクトマーカーの挿入

### 3. `cmd_pull(target: str, snapshot: bool = False)`
**目的**: Notionからローカルへpull操作

**テスト観点**:
- 基本実行フロー（モック使用）
- 設定ファイル読み込み
- マージ適用

## テスト構成（23テストケース）

### TestMergeTwoWay (10ケース)
マージアルゴリズムの核心をテスト

| テストケース | 検証内容 |
|------------|---------|
| `test_merge_identical_content` | 同一内容 → マーカーなし |
| `test_merge_empty_files` | 空ファイル同士 |
| `test_merge_insert_only_remote` | リモート追加 → 自動採用 |
| `test_merge_delete_only_local` | ローカル削除 → リモート採用 |
| `test_merge_delete_local_only_lines` | ローカル専有行 → コンフリクト |
| `test_merge_replace_conflict` | 両方変更 → コンフリクト |
| `test_merge_multiple_conflicts` | 複数箇所コンフリクト |
| `test_merge_mixed_operations` | 混合オペレーション |
| `test_merge_trailing_newlines` | 末尾改行処理 |
| `test_merge_single_line_change` | 1行変更 |

### TestApplyDirectMerge (5ケース)
ファイル操作と状態管理をテスト

| テストケース | 検証内容 |
|------------|---------|
| `test_apply_merge_same_content` | SAME ステータス |
| `test_apply_merge_add_new_file` | ADD/REPLACE ステータス |
| `test_apply_merge_replace_empty_file` | REPLACE ステータス |
| `test_apply_merge_update_with_conflict` | UPDATE + マーカー |
| `test_apply_merge_preserves_original_on_same` | 同一時は不変 |

### TestCmdPullIntegration (3ケース)
統合テスト

| テストケース | 検証内容 |
|------------|---------|
| `test_cmd_pull_basic_execution` | 基本フロー（モック） |
| `test_read_write_text_helpers` | ヘルパー関数 |
| `test_read_text_nonexistent_file` | 存在しないファイル |

### TestEdgeCases (5ケース)
境界条件とエラーケース

| テストケース | 検証内容 |
|------------|---------|
| `test_merge_very_long_lines` | 10,000文字の長い行 |
| `test_merge_unicode_characters` | 多言語文字 |
| `test_merge_only_whitespace_changes` | 空白のみの差異 |
| `test_apply_merge_with_permission_error` | 権限エラー |
| `test_merge_binary_like_content` | 制御文字含む |

## コンフリクトマーカー形式

```
<<<<<<< LOCAL
ローカルで変更された内容
または
ローカルにのみ存在する内容
=======
リモートで変更された内容
または
（空：リモートで削除された）
>>>>>>> REMOTE
```

## 実行例

```bash
# 全テスト実行
$ python3 test_pull_merge.py
.......................
----------------------------------------------------------------------
Ran 23 tests in 0.006s

OK

# 詳細表示
$ python3 test_pull_merge.py -v
test_merge_identical_content ... ok
test_merge_empty_files ... ok
test_merge_insert_only_remote ... ok
...
----------------------------------------------------------------------
Ran 23 tests in 0.006s

OK

# 特定クラスのみ
$ python3 test_pull_merge.py TestMergeTwoWay
..........
----------------------------------------------------------------------
Ran 10 tests in 0.002s

OK
```

## トラブルシューティング

### テストが失敗する場合

1. **importエラー**: `c2n.py` と同じディレクトリで実行
2. **権限エラー**: Unix系OSで一部テストがスキップされる可能性あり
3. **一時ファイルエラー**: `/tmp` への書き込み権限を確認

### デバッグ方法

```python
# 個別テストのデバッグ
python3 -c "
from c2n import _merge_two_way

dst = 'your local content'
src = 'your remote content'
result = _merge_two_way(dst, src)
print(result)
"
```

## 今後の改善案

- [ ] カバレッジ測定の追加
- [ ] CI/CD統合
- [ ] パフォーマンスベンチマーク
- [ ] より複雑な入れ子構造のテスト
- [ ] エンコーディングエラーケース

## 関連ファイル

- `c2n.py` - テスト対象のメインモジュール
- `test_markdown_converter.py` - マークダウン変換のテスト
- `TEST_PULL_MERGE_SUMMARY.md` - テスト実装サマリー
