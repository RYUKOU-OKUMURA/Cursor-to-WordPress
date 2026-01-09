#!/usr/bin/env python3
"""
Cursor → WordPress 自動投稿ツール

MarkdownファイルをWordPressに投稿するCLIツール。
"""

import argparse
import logging
import mimetypes
import os
import re
import sys
import traceback
from datetime import datetime, date
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, List

import markdown2
import requests
import yaml
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv


# MIMEタイプの初期化
mimetypes.init()


# =============================================================================
# Phase 1-10: ロギング機能
# =============================================================================

# ロガーの設定
logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """
    ロギングを設定する。
    
    Args:
        verbose: Trueの場合、DEBUGレベルで出力
    """
    level = logging.DEBUG if verbose else logging.INFO
    format_str = '%(asctime)s - %(levelname)s - %(message)s' if verbose else '%(message)s'
    
    logging.basicConfig(
        level=level,
        format=format_str,
        handlers=[logging.StreamHandler(sys.stdout)]
    )


# =============================================================================
# Phase 1-3: 設定読み込み
# =============================================================================

def load_config() -> dict:
    """
    .envファイルから設定を読み込む。
    
    Returns:
        dict: 設定値の辞書（WP_URL, WP_USER, WP_APP_PASSWORD）
    
    Raises:
        SystemExit: 必須キーが不足している場合
    """
    # .envファイルを読み込む
    load_dotenv()
    
    # 必須キーの定義
    required_keys = ['WP_URL', 'WP_USER', 'WP_APP_PASSWORD']
    
    config = {}
    missing_keys = []
    
    for key in required_keys:
        value = os.getenv(key)
        if value is None or value.strip() == '':
            missing_keys.append(key)
        else:
            config[key] = value.strip()
    
    # 必須キーが不足している場合はエラー
    if missing_keys:
        logger.error("以下の環境変数が設定されていません:")
        for key in missing_keys:
            logger.error(f"  - {key}")
        logger.error("\n.env ファイルを作成し、必要な値を設定してください。")
        logger.error("テンプレートは .env.example を参照してください。")
        sys.exit(1)
    
    # WP_URLの末尾スラッシュを除去
    config['WP_URL'] = config['WP_URL'].rstrip('/')
    
    # HTTPS警告チェック
    if not config['WP_URL'].startswith('https://'):
        logger.warning("警告: HTTPSではないURLが指定されています。セキュリティ上、HTTPSの使用を推奨します。")
    
    logger.debug(f"設定読み込み完了: WP_URL={config['WP_URL']}, WP_USER={config['WP_USER']}")
    
    return config


# =============================================================================
# Phase 1-4: ファイル読み込み
# =============================================================================

def read_markdown_file(file_path: str) -> str:
    """
    Markdownファイルを読み込む。
    
    Args:
        file_path: 読み込むファイルのパス
    
    Returns:
        str: ファイルの内容
    
    Raises:
        SystemExit: ファイルが存在しない、または読み取れない場合
    """
    path = Path(file_path)
    
    # ファイル存在チェック
    if not path.exists():
        logger.error(f"ファイルが見つかりません: {file_path}")
        sys.exit(1)
    
    # ファイルかどうかチェック
    if not path.is_file():
        logger.error(f"指定されたパスはファイルではありません: {file_path}")
        sys.exit(1)
    
    # 読み取り権限チェック
    if not os.access(path, os.R_OK):
        logger.error(f"ファイルの読み取り権限がありません: {file_path}")
        sys.exit(1)
    
    # UTF-8でファイルを読み込む
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        logger.debug(f"ファイル読み込み完了: {file_path} ({len(content)} 文字)")
        return content
    except UnicodeDecodeError:
        logger.error(f"ファイルがUTF-8形式ではありません: {file_path}")
        sys.exit(1)
    except IOError as e:
        logger.error(f"ファイルの読み込みに失敗しました: {e}")
        sys.exit(1)


# =============================================================================
# Phase 1-5: タイトル抽出
# =============================================================================

def extract_title(content: str, file_path: str) -> Tuple[str, str]:
    """
    Markdownコンテンツからタイトルを抽出する。
    
    抽出優先順:
    1. H1見出し（# タイトル）
    2. H2見出し（## タイトル）
    3. ファイル名（拡張子なし）
    
    Args:
        content: Markdownファイルの内容
        file_path: ファイルパス（フォールバック用）
    
    Returns:
        Tuple[str, str]: (タイトル, タイトル見出しを除去した本文)
    """
    lines = content.split('\n')
    title = None
    title_line_index = None
    
    # H1見出しを探す（# タイトル）
    h1_pattern = re.compile(r'^#\s+(.+)$')
    for i, line in enumerate(lines):
        match = h1_pattern.match(line.strip())
        if match:
            title = match.group(1).strip()
            title_line_index = i
            logger.debug(f"H1タイトルを検出: {title}")
            break
    
    # H1がなければH2を探す（## タイトル）
    if title is None:
        h2_pattern = re.compile(r'^##\s+(.+)$')
        for i, line in enumerate(lines):
            match = h2_pattern.match(line.strip())
            if match:
                title = match.group(1).strip()
                title_line_index = i
                logger.debug(f"H2タイトルを検出: {title}")
                break
    
    # 見出しが見つかった場合、本文から除去
    if title_line_index is not None:
        # タイトル行を除去
        new_lines = lines[:title_line_index] + lines[title_line_index + 1:]
        # 先頭の空行を除去
        while new_lines and new_lines[0].strip() == '':
            new_lines.pop(0)
        body = '\n'.join(new_lines)
    else:
        body = content
    
    # タイトルが見つからなければファイル名を使用
    if title is None:
        path = Path(file_path)
        title = path.stem  # 拡張子なしのファイル名
        logger.debug(f"ファイル名からタイトルを生成: {title}")
    
    return title, body


# =============================================================================
# Phase 1-6: Markdown→HTML変換
# =============================================================================

def convert_markdown_to_html(markdown_content: str) -> str:
    """
    MarkdownをHTMLに変換する。
    
    Args:
        markdown_content: Markdownテキスト
    
    Returns:
        str: 変換されたHTML
    """
    # markdown2のextras設定
    extras = [
        'fenced-code-blocks',  # ```で囲んだコードブロック
        'tables',              # テーブル
        'code-friendly',       # コード内のアンダースコアを保持
        'cuddled-lists',       # リストの前に空行不要
        'header-ids',          # 見出しにID付与
    ]
    
    html = markdown2.markdown(markdown_content, extras=extras)
    logger.debug(f"Markdown→HTML変換完了 ({len(markdown_content)} → {len(html)} 文字)")
    
    return html


# =============================================================================
# Phase 2-1: Front Matter対応
# =============================================================================

def parse_front_matter(content: str) -> Tuple[Dict[str, Any], str]:
    """
    Front Matterを解析して、メタデータと本文を分離する。
    
    Args:
        content: Markdownファイルの内容（Front Matterを含む可能性がある）
    
    Returns:
        Tuple[Dict[str, Any], str]: (メタデータ辞書, Front Matterを除いた本文)
    """
    metadata = {}
    body = content

    # BOMを除去（UTF-8 BOM: \ufeff）
    if content.startswith('\ufeff'):
        content = content[1:]
        body = content
        logger.debug("BOMを除去しました")

    # 先頭の空白文字を除去してからパターンマッチ
    stripped_content = content.lstrip()

    # Front Matterパターン: --- で始まり --- で終わるYAMLブロック
    front_matter_pattern = re.compile(
        r'^---\s*\n(.*?)\n---\s*\n',
        re.DOTALL
    )

    match = front_matter_pattern.match(stripped_content)
    if match:
        yaml_content = match.group(1)
        try:
            metadata = yaml.safe_load(yaml_content) or {}
            # 除去後のコンテンツから本文を取得
            body = stripped_content[match.end():]
            logger.debug(f"Front Matter検出: {list(metadata.keys())}")
        except yaml.YAMLError as e:
            logger.warning(f"Front Matterの解析に失敗しました: {e}")
            # 解析失敗時は元のコンテンツをそのまま返す
            metadata = {}
            body = content
    else:
        logger.debug("Front Matterは検出されませんでした")

    return metadata, body


def normalize_date_for_wp(value: Any) -> Optional[str]:
    """
    Front Matterの日時をWordPress向けの形式に正規化する。
    
    Args:
        value: Front Matterで指定された日時
    
    Returns:
        Optional[str]: 正規化済みの日時文字列（ISO 8601 など）
    """
    if value is None:
        return None
    
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat()
    
    if isinstance(value, date):
        return value.isoformat()
    
    value_str = str(value).strip()
    return value_str if value_str else None


def remove_heading_matching_title(content: str, title: str) -> str:
    """
    本文内のH1/H2がタイトルと一致する場合にその行を除去する。
    
    Args:
        content: 本文
        title: タイトル文字列
    
    Returns:
        str: タイトル見出しを除去した本文
    """
    if not title:
        return content
    
    lines = content.split('\n')
    title_line_index = None
    heading_pattern = re.compile(r'^(#{1,2})\s+(.+)$')
    
    for i, line in enumerate(lines):
        match = heading_pattern.match(line.strip())
        if match and match.group(2).strip() == title:
            title_line_index = i
            break
    
    if title_line_index is None:
        return content
    
    new_lines = lines[:title_line_index] + lines[title_line_index + 1:]
    while new_lines and new_lines[0].strip() == '':
        new_lines.pop(0)
    
    return '\n'.join(new_lines)


# =============================================================================
# Phase 2-2: カテゴリ/タグのID解決
# =============================================================================

def get_category_id(
    config: dict,
    category_name: str,
    create_if_not_exists: bool = False
) -> Optional[int]:
    """
    カテゴリ名からIDを取得する。
    
    Args:
        config: 設定辞書（WP_URL, WP_USER, WP_APP_PASSWORD）
        category_name: カテゴリ名
        create_if_not_exists: 存在しない場合に自動作成するか
    
    Returns:
        Optional[int]: カテゴリID（見つからない場合はNone）
    """
    endpoint = f"{config['WP_URL']}/wp-json/wp/v2/categories"
    
    try:
        # 名前で検索
        response = requests.get(
            endpoint,
            params={'search': category_name},
            auth=HTTPBasicAuth(config['WP_USER'], config['WP_APP_PASSWORD']),
            timeout=30
        )
        
        if response.status_code == 200:
            categories = response.json()
            # 完全一致するカテゴリを探す
            for cat in categories:
                if cat['name'].lower() == category_name.lower():
                    logger.debug(f"カテゴリ '{category_name}' のID: {cat['id']}")
                    return cat['id']
        
        # 見つからない場合
        if create_if_not_exists:
            return create_category(config, category_name)
        else:
            logger.warning(f"カテゴリ '{category_name}' が見つかりませんでした")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.warning(f"カテゴリ検索中にエラーが発生: {e}")
        return None


def create_category(config: dict, category_name: str) -> Optional[int]:
    """
    新しいカテゴリを作成する。
    
    Args:
        config: 設定辞書
        category_name: 作成するカテゴリ名
    
    Returns:
        Optional[int]: 作成されたカテゴリのID
    """
    endpoint = f"{config['WP_URL']}/wp-json/wp/v2/categories"
    
    try:
        response = requests.post(
            endpoint,
            auth=HTTPBasicAuth(config['WP_USER'], config['WP_APP_PASSWORD']),
            json={'name': category_name},
            timeout=30
        )
        
        if response.status_code == 201:
            cat_id = response.json()['id']
            logger.info(f"カテゴリ '{category_name}' を作成しました (ID: {cat_id})")
            return cat_id
        else:
            logger.warning(f"カテゴリ '{category_name}' の作成に失敗しました: {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.warning(f"カテゴリ作成中にエラーが発生: {e}")
        return None


def get_tag_id(
    config: dict,
    tag_name: str,
    create_if_not_exists: bool = False
) -> Optional[int]:
    """
    タグ名からIDを取得する。
    
    Args:
        config: 設定辞書（WP_URL, WP_USER, WP_APP_PASSWORD）
        tag_name: タグ名
        create_if_not_exists: 存在しない場合に自動作成するか
    
    Returns:
        Optional[int]: タグID（見つからない場合はNone）
    """
    endpoint = f"{config['WP_URL']}/wp-json/wp/v2/tags"
    
    try:
        # 名前で検索
        response = requests.get(
            endpoint,
            params={'search': tag_name},
            auth=HTTPBasicAuth(config['WP_USER'], config['WP_APP_PASSWORD']),
            timeout=30
        )
        
        if response.status_code == 200:
            tags = response.json()
            # 完全一致するタグを探す
            for tag in tags:
                if tag['name'].lower() == tag_name.lower():
                    logger.debug(f"タグ '{tag_name}' のID: {tag['id']}")
                    return tag['id']
        
        # 見つからない場合
        if create_if_not_exists:
            return create_tag(config, tag_name)
        else:
            logger.warning(f"タグ '{tag_name}' が見つかりませんでした")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.warning(f"タグ検索中にエラーが発生: {e}")
        return None


def create_tag(config: dict, tag_name: str) -> Optional[int]:
    """
    新しいタグを作成する。
    
    Args:
        config: 設定辞書
        tag_name: 作成するタグ名
    
    Returns:
        Optional[int]: 作成されたタグのID
    """
    endpoint = f"{config['WP_URL']}/wp-json/wp/v2/tags"
    
    try:
        response = requests.post(
            endpoint,
            auth=HTTPBasicAuth(config['WP_USER'], config['WP_APP_PASSWORD']),
            json={'name': tag_name},
            timeout=30
        )
        
        if response.status_code == 201:
            tag_id = response.json()['id']
            logger.info(f"タグ '{tag_name}' を作成しました (ID: {tag_id})")
            return tag_id
        else:
            logger.warning(f"タグ '{tag_name}' の作成に失敗しました: {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.warning(f"タグ作成中にエラーが発生: {e}")
        return None


def resolve_category_ids(
    config: dict,
    categories: List[str],
    create_if_not_exists: bool = False
) -> List[int]:
    """
    カテゴリ名のリストからIDのリストを取得する。
    
    Args:
        config: 設定辞書
        categories: カテゴリ名のリスト
        create_if_not_exists: 存在しない場合に自動作成するか
    
    Returns:
        List[int]: カテゴリIDのリスト
    """
    category_ids = []
    for cat_name in categories:
        cat_id = get_category_id(config, cat_name, create_if_not_exists)
        if cat_id is not None:
            category_ids.append(cat_id)
    return category_ids


def resolve_tag_ids(
    config: dict,
    tags: List[str],
    create_if_not_exists: bool = False
) -> List[int]:
    """
    タグ名のリストからIDのリストを取得する。
    
    Args:
        config: 設定辞書
        tags: タグ名のリスト
        create_if_not_exists: 存在しない場合に自動作成するか
    
    Returns:
        List[int]: タグIDのリスト
    """
    tag_ids = []
    for tag_name in tags:
        tag_id = get_tag_id(config, tag_name, create_if_not_exists)
        if tag_id is not None:
            tag_ids.append(tag_id)
    return tag_ids


# =============================================================================
# Phase 2-3: JSON-LD移動
# =============================================================================

def move_jsonld_to_end(html_content: str) -> str:
    """
    HTML内のJSON-LDスクリプトを末尾に移動する。
    
    Args:
        html_content: 元のHTMLコンテンツ
    
    Returns:
        str: JSON-LDを末尾に移動したHTML
    """
    # JSON-LDスクリプトを検出するパターン
    # type属性がどの位置にあっても検出できるよう柔軟なパターンを使用
    jsonld_pattern = re.compile(
        r'<script\s+[^>]*type=["\']application/ld\+json["\'][^>]*>.*?</script>',
        re.DOTALL | re.IGNORECASE
    )
    
    # すべてのJSON-LDスクリプトを抽出
    jsonld_scripts = jsonld_pattern.findall(html_content)
    
    if not jsonld_scripts:
        logger.debug("JSON-LDスクリプトは検出されませんでした")
        return html_content
    
    # JSON-LDスクリプトを本文から除去
    cleaned_html = jsonld_pattern.sub('', html_content)
    
    # 空行の重複を整理
    cleaned_html = re.sub(r'\n{3,}', '\n\n', cleaned_html)
    cleaned_html = cleaned_html.strip()
    
    # JSON-LDスクリプトを末尾に追加
    result = cleaned_html + '\n\n' + '\n'.join(jsonld_scripts)
    
    logger.debug(f"{len(jsonld_scripts)}個のJSON-LDスクリプトを末尾に移動しました")
    
    return result


# =============================================================================
# Phase 3-1: ローカル画像検出
# =============================================================================

def find_local_images(content: str, base_path: str) -> List[Dict[str, str]]:
    """
    Markdown/HTMLコンテンツからローカル画像を検出する。
    
    検出パターン:
    - Markdown: ![alt](path)
    - HTML: <img src="path">
    
    外部URL（http://, https://）は除外する。
    
    Args:
        content: Markdown/HTMLコンテンツ
        base_path: 画像パスの基準となるファイルパス
    
    Returns:
        List[Dict[str, str]]: 画像情報のリスト
        各要素は {'original': 元のパス, 'absolute': 絶対パス, 'alt': alt属性} を含む
    """
    images = []
    base_dir = Path(base_path).parent
    
    # Markdownの画像パターン: ![alt](path) または ![alt](path "title")
    md_pattern = re.compile(r'!\[([^\]]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
    
    # HTMLの画像パターン: <img ... src="path" ...>
    html_pattern = re.compile(
        r'<img\s+[^>]*src=["\']([^"\']+)["\'][^>]*>',
        re.IGNORECASE
    )
    
    # alt属性を抽出するパターン
    alt_pattern = re.compile(r'alt=["\']([^"\']*)["\']', re.IGNORECASE)
    
    # Markdownパターンで検索
    for match in md_pattern.finditer(content):
        alt_text = match.group(1)
        image_path = match.group(2)
        
        # 外部URLは除外
        if image_path.startswith(('http://', 'https://', '//')):
            logger.debug(f"外部URL画像をスキップ: {image_path}")
            continue
        
        # データURIは除外
        if image_path.startswith('data:'):
            logger.debug(f"データURI画像をスキップ")
            continue
        
        # 絶対パスまたは相対パスを解決
        if os.path.isabs(image_path):
            absolute_path = Path(image_path)
        else:
            absolute_path = (base_dir / image_path).resolve()
        
        # ファイルが存在するかチェック
        if absolute_path.exists() and absolute_path.is_file():
            images.append({
                'original': image_path,
                'absolute': str(absolute_path),
                'alt': alt_text or absolute_path.stem,
                'match': match.group(0)  # マッチした全体の文字列
            })
            logger.debug(f"ローカル画像を検出: {image_path} -> {absolute_path}")
        else:
            logger.warning(f"画像ファイルが見つかりません: {image_path} (解決先: {absolute_path})")
    
    # HTMLパターンで検索
    for match in html_pattern.finditer(content):
        image_path = match.group(1)
        full_tag = match.group(0)
        
        # 外部URLは除外
        if image_path.startswith(('http://', 'https://', '//')):
            logger.debug(f"外部URL画像をスキップ: {image_path}")
            continue
        
        # データURIは除外
        if image_path.startswith('data:'):
            logger.debug(f"データURI画像をスキップ")
            continue
        
        # すでにMarkdownパターンで検出済みかチェック（重複回避）
        if any(img['original'] == image_path for img in images):
            continue
        
        # alt属性を抽出
        alt_match = alt_pattern.search(full_tag)
        alt_text = alt_match.group(1) if alt_match else ''
        
        # 絶対パスまたは相対パスを解決
        if os.path.isabs(image_path):
            absolute_path = Path(image_path)
        else:
            absolute_path = (base_dir / image_path).resolve()
        
        # ファイルが存在するかチェック
        if absolute_path.exists() and absolute_path.is_file():
            images.append({
                'original': image_path,
                'absolute': str(absolute_path),
                'alt': alt_text or absolute_path.stem,
                'match': full_tag
            })
            logger.debug(f"ローカル画像を検出 (HTML): {image_path} -> {absolute_path}")
        else:
            logger.warning(f"画像ファイルが見つかりません: {image_path} (解決先: {absolute_path})")
    
    logger.info(f"ローカル画像を {len(images)} 件検出しました")
    return images


def get_mime_type(file_path: str) -> str:
    """
    ファイルのMIMEタイプを取得する。
    
    Args:
        file_path: ファイルパス
    
    Returns:
        str: MIMEタイプ
    """
    mime_type, _ = mimetypes.guess_type(file_path)
    
    if mime_type is None:
        # 拡張子から推測
        ext = Path(file_path).suffix.lower()
        mime_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.svg': 'image/svg+xml',
            '.bmp': 'image/bmp',
            '.ico': 'image/x-icon',
        }
        mime_type = mime_map.get(ext, 'application/octet-stream')
    
    return mime_type


def is_supported_image_format(file_path: str) -> bool:
    """
    サポートされている画像形式かどうかを判定する。
    
    Args:
        file_path: ファイルパス
    
    Returns:
        bool: サポートされている場合はTrue
    """
    supported_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    ext = Path(file_path).suffix.lower()
    return ext in supported_extensions


def find_existing_media(
    config: dict,
    file_name: str,
    local_file_path: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    既存のメディアから同名ファイルを検索する。
    ローカルファイルパスが指定された場合はファイルサイズも比較する。

    Args:
        config: 設定辞書
        file_name: 画像ファイル名
        local_file_path: ローカルファイルのパス（サイズ比較用）

    Returns:
        Optional[Dict[str, Any]]: 見つかった場合は {'id': ID, 'url': URL, 'filename': file_name}
    """
    endpoint = f"{config['WP_URL']}/wp-json/wp/v2/media"

    # ローカルファイルのサイズを取得
    local_file_size = None
    if local_file_path:
        local_path = Path(local_file_path)
        if local_path.exists():
            local_file_size = local_path.stat().st_size
            logger.debug(f"ローカルファイルサイズ: {local_file_size} bytes")

    try:
        response = requests.get(
            endpoint,
            params={'search': file_name, 'per_page': 100},
            auth=HTTPBasicAuth(config['WP_USER'], config['WP_APP_PASSWORD']),
            timeout=30
        )

        if response.status_code != 200:
            logger.debug(f"メディア検索失敗 [{response.status_code}]")
            return None

        file_name_lower = file_name.lower()

        for item in response.json():
            source_url = item.get('source_url') or ''
            media_file = (item.get('media_details') or {}).get('file') or ''

            if source_url.lower().endswith(file_name_lower) or media_file.lower().endswith(file_name_lower):
                # ファイルサイズの比較（ローカルファイルパスが指定されている場合）
                if local_file_size is not None:
                    media_details = item.get('media_details') or {}
                    remote_file_size = media_details.get('filesize')

                    if remote_file_size and remote_file_size != local_file_size:
                        logger.debug(
                            f"ファイルサイズ不一致: ローカル={local_file_size}, "
                            f"リモート={remote_file_size} - スキップして次を検索"
                        )
                        continue  # サイズが異なる場合は次のメディアをチェック

                return {
                    'id': item.get('id'),
                    'url': source_url,
                    'filename': file_name
                }

        return None

    except requests.exceptions.RequestException as e:
        logger.debug(f"メディア検索中にエラー: {e}")
        return None


# =============================================================================
# Phase 3-2: メディアアップロード
# =============================================================================

def upload_image(
    config: dict,
    image_path: str,
    alt_text: str = ''
) -> Optional[Dict[str, Any]]:
    """
    画像をWordPressメディアライブラリにアップロードする。
    
    Args:
        config: 設定辞書（WP_URL, WP_USER, WP_APP_PASSWORD）
        image_path: アップロードする画像のローカルパス
        alt_text: 画像のalt属性テキスト
    
    Returns:
        Optional[Dict[str, Any]]: アップロード成功時は {'id': メディアID, 'url': URL}
                                  失敗時は None
    """
    endpoint = f"{config['WP_URL']}/wp-json/wp/v2/media"
    
    # ファイル存在チェック
    path = Path(image_path)
    if not path.exists():
        logger.error(f"画像ファイルが見つかりません: {image_path}")
        return None
    
    # サポート形式チェック
    if not is_supported_image_format(image_path):
        logger.warning(f"サポートされていない画像形式です: {path.suffix}")
        logger.warning("対応形式: JPEG, PNG, GIF, WebP")
        return None
    
    # MIMEタイプを取得
    mime_type = get_mime_type(image_path)
    
    logger.debug(f"画像アップロード開始: {path.name} (MIME: {mime_type})")
    
    try:
        # ファイル名（日本語対応）
        file_name = path.name
        
        # 既存メディアの重複チェック（ファイルサイズも比較）
        existing = find_existing_media(config, file_name, image_path)
        if existing:
            logger.info(f"既存画像を再利用: {file_name} (ID: {existing['id']})")
            return existing
        
        with open(image_path, 'rb') as f:
            file_data = f.read()
        
        # リクエストヘッダー
        headers = {
            'Content-Disposition': f'attachment; filename="{file_name}"',
            'Content-Type': mime_type,
        }
        
        response = requests.post(
            endpoint,
            auth=HTTPBasicAuth(config['WP_USER'], config['WP_APP_PASSWORD']),
            headers=headers,
            data=file_data,
            timeout=60  # 画像アップロードは時間がかかる可能性があるため長めに設定
        )
        
        if response.status_code == 201:
            result = response.json()
            media_id = result.get('id')
            media_url = result.get('source_url')
            
            logger.info(f"画像アップロード成功: {path.name} (ID: {media_id})")
            logger.debug(f"  URL: {media_url}")
            
            # alt属性を設定（別途APIコールが必要）
            if alt_text:
                update_media_alt(config, media_id, alt_text)
            
            return {
                'id': media_id,
                'url': media_url,
                'filename': file_name
            }
        else:
            logger.error(f"画像アップロード失敗 [{response.status_code}]: {path.name}")
            try:
                error_data = response.json()
                if 'message' in error_data:
                    logger.error(f"  エラー: {error_data['message']}")
            except Exception:
                logger.error(f"  レスポンス: {response.text[:200]}")
            return None
            
    except requests.exceptions.Timeout:
        logger.error(f"画像アップロードがタイムアウトしました: {path.name}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"画像アップロード中にエラーが発生: {e}")
        return None
    except IOError as e:
        logger.error(f"画像ファイルの読み込みに失敗: {e}")
        return None


def update_media_alt(config: dict, media_id: int, alt_text: str) -> bool:
    """
    メディアのalt属性を更新する。
    
    Args:
        config: 設定辞書
        media_id: メディアID
        alt_text: 設定するalt属性テキスト
    
    Returns:
        bool: 成功時はTrue
    """
    endpoint = f"{config['WP_URL']}/wp-json/wp/v2/media/{media_id}"
    
    try:
        response = requests.post(
            endpoint,
            auth=HTTPBasicAuth(config['WP_USER'], config['WP_APP_PASSWORD']),
            json={'alt_text': alt_text},
            timeout=30
        )
        
        if response.status_code == 200:
            logger.debug(f"alt属性を設定しました (ID: {media_id}): {alt_text}")
            return True
        else:
            logger.debug(f"alt属性の設定に失敗しました (ID: {media_id})")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.debug(f"alt属性更新中にエラー: {e}")
        return False


# =============================================================================
# Phase 3-3: パス置換
# =============================================================================

def replace_image_paths(
    content: str,
    image_mappings: List[Dict[str, str]]
) -> str:
    """
    コンテンツ内のローカル画像パスをアップロード後のURLに置換する。
    
    Args:
        content: 元のコンテンツ
        image_mappings: 置換マッピングのリスト
            各要素は {'original': 元のパス, 'url': 新しいURL} を含む
    
    Returns:
        str: パスを置換したコンテンツ
    """
    result = content
    
    for mapping in image_mappings:
        original_path = mapping['original']
        new_url = mapping['url']
        
        # Markdownパターンの置換: ![alt](original_path) -> ![alt](new_url)
        md_pattern = re.compile(
            r'(!\[[^\]]*\]\()' + re.escape(original_path) + r'(\s*(?:"[^"]*")?\))',
            re.IGNORECASE
        )
        result = md_pattern.sub(r'\1' + new_url + r'\2', result)
        
        # HTMLパターンの置換: src="original_path" -> src="new_url"
        html_pattern = re.compile(
            r'(src=["\'])' + re.escape(original_path) + r'(["\'])',
            re.IGNORECASE
        )
        result = html_pattern.sub(r'\1' + new_url + r'\2', result)
        
        logger.debug(f"パス置換: {original_path} -> {new_url}")
    
    return result


def process_images(
    config: dict,
    content: str,
    file_path: str
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    コンテンツ内の画像を検出・アップロード・置換する統合処理。
    
    Args:
        config: 設定辞書
        content: 元のコンテンツ
        file_path: コンテンツファイルのパス
    
    Returns:
        Tuple[str, List[Dict]]: (置換後のコンテンツ, アップロードされた画像情報リスト)
    """
    # ローカル画像を検出
    local_images = find_local_images(content, file_path)
    
    if not local_images:
        return content, []
    
    logger.info(f"{len(local_images)} 件の画像をアップロードします...")
    
    uploaded_images = []
    image_mappings = []
    
    for image in local_images:
        result = upload_image(
            config,
            image['absolute'],
            image['alt']
        )
        
        if result:
            uploaded_images.append({
                'id': result['id'],
                'url': result['url'],
                'filename': result['filename'],
                'original_path': image['original']
            })
            image_mappings.append({
                'original': image['original'],
                'url': result['url']
            })
        else:
            logger.warning(f"画像のアップロードに失敗しました: {image['original']}")
    
    # パスを置換
    if image_mappings:
        content = replace_image_paths(content, image_mappings)
        logger.info(f"{len(image_mappings)} 件の画像パスを置換しました")
    
    return content, uploaded_images


# =============================================================================
# Phase 2-4: HTML入力対応
# =============================================================================

def is_html_file(file_path: str) -> bool:
    """
    ファイルがHTMLファイルかどうかを判定する。
    
    Args:
        file_path: ファイルパス
    
    Returns:
        bool: HTMLファイルの場合はTrue
    """
    path = Path(file_path)
    return path.suffix.lower() in ['.html', '.htm']


def is_markdown_file(file_path: str) -> bool:
    """
    ファイルがMarkdownファイルかどうかを判定する。
    
    Args:
        file_path: ファイルパス
    
    Returns:
        bool: Markdownファイルの場合はTrue
    """
    path = Path(file_path)
    return path.suffix.lower() in ['.md', '.markdown']


# =============================================================================
# Phase 1-7: WordPress投稿
# =============================================================================

def post_to_wordpress(
    config: dict,
    title: str,
    html_content: str,
    status: str = 'draft',
    categories: Optional[List[int]] = None,
    tags: Optional[List[int]] = None,
    slug: Optional[str] = None,
    date: Optional[str] = None,
    excerpt: Optional[str] = None,
    featured_media: Optional[int] = None
) -> requests.Response:
    """
    WordPressにコンテンツを投稿する。
    
    Args:
        config: 設定辞書（WP_URL, WP_USER, WP_APP_PASSWORD）
        title: 投稿タイトル
        html_content: 投稿本文（HTML）
        status: 投稿ステータス（'draft' または 'publish'）
        categories: カテゴリIDのリスト
        tags: タグIDのリスト
        slug: 投稿スラッグ（URLの一部）
        date: 投稿日時（ISO 8601形式）
        excerpt: 抜粋
        featured_media: アイキャッチ画像のメディアID
    
    Returns:
        requests.Response: APIレスポンス
    
    Raises:
        SystemExit: 接続エラー時
    """
    endpoint = f"{config['WP_URL']}/wp-json/wp/v2/posts"
    
    # 投稿データ
    post_data = {
        'title': title,
        'content': html_content,
        'status': status,
    }
    
    # オプションパラメータを追加
    if categories:
        post_data['categories'] = categories
        logger.debug(f"カテゴリID: {categories}")
    
    if tags:
        post_data['tags'] = tags
        logger.debug(f"タグID: {tags}")
    
    if slug:
        post_data['slug'] = slug
        logger.debug(f"スラッグ: {slug}")
    
    if date:
        post_data['date'] = date
        logger.debug(f"投稿日時: {date}")
    
    if excerpt:
        post_data['excerpt'] = excerpt
        logger.debug(f"抜粋: {excerpt[:50]}..." if len(excerpt) > 50 else f"抜粋: {excerpt}")
    
    if featured_media:
        post_data['featured_media'] = featured_media
        logger.debug(f"アイキャッチ画像ID: {featured_media}")
    
    logger.debug(f"投稿先: {endpoint}")
    logger.debug(f"ステータス: {status}")
    
    try:
        response = requests.post(
            endpoint,
            auth=HTTPBasicAuth(config['WP_USER'], config['WP_APP_PASSWORD']),
            json=post_data,
            timeout=30
        )
        logger.debug(f"レスポンスステータス: {response.status_code}")
        return response
    
    except requests.exceptions.Timeout:
        logger.error("接続がタイムアウトしました（30秒）")
        logger.error("ネットワーク接続を確認してください。")
        logger.debug(traceback.format_exc())
        sys.exit(1)

    except requests.exceptions.ConnectionError as e:
        logger.error(f"接続エラーが発生しました: {e}")
        logger.error("以下を確認してください:")
        logger.error("  - WP_URL が正しいか")
        logger.error("  - サイトが稼働しているか")
        logger.error("  - ネットワーク接続が有効か")
        logger.debug(traceback.format_exc())
        sys.exit(1)

    except requests.exceptions.RequestException as e:
        logger.error(f"リクエストエラーが発生しました: {e}")
        logger.debug(traceback.format_exc())
        sys.exit(1)


# =============================================================================
# Phase 1-8: 結果表示/エラー処理
# =============================================================================

def print_success(response: requests.Response, config: dict) -> None:
    """
    投稿成功時の結果を表示する。
    
    Args:
        response: APIレスポンス
        config: 設定辞書
    """
    data = response.json()
    post_id = data.get('id')
    post_link = data.get('link')
    post_status = data.get('status')
    
    # 編集URL
    edit_url = f"{config['WP_URL']}/wp-admin/post.php?post={post_id}&action=edit"
    
    logger.info("=" * 50)
    logger.info("投稿が完了しました！")
    logger.info("=" * 50)
    logger.info(f"投稿ID: {post_id}")
    logger.info(f"ステータス: {post_status}")
    logger.info(f"編集URL: {edit_url}")
    
    if post_status == 'publish':
        logger.info(f"公開URL: {post_link}")
    else:
        logger.info(f"プレビューURL: {post_link}")


def print_error(response: requests.Response) -> None:
    """
    エラー時のメッセージを表示する。
    
    Args:
        response: APIレスポンス
    """
    status_code = response.status_code
    
    # ステータスコード別のメッセージ
    error_messages = {
        400: (
            "リクエストが不正です",
            [
                "投稿データの形式を確認してください",
            ]
        ),
        401: (
            "認証に失敗しました",
            [
                "WP_USER が正しいか確認してください",
                "WP_APP_PASSWORD が正しいか確認してください",
                "Application Passwordsが有効か確認してください",
            ]
        ),
        403: (
            "権限が不足しています",
            [
                "使用しているユーザーに投稿権限があるか確認してください",
                "「投稿者」以上の権限が必要です",
            ]
        ),
        404: (
            "エンドポイントが見つかりません",
            [
                "WP_URL が正しいか確認してください",
                "WordPress REST APIが有効か確認してください",
                f"URLの形式: https://your-site.com（末尾スラッシュなし）",
            ]
        ),
        500: (
            "サーバーエラーが発生しました",
            [
                "WordPressサーバーの状態を確認してください",
                "サーバーログを確認してください",
            ]
        ),
    }
    
    if status_code in error_messages:
        message, hints = error_messages[status_code]
        logger.error(f"エラー [{status_code}]: {message}")
        logger.error("")
        logger.error("対処法:")
        for hint in hints:
            logger.error(f"  - {hint}")
    else:
        logger.error(f"エラー [{status_code}]: 予期しないエラーが発生しました")
    
    # レスポンスの詳細（verbose時）
    try:
        error_data = response.json()
        if 'message' in error_data:
            logger.debug(f"サーバーメッセージ: {error_data['message']}")
        if 'code' in error_data:
            logger.debug(f"エラーコード: {error_data['code']}")
    except Exception:
        logger.debug(f"レスポンス: {response.text[:500]}")


def handle_response(response: requests.Response, config: dict) -> None:
    """
    APIレスポンスを処理する。
    
    Args:
        response: APIレスポンス
        config: 設定辞書
    """
    if response.status_code == 201:
        print_success(response, config)
    else:
        print_error(response)
        sys.exit(1)


# =============================================================================
# Phase 1-2, 1-9: スクリプト骨格・CLIオプション整備
# =============================================================================

def create_argument_parser() -> argparse.ArgumentParser:
    """
    コマンドライン引数パーサーを作成する。
    
    Returns:
        argparse.ArgumentParser: 設定済みのパーサー
    """
    parser = argparse.ArgumentParser(
        prog='post_to_wp',
        description='Markdown/HTMLファイルをWordPressに投稿するCLIツール',
        epilog='''
使用例:
  python post_to_wp.py articles/sample.md           # 下書きとして投稿
  python post_to_wp.py articles/sample.md --publish # 公開として投稿
  python post_to_wp.py articles/sample.md -v        # 詳細ログ付きで投稿
  python post_to_wp.py articles/page.html           # HTMLファイルを投稿
  python post_to_wp.py articles/sample.md --create-terms  # カテゴリ/タグを自動作成

Front Matter対応:
  Markdownファイルの先頭に以下のYAML形式でメタデータを指定できます:
    ---
    title: 記事のタイトル
    categories:
      - カテゴリ1
      - カテゴリ2
    tags:
      - タグ1
      - タグ2
    slug: custom-slug
    date: 2024-01-01T12:00:00
    excerpt: 記事の抜粋文
    ---

設定:
  .env ファイルに以下の環境変数を設定してください:
    WP_URL=https://your-site.com
    WP_USER=your_username
    WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # 位置引数: ファイルパス（MarkdownまたはHTML）
    parser.add_argument(
        'input_file',
        type=str,
        metavar='markdown_file',
        help='投稿するMarkdown/HTMLファイルのパス'
    )
    
    # 投稿ステータス（排他的グループ）
    status_group = parser.add_mutually_exclusive_group()
    status_group.add_argument(
        '--draft',
        action='store_true',
        default=True,
        help='下書きとして投稿（デフォルト）'
    )
    status_group.add_argument(
        '--publish',
        action='store_true',
        help='公開として投稿'
    )
    
    # カテゴリ/タグの自動作成オプション
    parser.add_argument(
        '--create-terms',
        action='store_true',
        help='存在しないカテゴリ/タグを自動作成'
    )
    
    # アイキャッチ画像オプション
    parser.add_argument(
        '--no-featured',
        action='store_true',
        help='アイキャッチ画像を設定しない（デフォルトは最初の画像をアイキャッチに設定）'
    )
    
    # 詳細出力オプション
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='詳細なログを出力'
    )
    
    return parser


def main():
    """
    メイン関数。CLIエントリーポイント。
    """
    # 引数をパース
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # ロギング設定
    setup_logging(verbose=args.verbose)
    
    # 投稿ステータスを決定
    status = 'publish' if args.publish else 'draft'
    
    logger.info(f"Cursor → WordPress 自動投稿ツール")
    logger.info("-" * 40)
    
    # 設定を読み込み
    config = load_config()
    
    # ファイルを読み込み
    file_path = args.input_file
    logger.info(f"ファイル読み込み: {file_path}")
    content = read_markdown_file(file_path)
    
    # Front Matterを解析
    metadata, body = parse_front_matter(content)
    
    # ファイル形式に応じて処理
    if is_html_file(file_path):
        logger.info("HTMLファイルとして処理します")
        # HTMLファイルはタイトル抽出のみ行い、変換はスキップ
        if 'title' in metadata:
            title = metadata['title']
        else:
            # HTMLファイルからタイトルを抽出（簡易実装）
            title_match = re.search(r'<title>(.+?)</title>', body, re.IGNORECASE)
            if title_match:
                title = title_match.group(1)
            else:
                title = Path(file_path).stem
        html_content = body
        logger.info(f"タイトル: {title}")
    else:
        # Markdownファイルとして処理
        logger.info("Markdownファイルとして処理します")
        
        # Front Matterのタイトルを優先
        if 'title' in metadata:
            title = metadata['title']
            # タイトルが指定されている場合は本文からの抽出はスキップ
            body = remove_heading_matching_title(body, title)
            logger.info(f"タイトル (Front Matter): {title}")
        else:
            # 本文からタイトルを抽出
            title, body = extract_title(body, file_path)
            logger.info(f"タイトル: {title}")
        
        # Markdown→HTML変換
        logger.info("Markdown→HTML変換中...")
        html_content = convert_markdown_to_html(body)
    
    # JSON-LDを末尾に移動
    html_content = move_jsonld_to_end(html_content)
    
    # カテゴリ/タグのID解決
    category_ids = None
    tag_ids = None
    
    if 'categories' in metadata and metadata['categories']:
        categories = metadata['categories']
        if isinstance(categories, str):
            categories = [categories]
        logger.info(f"カテゴリを解決中: {categories}")
        category_ids = resolve_category_ids(config, categories, args.create_terms)
        if category_ids:
            logger.info(f"カテゴリID: {category_ids}")
    
    if 'tags' in metadata and metadata['tags']:
        tags = metadata['tags']
        if isinstance(tags, str):
            tags = [tags]
        logger.info(f"タグを解決中: {tags}")
        tag_ids = resolve_tag_ids(config, tags, args.create_terms)
        if tag_ids:
            logger.info(f"タグID: {tag_ids}")
    
    # その他のメタデータ
    slug = metadata.get('slug')
    date = normalize_date_for_wp(metadata.get('date'))
    excerpt = metadata.get('excerpt')
    
    if slug:
        logger.info(f"スラッグ: {slug}")
    if date:
        logger.info(f"投稿日時: {date}")
    if excerpt:
        logger.info(f"抜粋: {excerpt[:30]}..." if len(str(excerpt)) > 30 else f"抜粋: {excerpt}")
    
    # 画像処理（Phase 3）
    uploaded_images = []
    featured_media_id = None
    
    # Markdownの場合は変換前の本文から画像を検出し処理
    # HTMLの場合はhtml_contentから画像を検出し処理
    if is_html_file(file_path):
        # HTMLファイルの場合
        html_content, uploaded_images = process_images(config, html_content, file_path)
    else:
        # Markdownファイルの場合は、変換前の本文から画像を処理
        body, uploaded_images = process_images(config, body, file_path)
        # 画像パス置換後に再度HTML変換
        if uploaded_images:
            logger.info("画像パス置換後にMarkdown→HTML再変換中...")
            html_content = convert_markdown_to_html(body)
            # JSON-LDを再度末尾に移動
            html_content = move_jsonld_to_end(html_content)
    
    # アイキャッチ画像の設定
    if uploaded_images and not args.no_featured:
        # Front Matterでfeatured_imageが指定されている場合はそのファイルを使用
        featured_image_path = metadata.get('featured_image')
        
        if featured_image_path:
            # 指定された画像をアイキャッチとして探す
            for img in uploaded_images:
                if featured_image_path in img['original_path'] or featured_image_path == img['filename']:
                    featured_media_id = img['id']
                    logger.info(f"アイキャッチ画像を設定 (指定): {img['filename']} (ID: {featured_media_id})")
                    break
            
            if not featured_media_id:
                logger.warning(f"指定されたアイキャッチ画像が見つかりません: {featured_image_path}")
                logger.info("最初の画像をアイキャッチとして設定します")
                featured_media_id = uploaded_images[0]['id']
                logger.info(f"アイキャッチ画像を設定: {uploaded_images[0]['filename']} (ID: {featured_media_id})")
        else:
            # デフォルト: 最初の画像をアイキャッチに設定
            featured_media_id = uploaded_images[0]['id']
            logger.info(f"アイキャッチ画像を設定: {uploaded_images[0]['filename']} (ID: {featured_media_id})")
    elif args.no_featured:
        logger.info("アイキャッチ画像は設定しません (--no-featured オプション)")
    
    # WordPressに投稿
    status_label = "公開" if status == 'publish' else "下書き"
    logger.info(f"WordPressに{status_label}として投稿中...")
    response = post_to_wordpress(
        config,
        title,
        html_content,
        status,
        categories=category_ids,
        tags=tag_ids,
        slug=slug,
        date=date,
        excerpt=excerpt,
        featured_media=featured_media_id
    )
    
    # レスポンス処理
    handle_response(response, config)


if __name__ == '__main__':
    main()
