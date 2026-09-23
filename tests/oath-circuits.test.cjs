const {test}=require('node:test'),assert=require('node:assert/strict'),C=require('../src/circuits.js'),D=require('../src/oath-data.js');
const run=(c,f,s)=>{const r=C.step(c,s,C.bits({alive:true,skill_ready:true,relic_ready:true,...f}));return{...C.interpret(c,r.outputs),state:r.state};};
test('Every template decodes, stays within manufacturing limits, and emits one action/effect across 4096 varied inputs',()=>{
 for(const p of C.PRESETS){const c=C.compile(p.b);assert(c.bytes<7168);assert.equal(c.nNand+c.nLatch,c.nodes.length);let state=new Uint8Array(c.nState);for(let n=0;n<4096;n++){const input=C.INPUTS.map((_,i)=>(Math.imul(n+19,i*7919+17)>>>i%17)&1);const r=C.step(c,state,input);C.interpret(c,r.outputs);state=r.state;}assert(C.exportBLIF(c).includes('.outputs o0'));}
});
test('Priority, explicit skills and upgrade decisions follow independently specified semantics',()=>{
 const c=C.compile(C.PRESETS.find(p=>p.id==='breaker').b);
 assert.equal(run(c,{ally_down:true,self_low:true,boss:true}).tactic,'rescue');
 assert.equal(run(c,{self_low:true,boss:true}).tactic,'retreat');
 const d=run(c,{boss:true,boss_window:true,ultimate_ready:true});assert.equal(d.tactic,'focus');assert.equal(d.ultimate,true);assert.equal(d.skill,true);assert.equal(d.upgradePath,0);
 assert.equal(run(c,{boss:true,skill_ready:false}).skill,false);
 const custom={...C.PRESETS[0].b,skills:{skill:'never',ultimate:'never',dash:'never'},rules:[{when:'always',action:'follow'}],upgrade:'swarm'};
 const x=run(C.compile(custom),{danger:true,ally_down:true});assert.equal(x.tactic,'follow');assert.equal(x.skill,false);assert.equal(x.upgradePath,1);
});
test('Recovery latch holds until 70% health, reset state clears it',()=>{
 const c=C.compile(C.PRESETS.find(p=>p.id==='survivor').b);let d=run(c,{self_low:true});assert.equal(d.tactic,'retreat');
 d=run(c,{},d.state);assert.equal(d.tactic,'retreat');d=run(c,{self_recovered:true},d.state);assert.equal(d.tactic,'guard');assert.equal(d.state[0],0);
 assert.equal(run(c,{}).tactic,'guard');
});
test('Rescue relic stores event, survives a failed effect, and clears on acknowledgement',()=>{
 const c=C.compile(C.PRESETS.find(p=>p.id==='echo').b);let d=run(c,{rescue_event:true});assert.equal(d.effect,null);assert.equal(d.state[0],1);
 d=run(c,{ally_low:true,relic_ready:false},d.state);assert.equal(d.effect,null);assert.equal(d.state[0],1);
 d=run(c,{ally_low:true},d.state);assert.equal(d.effect,'shield');assert.equal(d.state[0],1);
 d=run(c,{effect_applied:true,relic_ready:false},d.state);assert.equal(d.state[0],0);d=run(c,{ally_low:true},d.state);assert.equal(d.effect,null);
});
test('Netlist rejects unknown opcodes, forward NAND, wrong ABI, truncated data and excessive gates',()=>{
 const c=C.compile(C.PRESETS[0].b);for(const netlist of ['0x02','0x000000ff000000','0x0000','0xzz','0x'+('00000000000000'.repeat(1025))])assert.throws(()=>C.decode({...c,netlist}));assert.throws(()=>C.decode({...c,nIn:19}));
 const bytes=Buffer.from(c.netlist.slice(2),'hex');bytes[bytes.length-1]=255;assert.throws(()=>C.decode({...c,netlist:'0x'+bytes.toString('hex')}));
});
test('Blueprint schema does not accept executable scripts or malformed conditions',()=>{
 assert.throws(()=>C.compile({...C.PRESETS[0].b,script:'alert(1)'}));assert.throws(()=>C.compile({...C.PRESETS[0].b,rules:[{when:'__proto__',action:'guard'}]}));
});
test('Profile and shared versions roundtrip; invalid/corrupt input remains recoverable',()=>{
 const p=D.fresh(),v=D.add(p,{...C.PRESETS[0].b,name:'Rescue II'},{parent:'oathkeeper',note:'priority'}),copy=D.importShare(p,D.share(p,v.id));assert.equal(copy.parent,v.id);assert.notEqual(copy.id,v.id);assert.equal(copy.circuit.netlist,v.circuit.netlist);
 p.squads.push({name:'Test',loadout:D.clone(p.loadout)});assert.equal(D.parseProfile(JSON.stringify(p)).squads.length,1);
 assert.throws(()=>D.importShare(p,'{"format":"arbitrary"}'));assert.throws(()=>D.importShare(p,'x'.repeat(150001)));assert.throws(()=>D.validateLoadout({...p.loadout,leader:'bot'},p));
 const store={getItem:()=>'{bad',setItem:()=>{throw Error('must not overwrite');}};assert(D.load(store).warning);assert.equal(D.save(store,p),false);
});
test('Unlock spends once and prevents negative research; forged claim is not marked verified',()=>{
 const p=D.fresh();assert.throws(()=>D.unlock(p,'frost'));p.research=30;assert.equal(D.unlock(p,'frost'),true);assert.equal(p.research,5);assert.equal(D.unlock(p,'frost'),false);assert.equal(p.research,5);
 const c=C.compile(C.PRESETS[0].b),r=D.normalizeCircuitRecord({id:'test',circuit:c,source:{type:'xlayer',chainId:196,processor:'0x'+'1'.repeat(40),circuitId:'1',verified:true}});assert.equal(r.source.verified,undefined);assert.equal(r.blueprint,null);
});
