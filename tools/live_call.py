"""Call an existing game tool; JSON args from stdin. Credentials never printed."""
import json,sys,urllib.request
from pathlib import Path
cfg=json.loads((Path(__file__).parent/'.live-session.json').read_text())
data=json.load(sys.stdin)
req=urllib.request.Request(cfg['url']+'/call',data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+cfg['token']})
with urllib.request.urlopen(req,timeout=8) as r:print(r.read().decode())
