# 仕様書サンプル

## 概要

このドキュメントは Notion への同期テスト用の仕様書サンプルです。

## 機能一覧

| 機能名 | 説明 | ステータス |
|--------|------|-----------|
| Push機能 | ローカル→Notion | ✅ 実装済み |
| Pull機能 | Notion→ローカル | ✅ 実装済み |
| 自動マージ | コンフリクト解決 | ✅ 実装済み |

## コード例

```python
# サンプルコード
def hello_world():
    print("Hello, Notion!")
    return True
```

## 注意事項

- Notion APIトークンが必要です
- `.c2n/config.json` の設定が必要です
- 初回は `nit init` で初期化してください




