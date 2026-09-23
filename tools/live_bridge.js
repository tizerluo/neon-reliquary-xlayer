(()=>{
'use strict';
const session=crypto.randomUUID(),key='__PAGE_TOKEN__';
const orders=new Map();let nextStatus=0;
const status=document.createElement('div');status.className='agent-bridge-status';status.style.cssText='font:10px/1.4 monospace;color:#8be4c5;margin-top:4px;pointer-events:none;overflow-wrap:anywhere';status.hidden=true;document.body.append(status);
async function post(path,data){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+key},body:JSON.stringify(data)});if(!r.ok)throw Error('HTTP '+r.status);return r.json();}
async function tick(){try{
 const response=await post('/poll',{session});
 for(const job of response.jobs){let result;
 try{
  if(!window.NRCoop)throw Error('GAME_LOADING');
  if(job.name==='nr_command'){
   const now=await NRCoop.call('nr_observe',{}),o=job.observation;
   if(!o||o.runId!==now.runId||job.args.runId!==o.runId)throw Error('STALE_DECISION_RUN');
   if(!Number.isFinite(o.observedAt)||Date.now()-o.observedAt>15000||o.observedAt>Date.now()+1000)throw Error('STALE_DECISION_AGE');
  }
  result=await NRCoop.call(job.name,job.args||{});
  if(job.name==='nr_observe'&&result.ok)result.observedAt=Date.now();
  if(job.name==='nr_command'&&result.ok)orders.set(job.args.agentId,{runId:job.args.runId,until:result.expiresAt,tactic:job.args.tactic});
 }catch(e){result={ok:false,error:e.message};}
 await post('/result',{session,id:job.id,result});
 }
 if(window.NRCoop&&Date.now()>nextStatus){
  nextStatus=Date.now()+500;const w=await NRCoop.call('nr_observe',{limit:1});
  const zh=document.documentElement.lang.startsWith('zh'),t=(en,cn)=>zh?cn:en;
  const seats=[...(w.leader?.controller==='external'?[{agentId:'leader',mode:'external',occupied:w.leader.connected,pending:false}]:[]),...w.slots];
  const labels=seats.filter(s=>s.mode==='external').map(s=>{
   if(!s.occupied)return t('Waiting for agent','等待 Agent 入队');
   if(s.pending)return t('Deploys next encounter','下一遭遇入场');
   if(w.state==='select'||w.state==='home')return t('Ready · waiting to start','已就位 · 等待开局');
   if(w.state==='paused')return t('Game paused','游戏暂停');
   if(w.state==='route'||w.state==='camp')return t('Waiting for route / camp choice','等待路线 / 营地选择');
   if(w.state==='result')return t('Expedition ended','本局结束');
   const u=w.units.find(u=>u.id===s.agentId),o=orders.get(s.agentId);
   if(u?.downed)return t('Downed · waiting for rescue','倒地 · 等待救援');
   if(o&&o.runId===w.runId&&o.until>=w.time&&!u?.stale)return t('Agent intent ','Agent 战术 ')+o.tactic+' · '+Math.ceil(o.until-w.time)+'s';
   return t('Local fallback · waiting for intent','本地接管 · 等待指令');
  });
  const host=document.getElementById('oathHUD');if(host&&status.parentElement!==host)host.append(status);
  status.hidden=!['play','paused'].includes(w.state);status.title=labels.join(' / ');
  const compact=seats.filter(s=>s.mode==='external').map((s,i)=>{
   const label=s.agentId==='leader'?t('Leader','队长'):t('Ally ','队友 ')+(s.slot||i);
   const u=w.units.find(u=>u.id===s.agentId),o=orders.get(s.agentId);
   const detail=!s.occupied?t('waiting','等待'):s.pending?t('queued','待入场'):u?.downed?t('down','倒地'):o&&o.runId===w.runId&&o.until>=w.time&&!u?.stale?Math.ceil(o.until-w.time)+'s':t('local','本地');
   return label+' '+detail;
  });status.textContent=w.state==='paused'?t('Agent bridge · paused','协作连接 · 已暂停'):compact.join(' · ')||t('Agent bridge ready','协作连接正常');
 }
}catch(e){status.textContent='LOCAL AGENT · disconnected';}
setTimeout(tick,100);
}tick();
})();
