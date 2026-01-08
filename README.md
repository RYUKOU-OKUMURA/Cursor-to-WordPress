# Cursor → WordPress 自動投稿ツール

CursorエディタでMarkdownを作成し、WordPressへ自動投稿するCLIツールです。

## 機能

- Markdownファイルを読み込んでHTMLに変換
- WordPress REST APIを使用して投稿
- 下書き/公開の切り替え対応
- タイトルの自動抽出（H1 → H2 → ファイル名の優先順）
- 詳細ログ出力（`--verbose`オプション）
- エラーメッセージの日本語対応

## 必要要件

- Python 3.8以上
- WordPress 5.6以上
- WordPressのApplication Passwords機能が有効

## インストール

```bash
# リポジトリをクローン
git clone https://github.com/RYUKOU-OKUMURA/Cursor-to-WordPress.git
cd Cursor-to-WordPress

# 仮想環境を作成（推奨）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存パッケージをインストール
pip install -r requirements.txt
```

## 設定

1. `.env.example` を `.env` にコピー
2. `.env` に認証情報を入力

```bash
cp .env.example .env
```

### `.env` の設定項目

| 項目 | 説明 | 例 |
|------|------|-----|
| `WP_URL` | WordPressサイトのURL（末尾スラッシュなし） | `https://your-site.com` |
| `WP_USER` | WordPressユーザー名 | `admin` |
| `WP_APP_PASSWORD` | Application Password | `xxxx xxxx xxxx xxxx xxxx xxxx` |

### Application Passwordの取得方法

1. WordPress管理画面にログイン
2. 「ユーザー」→「プロフィール」へ移動
3. 「アプリケーションパスワード」セクションで新規作成
4. 生成されたパスワードを `.env` に設定

## 使用方法

### 基本的な使い方

```bash
# 下書きとして投稿（デフォルト）
python post_to_wp.py path/to/article.md

# 公開投稿
python post_to_wp.py path/to/article.md --publish

# 詳細ログを表示
python post_to_wp.py path/to/article.md --verbose

# ヘルプを表示
python post_to_wp.py --help
```

### コマンドラインオプション

| オプション | 短縮形 | 説明 |
|-----------|--------|------|
| `--draft` | - | 下書きとして投稿（デフォルト） |
| `--publish` | - | 公開として投稿 |
| `--verbose` | `-v` | 詳細なログを出力 |
| `--help` | `-h` | ヘルプを表示 |

### サンプル記事で試す

```bash
python post_to_wp.py articles/sample_article.md
```

### 出力例

投稿成功時:

```
Cursor → WordPress 自動投稿ツール
----------------------------------------
ファイル読み込み: articles/sample_article.md
タイトル: サンプル記事
Markdown→HTML変換中...
WordPressに下書きとして投稿中...
==================================================
投稿が完了しました！
==================================================
投稿ID: 123
ステータス: draft
編集URL: https://your-site.com/wp-admin/post.php?post=123&action=edit
プレビューURL: https://your-site.com/?p=123
```

## Markdownの書き方

### タイトルの指定

タイトルは以下の優先順で抽出されます：

1. H1見出し（`# タイトル`）
2. H2見出し（`## タイトル`）
3. ファイル名

```markdown
# 記事のタイトル

ここから本文が始まります。
```

**注意**: タイトルとして抽出された見出しは本文から除去されます。

### 対応するMarkdown記法

- 見出し（`#`, `##`, `###` など）
- 強調（`**太字**`, `*斜体*`）
- リスト（番号なし・番号付き）
- コードブロック（バッククォート3つで囲む）
- テーブル
- リンク・画像

## ディレクトリ構成

```
├── post_to_wp.py      # メインスクリプト
├── requirements.txt   # 依存パッケージ
├── .env               # 環境変数（Git管理外）
├── .env.example       # 環境変数テンプレート
├── .gitignore
├── README.md          # このファイル
├── AGENTS.md          # AI向けプロジェクト説明
├── articles/          # Markdown置き場
│   └── sample_article.md
└── docs/              # 設計ドキュメント
    ├── 要件定義書_清書.md
    ├── アーキテクチャ_清書.md
    ├── 技術スタック_清書.md
    └── 実装計画書_清書.md
```

## トラブルシューティング

### 認証エラー（401）

- Application Passwordが正しく設定されているか確認
- スペース区切りのパスワードをそのまま入力（スペースを削除しない）
- ユーザー名が正しいか確認

### 権限不足（403）

- 使用しているユーザーに「投稿」権限があるか確認
- 「投稿者」以上の権限が必要

### エンドポイントが見つからない（404）

- `WP_URL` が正しいか確認（末尾スラッシュなし）
- WordPress REST APIが有効か確認（`https://サイトURL/wp-json/` にアクセス）

### 接続エラー

- サイトのURLが正しいか確認
- サイトがHTTPSに対応しているか確認
- ファイアウォールやプロキシの設定を確認

### 文字化けする場合

- Markdownファイルがの文字コードがUTF-8か確認
- BOMなしUTF-8で保存する

## 開発

### 依存パッケージ

- `requests`: HTTP通信
- `markdown2`: Markdown→HTML変換
- `python-dotenv`: 環境変数管理

### テスト実行

```bash
# 詳細ログ付きでテスト
python post_to_wp.py articles/sample_article.md -v
```

## ライセンス

MIT License
