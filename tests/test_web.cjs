const assert=require('node:assert/strict'),fs=require('node:fs');
const M=require('../web/core.js');let count=0;
function check(name,fn){fn();count++;console.log('PASS '+name);}
check('groups and repeated instances retained',()=>{const r=M.normalize([{SourceFile:'A.PEF','Pentax:RollAngle':4,'EXIF:GPS:GPSLatitude':35,'Composite:GPSLatitude':36,'EXIF:IFD1:Make':'B'}])[0];assert.equal(Object.keys(r.tags).length,5);assert.equal(M.category('Pentax:RollAngle'),'MakerNotes');assert.equal(M.category('EXIF:GPS:GPSLatitude'),'GPS');});
check('legacy JSON import',()=>assert.equal(M.normalize({exif_raw:[{SourceFile:'A.PEF'}]}).length,1));
check('invalid edits rejected',()=>{for(const [f,v] of [['GPSLatitude','NaN'],['GPSLongitude','181'],['DateTimeOriginal','2026-02-30T12:00:00'],['Rating','10'],['RollAngle','1']])assert.throws(()=>M.validate(f,v));});
check('XMP escapes text and preserves GPS sign',()=>{const r={source:'a.jpg',tags:{}};const x=M.xmp([M.plan(r,'Description','<森林> & 調査','test'),M.plan(r,'GPSLatitude','-35.5','test')]);assert.ok(x.includes('&lt;森林&gt; &amp; 調査'));assert.ok(x.includes('35,30.0000000000S'));});
check('CSV formula neutralized',()=>assert.ok(M.csv([{source:'a',tags:{x:'=1+1'}}]).includes("'=1+1")));
check('malformed images rejected',()=>{assert.throws(()=>M.photo(new Uint8Array([1,2]).buffer,'bad.jpg'));const b=new Uint8Array(12);b.set([0xff,0xd8,0xff,0xe1,0,100]);assert.throws(()=>M.photo(b.buffer,'bad.jpg'));});
function tiff(le){const b=new ArrayBuffer(64),v=new DataView(b);v.setUint16(0,le?0x4949:0x4d4d);v.setUint16(2,42,le);v.setUint32(4,8,le);v.setUint16(8,1,le);v.setUint16(10,271,le);v.setUint16(12,2,le);v.setUint32(14,7,le);v.setUint32(18,32,le);new Uint8Array(b,32,7).set([80,69,78,84,65,88,0]);return b;}
check('little and big endian TIFF',()=>{for(const le of [true,false])assert.equal(M.photo(tiff(le),'test.pef').tags['EXIF:IFD0:Make'],'PENTAX');});
check('IFD cycle rejected',()=>{const b=tiff(true);new DataView(b).setUint32(22,8,true);assert.throws(()=>M.photo(b,'cycle.pef'));});
if(process.argv[2]){const b=fs.readFileSync(process.argv[2]);const r=M.photo(b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength),'fixture.jpg');assert.equal(r.tags['EXIF:IFD0:Make'],'PENTAX');assert.equal(r.tags['EXIF:ExifIFD:DateTimeOriginal'],'2026:10:23 20:00:00');console.log('PASS real ExifTool-generated JPEG standard tags');count++;}
console.log(`${count} web checks passed`);
