"""Rebuild the portable HTML from its readable JS sources."""
from pathlib import Path
import re
import json
root=Path(__file__).resolve().parent/'web'
catalog=json.loads((root.parent/'metadata_catalog.json').read_text(encoding='utf-8'))
core=root/'core.js'
core_text=re.sub(r'/\* CATALOG_START \*/.*?/\* CATALOG_END \*/',lambda _: '/* CATALOG_START */\nconst catalog='+json.dumps(catalog,ensure_ascii=False,separators=(',',':'))+';\n/* CATALOG_END */',core.read_text(encoding='utf-8'),flags=re.S)
core.write_text(core_text,encoding='utf-8')
p=root/'index.html'
s=p.read_text(encoding='utf-8')
s=re.sub(r'<script>.*?</script><script>.*?</script>',lambda _: '<script>'+ (root/'core.js').read_text(encoding='utf-8')+'</script><script>'+(root/'app.js').read_text(encoding='utf-8')+'</script>',s,flags=re.S)
p.write_text(s,encoding='utf-8')
