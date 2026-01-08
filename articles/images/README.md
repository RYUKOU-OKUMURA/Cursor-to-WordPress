# サンプル画像ディレクトリ

このディレクトリには、`sample_with_images.md` で使用するテスト用画像を配置してください。

## 必要な画像ファイル

以下のファイルを配置すると、サンプル記事のテストができます：

- `sample-image.png` - メインのサンプル画像（アイキャッチ候補）
- `image1.jpg` - 追加画像1
- `image2.jpg` - 追加画像2
- `html-image.png` - HTML形式テスト用画像

## 対応形式

- JPEG (.jpg, .jpeg)
- PNG (.png)
- GIF (.gif)
- WebP (.webp)

## テスト方法

1. このディレクトリに画像ファイルを配置
2. 以下のコマンドを実行：

```bash
python post_to_wp.py articles/sample_with_images.md
```

画像がWordPressにアップロードされ、記事が投稿されます。
