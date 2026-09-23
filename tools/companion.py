"""Agent-side helper. Observe, reason in the agent, then command JSON on stdin."""
import json,sys,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOLS=ROOT/'tools'
cfg=json.loads((TOOLS/'.live-session.json').read_text())
identity=json.loads((TOOLS/'.companion-session.json').read_text())
def call(name,args,observation=None):
 data={'name':name,'args':args}
 if observation:data['observation']=observation
 req=urllib.request.Request(cfg['url']+'/call',json.dumps(data).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+cfg['token']})
 with urllib.request.urlopen(req,timeout=8) as r:return json.load(r)
auth={k:identity[k] for k in ('agentId','token')}
mode=sys.argv[1] if len(sys.argv)>1 else 'observe'
if mode=='observe':
 result=call('nr_observe',{'agentId':identity['agentId'],'limit':8})
 if result.get('ok'):
  p=TOOLS/'.observation-session.json';p.write_text(json.dumps(result));p.chmod(0o600)
  call('nr_heartbeat',auth)
elif mode=='command':
 order=json.load(sys.stdin);world=json.loads((TOOLS/'.observation-session.json').read_text())
 seq=identity.get('nextSeq',1)
 result=call('nr_command',{**order,**auth,'seq':seq,'runId':world['runId']}, {'runId':world['runId'],'observedAt':world['observedAt']})
 identity['nextSeq']=seq+1
 (TOOLS/'.companion-session.json').write_text(json.dumps(identity))
 with (ROOT/'evidence/live-coop/commands.jsonl').open('a') as f:f.write(json.dumps({'at':time.time(),'order':order,'result':result})+'\n')
elif mode=='heartbeat':result=call('nr_heartbeat',auth)
else:raise SystemExit('Use observe, command, heartbeat')
print(json.dumps(result,ensure_ascii=False))
