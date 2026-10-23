"""Rebuild the portable HTML from its readable JS sources."""
from pathlib import Path
import re
root=Path(__file__).resolve().parent/'web'
p=root/'index.html'
s=p.read_text(encoding='utf-8')
s=re.sub(r'<script>.*?</script><script>.*?</script>',lambda _: '<script>'+ (root/'core.js').read_text(encoding='utf-8')+'</script><script>'+(root/'app.js').read_text(encoding='utf-8')+'</script>',s,flags=re.S)
p.write_text(s,encoding='utf-8')
