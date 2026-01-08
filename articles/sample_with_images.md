---
title: 画像付きサンプル記事
categories:
  - サンプル
tags:
  - 画像
  - テスト
slug: sample-with-images
excerpt: この記事は画像アップロード機能のテスト用サンプルです。
featured_image: sample-image.png
---

# 画像機能のテスト

この記事は、WordPress自動投稿ツールの画像アップロード機能をテストするためのサンプルです。

## ローカル画像の埋め込み

以下のようにMarkdown形式で画像を埋め込むことができます：

![サンプル画像](images/sample-image.png)

相対パスで指定された画像は自動的にWordPressメディアライブラリにアップロードされ、
本文内のパスはアップロード後のURLに置換されます。

## 複数画像の対応

複数の画像を含む記事も対応しています：

![画像1](images/image1.jpg)
![画像2](images/image2.jpg)

## HTML形式の画像

HTML形式での画像指定もサポートしています：

<img src="images/html-image.png" alt="HTML形式の画像">

## アイキャッチ画像

- デフォルトでは最初の画像がアイキャッチとして設定されます
- Front Matterで `featured_image:` を指定することで特定の画像をアイキャッチに設定できます
- `--no-featured` オプションでアイキャッチを設定しないことも可能です

## 外部画像

外部URLの画像はアップロード対象外となります（そのまま保持されます）：

![外部画像](https://example.com/external-image.jpg)

## 対応形式

以下の画像形式に対応しています：
- JPEG (.jpg, .jpeg)
- PNG (.png)
- GIF (.gif)
- WebP (.webp)

---

*この記事は `post_to_wp.py` の画像機能テスト用サンプルです。*
