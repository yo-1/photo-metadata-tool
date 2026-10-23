# 写真メタデータ管理ツール v0.1.0（試用版）

## すぐ使う：ブラウザ版

1. ZIPをすべて展開します。
2. `web/index.html` をEdgeまたはChromeで開きます。サーバーやインストールは不要です。
3. 写真またはExifTool JSONを追加します。まず `examples/SYNTHETIC_metadata.json` で操作を試せます。
4. 写真A・写真Bを選ぶと同じ元タグの値を比較できます。黄色は相違です。
5. 変更する項目・変更後の値・理由を入力し、「候補を追加／更新」を押します。
6. 差分を確認して「XMPを保存」、続いて「JSON台帳」を保存します。

写真や台帳を外部へ送る処理はありません。CDN・外部フォント・アクセス解析・通信機能を使用しません。メモリ内で処理し、閉じると消えます。保存はブラウザのダウンロード機能を使います。上書きや保存先の最終動作はブラウザの設定に従います。

**直接読取は標準EXIFの部分対応です。** JPEG、通常TIFF形式のPEF/DNG/TIFFが対象です。MakerNotes本体・埋込XMPは直接解読しません。未知のTIFFタグは数値IDで表示します。BigTIFF、拡張XMP、大きな配列等には制限があります。全タグが必要ならWindows版のJSONを取り込みます。PENTAX機種ごとの姿勢や実時刻精度は未検証です。

写真名は識別子です。同じ名前のファイルの追加は拒否します。同名写真を複数フォルダから扱う場合は、フルパスを持つExifTool JSONを使ってください。写真1枚あたり256MBを上限としています。大量処理はWindows版でJSON化し、物件ごとに分けて扱ってください。

## Windows版（Python起動・EXEビルド）

本パッケージには**Windows EXE本体は未収録**です。Windowsで以下の手順により作成します。受領したExifTool 13.59のWindows用ツール一式は `tools/` に配置済みです。`exiftool_files` を削除しないでください。

Python 3.12（64bit）とインターネット接続のあるWindowsで `build_exe.bat` を実行します。初回はPySide6等を取得します。完了したら以下のファイルを起動します。

`dist/PhotoMetadataManager/PhotoMetadataManager.exe`

配布は **PhotoMetadataManagerフォルダ全体**で行います。EXEだけを移動しないでください。ビルド後の写真処理にはネット接続は不要です。

EXEを作らずPythonで起動する場合:

```powershell
py -m pip install -r requirements.txt
py src/photo_metadata_manager.py
```

Windows版はExifToolによるRAW/JPEG等の詳細タグ抽出、グループ別検索、2写真比較、全タグCSV・JSON台帳、変更候補作成、XMP保存、JPEGコピーへのXMP埋込に対応します。RAW対応範囲はExifToolに依存し、全機種での試験は行っていません。

## 編集と保存の意味

- 編集対象：説明、権利、ラベル、評価、撮影日時、緯度、経度。
- 撮影日時はISO 8601形式（例 `2026-10-23T20:00:00.123+09:00`）。時差を含めて入力できます。時差がなければ自動的にJST等を補いません。
- GPSは符号付き十進度で入力し、XMP保存時に規定の度・分・方位表現へ変換します。高さ・基準系の変換は行いません。
- XMPは標準EXIFとは別の保存先です。JPEGコピーでも元EXIFのGPS・撮影日時は変更しません。異なる値が並存するので、利用先がどちらを読むか確認してください。
- MakerNotes・原本RAWへの書込み、削除、一括CSV付与は初版の対象外です。
- XMPは新規サイドカーです。既存のサイドカーとの結合はしません。Windows版は既存出力への上書きを拒否します。
- XMP生成後はXML再読取で対象値を確認します。Windows版JPEGコピーはExifToolで再読取し、原本SHA-256不変も確認してから出力します。コピーと同時に監査JSONを保存します。
- XMPだけでは変更理由を保持しません。元タグ・変更理由・候補を保持するJSON台帳も保存してください。JSONは変更候補の状態を保存するもので、JPEG保存済み証明は `.audit.json` を確認してください。
- 旧版のJSON（`exif_raw`形式）、ExifToolのJSON配列、新しいJSON台帳を読み込めます。グループなしJSONは分類不能として表示し、由来を推測しません。

## 今回の検証と残る確認

`docs/VALIDATION.md` を参照してください。Windowsのビルド・EXE実行、実PEF、ブラウザでの画面操作は未検証です。初版を業務の原本に適用する前に、コピーと小規模データで確認してください。

NMEA照合は今回の新GUIには接続しません。旧ソースを `src/legacy_pef_exif_nmea_explorer.py` に変更せず保存しています。旧版の照合OKは、露光同期・姿勢の精度を保証しません。

## 開発用

- `src/metadata_core.py`: GUI非依存処理
- `src/photo_metadata_manager.py`: PySide6 GUI
- `web/core.js`, `web/app.js`: 読取・表示処理。変更後 `python build_web.py` で単体HTMLを更新
- `tests/`: Python・Nodeの自動検査（Python画像試験はPillowが必要）
- `docs/IMPLEMENTATION.md`: 対象・変更範囲・完了条件

```powershell
py -m pip install Pillow
$env:TEST_EXIFTOOL = (Resolve-Path tools/exiftool.exe).Path
py -m unittest discover -s tests -v
node tests/test_web.cjs examples/SYNTHETIC_sample.jpg
```

## 同梱物と権利

既存アプリの受領ソースを保管していますが、ライセンス指定は確認できていません。本パッケージ全体の再配布ライセンスは未確定です。ExifToolは作者Phil Harveyのソフトウェアです。利用・再配布条件は `tools/ExifTool_README.txt` および `tools/exiftool_files/LICENSE` 等に従ってください。PySide6/Qt等のWindowsバイナリを配布する際は、使用するパッケージのライセンス・同梱通知も確認してください。

## Git管理

ソース・合成サンプル・テスト・検証記録をGitで管理します。実写真・実NMEA・出力ファイル・ビルド生成物・第三者バイナリは登録しません。GitHub上のCIはコア処理とJavaScriptの自動検査を実行する設定です。CIの合格はWindows EXE・実機・ブラウザ操作の合格を意味しません。

Gitから取得した場合は `tools/README.md` に従ってExifToolを配置してください。初回配布ZIPとGit管理版では、ExifToolバイナリの同梱有無が異なります。
