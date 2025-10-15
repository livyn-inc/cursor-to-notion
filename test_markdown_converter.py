import unittest
import json
from md_to_blocks import (
    convert_markdown_to_notion_blocks,
    parse_inline_formatting,
    process_table,
    validate_notion_block,
    process_list_items
)


class TestMarkdownConverter(unittest.TestCase):
    """Markdown to Notion blocks converter のテストクラス"""

    def setUp(self):
        """テストの前処理"""
        self.maxDiff = None  # 長い差分も表示

    def test_convert_markdown_to_notion_blocks_empty(self):
        """空のマークダウンのテスト"""
        result = convert_markdown_to_notion_blocks("")
        self.assertEqual(result, [])

    def test_convert_markdown_to_notion_blocks_whitespace_only(self):
        """空白のみのマークダウンのテスト"""
        result = convert_markdown_to_notion_blocks("   \n\n  \t  \n  ")
        self.assertEqual(result, [])

    def test_convert_markdown_to_notion_blocks_yaml_frontmatter(self):
        """YAMLフロントマターの除去テスト"""
        markdown = """---
title: Test Document
author: Test Author
---

# Main Title

This is content after frontmatter.
"""
        result = convert_markdown_to_notion_blocks(markdown)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["type"], "heading_1")
        self.assertEqual(result[0]["heading_1"]["rich_text"][0]["text"]["content"], "Main Title")
        self.assertEqual(result[1]["type"], "paragraph")

    def test_convert_markdown_to_notion_blocks_headers(self):
        """ヘッダーの変換テスト"""
        markdown = """# H1 Title
## H2 Title
### H3 Title
#### H4 Title
##### H5 Title
###### H6 Title
"""
        result = convert_markdown_to_notion_blocks(markdown)
        
        # H1-H3は通常のヘッダーとして処理
        self.assertEqual(result[0]["type"], "heading_1")
        self.assertEqual(result[0]["heading_1"]["rich_text"][0]["text"]["content"], "H1 Title")
        
        self.assertEqual(result[1]["type"], "heading_2")
        self.assertEqual(result[1]["heading_2"]["rich_text"][0]["text"]["content"], "H2 Title")
        
        self.assertEqual(result[2]["type"], "heading_3")
        self.assertEqual(result[2]["heading_3"]["rich_text"][0]["text"]["content"], "H3 Title")
        
        # H4以下は太字の段落として処理（マーカー付き）
        self.assertEqual(result[3]["type"], "paragraph")
        self.assertTrue(result[3]["paragraph"]["rich_text"][0]["text"]["content"].startswith("(h_4) H4 Title"))
        self.assertTrue(result[3]["paragraph"]["rich_text"][0]["annotations"]["bold"])
        
        self.assertEqual(result[4]["type"], "paragraph")
        self.assertTrue(result[4]["paragraph"]["rich_text"][0]["text"]["content"].startswith("(h_5) H5 Title"))
        
        self.assertEqual(result[5]["type"], "paragraph")
        self.assertTrue(result[5]["paragraph"]["rich_text"][0]["text"]["content"].startswith("(h_6) H6 Title"))

    def test_convert_markdown_to_notion_blocks_paragraphs(self):
        """段落の変換テスト"""
        markdown = """This is a simple paragraph.

This is another paragraph with **bold text** and *italic text*.

This paragraph has a [link](https://example.com) in it.
"""
        result = convert_markdown_to_notion_blocks(markdown)
        
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["type"], "paragraph")
        self.assertEqual(result[0]["paragraph"]["rich_text"][0]["text"]["content"], "This is a simple paragraph.")
        
        self.assertEqual(result[1]["type"], "paragraph")
        # インライン書式のテストは別途実装
        
        self.assertEqual(result[2]["type"], "paragraph")

    def test_convert_markdown_to_notion_blocks_bulleted_lists(self):
        """箇条書きリストの変換テスト"""
        markdown = """- First item
- Second item
- Third item
"""
        result = convert_markdown_to_notion_blocks(markdown)
        
        self.assertEqual(len(result), 3)
        expected_contents = ["First item", "Second item", "Third item"]
        for i, item in enumerate(result):
            self.assertEqual(item["type"], "bulleted_list_item")
            self.assertEqual(item["bulleted_list_item"]["rich_text"][0]["text"]["content"], expected_contents[i])

    def test_convert_markdown_to_notion_blocks_numbered_lists(self):
        """番号付きリストの変換テスト"""
        markdown = """1. First item
2. Second item
3. Third item
"""
        result = convert_markdown_to_notion_blocks(markdown)
        
        self.assertEqual(len(result), 3)
        expected_contents = ["First item", "Second item", "Third item"]
        for i, item in enumerate(result):
            self.assertEqual(item["type"], "numbered_list_item")
            self.assertEqual(item["numbered_list_item"]["rich_text"][0]["text"]["content"], expected_contents[i])

    def test_convert_markdown_to_notion_blocks_code_blocks(self):
        """コードブロックの変換テスト"""
        markdown = """```python
def hello_world():
    print("Hello, World!")
```

```javascript
function hello() {
    console.log("Hello!");
}
```

```
Plain text code block
```
"""
        result = convert_markdown_to_notion_blocks(markdown)
        
        self.assertEqual(len(result), 3)
        
        # Pythonコードブロック
        self.assertEqual(result[0]["type"], "code")
        self.assertEqual(result[0]["code"]["language"], "python")
        self.assertIn("def hello_world():", result[0]["code"]["rich_text"][0]["text"]["content"])
        
        # JavaScriptコードブロック
        self.assertEqual(result[1]["type"], "code")
        self.assertEqual(result[1]["code"]["language"], "javascript")
        self.assertIn("function hello()", result[1]["code"]["rich_text"][0]["text"]["content"])
        
        # プレーンテキストコードブロック
        self.assertEqual(result[2]["type"], "code")
        self.assertEqual(result[2]["code"]["language"], "plain text")
        self.assertEqual(result[2]["code"]["rich_text"][0]["text"]["content"], "Plain text code block")

    def test_convert_markdown_to_notion_blocks_horizontal_rules(self):
        """水平線の変換テスト"""
        markdown = """Before divider
---
After divider
***
Another divider
___
Final divider
"""
        result = convert_markdown_to_notion_blocks(markdown)
        
        # 実際の結果を確認してからテストを調整
        self.assertGreaterEqual(len(result), 6)  # 少なくとも6つのブロック
        divider_count = sum(1 for block in result if block["type"] == "divider")
        self.assertEqual(divider_count, 3)  # 3つの区切り線

    def test_convert_markdown_to_notion_blocks_tables(self):
        """テーブルの変換テスト"""
        markdown = """| Header 1 | Header 2 | Header 3 |
|----------|----------|----------|
| Cell 1   | Cell 2   | Cell 3   |
| Cell 4   | Cell 5   | Cell 6   |
"""
        result = convert_markdown_to_notion_blocks(markdown)
        
        # テーブルは1つのtableブロックとして処理される
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "table")
        self.assertEqual(result[0]["table"]["table_width"], 3)
        self.assertTrue(result[0]["table"]["has_column_header"])
        self.assertEqual(len(result[0]["table"]["children"]), 3)  # ヘッダー + 2データ行

    def test_parse_inline_formatting_bold(self):
        """太字のインライン書式テスト"""
        result = parse_inline_formatting("This is **bold text**")
        self.assertTrue(result["annotations"]["bold"])
        self.assertEqual(result["text"]["content"], "This is bold text")

    def test_parse_inline_formatting_italic(self):
        """イタリックのインライン書式テスト"""
        result = parse_inline_formatting("This is *italic text*")
        self.assertTrue(result["annotations"]["italic"])
        self.assertEqual(result["text"]["content"], "This is italic text")

    def test_parse_inline_formatting_link(self):
        """リンクのインライン書式テスト"""
        result = parse_inline_formatting("This is a [link](https://example.com)")
        self.assertEqual(result["text"]["content"], "This is a link")
        self.assertEqual(result["text"]["link"]["url"], "https://example.com")

    def test_parse_inline_formatting_combined(self):
        """複合インライン書式テスト"""
        result = parse_inline_formatting("This is **bold** and *italic* with [link](https://example.com)")
        self.assertTrue(result["annotations"]["bold"])
        self.assertTrue(result["annotations"]["italic"])
        self.assertEqual(result["text"]["link"]["url"], "https://example.com")

    def test_process_table_valid(self):
        """有効なテーブルの処理テスト"""
        table_rows = [
            "| Header 1 | Header 2 |",
            "|----------|----------|",
            "| Cell 1   | Cell 2   |"
        ]
        result = process_table(table_rows)
        
        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "table")
        self.assertEqual(result["table"]["table_width"], 2)
        self.assertTrue(result["table"]["has_column_header"])
        self.assertEqual(len(result["table"]["children"]), 2)  # ヘッダー + 1データ行

    def test_process_table_invalid(self):
        """無効なテーブルの処理テスト"""
        # 行数不足
        table_rows = ["| Header |"]
        result = process_table(table_rows)
        self.assertIsNone(result)
        
        # ヘッダーなし
        table_rows = ["|----------|", "| Cell |"]
        result = process_table(table_rows)
        self.assertIsNone(result)

    def test_validate_notion_block_valid(self):
        """有効なNotionブロックの検証テスト"""
        valid_block = {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": "Test"}}]
            }
        }
        self.assertTrue(validate_notion_block(valid_block))

    def test_validate_notion_block_invalid(self):
        """無効なNotionブロックの検証テスト"""
        # objectが不正
        invalid_block = {"type": "paragraph"}
        self.assertFalse(validate_notion_block(invalid_block))
        
        # typeが不正
        invalid_block = {"object": "block"}
        self.assertFalse(validate_notion_block(invalid_block))
        
        # 必要なプロパティが不足
        invalid_block = {
            "object": "block",
            "type": "paragraph"
        }
        self.assertFalse(validate_notion_block(invalid_block))

    def test_process_list_items_bulleted(self):
        """箇条書きリストの処理テスト"""
        lines = ["- Item 1", "- Item 2", "- Item 3"]
        result, new_index = process_list_items(lines, 0)
        
        self.assertEqual(len(result), 3)
        self.assertEqual(new_index, 3)
        expected_contents = ["Item 1", "Item 2", "Item 3"]
        for i, item in enumerate(result):
            self.assertEqual(item["type"], "bulleted_list_item")
            self.assertEqual(item["bulleted_list_item"]["rich_text"][0]["text"]["content"], expected_contents[i])

    def test_process_list_items_numbered(self):
        """番号付きリストの処理テスト"""
        lines = ["1. Item 1", "2. Item 2", "3. Item 3"]
        result, new_index = process_list_items(lines, 0)
        
        self.assertEqual(len(result), 3)
        self.assertEqual(new_index, 3)
        expected_contents = ["Item 1", "Item 2", "Item 3"]
        for i, item in enumerate(result):
            self.assertEqual(item["type"], "numbered_list_item")
            self.assertEqual(item["numbered_list_item"]["rich_text"][0]["text"]["content"], expected_contents[i])

    def test_convert_markdown_to_notion_blocks_long_text(self):
        """長いテキストの分割テスト"""
        long_text = "A" * 2000  # 2000文字のテキスト
        markdown = f"# {long_text}"
        result = convert_markdown_to_notion_blocks(markdown)
        
        # H1は通常のヘッダーとして処理されるが、長い場合は段落に変換される可能性がある
        self.assertGreaterEqual(len(result), 1)
        # 長いテキストが分割されているかチェック
        total_content_length = 0
        for block in result:
            if block["type"] == "paragraph":
                content = block["paragraph"]["rich_text"][0]["text"]["content"]
                total_content_length += len(content)
                self.assertLessEqual(len(content), 1800)  # 最大長制限
            elif block["type"] == "heading_1":
                content = block["heading_1"]["rich_text"][0]["text"]["content"]
                total_content_length += len(content)
        
        # 元のテキストの長さが保持されているかチェック
        self.assertGreaterEqual(total_content_length, len(long_text))

    def test_convert_markdown_to_notion_blocks_mixed_content(self):
        """混合コンテンツのテスト"""
        markdown = """# Main Title

This is a paragraph with **bold** and *italic* text.

- List item 1
- List item 2

```python
print("Hello, World!")
```

| Column 1 | Column 2 |
|----------|----------|
| Value 1  | Value 2  |

---

Final paragraph.
"""
        result = convert_markdown_to_notion_blocks(markdown)
        
        # 各要素が正しく変換されているかチェック
        block_types = [block["type"] for block in result]
        self.assertIn("heading_1", block_types)
        self.assertIn("paragraph", block_types)
        self.assertIn("bulleted_list_item", block_types)
        self.assertIn("code", block_types)
        self.assertIn("table", block_types)
        self.assertIn("divider", block_types)

    def test_convert_markdown_to_notion_blocks_invalid_markdown(self):
        """無効なマークダウンの処理テスト"""
        # 不完全なコードブロック
        markdown = "```python\nprint('Hello')\n"
        result = convert_markdown_to_notion_blocks(markdown)
        
        # エラーが発生せず、可能な限り処理される
        self.assertIsInstance(result, list)

    def test_convert_markdown_to_notion_blocks_special_characters(self):
        """特殊文字の処理テスト"""
        markdown = """# 日本語タイトル

これは**太字**と*イタリック*のテストです。

- 項目1
- 項目2

```python
# コメント
print("こんにちは")
```
"""
        result = convert_markdown_to_notion_blocks(markdown)
        
        # 日本語が正しく処理される
        self.assertGreater(len(result), 0)
        for block in result:
            if block["type"] == "heading_1":
                self.assertEqual(block["heading_1"]["rich_text"][0]["text"]["content"], "日本語タイトル")


if __name__ == "__main__":
    # テスト実行時の詳細出力を有効化
    unittest.main(verbosity=2)