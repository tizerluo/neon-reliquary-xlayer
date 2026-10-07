const { test } = require('node:test');
const assert = require('node:assert/strict');
const { simulation } = require('./sim_harness.cjs');
const toolkit = import('../visual-game/skill-fx-timeline.mjs');

test('Only accepted skills produce visual records, including companion ownership', () => {
  const s=simulation({visual:true});s.start({hero:0,companion:2});s.clear();
  const {P,actor}=s.raw();s.skills.cast(P);s.skills.cast(P);
  assert.equal(s.skills.events.length,1);assert.equal(s.skills.events[0].kind,'cast');
  actor.skillCD=0;s.skills.cast(actor);
  assert.equal(s.skills.events[1].owner,actor.uid);assert.equal(s.skills.events[1].hero,2);
  P.ult=99;s.skills.ultimate(P);assert.equal(s.skills.events.length,2);
  P.ult=100;s.skills.ultimate(P);P.ult=100;s.skills.ultimate(P);
  assert.equal(s.skills.events.length,3);assert.equal(s.skills.events[2].duration,4.2);
  actor.downed=true;actor.skillCD=0;s.skills.cast(actor);assert.equal(s.skills.events.length,3);
  s.pause();P.skillCD=0;s.skills.cast(P);assert.equal(s.skills.events.length,3);
});

test('Cast capture keeps immediate damage, cooldown and seeded combat unchanged', () => {
  for(const hero of [0,1,2,3,4,5]){
    const plain=simulation({visual:false,seed:73041}),hd=simulation({visual:true,seed:73041});
    for(const s of [plain,hd]){
      s.start({hero,companion:4});s.clear();const P=s.raw().P;
      s.spawn(0,0,100,0);s.spawn(1,0,250,40);s.hash();P.hp-=12;s.skills.cast(P);
      assert(s.raw().run.damageDealt>0);P.ult=100;s.skills.ultimate(P);
      for(let n=0;n<60;n++)s.tick(1/60);
    }
    for(const k of ['hp','shield','skillCD','ultTime','damageDealt','kills'])assert.equal(hd.raw().P[k],plain.raw().P[k],hero+':'+k);
    for(const k of ['a','hp','slow','freeze','x','y'])assert.deepEqual(Array.from(hd.enemies[k]),Array.from(plain.enemies[k]),hero+':E.'+k);
    assert.equal(plain.skills.events.length,0);assert(hd.skills.events.length>0);
  }
});

test('Skill records are bounded and do not survive a new run', () => {
  const s=simulation({visual:true});s.start({hero:0});s.clear();const P=s.raw().P;
  for(let n=0;n<100;n++){P.skillCD=0;s.skills.cast(P);}
  assert.equal(s.skills.events.length,64);assert(s.skills.events.every((e,n,a)=>!n||e.id>a[n-1].id));
  s.start({hero:5});assert.equal(s.skills.events.length,0);
});

test('Presentation cues use frame timing; pause and skipped frames cannot replay pulses', async () => {
  const {FX_TIMING,COMMON_SKILL_PRESETS,compilePreset,createEffectTimeline}=await toolkit;
  assert.equal(FX_TIMING.castContact,14/26);assert.equal(FX_TIMING.channelEnter,13/26);assert.equal(FX_TIMING.channelHold,28/26);
  const t=createEffectTimeline();t.add(compilePreset(COMMON_SKILL_PRESETS.cast,{owner:0}),10);
  const read=time=>{const out=[];t.visit(time,(s,p)=>out.push({kind:s.kind,...p}));return out;};
  assert.equal(read(10.4).filter(s=>s.kind==='arc').length,0);
  assert.equal(read(10.6).filter(s=>s.kind==='arc').length,1);
  assert.deepEqual(read(10.6),read(10.6));
  assert.deepEqual(read(15),[]);assert.equal(t.metrics().scheduled,0);
});

test('Effect limits reject invalid data and reserve a whole recipe atomically', async () => {
  const {normalizeEffect,compilePreset,createEffectTimeline,COMMON_SKILL_PRESETS}=await toolkit;
  for(const bad of [{kind:'unknown'},{kind:'decal',x:NaN},{kind:'feedback',gain:1},{kind:'arc',life:100},{kind:'decal',attach:true},{kind:'petals',offset:[0,Infinity,0]}])assert.throws(()=>normalizeEffect(bad));
  assert.throws(()=>compilePreset({cues:[{at:'missing',effect:{kind:'arc'}}]}));
  const t=createEffectTimeline(3),cast=compilePreset(COMMON_SKILL_PRESETS.cast,{owner:0});
  assert.equal(t.add(cast,0),true);assert.equal(t.add(cast,0),false);
  assert.equal(t.metrics().scheduled,2);assert.equal(t.metrics().dropped,2);
  t.clear();assert.equal(t.metrics().scheduled,0);
});

test('Progress and dissolve have stable finite endpoints and cancel owner cues', async () => {
  const {normalizeEffect,sampleEffect,createEffectTimeline}=await toolkit;
  const flash=normalizeEffect({kind:'arc',life:.04});assert(Number.isFinite(sampleEffect(flash,0,.02).opacity));
  const s=normalizeEffect({kind:'decal',life:1,chargeTime:.5,fadeIn:.1,fadeOut:.2,attach:true,owner:7});
  assert.equal(sampleEffect(s,0,-.1),null);assert.equal(sampleEffect(s,0,1),null);
  assert.equal(sampleEffect(s,0,0).opacity,0);assert.equal(sampleEffect(s,0,.5).progress,1);
  assert(sampleEffect(s,0,.95).dissolve>sampleEffect(s,0,.85).dissolve);
  const t=createEffectTimeline();t.add([{at:.5,spec:s}],0);t.visit(.1,()=>assert.fail(),spec=>spec.owner===7);
  assert.equal(t.metrics().scheduled,0);
  t.add([{at:.5,spec:s}],12);
  t.visit(12.2,()=>assert.fail(),(spec,start,origin)=>{assert.equal(start,12.5);assert.equal(origin,12);return true;});
  assert.equal(t.metrics().scheduled,0);
});
