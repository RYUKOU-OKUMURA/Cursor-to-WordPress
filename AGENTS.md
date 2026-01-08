# AGENTS.md

## プロジェクト概要
- Cursorで書いたMarkdownをWordPressへ自動投稿するCLIツール（Phase 1はテキストのみ）
- 目的は管理画面操作を省略し、下書き/公開をコマンドで完結させること

## 技術スタック
- Python 3.8+
- requests / markdown2 / python-dotenv
- WordPress REST API v2 + Application Passwords

## 構成（設計前提）
- `post_to_wp.py` 単一スクリプトで実装
- `requirements.txt`, `.env`, `.env.example`, `.gitignore`, `docs/`
- `articles/` は任意のMarkdown置き場

## 実行コマンド
- 依存関係: `pip install -r requirements.txt`
- 実行: `python post_to_wp.py path/to/article.md`
- 公開投稿: `python post_to_wp.py path/to/article.md --publish`
- ヘルプ: `python post_to_wp.py --help`

## 注意事項
- `.env` はGit管理外。`WP_URL`は末尾スラッシュなしで設定
- タイトル抽出は `#` 見出し優先、次に `##`、なければファイル名
- 抽出したタイトル見出しは本文から除去する
- 既存実装が未生成の場合は `docs/` の設計に沿って追加する

## ドキュメント
- `docs/要件定義書_清書.md`
- `docs/アーキテクチャ_清書.md`
- `docs/技術スタック_清書.md`
- `docs/実装計画書_清書.md`
