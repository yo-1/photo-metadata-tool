"""Photo metadata v0.1: grouped evidence, XMP edits, immutable originals."""
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

VERSION = '0.1.0'
NS = {'x':'adobe:ns:meta/', 'rdf':'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
      'dc':'http://purl.org/dc/elements/1.1/', 'xmp':'http://ns.adobe.com/xap/1.0/',
      'exif':'http://ns.adobe.com/exif/1.0/'}
FIELDS = {'Description':('dc','description'), 'Rights':('dc','rights'),
          'Label':('xmp','Label'), 'Rating':('xmp','Rating'),
          'DateTimeOriginal':('exif','DateTimeOriginal'),
          'GPSLatitude':('exif','GPSLatitude'), 'GPSLongitude':('exif','GPSLongitude')}
SUPPORTED = {'.pef','.dng','.jpg','.jpeg','.tif','.tiff','.orf','.rw2','.cr2','.cr3','.nef','.arw'}


def category(key):
    groups = key.split(':')[:-1]
    if any(g.startswith('XMP') for g in groups): return 'XMP'
    if 'Composite' in groups: return 'Composite'
    if 'MakerNotes' in groups or any(g in {'Pentax','Canon','Nikon','Olympus','Panasonic','Sony','PentaxDng','LevelInfo'} for g in groups): return 'MakerNotes'
    if 'GPS' in groups: return 'GPS'
    if any(g in {'EXIF','IFD0','IFD1','ExifIFD','InteropIFD','SubIFD'} for g in groups): return 'EXIF/TIFF'
    if not groups or any(g in {'File','System','ExifTool'} for g in groups): return 'File/System' if key == 'SourceFile' or groups else 'Unclassified'
    return 'Other'


def normalize(payload):
    if isinstance(payload, dict):
        if 'exif_raw' in payload: payload = payload['exif_raw']
        elif 'records' in payload: payload = payload['records']
        else: payload = [payload]
    if not isinstance(payload, list): raise ValueError('ExifToolのJSON配列または管理台帳を指定してください')
    records=[]
    for i, item in enumerate(payload):
        if not isinstance(item,dict): raise ValueError('JSON項目がオブジェクトではありません')
        if 'tags' in item and isinstance(item['tags'], dict): records.append(item)
        else: records.append({'source':item.get('SourceFile',f'photo_{i+1}'),'tags':item, 'reader':'ExifTool JSON', 'warnings':[]})
    return records


def find_tool():
    base = Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent.parent
    for p in [base/'tools'/'exiftool.exe', base/'tools'/'exiftool',base/'exiftool.exe']:
        if p.is_file(): return str(p)
    tool=shutil.which('exiftool') or shutil.which('exiftool.exe')
    if not tool: raise FileNotFoundError('tools/exiftool.exe と exiftool_files を配置してください')
    return tool


def run_tool(args):
    cp=subprocess.run([find_tool(),*args],capture_output=True,encoding='utf-8',errors='strict',shell=False,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,timeout=180)
    if cp.returncode != 0: raise RuntimeError(cp.stderr.strip() or cp.stdout.strip() or 'ExifTool failed')
    return cp.stdout,cp.stderr.strip()


def extract(paths):
    paths=[str(Path(p).resolve(strict=True)) for p in paths]
    # Family 0 preserves EXIF/MakerNotes; family 4 disambiguates repeated instances.
    out,warnings=run_tool(['-json','-G0:1:4','-a','-u','-s','-n','-charset','filename=utf8',*paths])
    records=normalize(json.loads(out))
    for r in records:
        if warnings:r.setdefault('warnings',[]).append(warnings)
        r['reader']='ExifTool numeric / G0:1:4'
    return records


def validate(field,value):
    if field not in FIELDS: raise ValueError('編集対象外のタグです')
    value=str(value).strip()
    if not value: raise ValueError('初版では削除・空欄への変更に対応しません')
    if any(ord(c)<32 and c not in '\n\r\t' for c in value): raise ValueError('制御文字は保存できません')
    if field=='Rating' and value not in {'-1','0','1','2','3','4','5'}: raise ValueError('評価は-1～5の整数です')
    if field.startswith('GPS'):
        number=float(value); limit=90 if field=='GPSLatitude' else 180
        if not math.isfinite(number) or abs(number)>limit: raise ValueError('緯度・経度が範囲外です')
        return format(number,'.10g')
    if field=='DateTimeOriginal':
        from datetime import datetime
        if not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)?',value): raise ValueError('日時は ISO 8601形式です（例 2026-10-23T20:00:00+09:00）')
        datetime.fromisoformat(value.replace('Z','+00:00'))
    return value


def make_plan(record,field,value,reason):
    value=validate(field,value)
    if not reason.strip(): raise ValueError('変更理由を記入してください')
    prefix,local=FIELDS[field]
    before={k:v for k,v in record['tags'].items() if k.split(':')[-1].lower() in {field.lower(),local.lower()}}
    return {'source':record['source'],'field':field,'target':f'XMP-{prefix}:{local}',
            'before':before,'after':value,'reason':reason.strip(),'state':'candidate'}


def gps_xmp(field,value):
    v=float(value); deg=int(abs(v)); minutes=(abs(v)-deg)*60
    hemi=('N' if v>=0 else 'S') if field=='GPSLatitude' else ('E' if v>=0 else 'W')
    return f'{deg},{minutes:.10f}{hemi}'


def plan_values(plans):
    result={}
    for p in plans:
        field=p['field']; value=validate(field,p['after'])
        if field in result: raise ValueError('同じタグの変更候補が重複しています')
        result[field]=gps_xmp(field,value) if field.startswith('GPS') else value
    return result


def xmp_bytes(plans):
    for k,v in NS.items(): ET.register_namespace(k,v)
    root=ET.Element(f'{{{NS["x"]}}}xmpmeta'); rdf=ET.SubElement(root,f'{{{NS["rdf"]}}}RDF')
    desc=ET.SubElement(rdf,f'{{{NS["rdf"]}}}Description',{f'{{{NS["rdf"]}}}about':''})
    for field,value in plan_values(plans).items():
        prefix,local=FIELDS[field]; node=ET.SubElement(desc,f'{{{NS[prefix]}}}{local}')
        if prefix=='dc':
            alt=ET.SubElement(node,f'{{{NS["rdf"]}}}Alt')
            ET.SubElement(alt,f'{{{NS["rdf"]}}}li',{'{http://www.w3.org/XML/1998/namespace}lang':'x-default'}).text=value
        else: node.text=value
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)


def verify_xmp(data,plans):
    root=ET.fromstring(data)
    for field,value in plan_values(plans).items():
        prefix,local=FIELDS[field]; node=root.find(f'.//{{{NS[prefix]}}}{local}')
        if node is None or ''.join(node.itertext())!=value: raise RuntimeError('XMP再読取不一致: '+field)


def exclusive_write(path,data):
    with Path(path).open('xb') as f:f.write(data)


def save_sidecar(path,plans):
    if not plans: raise ValueError('変更候補がありません')
    if len({p['source'] for p in plans})!=1: raise ValueError('1つの写真の変更候補を指定してください')
    data=xmp_bytes(plans); verify_xmp(data,plans)
    exclusive_write(path,data)
    verify_xmp(Path(path).read_bytes(),plans)


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def save_jpeg_copy(source,target,plans):
    source=Path(source).resolve(strict=True); target=Path(target).resolve()
    if source.suffix.lower() not in {'.jpg','.jpeg'} or target.suffix.lower() not in {'.jpg','.jpeg'}: raise ValueError('コピー書込みはJPEGのみです')
    if not plans or any(Path(p['source']).resolve()!=source for p in plans): raise ValueError('写真と変更候補が一致しません')
    if target.exists() or source==target: raise FileExistsError('既存ファイルには上書きしません')
    original=digest(source)
    with tempfile.TemporaryDirectory(dir=target.parent) as tmp:
        work=Path(tmp)/source.name; shutil.copy2(source,work)
        args=['-overwrite_original','-charset','filename=utf8']
        for field,value in plan_values(plans).items():
            prefix,local=FIELDS[field]; args.append(f'-XMP-{prefix}:{local}={value}')
        run_tool([*args,str(work)])
        read=extract([work])[0]['tags']
        for field,value in plan_values(plans).items():
            prefix,local=FIELDS[field]
            found=[v for k,v in read.items() if f'XMP-{prefix}' in k.split(':')[:-1] and k.split(':')[-1].lower()==local.lower()]
            if field.startswith('GPS'):
                ok=any(abs(float(v)-float(plans[[p['field'] for p in plans].index(field)]['after']))<1e-7 for v in found)
            elif field=='DateTimeOriginal':
                ok=any(str(v)[:10].replace(':','-')+'T'+str(v)[11:]==value for v in found)
            else: ok=any(str(v)==value for v in found)
            if not ok: raise RuntimeError('保存後の再読取不一致: '+field)
        if digest(source)!=original: raise RuntimeError('原本の変更を検出しました')
        os.link(work,target) # exclusive publication; never replace an existing output
    return {'source_sha256':original,'output_sha256':digest(target),'verification':'reread_passed','plans':plans}


def csv_text(records):
    out=io.StringIO(newline=''); writer=csv.writer(out); writer.writerow(['source','category','tag','value'])
    for r in records:
        for k,v in r['tags'].items():
            val=json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else str(v)
            writer.writerow([safe_cell(r['source']),category(k),safe_cell(k),safe_cell(val)])
    return '\ufeff'+out.getvalue()


def safe_cell(value):
    value=str(value)
    return "'"+value if value.lstrip().startswith(('=','+','-','@')) else value
