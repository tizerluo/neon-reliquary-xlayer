(function(root,factory){const c=typeof module==='object'&&module.exports?require('./circuits.js'):root.NRCircuits;const api=factory(c);if(typeof module==='object'&&module.exports)module.exports=api;else root.NROathData=api;})(globalThis,C=>{
 'use strict';
 const KEY='nr.oath.profile.v1',MAX_LIBRARY=100,MAX_PACKAGE=150000;
 const clone=x=>JSON.parse(JSON.stringify(x));
 const effectCosts=Object.freeze({shield:0,heal:0,repulse:0,fury:20,frost:25,charge:30});
 const bases=Object.freeze({
  shield:{en:'Oath Lamp',zh:'守誓灯',cost:30,cooldown:18,description:['Shield the most wounded member nearby.','保护附近生命比例最低的成员。']},
  heal:{en:'Living Chalice',zh:'复苏圣杯',cost:38,cooldown:24,description:['Restore nearby wounded health.','恢复附近受伤成员的生命。']},
  repulse:{en:'Breach Bell',zh:'破阵钟',cost:25,cooldown:15,description:['Drive close enemies away.','击退近身敌人，打开缺口。']},
  fury:{en:'Dawn Banner',zh:'破晓战旗',cost:42,cooldown:24,description:['Briefly accelerate this member’s attacks.','短暂加速本角色的攻击。']},
  frost:{en:'Winter Seal',zh:'寒冬印',cost:35,cooldown:20,description:['Freeze nearby ordinary enemies; bosses resist.','冻结附近普通敌人；首领抵抗冻结。']},
  charge:{en:'Star Conduit',zh:'星能导管',cost:45,cooldown:30,description:['Add a bounded pulse of overdrive charge.','提供一次有限的终极技充能。']}
 });
 function fresh(){return{version:1,research:0,unlocked:['shield','heal','repulse'],runs:0,wins:0,bestChapter:0,library:[],squads:[],selectedSquad:null,history:[],loadout:{leader:'human',leaderChip:'oathkeeper',leaderRelics:['mercy','bell'],slots:[{mode:'chip',heroId:2,chip:'breaker',relics:['bell','mercy']},{mode:'chip',heroId:4,chip:'oathkeeper',relics:['chalice','echo']},{mode:'chip',heroId:5,chip:'survivor',relics:['mercy','bell']}]}};}
 function record(b,{parent=null,note='',id=null,source=null}={}){const blueprint=C.normalize(b),c=C.compile(blueprint);return{id:id||('bp-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,9)),blueprint,parent:parent?String(parent).slice(0,100):null,note:String(note).slice(0,200),createdAt:new Date().toISOString(),source:source||{type:'local'},circuit:{netlist:c.netlist,nIn:c.nIn,nOut:c.nOut}};}
 const presets=C.PRESETS.map(p=>({...record(p.b,{id:p.id}),en:p.en,zh:p.zh,preset:true}));
 function list(profile){return [...presets,...profile.library];}
 function find(profile,id){return list(profile).find(r=>r.id===id)||null;}
 function normalizeCircuitRecord(r){
  if(!r||typeof r!=='object'||Array.isArray(r))throw Error('INVALID_RECORD');
  const id=String(r.id||'');if(!/^[\w-]{1,100}$/.test(id))throw Error('INVALID_RECORD_ID');
  let b=null,c;
  if(r.blueprint){b=C.normalize(r.blueprint);c=C.compile(b);}
  else {c=C.decode(r.circuit);if(!r.source||r.source.type!=='xlayer')throw Error('MISSING_BLUEPRINT');}
  let source={type:'local'};
  if(r.source?.type==='xlayer'){
   const s=r.source;if(s.chainId!==196||!/^0x[\da-f]{40}$/i.test(s.processor)||!/^\d{1,20}$/.test(String(s.circuitId)))throw Error('INVALID_CHAIN_SOURCE');
   const chainCircuit=C.decode(r.circuit);source={type:'xlayer',chainId:196,processor:s.processor,circuitId:String(s.circuitId),block:Number(s.block)||0};
   // On import, chain claims are unverified until a fresh RPC read compares bytes.
   c=chainCircuit;b=null;
  }
  return{id,blueprint:b,name:r.name?String(r.name).slice(0,48):undefined,parent:r.parent?String(r.parent).slice(0,100):null,note:String(r.note||'').slice(0,200),createdAt:String(r.createdAt||'').slice(0,40),source,circuit:{netlist:c.netlist,nIn:c.nIn,nOut:c.nOut}};
 }
 function validateLoadout(input,profile){
  if(!input||!['human','external'].includes(input.leader)||!Array.isArray(input.slots)||input.slots.length!==3)throw Error('INVALID_LOADOUT');
  const select=(id,kind)=>{const r=find(profile,String(id));if(!r)throw Error('BLUEPRINT_NOT_FOUND');const c=C.decode(r.circuit);if(c.kind!==kind)throw Error('WRONG_SOCKET');return r.id;};
  const relics=xs=>{if(!Array.isArray(xs)||xs.length>2)throw Error('RELIC_SLOTS');return [0,1].map(i=>xs[i]?select(xs[i],'relic'):null);};
  const slots=input.slots.map(s=>{if(!s||!['off','chip','external'].includes(s.mode)||!Number.isInteger(s.heroId)||s.heroId<0||s.heroId>5)throw Error('INVALID_SEAT');return{mode:s.mode,heroId:s.heroId,chip:select(s.chip,'tactic'),relics:relics(s.relics)};});
  return{leader:input.leader,leaderChip:select(input.leaderChip,'tactic'),leaderRelics:relics(input.leaderRelics),slots};
 }
 function parseProfile(value){
  if(typeof value!=='string'||value.length>2e6)throw Error('PROFILE_TOO_LARGE');
  const p=JSON.parse(value),base=fresh();if(p.version!==1)throw Error('PROFILE_VERSION');
  for(const k of ['research','runs','wins','bestChapter']){if(!Number.isSafeInteger(p[k])||p[k]<0||p[k]>1000000)throw Error('INVALID_PROGRESS');base[k]=p[k];}
  if(!Array.isArray(p.unlocked)||p.unlocked.some(e=>!C.EFFECTS.includes(e)))throw Error('INVALID_UNLOCKS');base.unlocked=[...new Set(['shield','heal','repulse',...p.unlocked])];
  if(!Array.isArray(p.library)||p.library.length>MAX_LIBRARY)throw Error('LIBRARY_LIMIT');base.library=p.library.map(normalizeCircuitRecord);
  if(new Set(base.library.map(x=>x.id)).size!==base.library.length||base.library.some(x=>C.PRESETS.some(p=>p.id===x.id)))throw Error('DUPLICATE_ID');
  base.loadout=validateLoadout(p.loadout,base);
  base.squads=Array.isArray(p.squads)?p.squads.slice(0,12).map(s=>({name:C.normalize({...C.PRESETS[0].b,name:s.name}).name,loadout:validateLoadout(s.loadout,base)})):[];
  base.history=Array.isArray(p.history)?p.history.slice(0,12).filter(x=>x&&typeof x==='object').map(h=>({date:String(h.date).slice(0,40),won:!!h.won,chapter:Math.max(0,Math.min(3,Number(h.chapter)||0)),time:Math.max(0,Math.min(10000,Number(h.time)||0)),seed:Number(h.seed)>>>0,research:Math.max(0,Math.min(1000,Number(h.research)||0))})):[];
  return base;
 }
 function load(storage){try{const raw=storage.getItem(KEY);return{profile:raw?parseProfile(raw):fresh(),warning:null};}catch(e){return{profile:fresh(),warning:'PROFILE_RECOVERY: '+e.message};}}
 function save(storage,profile){try{storage.setItem(KEY,JSON.stringify(profile));return true;}catch{return false;}}
 function add(profile,b,opts){if(profile.library.length>=MAX_LIBRARY)throw Error('LIBRARY_LIMIT');const r=record(b,opts);profile.library.push(r);return r;}
 function unlock(profile,effect){if(!C.EFFECTS.includes(effect))throw Error('UNKNOWN_RELIC');if(profile.unlocked.includes(effect))return false;const cost=effectCosts[effect];if(profile.research<cost)throw Error('NOT_ENOUGH_RESEARCH');profile.research-=cost;profile.unlocked.push(effect);return true;}
 function share(profile,id){const r=find(profile,id);if(!r)throw Error('BLUEPRINT_NOT_FOUND');return JSON.stringify({format:'nr-oath-blueprint',version:1,record:{...r,preset:undefined,en:undefined,zh:undefined}},null,2);}
 function importShare(profile,value){
  if(typeof value!=='string'||value.length>MAX_PACKAGE)throw Error('PACKAGE_TOO_LARGE');const p=JSON.parse(value);if(p.format!=='nr-oath-blueprint'||p.version!==1)throw Error('PACKAGE_VERSION');
  const r=normalizeCircuitRecord(p.record);if(profile.library.length>=MAX_LIBRARY)throw Error('LIBRARY_LIMIT');
  r.parent=r.id;r.id='bp-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,9);profile.library.push(r);return r;
 }
 return Object.freeze({KEY,MAX_LIBRARY,bases,effectCosts,fresh,load,save,list,find,add,unlock,share,importShare,validateLoadout,parseProfile,normalizeCircuitRecord,clone});
});
