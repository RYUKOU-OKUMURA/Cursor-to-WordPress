# Cursor → WordPress 自動投稿ツール

CursorエディタでMarkdownを作成し、WordPressへ自動投稿するCLIツールです。

## 機能

- Markdownファイルを読み込んでHTMLに変換
- WordPress REST APIを使用して投稿
- 下書き/公開の切り替え対応
- タイトルの自動抽出（H1 → H2 → ファイル名の優先順）

## 必要要件

- Python 3.8以上
- WordPress 5.6以上
- WordPressのApplication Passwords機能が有効

## インストール

```bash
# リポジトリをクローン
git clone <repository-url>
cd <repository-name>

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

# ヘルプを表示
python post_to_wp.py --help
```

### サンプル記事で試す

```bash
python post_to_wp.py articles/sample_article.md
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

## ディレクトリ構成

```
├── post_to_wp.py      # メインスクリプト
├── requirements.txt   # 依存パッケージ
├── .env               # 環境変数（Git管理外）
├── .env.example       # 環境変数テンプレート
├── .gitignore
├── articles/          # Markdown置き場
│   └── sample_article.md
└── docs/              # 設計ドキュメント
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

## ライセンス

MIT License
