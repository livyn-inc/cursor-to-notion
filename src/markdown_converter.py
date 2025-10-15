import re
from typing import List, Dict, Any, Tuple
import json
import sys

# Notionが受け付けるコードブロック言語のホワイトリスト
SUPPORTED_CODE_LANGUAGES = set([
    "abap", "abc", "agda", "arduino", "ascii art", "assembly", "bash", "basic", "bnf",
    "c", "c#", "c++", "clojure", "coffeescript", "coq", "css", "dart", "dhall", "diff",
    "docker", "ebnf", "elixir", "elm", "erlang", "f#", "flow", "fortran", "gherkin", "glsl",
    "go", "graphql", "groovy", "haskell", "hcl", "html", "idris", "java", "javascript",
    "json", "julia", "kotlin", "latex", "less", "lisp", "livescript", "llvm ir", "lua",
    "makefile", "markdown", "markup", "matlab", "mathematica", "mermaid", "nix", "notion formula",
    "objective-c", "ocaml", "pascal", "perl", "php", "plain text", "powershell", "prolog",
    "protobuf", "purescript", "python", "r", "racket", "reason", "ruby", "rust", "sass",
    "scala", "scheme", "scss", "shell", "smalltalk", "solidity", "sql", "swift", "toml",
    "typescript", "vb.net", "verilog", "vhdl", "visual basic", "webassembly", "xml", "yaml",
    "java/c/c++/c#"
])

def _remove_yaml_frontmatter(lines: List[str]) -> List[str]:
    """YAMLフロントマターを除去"""
    if lines and lines[0].strip() == '---':
        # YAMLフロントマターの終了を探す
        yaml_end = -1
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                yaml_end = i
                break
        if yaml_end > 0:
            lines = lines[yaml_end + 1:]
            print(f"YAMLフロントマターを除去しました（{yaml_end + 1}行）")
    return lines


def _process_header(line: str) -> List[Dict[str, Any]]:
    """ヘッダーを処理"""
    # print("ヘッダーを処理します")  # デバッグログ: 非表示
    raw_level = len(line.split()[0])
    content = line.lstrip('#').strip()
    blocks = []
    
    if raw_level <= 3:
        level = raw_level
        blocks.append({
            "object": "block",
            "type": f"heading_{level}",
            f"heading_{level}": {
                "rich_text": [parse_inline_formatting(content)]
            }
        })
    else:
        # H4以下は太字の段落へ。復元用に (h_4) 等のマーカーを先頭に付与
        marker = f"(h_{raw_level}) "
        text = marker + content
        MAX_LEN = 1800
        if len(text) <= MAX_LEN:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": text},
                        "annotations": {
                            "bold": True,
                            "italic": False,
                            "strikethrough": False,
                            "underline": False,
                            "code": False,
                            "color": "default"
                        }
                    }]
                }
            })
        else:
            start = 0
            first = True
            while start < len(text):
                chunk = text[start:start+MAX_LEN]
                if start + MAX_LEN < len(text):
                    cut = chunk.rfind(' ')
                    if cut > 100:
                        chunk = chunk[:cut]
                        start += cut + 1
                    else:
                        start += MAX_LEN
                else:
                    start += MAX_LEN
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": chunk},
                            "annotations": {
                                "bold": True if first else False,
                                "italic": False,
                                "strikethrough": False,
                                "underline": False,
                                "code": False,
                                "color": "default"
                            }
                        }]
                    }
                })
                first = False
    return blocks


def _process_code_block(lines: List[str], start_i: int) -> tuple[List[Dict[str, Any]], int]:
    """コードブロックを処理"""
    print("コードブロックを処理します")
    line = lines[start_i]
    raw_lang = (line[3:] or '').strip().lower()
    
    # Notionサポート言語へマッピング
    lang_map = {
        '': 'plain text',
        'txt': 'plain text',
        'text': 'plain text',
        'plain_text': 'plain text',
        'sh': 'bash', 'zsh': 'bash', 'shell': 'shell',
        'py': 'python', 'js': 'javascript', 'ts': 'typescript',
        'yml': 'yaml', 'md': 'markdown', 'json5': 'json',
        'html': 'html', 'css': 'css'
    }
    
    # フォールバック: 未対応言語は plain text
    language = lang_map.get(raw_lang, raw_lang if raw_lang in {
        'abap','abc','agda','arduino','ascii art','assembly','bash','basic','bnf','c','c#','c++','clojure','coffeescript','coq','css','dart','dhall','diff','docker','ebnf','elixir','elm','erlang','f#','flow','fortran','gherkin','glsl','go','graphql','groovy','haskell','hcl','html','idris','java','javascript','json','julia','kotlin','latex','less','lisp','livescript','llvm ir','lua','makefile','markdown','markup','matlab','mathematica','mermaid','nix','notion formula','objective-c','ocaml','pascal','perl','php','plain text','powershell','prolog','protobuf','purescript','python','r','racket','reason','ruby','rust','sass','scala','scheme','scss','shell','smalltalk','solidity','sql','swift','toml','typescript','vb.net','verilog','vhdl','visual basic','webassembly','xml','yaml','java/c/c++/c#'
    } else 'plain text')
    
    # 未対応言語は安全側で plain text にフォールバック
    if language not in SUPPORTED_CODE_LANGUAGES:
        language = 'plain text'
    
    code_lines = []
    i = start_i + 1
    while i < len(lines) and not lines[i].strip().startswith('```'):
        code_lines.append(lines[i])
        i += 1
    
    # Skip the closing ``` line
    if i < len(lines) and lines[i].strip().startswith('```'):
        i += 1
    
    code_text = "\n".join(code_lines)
    
    # 空のコードブロックの場合は空のブロックを返す
    if not code_text.strip():
        return [{
            "object": "block",
            "type": "code",
            "code": {
                "rich_text": [{"type": "text", "text": {"content": ""}}],
                "language": language
            }
        }], i
    
    blocks = []
    
    # Notionのtext.contentは最大2000文字。安全側で1800文字に分割
    MAX_LEN = 1800
    if len(code_text) <= MAX_LEN:
        blocks.append({
            "object": "block",
            "type": "code",
            "code": {
                "rich_text": [{"type": "text", "text": {"content": code_text}}],
                "language": language
            }
        })
    else:
        start = 0
        part = 1
        while start < len(code_text):
            chunk = code_text[start:start+MAX_LEN]
            # 途中で改行区切りに寄せる（最後の改行位置まで）
            if start + MAX_LEN < len(code_text):
                cut = chunk.rfind('\n')
                # YAMLファイルは常に改行位置で分割（行の途中で切れないように）
                # その他のファイルは100文字以上の場合のみ改行で分割
                if language == 'yaml':
                    # YAMLの場合: 改行が見つかれば必ずそこで切る（cut >= 0）
                    if cut >= 0:
                        chunk = chunk[:cut]
                        start += cut + 1
                    else:
                        # 改行が見つからない場合は強制的にMAX_LENで切る
                        start += MAX_LEN
                else:
                    # その他の言語: 100文字以上の場合のみ改行で切る
                    if cut > 100:
                        chunk = chunk[:cut]
                        start += cut + 1
                    else:
                        start += MAX_LEN
            else:
                start += MAX_LEN
            blocks.append({
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [{"type": "text", "text": {"content": chunk}}],
                    "language": language
                }
            })
    
    return blocks, i


def _is_valid_table_start(lines: List[str], i: int) -> bool:
    """Markdownテーブルの開始行かどうかを判定
    
    有効なテーブルは以下の条件を満たす必要がある:
    1. 現在の行に | が含まれる
    2. 次の行が区切り線（|---|---|など）である
    """
    if i >= len(lines) - 1:  # 次の行がない
        return False
    
    current_line = lines[i].strip()
    next_line = lines[i + 1].strip()
    
    # 現在の行に | がない
    if '|' not in current_line:
        return False
    
    # 次の行が区切り線かチェック
    # 区切り線は | と - と : のみで構成される（スペース含む）
    if '|' not in next_line:
        return False
    
    # 区切り線の各セルが - のみ（または :--: や :-- などのアライメント指定）で構成されているか
    cells = [cell.strip() for cell in next_line.split('|') if cell.strip()]
    if not cells:
        return False
    
    for cell in cells:
        # セルが空でなく、- と : のみで構成されている
        if not cell or not all(c in '-: ' for c in cell):
            return False
    
    return True


def _process_table(lines: List[str], start_i: int) -> tuple[List[Dict[str, Any]], int]:
    """テーブルを処理"""
    print("テーブルを処理します")
    table_rows = []
    i = start_i
    # テーブル行を収集
    while i < len(lines) and '|' in lines[i]:
        table_rows.append(lines[i])
        i += 1
    
    # ✅ FIX: テーブル収集後、次の行を指すように調整（無限ループ防止）
    # i は既に次の行（テーブル終了後）を指しているので、-1 しない
    next_i = i  # テーブル終了後の次の行
    
    blocks = []
    # テーブルの処理
    table_blocks = process_table(table_rows)
    if table_blocks:
        # 複数ブロック（table本体＋row群）を想定
        if isinstance(table_blocks, list):
            for tb in table_blocks:
                if validate_notion_block(tb):
                    blocks.append(tb)
        elif isinstance(table_blocks, dict):
            if validate_notion_block(table_blocks):
                blocks.append(table_blocks)
    else:
        # ✅ FIX: テーブル処理に失敗した場合は、テーブル行全体をスキップして次の行に進む
        # 段落として処理すると、再度 '|' を含む行として認識され無限ループに陥る
        print(f"テーブル処理失敗: {len(table_rows)}行をスキップします")
    
    # ✅ FIX: 必ず next_i - 1 を返す（呼び出し側で i += 1 するため）
    return blocks, next_i - 1


def _process_paragraph(line: str) -> List[Dict[str, Any]]:
    """段落を処理"""
    # print("段落を処理します")  # デバッグログ: 非表示
    blocks = []
    try:
        rt = parse_inline_formatting(line)
        content_text = rt["text"]["content"]
        MAX_LEN = 1800  # 安全側（Notion制限は2000）
        if len(content_text) <= MAX_LEN:
            paragraph_block = {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [rt]}
            }
            if content_text.strip():
                blocks.append(paragraph_block)
        else:
            start = 0
            while start < len(content_text):
                chunk = content_text[start:start+MAX_LEN]
                if start + MAX_LEN < len(content_text):
                    cut = chunk.rfind(' ')
                    if cut > 100:
                        chunk = chunk[:cut]
                        start += cut + 1
                    else:
                        start += MAX_LEN
                else:
                    start += MAX_LEN
                chunk_rt = dict(rt)
                # deep copy minimal
                chunk_rt = {
                    "type": "text",
                    "text": {"content": chunk},
                    "annotations": rt.get("annotations", {})
                }
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [chunk_rt]}
                })
    except ValueError as e:
        print(f"警告: {e}. 行をスキップします: {line}")
    
    return blocks


def convert_markdown_to_notion_blocks(markdown: str) -> List[Dict[str, Any]]:
    # print("convert_markdown_to_notion_blocks 関数を開始します")  # デバッグログ: 非表示
    try:
        # YAMLフロントマターを除去
        lines = markdown.split('\n')
        lines = _remove_yaml_frontmatter(lines)
        
        blocks = []
        # print(f"処理対象行数: {len(lines)}")  # デバッグログ: 非表示
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            # print(f"処理中の行: {i + 1}")  # デバッグログ: 非表示
            
            if not line:
                i += 1
                continue
            
            # ヘッダー
            if line.startswith('#'):
                header_blocks = _process_header(line)
                blocks.extend(header_blocks)
            
            # リスト（箇条書きと番号）
            elif line.lstrip().startswith('- ') or line.lstrip().startswith('* ') or re.match(r'^\s*\d+\.', line):
                # print("リストを処理します")  # デバッグログ: 非表示
                list_items, new_i = process_list_items(lines, i)
                blocks.extend(list_items)
                if new_i <= i:
                    print(f"警告: リスト処理でインデックスが進みませんでした。強制的に次の行に進みます。")
                    i += 1
                else:
                    i = new_i
                continue
            
            # コードブロック
            elif line.startswith('```'):
                code_blocks, new_i = _process_code_block(lines, i)
                blocks.extend(code_blocks)
                i = new_i
                continue
            
            # 水平線
            elif line == '---' or line == '***' or line == '___':
                # print("水平線を処理します")  # デバッグログ: 非表示
                blocks.append({
                    "object": "block",
                    "type": "divider",
                    "divider": {}
                })
            
            # テーブル
            elif '|' in line and _is_valid_table_start(lines, i):
                table_blocks, new_i = _process_table(lines, i)
                blocks.extend(table_blocks)
                i = new_i
                continue
            
            # 通常のテキスト
            else:
                if line.strip():  # 空行でない場合のみ処理
                    paragraph_blocks = _process_paragraph(line)
                    blocks.extend(paragraph_blocks)
            
            i += 1
        
        # print("すべての行の処理が完了しました")  # デバッグログ: 非表示
        
        # 最終的なブロックバリデーション
        valid_blocks = []
        for i, block in enumerate(blocks):
            if validate_notion_block(block):
                valid_blocks.append(block)
            else:
                print(f"無効なブロックをスキップしました (インデックス: {i})")
                print(f"ブロック内容: {json.dumps(block, indent=2, ensure_ascii=False)}")
        
        # print(f"有効なブロック数: {len(valid_blocks)}")  # デバッグログ: 非表示
        
        # デバッグ: 最初の20個のブロックの構造を確認
        # print("=== デバッグ: 最初の20個のブロック構造 ===")  # デバッグログ: 非表示
        # for i, block in enumerate(valid_blocks[:20]):  # デバッグログ: 非表示
        #     print(f"Block {i}: type={block.get('type', 'UNKNOWN')}, keys={list(block.keys())}")  # デバッグログ: 非表示
        
        return valid_blocks
    except Exception as e:
        print(f"Markdownの変換中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        raise

def parse_inline_formatting(text: str) -> Dict[str, Any]:
    # イタリック、太字、リンクの処理
    formatted_text = {
        "type": "text",
        "text": {"content": text},
        "annotations": {
            "bold": False,
            "italic": False,
            "strikethrough": False,
            "underline": False,
            "code": False,
            "color": "default"
        }
    }
    
    # 太字
    bold_pattern = r'\*\*(.*?)\*\*'
    if re.search(bold_pattern, text):
        formatted_text["annotations"]["bold"] = True
        text = re.sub(bold_pattern, r'\1', text)
    
    # イタリック
    italic_pattern = r'\*(.*?)\*'
    if re.search(italic_pattern, text):
        formatted_text["annotations"]["italic"] = True
        text = re.sub(italic_pattern, r'\1', text)
    
    # リンク
    link_pattern = r'\[(.*?)\]\((.*?)\)'
    match = re.search(link_pattern, text)
    if match:
        link_text, url = match.groups()
        # URLがhttpまたはhttpsで始まる場合のみ検証
        if re.match(r"https?://", url):
            if not re.match(r"https?://", url):
                raise ValueError(f"Invalid URL: {url}")
            formatted_text["text"]["content"] = link_text
            formatted_text["text"]["link"] = {"url": url}
            text = re.sub(link_pattern, link_text, text)
    
    formatted_text["text"]["content"] = text
    return formatted_text

def process_table(table_rows: List[str]) -> Dict[str, Any]:
    if len(table_rows) < 3:
        print("テーブル行数が不足しています")
        return None  # テーブルには少なくともヘッダー行、区切り行、データ行が必要

    try:
        # ヘッダー行の処理
        header = [cell.strip() for cell in table_rows[0].split('|')[1:-1] if cell.strip()]
        if not header:
            print("ヘッダーが空です")
            return None
        
        # データ行の処理
        rows = []
        for row in table_rows[2:]:
            cells = [cell.strip() for cell in row.split('|')[1:-1] if cell.strip()]
            if cells:  # 空でない行のみ追加
                rows.append(cells)
        
        if not rows:
            print("データ行がありません")
            return None
        
        # Notionのテーブルはtable本体とtable_rowブロックを別々に送るのが安全
        row_blocks = []
        # ヘッダー行
        row_blocks.append({
            "object": "block",
            "type": "table_row",
            "table_row": {
                "cells": [[{"type": "text", "text": {"content": cell}}] for cell in header]
            }
        })
        # データ行
        for row in rows:
            while len(row) < len(header):
                row.append("")
            row = row[:len(header)]
            row_blocks.append({
                "object": "block",
                "type": "table_row",
                "table_row": {
                    "cells": [[{"type": "text", "text": {"content": cell}}] for cell in row]
                }
            })

        # テーブル本体（childrenに行を含める必要あり）
        table_block = {
            "object": "block",
            "type": "table",
            "table": {
                "table_width": len(header),
                "has_column_header": True,
                "has_row_header": False,
                "children": row_blocks
            }
        }

        return table_block
    except Exception as e:
        print(f"テーブル処理エラー: {e}")
        return None

def validate_notion_block(block: Dict[str, Any]) -> bool:
    """Notionブロックの構造が正しいかチェック"""
    if not isinstance(block, dict):
        return False
    
    if "object" not in block or block["object"] != "block":
        return False
    
    if "type" not in block:
        return False
    
    block_type = block["type"]
    
    # 各ブロックタイプに対応するプロパティが存在するかチェック
    required_properties = {
        "paragraph": "paragraph",
        "heading_1": "heading_1",
        "heading_2": "heading_2", 
        "heading_3": "heading_3",
        "bulleted_list_item": "bulleted_list_item",
        "numbered_list_item": "numbered_list_item",
        "code": "code",
        "quote": "quote",
        "divider": "divider",
        "table": "table",
        "table_row": "table_row"
    }
    
    if block_type in required_properties:
        required_prop = required_properties[block_type]
        if required_prop not in block:
            print(f"ブロックタイプ {block_type} に必要なプロパティ {required_prop} がありません")
            return False
    
    return True

def process_list_items(lines: List[str], start_index: int) -> Tuple[List[Dict[str, Any]], int]:
    print(f"process_list_items 関数を開始します。開始インデックス: {start_index}")
    list_items = []
    current_indent = 0
    stack = []
    i = start_index

    while i < len(lines):
        line = lines[i].rstrip()
        print(f"  処理中のリスト行: {i + 1}")
        if not line or (not line.lstrip().startswith('- ') and not line.lstrip().startswith('* ') and not re.match(r'^\s*\d+\.', line)):
            break

        indent = len(line) - len(line.lstrip())
        is_numbered = re.match(r'^\s*\d+\.', line)
        content = line.lstrip('- *').lstrip()
        if is_numbered:
            content = re.sub(r'^\d+\.\s*', '', content)
            list_type = "numbered_list_item"
        else:
            list_type = "bulleted_list_item"

        item = {
            "object": "block",
            "type": list_type,
            list_type: {
                "rich_text": [parse_inline_formatting(content)]
            }
        }

        if indent > current_indent:
            # 親が存在しないのにネストしている場合はフラット化
            if list_items:
                stack.append(list_items[-1])
            # 親のない先頭ネストはトップ扱い
            current_indent = indent
        elif indent < current_indent:
            # インデントを戻す。詳細な段数は保持していないため安全側で一気に合わせる
            while stack and indent <= current_indent:
                stack.pop()
            current_indent = indent

        if stack:
            parent = stack[-1]
            if "children" not in parent[parent["type"]]:
                parent[parent["type"]]["children"] = []
            parent[parent["type"]]["children"].append(item)
        else:
            list_items.append(item)

        i += 1

    print(f"process_list_items 関数を終了します。終了インデックス: {i}")
    return list_items, i

def main():
    if len(sys.argv) != 2:
        print("使用方法: python markdown_converter.py <markdown_file>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            markdown_content = file.read()
        
        blocks = convert_markdown_to_notion_blocks(markdown_content)
        print(json.dumps(blocks, indent=2, ensure_ascii=False))
    except FileNotFoundError:
        print(f"エラー: ファイル '{file_path}' が見つかりません。")
        sys.exit(1)
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()