"""Desktop UI; core is independently testable without Qt."""
import json
import sys
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,
    QPushButton,QLabel,QFileDialog,QTableWidget,QTableWidgetItem,QLineEdit,QComboBox,
    QTextEdit,QMessageBox,QSplitter)
import metadata_core as core

class Reader(QThread):
    result=Signal(object); failed=Signal(str)
    def __init__(self,files): super().__init__(); self.files=files
    def run(self):
        try:self.result.emit(core.extract(self.files))
        except Exception as e:self.failed.emit(str(e))

class Window(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle('写真メタデータ管理ツール '+core.VERSION); self.resize(1280,820)
        self.records=[]; self.plans=[]; self.worker=None
        root=QWidget(); layout=QVBoxLayout(root); self.setCentralWidget(root)
        bar=QHBoxLayout()
        for title,fn in [('写真を追加',self.load_photos),('フォルダを追加',self.load_folder),('JSONを追加',self.load_json),('JSON台帳保存',self.export_json),('CSV保存',self.export_csv),('Excel保存',self.export_xlsx),('クリア',self.clear)]:
            b=QPushButton(title);b.clicked.connect(fn);bar.addWidget(b)
        layout.addLayout(bar)
        layout.addWidget(QLabel('原本を保持 / 編集はXMPへ保存 / 姿勢タグは取得値として保持し、検証済みとは扱いません'))
        selectors=QHBoxLayout();self.first=QComboBox();self.second=QComboBox();self.second.addItem('比較なし',-1)
        self.search=QLineEdit();self.search.setPlaceholderText('タグ名・値を検索')
        self.group=QComboBox();self.group.addItems(['すべて','EXIF/TIFF','GPS','MakerNotes','XMP','Composite','File/System','Other','Unclassified'])
        for w in [self.first,self.second,self.group,self.search]:selectors.addWidget(w)
        layout.addLayout(selectors)
        self.table=QTableWidget(0,4);self.table.setHorizontalHeaderLabels(['分類','元タグ（グループ保持）','写真A','写真B'])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers);layout.addWidget(self.table,1)
        edits=QHBoxLayout();self.field=QComboBox();self.field.addItems(core.FIELDS)
        self.value=QLineEdit();self.value.setPlaceholderText('変更後の値（緯度経度は十進度、日時はISO形式）')
        self.reason=QLineEdit();self.reason.setPlaceholderText('変更理由')
        for w in [self.field,self.value,self.reason]:edits.addWidget(w)
        for title,fn in [('候補を追加／更新',self.stage),('候補を破棄',self.discard)]:
            b=QPushButton(title);b.clicked.connect(fn);edits.addWidget(b)
        layout.addLayout(edits)
        self.preview=QTextEdit();self.preview.setReadOnly(True);self.preview.setMaximumHeight(160);layout.addWidget(self.preview)
        savebar=QHBoxLayout()
        for title,fn in [('XMPサイドカー保存',self.save_xmp),('JPEGコピーへ保存',self.save_copy)]:
            b=QPushButton(title);b.clicked.connect(fn);savebar.addWidget(b)
        layout.addLayout(savebar);self.status=QLabel('写真またはExifTool JSONを追加してください');layout.addWidget(self.status)
        for w in [self.first,self.second,self.group]:w.currentIndexChanged.connect(self.render)
        self.search.textChanged.connect(self.render)
    def error(self,e):QMessageBox.warning(self,'処理できません',str(e))
    def load_photos(self):
        if self.worker and self.worker.isRunning():return
        files,_=QFileDialog.getOpenFileNames(self,'写真を選択','','Photos (*.pef *.PEF *.jpg *.jpeg *.dng *.tif *.tiff *.orf *.rw2 *.cr2 *.cr3 *.nef *.arw);;All (*)')
        if not files:return
        self.status.setText('読取中…');self.worker=Reader(files);self.worker.result.connect(self.add);self.worker.failed.connect(self.error);self.worker.start()
    def load_folder(self):
        if self.worker and self.worker.isRunning():return
        folder=QFileDialog.getExistingDirectory(self,'写真フォルダ（サブフォルダを含む）')
        if not folder:return
        files=sorted(p for p in Path(folder).rglob('*') if p.is_file() and p.suffix.lower() in core.SUPPORTED)
        if not files:self.error('対応する写真がありません');return
        self.status.setText(f'{len(files)}写真を読取中…');self.worker=Reader(files);self.worker.result.connect(self.add);self.worker.failed.connect(self.error);self.worker.start()
    def load_json(self):
        files,_=QFileDialog.getOpenFileNames(self,'JSONを選択','','JSON (*.json)')
        for path in files:
            try:
                payload=json.loads(Path(path).read_text(encoding='utf-8-sig')); records=core.normalize(payload)
                restored=[]
                if isinstance(payload,dict):
                    for p in payload.get('plans',[]):
                        r=next((r for r in records if r['source']==p['source']),None)
                        if r: restored.append(core.make_plan(r,p['field'],p['after'],p['reason']))
                if self.add(records):self.plans.extend(restored);self.show_plans()
            except Exception as e:self.error(e)
    def add(self,records):
        used={r['source'] for r in self.records}
        for r in records:
            if r['source'] in used:
                self.error('同じ写真識別名が既にあります。先にクリアしてください');return False
            used.add(r['source'])
        self.records.extend(records)
        self.first.blockSignals(True);self.second.blockSignals(True)
        self.first.clear();self.second.clear();self.second.addItem('比較なし',-1)
        for i,r in enumerate(self.records):
            label=f'{i+1}: {r["source"]}';self.first.addItem(label,i);self.second.addItem(label,i)
        self.first.blockSignals(False);self.second.blockSignals(False);self.render()
        self.status.setText(f'{len(self.records)}写真 / '+ '; '.join(w for r in records for w in r.get('warnings',[])))
        return True
    def selected(self):
        i=self.first.currentData()
        if i is None:raise ValueError('写真を選択してください')
        return self.records[i]
    def render(self,*_):
        self.table.setRowCount(0)
        if not self.records:return
        a=self.selected()['tags'];j=self.second.currentData();b=self.records[j]['tags'] if j is not None and j>=0 else {}
        query=self.search.text().lower();group=self.group.currentText()
        for k in sorted(set(a)|set(b)):
            values=[core.category(k),k,json.dumps(a[k],ensure_ascii=False) if k in a else '—',json.dumps(b[k],ensure_ascii=False) if k in b else '—']
            if group!='すべて' and values[0]!=group:continue
            if query not in ' '.join(values).lower():continue
            row=self.table.rowCount();self.table.insertRow(row)
            for col,value in enumerate(values):self.table.setItem(row,col,QTableWidgetItem(value))
        self.table.resizeColumnsToContents();self.show_plans()
    def stage(self):
        try:
            plan=core.make_plan(self.selected(),self.field.currentText(),self.value.text(),self.reason.text())
            self.plans=[p for p in self.plans if (p['source'],p['field'])!=(plan['source'],plan['field'])]+[plan];self.show_plans()
        except Exception as e:self.error(e)
    def show_plans(self):self.preview.setPlainText(json.dumps(self.current_plans(),ensure_ascii=False,indent=2))
    def current_plans(self):return [p for p in self.plans if self.records and p['source']==self.selected()['source']]
    def discard(self):
        if self.records:self.plans=[p for p in self.plans if p['source']!=self.selected()['source']]
        self.show_plans()
    def save_xmp(self):
        try:
            plans=self.current_plans()
            if not plans:raise ValueError('先に変更候補を追加してください')
            path,_=QFileDialog.getSaveFileName(self,'XMPを新規保存',Path(self.selected()['source']).name+'.xmp','XMP (*.xmp)')
            if path:core.save_sidecar(path,plans);self.status.setText('XMP保存・再読取一致。変更理由はJSON台帳にも保存してください')
        except Exception as e:self.error(e)
    def save_copy(self):
        try:
            plans=self.current_plans()
            if not plans:raise ValueError('先に変更候補を追加してください')
            path,_=QFileDialog.getSaveFileName(self,'JPEGコピーを新規保存','edited_'+Path(self.selected()['source']).name,'JPEG (*.jpg *.jpeg)')
            if path:
                if Path(path+'.audit.json').exists():raise FileExistsError('監査JSONが既に存在します。別名で保存してください')
                report=core.save_jpeg_copy(self.selected()['source'],path,plans)
                core.exclusive_write(path+'.audit.json',json.dumps(report,ensure_ascii=False,indent=2).encode())
                self.status.setText('JPEGコピー保存・再読取一致・原本SHA-256不変。監査JSONも保存しました')
        except Exception as e:self.error(e)
    def export_json(self):
        path,_=QFileDialog.getSaveFileName(self,'台帳保存','metadata.json','JSON (*.json)')
        if path:
            try:core.exclusive_write(path,json.dumps({'version':core.VERSION,'records':self.records,'plans':self.plans},ensure_ascii=False,indent=2).encode())
            except Exception as e:self.error(e)
    def export_csv(self):
        path,_=QFileDialog.getSaveFileName(self,'CSV保存','metadata.csv','CSV (*.csv)')
        if path:
            try:core.exclusive_write(path,core.csv_text(self.records).encode())
            except Exception as e:self.error(e)
    def export_xlsx(self):
        try:
            from openpyxl import Workbook
            path,_=QFileDialog.getSaveFileName(self,'Excel保存','metadata.xlsx','Excel (*.xlsx)')
            if not path:return
            if Path(path).exists():raise FileExistsError('既存ファイルには上書きしません')
            wb=Workbook();ws=wb.active;ws.title='Metadata';ws.append(['source','category','tag','value'])
            for r in self.records:
                for k,v in r['tags'].items():
                    ws.append([core.safe_cell(r['source']),core.category(k),core.safe_cell(k),core.safe_cell(json.dumps(v,ensure_ascii=False))])
            ws.freeze_panes='A2';ws.auto_filter.ref=ws.dimensions
            for col,width in [('A',45),('B',20),('C',45),('D',70)]:ws.column_dimensions[col].width=width
            import io
            out=io.BytesIO();wb.save(out);core.exclusive_write(path,out.getvalue())
        except Exception as e:self.error(e)
    def clear(self):
        self.records=[];self.plans=[];self.first.clear();self.second.clear();self.table.setRowCount(0);self.preview.clear()
    def closeEvent(self,event):
        if self.worker and self.worker.isRunning():self.status.setText('読取完了後に終了してください');event.ignore()
        else:event.accept()

if __name__=='__main__':
    app=QApplication(sys.argv);w=Window();w.show();sys.exit(app.exec())
