# 初版の変更範囲・完了条件

対象: 外部ExifTool版（受領ZIP）を保存し、新規の独立処理と管理GUIを追加。

|対象|変更範囲|完了条件|
|---|---|---|
|src/legacy_pef_exif_nmea_explorer.py|受領版をそのまま保管|既存処理を比較可能。新GUIから自動実行しない|
|src/metadata_core.py|全タグ読取・分類、変更候補、XMP、JPEGコピー保存|グループ保持、原本ハッシュ不変、再読取一致、既存出力を上書きしない|
|src/photo_metadata_manager.py|既存と同じPySide6のGUI基盤|検索、2写真比較、出力、差分プレビュー、保存|
|web/index.html|依存不要のローカルHTML|通信なし、JPEG/TIFF/PEFの標準TIFFタグを読取、JSON取込、比較、XMPと台帳出力|
|build_exe.bat|onedir配布|toolsを外置き、失敗時停止。Windowsビルドと実機試験は別途|

編集はXMPの説明・権利・ラベル・評価・時差を含む日時・GPSに限定。MakerNotes、RAW画像、画素は編集しない。RAWはXMPサイドカー、JPEGはXMP埋込コピーも選択可。元値・変更理由はJSON台帳に保存。ブラウザ内のPEF MakerNotes、未知タグ、拡張XMP、BigTIFFは完全対応としない。ExifTool JSON経由で全タグを扱う。

NMEAは旧版を保存するのみ。旧照合のOKを同期精度・姿勢の検証済み根拠にしない。Drogger側の採用規則確定後に独立モジュールとして接続。

実PEF・実NMEAは今回取得した2つのZIPには入っていない。合成データ検査と実カメラ検証を区別する。
