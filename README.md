# Cursor → WordPress 自動投稿ツール

CursorエディタでMarkdownを作成し、WordPressへ自動投稿するCLIツールです。

## 機能

### 基本機能
- Markdownファイルを読み込んでHTMLに変換
- HTMLファイルをそのまま投稿
- WordPress REST APIを使用して投稿
- 下書き/公開の切り替え対応
- タイトルの自動抽出（H1 → H2 → ファイル名の優先順）
- 詳細ログ出力（`--verbose`オプション）
- エラーメッセージの日本語対応

### 追加機能（Phase 2）
- **Front Matter対応**: YAML形式でメタデータを指定
- **カテゴリ/タグの自動設定**: 名前からIDを自動解決
- **カテゴリ/タグの自動作成**: `--create-terms`オプションで存在しない場合に自動作成
- **JSON-LD対応**: 構造化データを自動的に本文末尾に移動
- **投稿パラメータ拡張**: slug、date、excerptの指定が可能

### 画像対応（Phase 3）
- **ローカル画像の自動アップロード**: Markdown/HTML内のローカル画像を自動検出
- **メディアライブラリへのアップロード**: WordPress REST API経由で画像をアップロード
- **パス自動置換**: 本文内のローカルパスをアップロード後のURLに自動置換
- **アイキャッチ画像の自動設定**: 最初の画像を自動的にアイキャッチに設定
- **対応形式**: JPEG、PNG、GIF、WebP

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
| `--create-terms` | - | 存在しないカテゴリ/タグを自動作成 |
| `--no-featured` | - | アイキャッチ画像を設定しない |
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

### Front Matter（YAML形式）

ファイルの先頭にYAML形式でメタデータを指定できます。

```markdown
---
title: 記事のタイトル
categories:
  - プログラミング
  - Python
tags:
  - CLI
  - WordPress
  - 自動化
slug: custom-post-slug
date: 2024-01-15T12:00:00
excerpt: この記事はMarkdownからWordPressへ投稿する方法を解説します。
---

ここから本文が始まります。
```

#### Front Matterで指定可能な項目

| 項目 | 説明 | 例 |
|------|------|-----|
| `title` | 記事タイトル | `title: 記事のタイトル` |
| `categories` | カテゴリ（リスト形式） | `categories: [カテゴリ1, カテゴリ2]` |
| `tags` | タグ（リスト形式） | `tags: [タグ1, タグ2]` |
| `slug` | 投稿スラッグ（URLの一部） | `slug: my-custom-slug` |
| `date` | 投稿日時（ISO 8601形式） | `date: 2024-01-15T12:00:00` |
| `excerpt` | 抜粋文 | `excerpt: 記事の概要` |
| `featured_image` | アイキャッチ画像のファイル名 | `featured_image: image.png` |

### タイトルの指定

タイトルは以下の優先順で抽出されます：

1. Front Matterの`title`
2. H1見出し（`# タイトル`）
3. H2見出し（`## タイトル`）
4. ファイル名

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

### 画像の埋め込み

ローカル画像を含む記事を投稿すると、画像は自動的にWordPressメディアライブラリにアップロードされます。

```markdown
![画像の説明](images/sample.png)
```

#### 画像の動作

- **ローカル画像**: 相対パスまたは絶対パスで指定された画像は自動アップロード
- **外部URL**: `http://` や `https://` で始まるURLはそのまま保持
- **アイキャッチ**: デフォルトで最初の画像がアイキャッチに設定
- **対応形式**: JPEG, PNG, GIF, WebP

#### アイキャッチ画像の制御

```markdown
---
title: 記事タイトル
featured_image: special-image.png  # 特定の画像をアイキャッチに指定
---
```

アイキャッチを設定しない場合は `--no-featured` オプションを使用：

```bash
python post_to_wp.py article.md --no-featured
```

#### 画像付き記事の例

```bash
# 画像付き記事を投稿
python post_to_wp.py articles/sample_with_images.md

# アイキャッチなしで投稿
python post_to_wp.py articles/sample_with_images.md --no-featured
```

### HTMLファイルの投稿

`.html`または`.htm`ファイルを直接投稿することもできます。

```bash
python post_to_wp.py articles/page.html --publish
```

HTMLファイルの場合：
- Markdown→HTML変換はスキップされます
- タイトルは`<title>`タグまたはファイル名から抽出されます
- Front Matterも利用可能です

### JSON-LD（構造化データ）

本文中にJSON-LDスクリプトが含まれている場合、自動的に本文末尾に移動されます。

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "記事のタイトル"
}
</script>
```

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
│   ├── sample_article.md
│   ├── sample_with_frontmatter.md
│   ├── sample_with_images.md
│   └── images/        # 画像ファイル置き場
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
- `pyyaml`: Front Matter（YAML）解析

### 画像アップロードの仕組み

1. **検出**: `find_local_images()` がMarkdown/HTML内のローカル画像パスを検出
2. **アップロード**: `upload_image()` が `/wp-json/wp/v2/media` エンドポイントに画像をPOST
3. **置換**: `replace_image_paths()` が本文内のパスをアップロード後のURLに置換
4. **アイキャッチ**: 最初の画像IDを `featured_media` パラメータとして投稿APIに送信

### テスト実行

```bash
# 詳細ログ付きでテスト
python post_to_wp.py articles/sample_article.md -v
```

## ライセンス

MIT License
