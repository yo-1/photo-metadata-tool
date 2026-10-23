'use strict';
const M=PhotoMeta,$=id=>document.getElementById(id);let records=[],plans=[];
function message(v){$('status').textContent=v;}
function current(){const r=records[+$('first').value];if(!r)throw Error('写真を追加してください');return r;}
function currentPlans(){return plans.filter(p=>p.source===current().source);}
function fill(){for(const id of ['first','second']){$(id).replaceChildren();if(id==='second')$(id).add(new Option('比較なし','-1'));records.forEach((r,i)=>$(id).add(new Option(`${i+1}. ${r.source}`,i)));}render();}
function render(){
 if(!records.length){$('tbody').replaceChildren();$('warnings').textContent='';$('preview').textContent='変更候補はありません';return;}
 const a=current(),b=records[+$('second').value],query=$('search').value.toLowerCase(),group=$('group').value,frag=document.createDocumentFragment();
 for(const k of [...new Set([...Object.keys(a.tags),...Object.keys(b?.tags||{})])].sort()){
  const hasA=Object.hasOwn(a.tags,k),hasB=b&&Object.hasOwn(b.tags,k),av=hasA?JSON.stringify(a.tags[k]):'—',bv=hasB?JSON.stringify(b.tags[k]):'—',cat=M.category(k),help=M.tagHelp(k),humanA=hasA?M.humanValue(k,a.tags[k],a):'—',humanB=hasB?M.humanValue(k,b.tags[k],b):'—';
  if(group&&group!==cat||![k,av,bv,help.label,help.description,humanA,humanB].join(' ').toLowerCase().includes(query))continue;
  const tr=document.createElement('tr');if(b&&av!==bv)tr.className='different';
  const categoryCell=document.createElement('td');categoryCell.textContent=help.groupLabel;tr.append(categoryCell);
  const nameCell=document.createElement('td'),label=document.createElement('strong'),rawTag=document.createElement('small');label.textContent=help.label;rawTag.textContent=k;rawTag.className='rawtag';nameCell.append(label,rawTag);
  const details=document.createElement('details'),summary=document.createElement('summary'),explanation=document.createElement('p');summary.textContent='意味・注意点';explanation.textContent=help.description;details.append(summary,explanation);nameCell.append(details);tr.append(nameCell);
  for(const [has,pretty,raw] of [[hasA,humanA,av],[hasB,humanB,bv]]){const td=document.createElement('td'),main=document.createElement('div');main.textContent=pretty;td.append(main);if(has){const d=document.createElement('details'),s=document.createElement('summary'),code=document.createElement('code');s.textContent='元の値';code.textContent=raw;d.append(s,code);td.append(d);}tr.append(td);}
  frag.append(tr);
 }
 $('tbody').replaceChildren(frag);$('count').textContent=records.length+'写真 / '+$('tbody').children.length+'タグ';$('warnings').textContent=(a.reader||'')+' — '+(a.warnings||[]).join(' / ');$('preview').textContent=JSON.stringify(currentPlans(),null,2);
}
function appendRecords(rr){const used=new Set(records.map(r=>r.source));for(const r of rr){if(used.has(r.source))throw Error('同じ識別名が既にあります。クリアするか、フルパスを持つExifTool JSONを使用してください');used.add(r.source);}records.push(...rr);}
async function addFiles(files){let errors=[],count=0;for(const file of files){try{if(file.size>256*1024*1024)throw Error('256MBを超えるファイルです。ExifTool JSONで取り込んでください');message('読取中: '+file.name);if(/\.json$/i.test(file.name)){const payload=JSON.parse((await file.text()).replace(/^\uFEFF/,''));const rr=M.normalize(payload);appendRecords(rr);if(Array.isArray(payload.plans)){for(const p of payload.plans){const r=rr.find(r=>r.source===p.source);if(r){const valid=M.plan(r,p.field,p.after,p.reason);plans=plans.filter(x=>x.source!==p.source||x.field!==p.field);plans.push(valid);}}}}else appendRecords([M.photo(await file.arrayBuffer(),file.name)]);count++;}catch(e){errors.push(file.name+': '+e.message);}}fill();message(`${count}ファイル読取完了`+(errors.length?' / '+errors.join(' / '):''));}
function download(name,text,type){const blob=new Blob([text],{type}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);}
function act(fn){return ()=>{try{fn();}catch(e){message(e.message);}};}
$('files').onchange=e=>addFiles(e.target.files);
$('drop').ondragover=e=>{e.preventDefault();};$('drop').ondrop=e=>{e.preventDefault();addFiles(e.dataTransfer.files);};
for(const id of ['first','second','group','search'])$(id).addEventListener(id==='search'?'input':'change',render);
for(const f of Object.keys(M.fields))$('field').add(new Option((M.catalog[f]?.label||f)+'（'+f+'）',f));
$('stage').onclick=act(()=>{const p=M.plan(current(),$('field').value,$('value').value,$('reason').value);plans=plans.filter(x=>x.source!==p.source||x.field!==p.field);plans.push(p);render();message('変更候補を追加しました。保存前に差分を確認してください');});
$('discard').onclick=act(()=>{plans=plans.filter(p=>p.source!==current().source);render();});
$('json').onclick=act(()=>{if(!records.length)throw Error('写真を追加してください');download('photo_metadata.json',JSON.stringify({version:'0.1.1',records,plans},null,2),'application/json');});
$('csv').onclick=act(()=>{if(!records.length)throw Error('写真を追加してください');download('photo_metadata.csv',M.csv(records),'text/csv;charset=utf-8');});
$('xmp').onclick=act(()=>{const pp=currentPlans(),text=M.xmp(pp),xml=new DOMParser().parseFromString(text,'application/xml');if(xml.querySelector('parsererror'))throw Error('XMP再読取失敗');for(const p of pp){const [pre,key]=M.fields[p.field],names={dc:'http://purl.org/dc/elements/1.1/',xmp:'http://ns.adobe.com/xap/1.0/',exif:'http://ns.adobe.com/exif/1.0/'};const nodes=xml.getElementsByTagNameNS(names[pre],key);let expected=M.validate(p.field,p.after);if(p.field.startsWith('GPS')){const n=+expected,d=Math.floor(Math.abs(n));expected=d+','+((Math.abs(n)-d)*60).toFixed(10)+(p.field==='GPSLatitude'?(n>=0?'N':'S'):(n>=0?'E':'W'));}if(nodes.length!==1||nodes[0].textContent!==expected)throw Error('XMP再読取不一致');}download(current().source.split(/[\\/]/).pop()+'.xmp',text,'application/rdf+xml');message('XMP生成・XML再読取済み。変更理由を含むJSON台帳も保存してください');});
$('clear').onclick=()=>{records=[];plans=[];$('files').value='';fill();message('クリアしました');};
