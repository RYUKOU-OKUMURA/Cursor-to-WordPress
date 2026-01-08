#!/usr/bin/env python3
"""
Cursor → WordPress 自動投稿ツール

MarkdownファイルをWordPressに投稿するCLIツール。
"""

import argparse
import logging
import os
import re
import sys
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

import markdown2
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv


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
# Phase 1-7: WordPress投稿
# =============================================================================

def post_to_wordpress(
    config: dict,
    title: str,
    html_content: str,
    status: str = 'draft'
) -> requests.Response:
    """
    WordPressにコンテンツを投稿する。
    
    Args:
        config: 設定辞書（WP_URL, WP_USER, WP_APP_PASSWORD）
        title: 投稿タイトル
        html_content: 投稿本文（HTML）
        status: 投稿ステータス（'draft' または 'publish'）
    
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
        sys.exit(1)
    
    except requests.exceptions.ConnectionError as e:
        logger.error(f"接続エラーが発生しました: {e}")
        logger.error("以下を確認してください:")
        logger.error("  - WP_URL が正しいか")
        logger.error("  - サイトが稼働しているか")
        logger.error("  - ネットワーク接続が有効か")
        sys.exit(1)
    
    except requests.exceptions.RequestException as e:
        logger.error(f"リクエストエラーが発生しました: {e}")
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
        description='MarkdownファイルをWordPressに投稿するCLIツール',
        epilog='''
使用例:
  python post_to_wp.py articles/sample.md           # 下書きとして投稿
  python post_to_wp.py articles/sample.md --publish # 公開として投稿
  python post_to_wp.py articles/sample.md -v        # 詳細ログ付きで投稿

設定:
  .env ファイルに以下の環境変数を設定してください:
    WP_URL=https://your-site.com
    WP_USER=your_username
    WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # 位置引数: Markdownファイルパス
    parser.add_argument(
        'markdown_file',
        type=str,
        help='投稿するMarkdownファイルのパス'
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
    
    # Markdownファイルを読み込み
    logger.info(f"ファイル読み込み: {args.markdown_file}")
    content = read_markdown_file(args.markdown_file)
    
    # タイトルを抽出
    title, body = extract_title(content, args.markdown_file)
    logger.info(f"タイトル: {title}")
    
    # Markdown→HTML変換
    logger.info("Markdown→HTML変換中...")
    html_content = convert_markdown_to_html(body)
    
    # WordPressに投稿
    status_label = "公開" if status == 'publish' else "下書き"
    logger.info(f"WordPressに{status_label}として投稿中...")
    response = post_to_wordpress(config, title, html_content, status)
    
    # レスポンス処理
    handle_response(response, config)


if __name__ == '__main__':
    main()
