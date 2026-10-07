const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {simulation,ROOT}=require('./sim_harness.cjs');
const plain=v=>JSON.parse(JSON.stringify(v));
const current=fs.readFileSync(path.join(ROOT,'src/core.js'),'utf8');
// Expose existing functions and pools only; the fixture does not reproduce reward logic.
function fixture({visual=true,coreSource=current,seed=96481}={}){
  const probe=`
    const chestStart=startGame;
    startGame=function(){chestStart();Object.defineProperty(run,'chestProbe',{value:{
      spawn:spawnOrb,update:updateOrbs,orbs:O,rings,pools:{E,B,HB,F,O},
      rewards:()=>typeof pickupEvents==='undefined'?[]:window.__NR.pickupEffects.rewards()
    }});};`;
  const s=simulation({visual,seed,coreSource:coreSource+probe});
  s.start({hero:0,companion:2});s.clear();
  return {s,get p(){return s.raw().run.chestProbe;}};
}
function placeParty(s){const {P,actor}=s.raw();P.x=0;P.y=0;P.magnet=0;actor.x=320;actor.y=0;actor.magnet=0;return {P,actor};}
function collect(p,unit,{energy=60,shield=0,kind=2}={}){
  unit.ult=energy;unit.shield=shield;const i=p.orbs.free.at(-1);p.spawn(unit.x+10,unit.y,3.5,kind);
  p.lastSpot={x:p.orbs.x[i],y:p.orbs.y[i]};p.update(0);
  return p.rewards().at(-1);
}

test('Chest events identify the real leader or Volt recipient and report granted increments',()=>{
  const {s,p}=fixture(),{P,actor}=placeParty(s);s.raw().run.time=12.5;
  for(const unit of [P,actor]){
    const other=unit===P?actor:P,oldOther=plain({ult:other.ult,shield:other.shield,boost:other.boost});
    const event=collect(p,unit);
    assert.deepEqual(plain(event),{id:unit===P?1:2,kind:'chest',time:12.5,owner:unit.uid,
      ...p.lastSpot,rewards:{overclock:8,energy:20,shield:12}});
    assert.equal(unit.boost,8);assert.equal(unit.ult,80);assert.equal(unit.shield,12);
    assert.deepEqual(plain({x:p.rings.at(-1).x,y:p.rings.at(-1).y}),{x:unit.x,y:unit.y});
    assert.deepEqual(plain({ult:other.ult,shield:other.shield,boost:other.boost}),oldOther);
  }
  const copy=p.rewards();copy[0].rewards.energy=999;copy[0].owner=999;copy.length=0;
  assert.equal(p.rewards()[0].rewards.energy,20);assert.equal(p.rewards()[0].owner,P.uid);
});

test('Full or partially capped energy and shields report only actual nonnegative grants',()=>{
  const {s,p}=fixture(),{P,actor}=placeParty(s);
  for(const unit of [P,actor]){
    const cap=unit.maxhp*.8;
    assert.deepEqual(plain(collect(p,unit,{energy:97,shield:cap-3}).rewards),{overclock:8,energy:3,shield:3});
    assert.deepEqual(plain(collect(p,unit,{energy:100,shield:cap}).rewards),{overclock:8,energy:0,shield:0});
    // Existing caps can lower an over-cap state; observation must never call that a grant.
    assert.deepEqual(plain(collect(p,unit,{energy:103,shield:cap+4}).rewards),{overclock:8,energy:0,shield:0});
  }
});

test('Approach, release, clearing and ordinary pickups cannot invent chest rewards; age expiry keeps the real path',()=>{
  const {s,p}=fixture(),{P,actor}=placeParty(s);
  p.spawn(1000,0,3.5,2);p.update(1/60);assert.equal(p.rewards().length,0);
  const released=p.orbs.free.length;p.orbs.release(Array.from(p.orbs.a).findIndex(Boolean));
  assert.equal(p.orbs.free.length,released+1);p.update(0);assert.equal(p.rewards().length,0);
  p.spawn(1000,0,3.5,2);p.orbs.clear();p.update(0);assert.equal(p.rewards().length,0);
  collect(p,P,{kind:0});collect(p,P,{kind:1});collect(p,P,{kind:3});assert.equal(p.rewards().length,0);
  actor.ult=0;actor.shield=0;p.spawn(1000,0,3.5,2);
  const index=Array.from(p.orbs.a).findIndex(Boolean);p.orbs.age[index]=85;
  const spot={x:p.orbs.x[index],y:p.orbs.y[index]};
  p.update(0);assert.equal(p.rewards().length,0);
  p.update(.01);const e=p.rewards().at(-1);
  assert.equal(e.owner,actor.uid);assert.equal(e.x,spot.x);assert.equal(e.y,spot.y);
  assert.deepEqual(plain(e.rewards),{overclock:8,energy:20,shield:12});assert.equal(p.orbs.count,0);
});

test('Chest history is bounded, restarts clear history and observation ids remain monotonic',()=>{
  const f=fixture(),{P}=placeParty(f.s);
  for(let i=0;i<40;i++)collect(f.p,P);
  assert.equal(f.p.rewards().length,32);assert.equal(f.p.rewards()[0].id,9);assert.equal(f.p.rewards().at(-1).id,40);
  f.s.start({hero:0,companion:2});assert.equal(f.p.rewards().length,0);
  const units=placeParty(f.s);assert.equal(collect(f.p,units.P).id,41);
});

function state(s,p){
  return {P:plain(s.raw().P),actor:plain(s.raw().actor),run:plain(s.raw().run),rng:s.randomState(),
    pools:Object.fromEntries(Object.entries(p.pools).map(([name,pool])=>[name,Object.fromEntries(Object.entries(pool)
      .filter(([,v])=>ArrayBuffer.isView(v)||Array.isArray(v)||typeof v==='number')
      .map(([key,v])=>[key,typeof v==='number'?v:Array.from(v)]))]))};
}
test('Enabled and disabled observation preserve seeded combat and every pool array against original core 28d7719',()=>{
  // Keep this baseline independent of private Git history / shallow checkouts.
  const original=fs.readFileSync(path.join(ROOT,'tests/fixtures/core-before-observations.js'),'utf8');
  const results=[{visual:true,coreSource:original},{visual:false},{visual:true}].map(options=>{
    const {s,p}=fixture(options),{P,actor}=placeParty(s);
    for(let i=0;i<5;i++)s.spawn(i,0,150+i*60,20-i*10);s.hash();
    for(let i=0;i<180;i++){
      if(i%30===0){p.spawn(P.x+10,P.y,3.5,2);p.spawn(actor.x+10,actor.y,3.5,2);}
      if(i===40)p.spawn(700,700,3.5,2);
      s.tick(1/60);
    }
    return {state:state(s,p),events:p.rewards()};
  });
  assert.deepEqual(results[1].state,results[0].state);assert.deepEqual(results[2].state,results[0].state);
  assert.equal(results[1].events.length,0);assert(results[2].events.length>=12);
});
