const {test}=require('node:test'),assert=require('node:assert/strict'),{simulation}=require('./sim_harness.cjs'),C=require('../src/circuits.js'),D=require('../src/oath-data.js');
test('Route → encounter → camp → next region → final result is idempotent',()=>{
 const s=simulation();s.startFull();assert.equal(s.raw().state,'route');
 for(let i=0;i<12;i++){
  const type=s.options()[0];assert(s.chooseRoute(type));let {run}=s.raw(),ex=run.expedition;
  // State-machine fixture only: full combat endurance has a separate real simulation report.
  if(type==='boss')run.bosses=ex.chapter+1;else if(type==='clear'){run.kills=ex.startKills+200;ex.clock=100;}else ex.objective.progress=ex.objective.target;
  s.tick(1/60);
  if(i<11){assert.equal(s.raw().state,'camp');assert(s.reward('mend'));assert.equal(s.reward('mend'),false);assert.equal(s.raw().state,'route');}
 }
 assert.equal(s.raw().state,'result');assert.equal(s.oath.profile.wins,1);const research=s.oath.profile.research;s.finish(true);assert.equal(s.oath.profile.research,research);assert.equal(s.raw().run.expedition.cleared,12);
});
test('Objective failure settles a loss; absent allies never advance an escort',()=>{
 const s=simulation();s.startFull();s.raw().run.expedition.seed=2;s.raw().run.expedition.node=1;s.chooseRoute('escort');s.clear();const ex=s.raw().run.expedition;for(const a of s.all()){a.x=-1200;a.y=-1200;}const before=ex.objective.progress;s.tick(1/60);assert.equal(ex.objective.progress,before);ex.objective.hp=0;s.tick(1/60);assert.equal(s.raw().state,'result');assert.equal(s.oath.profile.wins,0);
});
test('Chip intents cannot be silently replaced by legacy rescue or autoskills',()=>{
 const s=simulation();const b=D.add(s.oath.profile,{...C.PRESETS[0].b,name:'Deliberate follow',rules:[{when:'always',action:'follow'}],skills:{skill:'never',ultimate:'never',dash:'never'},upgrade:'swarm',memory:'none'});s.oath.profile.loadout.slots[0].chip=b.id;s.startFull();s.chooseRoute(s.options()[0]);s.clear();const {P,actor}=s.raw();P.downed=true;P.hp=0;actor.skillCD=0;s.decision(actor);assert.equal(actor.order.tactic,'follow');assert.equal(actor.order.autoSkills,false);assert.equal(actor.path,1);assert.equal(actor.skillCD,0);
});
test('Relic shared energy, cooldown, real rescue events, pause and new-run reset',()=>{
 const s=simulation();s.startFull();s.chooseRoute(s.options()[0]);s.clear();const {P,actor,run}=s.raw();P.hp=10;P.shield=0;actor.x=P.x+25;actor.y=P.y;s.relicTick(.2);assert(P.oath.energy<66);const fire=P.oath.relics[0].fires;s.relicTick(.2);assert.equal(P.oath.relics[0].fires,fire);
 const hp=P.hp;P.downed=true;P.hp=0;s.revive(P,'boss');assert.equal(run.coopRescues,0);assert.equal(actor.oath.rescueEvent,false);
 P.downed=true;P.hp=0;P.revive=2.39;s.coopRescue(.1);assert.equal(run.coopRescues,1);assert.equal(actor.oath.rescueEvent,true);
 const energy=P.oath.energy;s.pause();for(let i=0;i<120;i++)s.tick(1/60);assert.equal(P.oath.energy,energy);
 s.startFull();assert.equal(s.raw().P.oath.energy,65);assert.equal(s.raw().P.oath.relics[0].fires,0);
});
test('External leader is opt-in, isolated, sequenced, upgrade-capable and instantly revocable',()=>{
 const s=simulation();s.startFull();assert.equal(s.call('nr_join',{slot:0,name:'Model'}).ok,false);
 s.oath.profile.loadout.leader='external';s.startFull();const joined=s.call('nr_join',{slot:0,name:'Model'});assert(joined.ok);s.chooseRoute(s.options()[0]);const auth={agentId:joined.agentId,token:joined.token,runId:s.raw().run?joined.runId:null};
 const cmd=s.call('nr_command',{...auth,seq:1,tactic:'objective',upgradePath:2});assert(cmd.ok,cmd.error);assert.equal(s.raw().P.path,2);s.level();assert.equal(s.raw().P.pending,0);assert.equal(s.raw().P.upgrades[2],1);
 assert.equal(s.call('nr_command',{...auth,seq:1,tactic:'assault'}).error,'STALE_SEQUENCE');
 s.takeover();assert.equal(s.raw().P.controller,'human');assert.equal(s.call('nr_command',{...auth,seq:2,tactic:'move',x:900,y:900}).ok,false);
});
test('All six relic chassis apply bounded effects; locked chassis cannot execute',()=>{
 const s=simulation();s.startFull();s.chooseRoute(s.options()[0]);s.clear();const a=s.raw().P;a.hp=30;a.shield=0;a.ult=20;a.boost=0;s.spawn(0,0,a.x+30,a.y);s.hash();assert.equal(s.effect(a,'frost'),false);
 s.oath.profile.unlocked=[...C.EFFECTS];for(const k of C.EFFECTS)assert.equal(s.effect(a,k),true,k);assert(a.ult<=100);assert(a.shield<=a.maxhp*.6);assert(a.hp<=a.maxhp);
});
test('Four external seats coexist, companion arrival is scheduled, identities cannot cross-control',()=>{
 const s=simulation();s.oath.profile.loadout.leader='external';for(const config of s.oath.profile.loadout.slots)config.mode='external';s.startFull();
 const joined=[0,1,2,3].map(slot=>s.call('nr_join',{slot,name:'Agent '+slot}));assert(joined.every(j=>j.ok));assert.equal(s.call('nr_join',{slot:1,name:'Duplicate'}).error,'SEAT_OCCUPIED');
 s.chooseRoute(s.options()[0]);assert.equal(s.all().length,4);assert.equal(s.raw().run.scaling.agents,3);
 const spoof=s.call('nr_command',{agentId:joined[1].agentId,token:joined[0].token,runId:joined[0].runId,seq:1,tactic:'assault'});assert.equal(spoof.ok,false);
 const lead=joined[0],order={agentId:lead.agentId,token:lead.token,runId:lead.runId,seq:1,tactic:'assault'};assert(s.call('nr_command',order).ok);assert.equal(s.oath.command,'assault');assert.equal(s.call('nr_command',{...order,seq:2,runId:'old'}).error,'STALE_RUN');
 assert(s.call('nr_leave',{agentId:lead.agentId,token:lead.token}).ok);assert.equal(s.raw().P.controller,'external');assert.equal(s.raw().P.stale,true);assert(s.call('nr_join',{slot:0,name:'Replacement'}).ok);
});
test('Chain claims cannot be equipped until this session verifies their exact record',()=>{
 const s=simulation(),c=C.compile(C.PRESETS[0].b),r=D.normalizeCircuitRecord({id:'claimed',circuit:c,source:{type:'xlayer',chainId:196,processor:'0x'+'2'.repeat(40),circuitId:'1'}});s.oath.profile.library.push(r);s.oath.profile.loadout.slots[0].chip=r.id;
 assert.equal(s.preflight(),false);s.oath.verified.set(r.id,{hash:'session-test'});assert.equal(s.preflight(),true);
});
test('Restart settles earned research once before beginning a new expedition',()=>{
 const s=simulation();s.startFull();s.raw().run.expedition.research=10;s.raw().run.expedition.cleared=2;s.startFull();assert.equal(s.oath.profile.research,10);assert.equal(s.oath.profile.runs,1);assert.equal(s.raw().run.expedition.research,0);assert.equal(s.raw().state,'route');
});
test('An invalid chain upgrade output faults only its actor and never interrupts leveling',()=>{
 const s=simulation(),c=C.compile(C.PRESETS[0].b);c.netlist=c.netlist.slice(0,-28)+'00000000000000'.repeat(2);
 const r=D.normalizeCircuitRecord({id:'invalid-upgrade',circuit:c,source:{type:'xlayer',chainId:196,processor:'0x'+'3'.repeat(40),circuitId:'1'}});
 s.oath.profile.library.push(r);s.oath.profile.loadout.slots[0].chip=r.id;s.oath.verified.set(r.id,{hash:'fixture'});s.startFull();s.chooseRoute(s.options()[0]);
 const a=s.raw().actor,path=a.path;a.oath.requests={skill:true,ultimate:true,dash:true};assert.doesNotThrow(()=>s.level());assert.equal(a.oath.chip.fault,'INVALID_UPGRADE');assert.equal(a.order.tactic,'hold');assert.equal(a.oath.requests,null);assert.equal(a.path,path);assert.equal(a.level,s.raw().P.level);assert.doesNotThrow(()=>s.level());
});
