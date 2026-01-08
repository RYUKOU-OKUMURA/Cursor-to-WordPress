# AGENTS.md

## プロジェクト概要
Cursorで書いたMarkdownをWordPressへ自動投稿するCLIツール（Phase 1はテキストのみ）。管理画面操作を省略し、下書き/公開をコマンドで完結させる。

## 技術スタック
- Python 3.8+
- requests / markdown2 / python-dotenv
- WordPress REST API v2 + Application Passwords

## ディレクトリ構成
```
├── post_to_wp.py      # メインスクリプト
├── requirements.txt   # 依存パッケージ
├── .env               # 環境変数（Git管理外）
├── .env.example       # 環境変数テンプレート
├── .gitignore
├── articles/          # Markdown置き場（任意）
└── docs/              # 設計ドキュメント
```

## 実行コマンド
```bash
pip install -r requirements.txt          # 依存関係インストール
python post_to_wp.py path/to/article.md  # 下書き投稿
python post_to_wp.py path/to/article.md --publish  # 公開投稿
python post_to_wp.py --help              # ヘルプ表示
```

## 注意事項
- `.env` はGit管理外。`WP_URL`は末尾スラッシュなしで設定
- タイトル抽出: `#` 見出し優先 → `##` → ファイル名
- 抽出したタイトル見出しは本文から除去する
- 既存実装が未生成の場合は `docs/` の設計に沿って追加する

## 作業ルール
- 完了したタスクのチェックボックスには必ずチェックを入れる（`[ ]` → `[x]`）
- コードを変更する前に必ず既存のファイルを読む
- シンプルな実装を優先し、過度な抽象化を避ける

## ドキュメント
- [docs/要件定義書_清書.md](docs/要件定義書_清書.md)
- [docs/アーキテクチャ_清書.md](docs/アーキテクチャ_清書.md)
- [docs/技術スタック_清書.md](docs/技術スタック_清書.md)
- [docs/実装計画書_清書.md](docs/実装計画書_清書.md)
