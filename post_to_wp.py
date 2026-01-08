#!/usr/bin/env python3
"""
Cursor → WordPress 自動投稿ツール

MarkdownファイルをWordPressに投稿するCLIツール。
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Tuple, Optional

from dotenv import load_dotenv


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
        print("エラー: 以下の環境変数が設定されていません:", file=sys.stderr)
        for key in missing_keys:
            print(f"  - {key}", file=sys.stderr)
        print("\n.env ファイルを作成し、必要な値を設定してください。", file=sys.stderr)
        print("テンプレートは .env.example を参照してください。", file=sys.stderr)
        sys.exit(1)
    
    # WP_URLの末尾スラッシュを除去
    config['WP_URL'] = config['WP_URL'].rstrip('/')
    
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
        print(f"エラー: ファイルが見つかりません: {file_path}", file=sys.stderr)
        sys.exit(1)
    
    # ファイルかどうかチェック
    if not path.is_file():
        print(f"エラー: 指定されたパスはファイルではありません: {file_path}", file=sys.stderr)
        sys.exit(1)
    
    # 読み取り権限チェック
    if not os.access(path, os.R_OK):
        print(f"エラー: ファイルの読み取り権限がありません: {file_path}", file=sys.stderr)
        sys.exit(1)
    
    # UTF-8でファイルを読み込む
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except UnicodeDecodeError:
        print(f"エラー: ファイルがUTF-8形式ではありません: {file_path}", file=sys.stderr)
        sys.exit(1)
    except IOError as e:
        print(f"エラー: ファイルの読み込みに失敗しました: {e}", file=sys.stderr)
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
            break
    
    # H1がなければH2を探す（## タイトル）
    if title is None:
        h2_pattern = re.compile(r'^##\s+(.+)$')
        for i, line in enumerate(lines):
            match = h2_pattern.match(line.strip())
            if match:
                title = match.group(1).strip()
                title_line_index = i
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
    
    return title, body


# =============================================================================
# Phase 1-2: スクリプト骨格（argparse CLIおよびエントリーポイント）
# =============================================================================

def create_argument_parser() -> argparse.ArgumentParser:
    """
    コマンドライン引数パーサーを作成する。
    
    Returns:
        argparse.ArgumentParser: 設定済みのパーサー
    """
    parser = argparse.ArgumentParser(
        prog='post_to_wp',
        description='Markdownファイルを読み込んでWordPressに投稿するCLIツール',
        epilog='例: python post_to_wp.py articles/sample.md --publish'
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
    
    return parser


def main():
    """
    メイン関数。CLIエントリーポイント。
    """
    # 引数をパース
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # 投稿ステータスを決定
    status = 'publish' if args.publish else 'draft'
    
    # 設定を読み込み
    config = load_config()
    
    # Markdownファイルを読み込み
    content = read_markdown_file(args.markdown_file)
    
    # タイトルを抽出
    title, body = extract_title(content, args.markdown_file)
    
    # デバッグ出力（Phase 1-6以降で実際の投稿処理に置き換え）
    print(f"設定:")
    print(f"  WP_URL: {config['WP_URL']}")
    print(f"  WP_USER: {config['WP_USER']}")
    print(f"  WP_APP_PASSWORD: {'*' * len(config['WP_APP_PASSWORD'])}")
    print()
    print(f"ファイル: {args.markdown_file}")
    print(f"ステータス: {status}")
    print(f"タイトル: {title}")
    print(f"本文長: {len(body)} 文字")
    print()
    print("--- 本文プレビュー（先頭500文字） ---")
    print(body[:500])
    if len(body) > 500:
        print("...")


if __name__ == '__main__':
    main()
