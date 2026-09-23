/* Oath Circuit ABI 1. Pure NAND/LATCH compiler and bounded evaluator.
 * Signals 0/1 are constants; inputs start at 2; final nOut signals are outputs.
 * Encoding: NAND=0 + two big-endian u24 IDs; LATCH=1 + D u24.
 * State is caller-owned, sampled once per logical step. No REF or executable JS.
 */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.NRCircuits=api;})(globalThis,()=>{
 'use strict';
 const VERSION=1,MAX_GATES=1024,MAX_STATE=4,INPUTS=Object.freeze([
  'ally_down','self_low','self_recovered','boss','ally_low','skill_ready','ultimate_ready','danger','blade_room','objective','objective_threat','rescue_event','leader_assault','leader_guard','distant','alive','relic_ready','effect_applied','boss_window','moving'
 ]);
 const ACTIONS=Object.freeze(['guard','rescue','retreat','focus','assault','objective','follow']);
 const EFFECTS=Object.freeze(['shield','heal','repulse','fury','frost','charge']);
 const CONDITIONS=Object.freeze(['always','ally_down','self_low','boss','ally_low','danger','objective','objective_threat','leader_assault','leader_guard','distant','boss_window','moving','boss_or_crowd','safe']);
 const text=(value,max=48)=>{if(typeof value!=='string'||!value.trim()||value.length>max||/[\u0000-\u001f]/.test(value))throw Error('INVALID_TEXT');return value.trim();};
 const exact=(x,keys)=>{if(!x||typeof x!=='object'||Array.isArray(x)||Object.keys(x).some(k=>!keys.includes(k)))throw Error('INVALID_BLUEPRINT');};
 function normalize(x){
  exact(x,['version','kind','name','rules','skills','upgrade','memory','effect','trigger']);
  if(x.version!==1||!['tactic','relic'].includes(x.kind))throw Error('UNSUPPORTED_BLUEPRINT');
  const b={version:1,kind:x.kind,name:text(x.name)};
  if(x.kind==='tactic'){
   if(!Array.isArray(x.rules)||x.rules.length<1||x.rules.length>6)throw Error('RULE_LIMIT');
   b.rules=x.rules.map(r=>{exact(r,['when','action']);if(!CONDITIONS.includes(r.when)||!ACTIONS.includes(r.action))throw Error('INVALID_RULE');return{when:r.when,action:r.action};});
   exact(x.skills,['skill','ultimate','dash']);b.skills={};
   for(const k of ['skill','ultimate','dash']){if(!['never',...CONDITIONS].includes(x.skills[k]))throw Error('INVALID_SKILL_RULE');b.skills[k]=x.skills[k];}
   if(!['balanced','vigor','swarm','fury'].includes(x.upgrade)||!['none','recovery'].includes(x.memory))throw Error('INVALID_TACTIC_OPTION');
   b.upgrade=x.upgrade;b.memory=x.memory;
  }else{
   if(!EFFECTS.includes(x.effect)||!CONDITIONS.includes(x.trigger)||!['none','rescue'].includes(x.memory))throw Error('INVALID_RELIC_OPTION');
   b.effect=x.effect;b.trigger=x.trigger;b.memory=x.memory;
  }
  return b;
 }
 class Builder{
  constructor(){this.nodes=[];this.next=2+INPUTS.length;this.cache=new Map();}
  nand(a,b,force=false){
   if(!force){if(a===0||b===0)return 1;if(a===1&&b===1)return 0;const k=Math.min(a,b)+','+Math.max(a,b);if(this.cache.has(k))return this.cache.get(k);const id=this.next++;this.nodes.push({op:0,a,b,id});this.cache.set(k,id);return id;}
   const id=this.next++;this.nodes.push({op:0,a,b,id});return id;
  }
  not(a){return this.nand(a,a)}
  and(a,b){return this.not(this.nand(a,b))}
  or(a,b){return this.nand(this.not(a),this.not(b))}
  latch(){const n={op:1,d:0,id:this.next++};this.nodes.push(n);return n;}
  input(name){const i=INPUTS.indexOf(name);if(i<0)throw Error('UNKNOWN_INPUT');return i+2;}
  finish(outputs){const inv=outputs.map(s=>this.nand(s,s,true));inv.forEach(s=>this.nand(s,s,true));const bytes=[];const u24=x=>bytes.push(x>>>16&255,x>>>8&255,x&255);for(const n of this.nodes){bytes.push(n.op);if(n.op===0){u24(n.a);u24(n.b);}else u24(n.d);}return '0x'+bytes.map(b=>b.toString(16).padStart(2,'0')).join('');}
 }
 function compile(input){
  const blueprint=normalize(input),b=new Builder(),vars=Object.fromEntries(INPUTS.map(k=>[k,b.input(k)]));
  if(blueprint.kind==='tactic'&&blueprint.memory==='recovery'){const q=b.latch();vars.self_low=b.or(vars.self_low,b.and(q.id,b.not(vars.self_recovered)));q.d=b.and(vars.alive,vars.self_low);}
  function condition(k){if(k==='always')return 1;if(k==='never')return 0;if(k==='safe')return b.not(vars.self_low);if(k==='boss_or_crowd')return b.or(vars.boss,vars.danger);return vars[k];}
  const signature=blueprint.kind==='tactic'?0x114f:0x124f;
  const out=Array.from({length:16},(_,i)=>signature>>i&1);
  if(blueprint.kind==='tactic'){
   const actions=Array(7).fill(0);let available=1;
   for(const r of blueprint.rules){const c=condition(r.when),hit=b.and(available,c),idx=ACTIONS.indexOf(r.action);actions[idx]=b.or(actions[idx],hit);available=b.and(available,b.not(c));}
   actions[0]=b.or(actions[0],available);actions.forEach(a=>out.push(b.and(a,vars.alive)));
   out.push(b.and(b.and(condition(blueprint.skills.skill),vars.skill_ready),vars.alive));
   out.push(b.and(b.and(condition(blueprint.skills.ultimate),vars.ultimate_ready),vars.alive));
   out.push(b.and(condition(blueprint.skills.dash),vars.alive));
   let u0=0,u1=0;
   if(blueprint.upgrade==='vigor')u1=1;
   else if(blueprint.upgrade==='swarm')u0=1;
   else if(blueprint.upgrade==='balanced'){u1=vars.self_low;u0=b.and(b.not(vars.self_low),vars.blade_room);}
   out.push(u0,u1);
  }else{
   let armed=1;
   if(blueprint.memory==='rescue'){const q=b.latch();armed=q.id;q.d=b.and(vars.alive,b.and(b.not(vars.effect_applied),b.or(q.id,vars.rescue_event)));}
   const fire=b.and(vars.alive,b.and(vars.relic_ready,b.and(armed,condition(blueprint.trigger))));
   EFFECTS.forEach(k=>out.push(k===blueprint.effect?fire:0));
  }
  const netlist=b.finish(out),c=decode({netlist,nIn:INPUTS.length,nOut:out.length});
  return{...c,blueprint};
 }
 function decode({netlist,nIn,nOut}){
  if(nIn!==INPUTS.length||![28,22].includes(nOut)||typeof netlist!=='string'||!/^0x(?:[0-9a-fA-F]{2})+$/.test(netlist)||netlist.length>MAX_GATES*14+2)throw Error('INCOMPATIBLE_CIRCUIT');
  const raw=Uint8Array.from(netlist.slice(2).match(/../g),x=>parseInt(x,16));let p=0,id=2+nIn,state=0;const nodes=[];
  const read=()=>{if(p+3>raw.length)throw Error('TRUNCATED_NETLIST');const v=(raw[p]<<16)|(raw[p+1]<<8)|raw[p+2];p+=3;return v;};
  while(p<raw.length){const op=raw[p++];if(nodes.length>=MAX_GATES)throw Error('GATE_LIMIT');if(op===0){const a=read(),b=read();if(a>=id||b>=id)throw Error('FORWARD_NAND');nodes.push({op,a,b,id:id++});}else if(op===1){const d=read();if(state>=MAX_STATE)throw Error('STATE_LIMIT');nodes.push({op,d,id:id++,state:state++});}else throw Error('UNSUPPORTED_OPCODE');}
  if(nodes.length<nOut||nodes.some(n=>n.op===1&&n.d>=id))throw Error('INVALID_OUTPUTS_OR_LATCH');
  // Header must be provably constant, including for adversarial state and inputs.
  const known=Array(id).fill(null);known[0]=0;known[1]=1;
  for(const n of nodes)if(n.op===0){const a=known[n.a],b=known[n.b];known[n.id]=a===0||b===0?1:a===1&&b===1?0:null;}
  const offset=id-nOut;let signature=0;
  for(let i=0;i<16;i++){const v=known[offset+i];if(v===null)throw Error('NON_CONSTANT_HEADER');signature|=v<<i;}
  const kind=signature===0x114f&&nOut===28?'tactic':signature===0x124f&&nOut===22?'relic':null;
  if(!kind)throw Error('UNSUPPORTED_ABI');
  return{version:1,kind,netlist:netlist.toLowerCase(),nIn,nOut,nState:state,nNand:nodes.length-state,nLatch:state,bytes:raw.length,nodes,nSignals:id};
 }
 function step(c,state,inputs){
  if(!Array.isArray(inputs)&&!(inputs instanceof Uint8Array))throw Error('INVALID_INPUT_BITS');
  if(inputs.length!==c.nIn||inputs.some(x=>x!==0&&x!==1))throw Error('INVALID_INPUT_BITS');
  const prior=state??new Uint8Array(c.nState);if(prior.length!==c.nState||Array.from(prior).some(x=>x!==0&&x!==1))throw Error('INVALID_STATE_BITS');
  const signals=new Uint8Array(c.nSignals),next=new Uint8Array(c.nState);signals[1]=1;signals.set(inputs,2);
  for(const n of c.nodes)signals[n.id]=n.op===0?1-(signals[n.a]&signals[n.b]):prior[n.state];
  for(const n of c.nodes)if(n.op===1)next[n.state]=signals[n.d];
  return{state:next,outputs:signals.slice(-c.nOut),signals};
 }
 function interpret(c,out){
  if(out.length!==c.nOut)throw Error('OUTPUT_LENGTH');
  if(c.kind==='tactic'){
   const active=ACTIONS.filter((_,i)=>out[16+i]);if(active.length>1)throw Error('CONFLICTING_ACTIONS');const up=out[26]+2*out[27];if(up===3)throw Error('INVALID_UPGRADE');
   return{tactic:active[0]||'guard',skill:!!out[23],ultimate:!!out[24],dash:!!out[25],upgradePath:up};
  }
  const active=EFFECTS.filter((_,i)=>out[16+i]);if(active.length>1)throw Error('CONFLICTING_EFFECTS');return{effect:active[0]||null};
 }
 function bits(facts){return INPUTS.map(k=>facts[k]?1:0)}
 function exportBLIF(c){
  const prefix=2+c.nIn,signal=n=>n===0?'zero':n===1?'one':n<prefix?INPUTS[n-2]:'n'+n;
  const lines=['.model oath_'+c.kind+'_v1','.inputs '+INPUTS.join(' '),'.outputs '+Array.from({length:c.nOut},(_,i)=>'o'+i).join(' '),'.names zero','.names one','1'];
  // Preserve arbitrary verified netlists, including imported output layouts.
  for(const n of c.nodes){if(n.op===1)lines.push('.latch '+signal(n.d)+' '+signal(n.id)+' 0');else if(n.a===n.b)lines.push('.names '+signal(n.a)+' '+signal(n.id),'0 1');else lines.push('.names '+signal(n.a)+' '+signal(n.b)+' '+signal(n.id),'11 0');}
  c.nodes.slice(-c.nOut).forEach((n,i)=>lines.push('.names '+signal(n.id)+' o'+i,'1 1'));
  return lines.concat('.end','').join('\n');
 }
 function hashText(s){let h=2166136261;for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619);}return(h>>>0).toString(16).padStart(8,'0');}
 // Local content IDs are convenience identifiers, never cryptographic attestation.
 const localId=b=>'draft-'+hashText(JSON.stringify(normalize(b)));
 const tactic=(name,rules,skills,upgrade='balanced',memory='recovery')=>({version:1,kind:'tactic',name,rules:rules.map(([when,action])=>({when,action})),skills:{skill:skills[0],ultimate:skills[1],dash:skills[2]},upgrade,memory});
 const relic=(name,effect,trigger,memory='none')=>({version:1,kind:'relic',name,effect,trigger,memory});
 const PRESETS=Object.freeze([
  {id:'oathkeeper',en:'Oathkeeper',zh:'守誓者',b:tactic('Oathkeeper',[['ally_down','rescue'],['self_low','retreat'],['objective_threat','objective'],['boss','focus']],['ally_low','boss_or_crowd','danger'])},
  {id:'survivor',en:'Survivor',zh:'生还者',b:tactic('Survivor',[['self_low','retreat'],['ally_down','rescue'],['objective','objective'],['boss','focus']],['self_low','boss','danger'],'vigor')},
  {id:'breaker',en:'Dawnbreaker',zh:'破晓者',b:tactic('Dawnbreaker',[['ally_down','rescue'],['self_low','retreat'],['boss','focus'],['leader_assault','assault']],['boss_or_crowd','boss_window','danger'],'fury')},
  {id:'sentinel',en:'Sentinel',zh:'守望者',b:tactic('Sentinel',[['ally_down','rescue'],['objective','objective'],['self_low','retreat'],['leader_guard','guard']],['danger','objective_threat','danger'],'swarm')},
  {id:'mercy',en:'Mercy Lamp',zh:'急救灯',b:relic('Mercy Lamp','shield','ally_low')},
  {id:'echo',en:'Echo Lamp',zh:'回响灯',b:relic('Echo Lamp','shield','ally_low','rescue')},
  {id:'chalice',en:'Living Chalice',zh:'复苏圣杯',b:relic('Living Chalice','heal','ally_low')},
  {id:'bell',en:'Breach Bell',zh:'破阵钟',b:relic('Breach Bell','repulse','danger')},
  {id:'banner',en:'Dawn Banner',zh:'破晓战旗',b:relic('Dawn Banner','fury','boss_window')},
  {id:'winter',en:'Winter Seal',zh:'寒冬印',b:relic('Winter Seal','frost','objective_threat')},
  {id:'conduit',en:'Star Conduit',zh:'星能导管',b:relic('Star Conduit','charge','boss')}
 ]);
 return Object.freeze({VERSION,MAX_GATES,MAX_STATE,INPUTS,ACTIONS,EFFECTS,CONDITIONS,PRESETS,normalize,compile,decode,step,interpret,bits,exportBLIF,localId});
});
