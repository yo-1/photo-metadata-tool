import json,os,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import metadata_core as m
from PIL import Image

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.dir=Path(self.tmp.name);self.source=self.dir/'日本語 空白.jpg'
        Image.new('RGB',(16,16),(30,80,50)).save(self.source)
        self.r={'source':str(self.source),'tags':{'EXIF:ExifIFD:DateTimeOriginal':'2026:10:23 20:00:00','MakerNotes:Pentax:RollAngle':4,'Composite:GPSLatitude':35},'warnings':[]}
    def tearDown(self):self.tmp.cleanup()
    def test_group_preservation(self):
        r=m.normalize([self.r['tags']])[0];self.assertEqual(len(r['tags']),3)
        self.assertEqual(m.category('MakerNotes:Pentax:RollAngle'),'MakerNotes')
        self.assertEqual(m.category('EXIF:GPS:GPSLatitude'),'GPS')
        self.assertEqual(m.category('Composite:GPSLatitude'),'Composite')
        self.assertEqual(m.category('XMP:XMP-exif:GPSLatitude'),'XMP')
    def test_sidecar_escapes_and_exclusive(self):
        p=m.make_plan(self.r,'Description','<森林> & "調査"','検証');path=self.dir/'test.xmp';m.save_sidecar(path,[p]);m.verify_xmp(path.read_bytes(),[p]);original=path.read_bytes()
        with self.assertRaises(FileExistsError):m.save_sidecar(path,[p])
        self.assertEqual(path.read_bytes(),original)
    def test_reject_bad_edits(self):
        for f,v in [('GPSLatitude','nan'),('GPSLongitude','181'),('Rating','6'),('DateTimeOriginal','2026-02-30T00:00:00'),('RollAngle','1')]:
            with self.subTest(f=f):
                with self.assertRaises((ValueError,KeyError)):m.make_plan(self.r,f,v,'検証')
        with self.assertRaises(ValueError):m.make_plan(self.r,'Label','x','')
    def test_csv_formula(self):self.assertIn("'=SUM(1,2)",m.csv_text([{'source':'a','tags':{'x':'=SUM(1,2)'}}]))
    def test_raw_not_writable(self):
        raw=self.dir/'test.pef';raw.write_bytes(b'raw');p=m.make_plan({'source':str(raw),'tags':{}},'Label','x','test')
        with self.assertRaises(ValueError):m.save_jpeg_copy(raw,self.dir/'out.pef',[p])
        self.assertEqual(raw.read_bytes(),b'raw')
    @unittest.skipUnless(os.environ.get('TEST_EXIFTOOL'),'TEST_EXIFTOOL not configured')
    def test_real_exiftool_roundtrip(self):
        m.find_tool=lambda:os.environ['TEST_EXIFTOOL']
        original=m.digest(self.source);r=m.extract([self.source])[0];self.assertIn('File:FileType',r['tags'])
        cases={'Description':'<森林> & 調査','Rights':'著作権 テスト','Label':'検証','Rating':'4','DateTimeOriginal':'2026-10-23T20:00:00.123+09:00','GPSLatitude':'-35.12345678','GPSLongitude':'139.12345678'}
        for field,value in cases.items():
            with self.subTest(field=field):
                target=self.dir/(field+'.jpg');p=m.make_plan(r,field,value,'roundtrip')
                report=m.save_jpeg_copy(self.source,target,[p]);self.assertEqual(report['verification'],'reread_passed');self.assertEqual(m.digest(self.source),original)
                self.assertEqual(Image.open(target).tobytes(),Image.open(self.source).tobytes())
        existing=self.dir/'exists.jpg';existing.write_bytes(b'keep')
        with self.assertRaises(FileExistsError):m.save_jpeg_copy(self.source,existing,[m.make_plan(r,'Label','x','test')])
        self.assertEqual(existing.read_bytes(),b'keep')

if __name__=='__main__':unittest.main()
