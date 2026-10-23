# 検証記録 2026-10-23

## 実施済み

- 受領した外部ExifTool版を静的に確認。元の単一ファイルを変更せず保管。
- Python 6試験合格。分類・元タグ保持、XMLエスケープ、既存出力保護、不正値拒否、CSV数式化対策、RAW書込み拒否、ExifToolを使ったJPEGコピー保存／再読取。
- ExifTool 13.59による説明・権利・ラベル・評価・日時（小数秒・UTC時差付き）・負の緯度・正の経度の書込みを検査。原本SHA-256不変、出力JPEGの復号画素一致を確認。
- ExifToolの受領Windows配布物に含まれるPerl本体を、Linux標準Perlと純Perlライブラリで実行。Windows EXEを実行した結果ではない。
- JavaScript 9検査合格。旧JSON、タグの由来、不正値、XMPエスケープ・緯度符号、CSV、破損JPEG、両バイト順TIFF、IFD循環、ExifToolでタグを付けた合成JPEG読取。
- PySide6 6.12.0をLinuxオフスクリーン環境で起動。タグ表示・検索・変更候補作成・クリアのスモーク試験合格。
- Python構文・JS構文検査。

## 試験で修正した点

- XMPには単独の `OffsetTimeOriginal` を書き込まない。ExifToolで書込対象外であることを確認。UTC時差は `XMP-exif:DateTimeOriginal` の日時文字列に含める。
- ExifToolの再読取日時は日付をコロン区切りで返すので、比較時に区切りだけをISO形式に正規化。時差・小数秒を捨てない。
- 同名写真の識別子衝突を拒否。

## 未確認・次の完了条件

1. Windows 3.12でbuild_exe.batを実行し、onedirフォルダ全体を別の場所に移して起動する。
2. 日本語・空白パスの実PEFとJPEGでタグ抽出・比較・JSON再取込・XMP・JPEGコピー・原本ハッシュを確認する。
3. Edge/Chromeでweb/index.htmlを直接開き、写真／JSONの追加、検索・比較、変更候補、XMPとJSONのダウンロード、再取込を確認する。今回のクラウドブラウザはローカルプレビューへのURL制限で画面確認できなかった。
4. PENTAX K-1 Mark IIの実ファイル・ファームウェア・形式ごとにMakerNotesの存在を確認する。姿勢の軸・符号・精度は元のDrogger検討で検証する。
5. 他メーカーは機種ごとに入力を確認する。標準読取実装の存在だけでメーカー全機種対応とはしない。

実PEF・実NMEAは今回取得した引継ぎZIP／ソースZIPには含まれていない。合成画像の結果は実機合格の代わりにはならない。
