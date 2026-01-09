#!/usr/bin/env python3
"""
post_to_wp.py のユニットテスト
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime, date
from pathlib import Path
from unittest.mock import patch, MagicMock

# テスト対象のモジュールをインポートするためにパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from post_to_wp import (
    extract_title,
    convert_markdown_to_html,
    load_config,
    parse_front_matter,
    move_jsonld_to_end,
    is_html_file,
    is_markdown_file,
    normalize_date_for_wp,
    remove_heading_matching_title,
    get_category_id,
    get_tag_id,
    resolve_category_ids,
    resolve_tag_ids,
    find_local_images,
    find_existing_media,
    is_supported_image_format,
)


class TestExtractTitle(unittest.TestCase):
    """extract_title() 関数のテスト"""

    def test_extract_h1_title(self):
        """H1見出しからタイトルを抽出できる"""
        content = "# テストタイトル\n\n本文の内容です。"
        title, body = extract_title(content, "test.md")
        
        self.assertEqual(title, "テストタイトル")
        self.assertEqual(body.strip(), "本文の内容です。")

    def test_extract_h2_title_when_no_h1(self):
        """H1がない場合、H2からタイトルを抽出できる"""
        content = "## サブタイトル\n\n本文の内容です。"
        title, body = extract_title(content, "test.md")
        
        self.assertEqual(title, "サブタイトル")
        self.assertEqual(body.strip(), "本文の内容です。")

    def test_extract_title_from_filename(self):
        """見出しがない場合、ファイル名からタイトルを生成"""
        content = "本文だけの内容です。"
        title, body = extract_title(content, "my_article.md")
        
        self.assertEqual(title, "my_article")
        self.assertEqual(body.strip(), "本文だけの内容です。")

    def test_h1_priority_over_h2(self):
        """H1がH2より優先される"""
        content = "## H2タイトル\n\n# H1タイトル\n\n本文"
        title, body = extract_title(content, "test.md")
        
        # H2が先にあってもH1を探す（実装に依存）
        # 現在の実装では最初に見つかったH1を使用
        self.assertEqual(title, "H1タイトル")

    def test_title_with_special_characters(self):
        """特殊文字を含むタイトルを正しく抽出"""
        content = "# タイトル【重要】& 特殊文字！\n\n本文"
        title, body = extract_title(content, "test.md")
        
        self.assertEqual(title, "タイトル【重要】& 特殊文字！")

    def test_empty_content(self):
        """空のコンテンツからファイル名をタイトルとして使用"""
        content = ""
        title, body = extract_title(content, "empty_file.md")
        
        self.assertEqual(title, "empty_file")
        self.assertEqual(body, "")

    def test_title_line_removed_from_body(self):
        """タイトル行が本文から除去される"""
        content = "# タイトル\n\n## セクション1\n\n内容"
        title, body = extract_title(content, "test.md")
        
        self.assertEqual(title, "タイトル")
        self.assertNotIn("# タイトル", body)
        self.assertIn("## セクション1", body)


class TestConvertMarkdownToHtml(unittest.TestCase):
    """convert_markdown_to_html() 関数のテスト"""

    def test_basic_paragraph(self):
        """基本的な段落を変換"""
        markdown = "これはテストです。"
        html = convert_markdown_to_html(markdown)
        
        self.assertIn("<p>", html)
        self.assertIn("これはテストです。", html)

    def test_heading_conversion(self):
        """見出しを変換"""
        markdown = "## 見出し2\n\n### 見出し3"
        html = convert_markdown_to_html(markdown)
        
        self.assertIn("<h2", html)
        self.assertIn("見出し2", html)
        self.assertIn("<h3", html)
        self.assertIn("見出し3", html)

    def test_fenced_code_block(self):
        """フェンス付きコードブロックを変換"""
        markdown = "```python\nprint('Hello')\n```"
        html = convert_markdown_to_html(markdown)
        
        self.assertIn("<code", html)
        self.assertIn("print", html)

    def test_table_conversion(self):
        """テーブルを変換"""
        markdown = """
| 列1 | 列2 |
|-----|-----|
| A   | B   |
"""
        html = convert_markdown_to_html(markdown)
        
        self.assertIn("<table>", html)
        self.assertIn("<th>", html)
        self.assertIn("<td>", html)

    def test_bold_and_italic(self):
        """太字と斜体を変換"""
        markdown = "**太字** と *斜体*"
        html = convert_markdown_to_html(markdown)
        
        self.assertIn("<strong>", html)
        self.assertIn("<em>", html)

    def test_unordered_list(self):
        """番号なしリストを変換"""
        markdown = "- 項目1\n- 項目2\n- 項目3"
        html = convert_markdown_to_html(markdown)
        
        self.assertIn("<ul>", html)
        self.assertIn("<li>", html)

    def test_ordered_list(self):
        """番号付きリストを変換"""
        markdown = "1. 項目1\n2. 項目2\n3. 項目3"
        html = convert_markdown_to_html(markdown)
        
        self.assertIn("<ol>", html)
        self.assertIn("<li>", html)

    def test_link_conversion(self):
        """リンクを変換"""
        markdown = "[リンクテキスト](https://example.com)"
        html = convert_markdown_to_html(markdown)
        
        self.assertIn("<a ", html)
        self.assertIn('href="https://example.com"', html)
        self.assertIn("リンクテキスト", html)

    def test_image_conversion(self):
        """画像を変換"""
        markdown = "![代替テキスト](image.png)"
        html = convert_markdown_to_html(markdown)
        
        self.assertIn("<img", html)
        self.assertIn('src="image.png"', html)


class TestLoadConfig(unittest.TestCase):
    """load_config() 関数のテスト"""

    def test_load_config_success(self):
        """正常に設定を読み込める"""
        env_vars = {
            'WP_URL': 'https://example.com',
            'WP_USER': 'testuser',
            'WP_APP_PASSWORD': 'test password',
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            with patch('post_to_wp.load_dotenv'):
                config = load_config()
        
        self.assertEqual(config['WP_URL'], 'https://example.com')
        self.assertEqual(config['WP_USER'], 'testuser')
        self.assertEqual(config['WP_APP_PASSWORD'], 'test password')

    def test_load_config_strips_trailing_slash(self):
        """URLの末尾スラッシュが除去される"""
        env_vars = {
            'WP_URL': 'https://example.com/',
            'WP_USER': 'testuser',
            'WP_APP_PASSWORD': 'test password',
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            with patch('post_to_wp.load_dotenv'):
                config = load_config()
        
        self.assertEqual(config['WP_URL'], 'https://example.com')

    def test_load_config_missing_keys(self):
        """必須キーが不足している場合にSystemExit"""
        env_vars = {
            'WP_URL': 'https://example.com',
            # WP_USER と WP_APP_PASSWORD が不足
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with patch('post_to_wp.load_dotenv'):
                with self.assertRaises(SystemExit):
                    load_config()


class TestParseFrontMatter(unittest.TestCase):
    """parse_front_matter() 関数のテスト"""

    def test_parse_front_matter_basic(self):
        """基本的なFront Matterを解析"""
        content = """---
title: テストタイトル
categories:
  - カテゴリ1
  - カテゴリ2
tags:
  - タグ1
slug: test-slug
---

本文の内容"""
        
        metadata, body = parse_front_matter(content)
        
        self.assertEqual(metadata['title'], 'テストタイトル')
        self.assertEqual(metadata['categories'], ['カテゴリ1', 'カテゴリ2'])
        self.assertEqual(metadata['tags'], ['タグ1'])
        self.assertEqual(metadata['slug'], 'test-slug')
        self.assertIn('本文の内容', body)

    def test_parse_front_matter_no_front_matter(self):
        """Front Matterがない場合"""
        content = "# タイトル\n\n本文の内容"
        
        metadata, body = parse_front_matter(content)
        
        self.assertEqual(metadata, {})
        self.assertEqual(body, content)

    def test_parse_front_matter_with_date(self):
        """日付を含むFront Matterを解析"""
        content = """---
title: テスト
date: 2024-01-15T12:00:00
---

本文"""
        
        metadata, body = parse_front_matter(content)
        
        self.assertEqual(metadata['title'], 'テスト')
        self.assertIn('date', metadata)

    def test_parse_front_matter_with_excerpt(self):
        """抜粋を含むFront Matterを解析"""
        content = """---
title: テスト
excerpt: これは記事の抜粋です。
---

本文"""
        
        metadata, body = parse_front_matter(content)
        
        self.assertEqual(metadata['excerpt'], 'これは記事の抜粋です。')


class TestMoveJsonldToEnd(unittest.TestCase):
    """move_jsonld_to_end() 関数のテスト"""

    def test_move_jsonld_to_end(self):
        """JSON-LDスクリプトを末尾に移動"""
        html = """<p>本文</p>
<script type="application/ld+json">
{"@context": "https://schema.org"}
</script>
<p>続き</p>"""
        
        result = move_jsonld_to_end(html)
        
        # JSON-LDが末尾にある
        self.assertTrue(result.strip().endswith('</script>'))
        # 本文の順序が保たれている
        self.assertIn('<p>本文</p>', result)
        self.assertIn('<p>続き</p>', result)

    def test_no_jsonld(self):
        """JSON-LDがない場合は変更なし"""
        html = "<p>本文</p><p>続き</p>"
        
        result = move_jsonld_to_end(html)
        
        self.assertEqual(result, html)

    def test_multiple_jsonld_scripts(self):
        """複数のJSON-LDスクリプトを処理"""
        html = """<p>本文</p>
<script type="application/ld+json">{"@type": "Article"}</script>
<p>続き</p>
<script type="application/ld+json">{"@type": "Organization"}</script>"""
        
        result = move_jsonld_to_end(html)
        
        # 両方のJSON-LDが含まれる
        self.assertIn('Article', result)
        self.assertIn('Organization', result)


class TestNormalizeDateForWp(unittest.TestCase):
    """normalize_date_for_wp() 関数のテスト"""

    def test_normalize_datetime(self):
        """datetimeをISO 8601に変換"""
        value = datetime(2024, 1, 15, 12, 30, 5, 123456)
        self.assertEqual(normalize_date_for_wp(value), "2024-01-15T12:30:05")

    def test_normalize_date(self):
        """dateをISO形式に変換"""
        value = date(2024, 1, 15)
        self.assertEqual(normalize_date_for_wp(value), "2024-01-15")

    def test_normalize_string(self):
        """文字列はそのまま返す"""
        value = "2024-01-15T12:00:00"
        self.assertEqual(normalize_date_for_wp(value), value)

    def test_normalize_none(self):
        """NoneはNoneのまま"""
        self.assertIsNone(normalize_date_for_wp(None))


class TestRemoveHeadingMatchingTitle(unittest.TestCase):
    """remove_heading_matching_title() 関数のテスト"""

    def test_remove_h1_matching_title(self):
        """H1がタイトルと一致する場合に除去"""
        content = "# タイトル\n\n本文"
        result = remove_heading_matching_title(content, "タイトル")
        self.assertEqual(result.strip(), "本文")

    def test_remove_h2_matching_title(self):
        """H2がタイトルと一致する場合に除去"""
        content = "## タイトル\n\n本文"
        result = remove_heading_matching_title(content, "タイトル")
        self.assertEqual(result.strip(), "本文")

    def test_no_change_when_not_matching(self):
        """タイトルが一致しない場合は変更しない"""
        content = "# 別タイトル\n\n本文"
        result = remove_heading_matching_title(content, "タイトル")
        self.assertEqual(result, content)


class TestFileTypeDetection(unittest.TestCase):
    """is_html_file(), is_markdown_file() 関数のテスト"""

    def test_is_html_file(self):
        """HTMLファイルを正しく判定"""
        self.assertTrue(is_html_file("test.html"))
        self.assertTrue(is_html_file("test.HTML"))
        self.assertTrue(is_html_file("test.htm"))
        self.assertTrue(is_html_file("path/to/file.html"))
        
        self.assertFalse(is_html_file("test.md"))
        self.assertFalse(is_html_file("test.txt"))

    def test_is_markdown_file(self):
        """Markdownファイルを正しく判定"""
        self.assertTrue(is_markdown_file("test.md"))
        self.assertTrue(is_markdown_file("test.MD"))
        self.assertTrue(is_markdown_file("test.markdown"))
        self.assertTrue(is_markdown_file("path/to/file.md"))
        
        self.assertFalse(is_markdown_file("test.html"))
        self.assertFalse(is_markdown_file("test.txt"))


class TestMoveJsonldToEndExtended(unittest.TestCase):
    """move_jsonld_to_end() 関数の拡張テスト（修正1の検証）"""

    def test_jsonld_with_id_attribute(self):
        """type属性が先頭でないJSON-LDを検出"""
        html = """<p>本文</p>
<script id="schema" type="application/ld+json">
{"@context": "https://schema.org"}
</script>
<p>続き</p>"""

        result = move_jsonld_to_end(html)

        self.assertTrue(result.strip().endswith('</script>'))
        self.assertIn('<p>本文</p>', result)
        self.assertIn('<p>続き</p>', result)

    def test_jsonld_with_multiple_attributes(self):
        """複数属性を持つscriptタグのJSON-LD"""
        html = """<script id="ld" class="structured-data" type="application/ld+json">
{"@type": "Article"}
</script>
<p>本文</p>"""

        result = move_jsonld_to_end(html)

        self.assertTrue(result.strip().endswith('</script>'))
        self.assertIn('<p>本文</p>', result)

    def test_jsonld_with_data_attribute(self):
        """data-*属性を持つJSON-LD"""
        html = """<p>本文</p>
<script data-schema="main" type="application/ld+json">
{"@type": "WebPage"}
</script>"""

        result = move_jsonld_to_end(html)

        self.assertTrue(result.strip().endswith('</script>'))


class TestParseFrontMatterExtended(unittest.TestCase):
    """parse_front_matter() 関数の拡張テスト（修正3の検証）"""

    def test_parse_front_matter_with_bom(self):
        """BOM付きファイルのFront Matterを解析"""
        content = "\ufeff---\ntitle: テスト\n---\n\n本文"
        metadata, body = parse_front_matter(content)

        self.assertEqual(metadata['title'], 'テスト')
        self.assertIn('本文', body)

    def test_parse_front_matter_with_leading_newline(self):
        """先頭空行があるFront Matterを解析"""
        content = "\n\n---\ntitle: テスト\n---\n\n本文"
        metadata, body = parse_front_matter(content)

        self.assertEqual(metadata['title'], 'テスト')
        self.assertIn('本文', body)

    def test_parse_front_matter_with_leading_spaces(self):
        """先頭スペースがあるFront Matterを解析"""
        content = "   ---\ntitle: テスト\n---\n\n本文"
        metadata, body = parse_front_matter(content)

        self.assertEqual(metadata['title'], 'テスト')
        self.assertIn('本文', body)


class TestCategoryResolution(unittest.TestCase):
    """カテゴリID解決のテスト"""

    @patch('post_to_wp.requests.get')
    def test_get_category_id_found(self, mock_get):
        """既存カテゴリのIDを取得"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {'id': 5, 'name': 'テストカテゴリ', 'slug': 'test-category'}
        ]
        mock_get.return_value = mock_response

        config = {'WP_URL': 'https://example.com', 'WP_USER': 'user', 'WP_APP_PASSWORD': 'pass'}
        result = get_category_id(config, 'テストカテゴリ')

        self.assertEqual(result, 5)

    @patch('post_to_wp.requests.get')
    def test_get_category_id_not_found(self, mock_get):
        """存在しないカテゴリの場合はNone"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        config = {'WP_URL': 'https://example.com', 'WP_USER': 'user', 'WP_APP_PASSWORD': 'pass'}
        result = get_category_id(config, '存在しないカテゴリ')

        self.assertIsNone(result)

    @patch('post_to_wp.requests.get')
    @patch('post_to_wp.requests.post')
    def test_get_category_id_create_if_not_exists(self, mock_post, mock_get):
        """存在しないカテゴリを自動作成"""
        # GET: カテゴリが見つからない
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = []
        mock_get.return_value = mock_get_response

        # POST: カテゴリを作成
        mock_post_response = MagicMock()
        mock_post_response.status_code = 201
        mock_post_response.json.return_value = {'id': 10}
        mock_post.return_value = mock_post_response

        config = {'WP_URL': 'https://example.com', 'WP_USER': 'user', 'WP_APP_PASSWORD': 'pass'}
        result = get_category_id(config, '新カテゴリ', create_if_not_exists=True)

        self.assertEqual(result, 10)

    @patch('post_to_wp.get_category_id')
    def test_resolve_category_ids(self, mock_get_category_id):
        """複数カテゴリのID解決"""
        mock_get_category_id.side_effect = [1, 2, None]  # 3番目は見つからない

        config = {'WP_URL': 'https://example.com', 'WP_USER': 'user', 'WP_APP_PASSWORD': 'pass'}
        result = resolve_category_ids(config, ['カテゴリ1', 'カテゴリ2', 'カテゴリ3'])

        self.assertEqual(result, [1, 2])


class TestTagResolution(unittest.TestCase):
    """タグID解決のテスト"""

    @patch('post_to_wp.requests.get')
    def test_get_tag_id_found(self, mock_get):
        """既存タグのIDを取得"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {'id': 15, 'name': 'テストタグ', 'slug': 'test-tag'}
        ]
        mock_get.return_value = mock_response

        config = {'WP_URL': 'https://example.com', 'WP_USER': 'user', 'WP_APP_PASSWORD': 'pass'}
        result = get_tag_id(config, 'テストタグ')

        self.assertEqual(result, 15)

    @patch('post_to_wp.get_tag_id')
    def test_resolve_tag_ids(self, mock_get_tag_id):
        """複数タグのID解決"""
        mock_get_tag_id.side_effect = [10, 20]

        config = {'WP_URL': 'https://example.com', 'WP_USER': 'user', 'WP_APP_PASSWORD': 'pass'}
        result = resolve_tag_ids(config, ['タグ1', 'タグ2'])

        self.assertEqual(result, [10, 20])


class TestImageProcessing(unittest.TestCase):
    """画像処理のテスト"""

    def test_find_local_images_markdown(self):
        """Markdownからローカル画像を検出（実ファイル使用）"""
        # 一時ディレクトリを作成して画像ファイルも作成
        with tempfile.TemporaryDirectory() as tmpdir:
            # テスト用画像ファイルを作成
            images_dir = Path(tmpdir) / 'images'
            images_dir.mkdir()
            (images_dir / 'test.png').write_bytes(b'PNG fake content')

            md_file = Path(tmpdir) / 'article.md'
            content = """
本文です。
![代替テキスト](./images/test.png)
![外部画像](https://example.com/image.png)
"""
            md_file.write_text(content)

            images = find_local_images(content, str(md_file))
            # 外部URLは除外され、存在するローカル画像のみ検出される
            local_paths = [img['original'] for img in images]
            self.assertEqual(len(local_paths), 1)
            self.assertTrue(any('test.png' in p for p in local_paths))

    def test_find_local_images_html(self):
        """HTMLからローカル画像を検出（実ファイル使用）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # テスト用画像ファイルを作成
            images_dir = Path(tmpdir) / 'images'
            images_dir.mkdir()
            (images_dir / 'test.png').write_bytes(b'PNG fake content')

            html_file = Path(tmpdir) / 'article.html'
            content = """
<p>本文</p>
<img src="./images/test.png" alt="テスト">
<img src="https://example.com/image.png">
"""
            html_file.write_text(content)

            images = find_local_images(content, str(html_file))
            local_paths = [img['original'] for img in images]
            self.assertEqual(len(local_paths), 1)
            self.assertTrue(any('test.png' in p for p in local_paths))

    def test_is_supported_image_format(self):
        """サポートされている画像形式の判定"""
        self.assertTrue(is_supported_image_format('test.jpg'))
        self.assertTrue(is_supported_image_format('test.jpeg'))
        self.assertTrue(is_supported_image_format('test.png'))
        self.assertTrue(is_supported_image_format('test.gif'))
        self.assertTrue(is_supported_image_format('test.webp'))
        self.assertTrue(is_supported_image_format('test.PNG'))  # 大文字

        self.assertFalse(is_supported_image_format('test.svg'))
        self.assertFalse(is_supported_image_format('test.bmp'))
        self.assertFalse(is_supported_image_format('test.pdf'))

    @patch('post_to_wp.requests.get')
    def test_find_existing_media_found(self, mock_get):
        """既存メディアの検索（見つかった場合）"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                'id': 100,
                'source_url': 'https://example.com/wp-content/uploads/2024/01/test.png',
                'media_details': {'file': '2024/01/test.png', 'filesize': 12345}
            }
        ]
        mock_get.return_value = mock_response

        config = {'WP_URL': 'https://example.com', 'WP_USER': 'user', 'WP_APP_PASSWORD': 'pass'}
        result = find_existing_media(config, 'test.png')

        self.assertIsNotNone(result)
        self.assertEqual(result['id'], 100)

    @patch('post_to_wp.requests.get')
    def test_find_existing_media_not_found(self, mock_get):
        """既存メディアの検索（見つからない場合）"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        config = {'WP_URL': 'https://example.com', 'WP_USER': 'user', 'WP_APP_PASSWORD': 'pass'}
        result = find_existing_media(config, 'nonexistent.png')

        self.assertIsNone(result)

    @patch('post_to_wp.requests.get')
    def test_find_existing_media_size_mismatch(self, mock_get):
        """ファイルサイズ不一致時は既存メディアを使用しない"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                'id': 100,
                'source_url': 'https://example.com/wp-content/uploads/test.png',
                'media_details': {'file': 'test.png', 'filesize': 99999}  # 異なるサイズ
            }
        ]
        mock_get.return_value = mock_response

        # 一時ファイルを作成（サイズが異なる）
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            f.write(b'small content')  # 13 bytes
            temp_path = f.name

        try:
            config = {'WP_URL': 'https://example.com', 'WP_USER': 'user', 'WP_APP_PASSWORD': 'pass'}
            result = find_existing_media(config, 'test.png', temp_path)

            # サイズ不一致のため None が返される
            self.assertIsNone(result)
        finally:
            os.unlink(temp_path)


if __name__ == '__main__':
    unittest.main()
