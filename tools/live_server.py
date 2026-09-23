"""Loopback-only gameplay tool bridge. No remote scripts, accounts or model keys."""
import json, secrets, threading, time, uuid, os, re, tempfile
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[1]
PORT=int(os.environ.get('NR_PORT','8766'))
TOKEN=secrets.token_urlsafe(32)
PAGE_TOKEN=secrets.token_urlsafe(32)
LOCK=threading.Lock()
PENDING={}
ACTIVE=None
TOOLS={'nr_roster','nr_observe','nr_join','nr_command','nr_heartbeat','nr_leave','nr_events'}

def load_session(path, port):
    """Keep the same private credentials across a local server restart."""
    url=f'http://127.0.0.1:{port}'
    saved=json.loads(path.read_text()) if path.exists() else {}
    if not isinstance(saved,dict):raise ValueError('INVALID_SESSION_FILE')
    if saved.get('url')!=url:saved={}
    values={'url':url}
    for key in ('token','page_token'):
        value=saved.get(key,secrets.token_urlsafe(32))
        if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]{43,128}',value):
            raise ValueError('INVALID_SESSION_CREDENTIAL')
        values[key]=value
    if values['token']==values['page_token']:raise ValueError('SESSION_CREDENTIALS_MUST_DIFFER')
    # Publish only after the private file is complete; never briefly create a
    # world-readable credential file even under a permissive umask.
    with tempfile.NamedTemporaryFile(mode='w',dir=path.parent,prefix='.live-session-',suffix='.json',delete=False) as out:
        temporary=Path(out.name)
        try:
            os.fchmod(out.fileno(),0o600)
            json.dump(values,out)
            out.flush();os.fsync(out.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:os.replace(temporary,path)
    finally:temporary.unlink(missing_ok=True)
    return values
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def send(self,status,data,kind='application/json'):
        raw=data.encode() if isinstance(data,str) else json.dumps(data).encode()
        self.send_response(status); self.send_header('Content-Type',kind); self.send_header('Content-Length',str(len(raw))); self.send_header('Cache-Control','no-store'); self.send_header('X-Frame-Options','DENY'); self.end_headers()
        try:self.wfile.write(raw)
        except (BrokenPipeError,ConnectionResetError):pass
    def safe(self):
        origin=self.headers.get('Origin')
        return self.headers.get('Host')==f'127.0.0.1:{PORT}' and (origin is None or origin==f'http://127.0.0.1:{PORT}')
    def do_GET(self):
        if not self.safe():return self.send(403,{'error':'ORIGIN'})
        if self.path=='/':
            html=(ROOT/'Neon_Reliquary_v3.html').read_text()
            script=(ROOT/'tools/live_bridge.js').read_text().replace('__PAGE_TOKEN__',PAGE_TOKEN)
            return self.send(200,html.replace('</body>','<script>'+script+'</script></body>'),'text/html; charset=utf-8')
        self.send(404,{'error':'NOT_FOUND'})
    def do_POST(self):
        global ACTIVE
        if not self.safe():return self.send(403,{'error':'ORIGIN'})
        key=PAGE_TOKEN if self.path in ('/poll','/result') else TOKEN
        if self.headers.get('Authorization')!='Bearer '+key:return self.send(403,{'error':'AUTH'})
        try:
            n=int(self.headers.get('Content-Length',0))
            if n<1 or n>65536:raise ValueError()
            data=json.loads(self.rfile.read(n))
            if not isinstance(data,dict):raise ValueError()
        except Exception:return self.send(400,{'error':'INVALID_JSON'})
        if self.path=='/poll':
            session=data.get('session')
            if not isinstance(session,str):return self.send(400,{'error':'SESSION'})
            with LOCK:
                if ACTIVE!=session:
                    ACTIVE=session
                    for p in PENDING.values():p['result']={'ok':False,'error':'PAGE_CHANGED'};p['event'].set()
                jobs=[]
                for i,p in PENDING.items():
                    if not p['sent'] and not p['event'].is_set() and p['deadline']>time.monotonic():
                        p['sent']=True;jobs.append({'id':i,'name':p['name'],'args':p['args'],'observation':p.get('observation')})
            return self.send(200,{'jobs':jobs})
        if self.path=='/result':
            with LOCK:
                p=PENDING.get(data.get('id'))
                if p and data.get('session')==ACTIVE:p['result']=data.get('result');p['event'].set()
            return self.send(200,{'ok':True})
        if self.path!='/call':return self.send(404,{'error':'NOT_FOUND'})
        if not isinstance(data.get('name'),str) or data['name'] not in TOOLS:return self.send(400,{'error':'UNKNOWN_TOOL'})
        if not isinstance(data.get('args',{}),dict):return self.send(400,{'error':'INVALID_ARGS'})
        if data['name']=='nr_command' and not isinstance(data.get('observation'),dict):return self.send(400,{'error':'OBSERVATION_REQUIRED'})
        ident=uuid.uuid4().hex;p={**data,'event':threading.Event(),'sent':False,'deadline':time.monotonic()+5}
        with LOCK:
            if len(PENDING)>=16:return self.send(429,{'error':'BUSY'})
            PENDING[ident]=p
        p['event'].wait(5)
        with LOCK:PENDING.pop(ident,None)
        self.send(200,p.get('result',{'ok':False,'error':'GAME_NOT_CONNECTED_OR_TIMEOUT'}))
if __name__=='__main__':
    server=ThreadingHTTPServer(('127.0.0.1',PORT),Handler)
    session=load_session(ROOT/'tools/.live-session.json',PORT)
    TOKEN=session['token'];PAGE_TOKEN=session['page_token']
    print(f'Game ready: http://127.0.0.1:{PORT}',flush=True)
    server.serve_forever()
