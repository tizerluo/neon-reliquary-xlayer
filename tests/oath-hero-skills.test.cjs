const {test}=require('node:test');
const assert=require('node:assert/strict');
const {simulation}=require('./sim_harness.cjs');
const recipes=import('../visual-game/hero-skills/index.mjs');
const timeline=import('../visual-game/skill-fx-timeline.mjs');
const plain=v=>JSON.parse(JSON.stringify(v));

test('Persistent faults and four bomb explosions report actual zones and fuse results',()=>{
  for(const hero of [1,3]){
    const s=simulation({visual:true});s.start({hero});s.clear();const {P,actor}=s.raw();
    P.x=35;P.y=-60;P.aim=.37;P.shotCD=999;actor.skillCD=999;actor.ult=0;
    s.skills.cast(P);const cast=s.skills.events.find(e=>e.kind==='cast');
    assert.equal(cast.points.length,hero===1?3:4);
    for(const [i,p]of cast.points.entries())assert.deepEqual(plain({x:p.x,y:p.y,r:p.r}),plain({x:s.zones[i].x,y:s.zones[i].y,r:s.zones[i].r}));
    const expected=plain(cast.points.map(p=>({x:p.x,y:p.y,r:p.r})));
    for(let i=0;i<40;i++)s.tick(1/60);
    if(hero===3){const bombs=s.skills.events.filter(e=>e.kind==='bomb'&&e.owner===0);
      assert.equal(bombs.length,4);assert.deepEqual(plain(bombs.map(e=>e.points[0])),expected);
      assert(bombs.every(e=>e.time>0&&e.time<=.5));
    }else assert(s.zones.every(z=>z.owner===0&&z.skill));
  }
});

test('Ultimate visual observation preserves all six seeded combat simulations for a full channel',()=>{
  for(let hero=0;hero<6;hero++){
    const states=[false,true].map(visual=>{
      const s=simulation({visual,seed:619734});s.start({hero,companion:2});s.clear();const {P,actor}=s.raw();
      actor.skillCD=999;actor.ult=0;P.shotCD=999;P.aim=0;P.ult=100;
      for(let j=0;j<4;j++){const i=s.spawn(j,1,140+j*60,(j-1.5)*22);s.enemies.hp[i]=s.enemies.maxhp[i]=1e6;}
      s.hash();s.skills.cast(P);s.skills.ultimate(P);for(let i=0;i<264;i++)s.tick(1/60);return s;
    });
    const [legacy,hd]=states;
    for(const key of ['hp','shield','skillCD','ultTime','damageDealt','kills'])assert.equal(hd.raw().P[key],legacy.raw().P[key],hero+':P.'+key);
    for(const key of ['x','y','hp','freeze','stagger','slow'])assert.deepEqual(Array.from(hd.enemies[key]),Array.from(legacy.enemies[key]),hero+':E.'+key);
    for(const key of ['x','y','vx','vy','seed','target','targetGen'])assert.deepEqual(Array.from(hd.weapon.blades[key]),Array.from(legacy.weapon.blades[key]),hero+':B.'+key);
    const pulses=hd.skills.events.filter(e=>e.kind==='pulse'&&e.owner===0);assert(pulses.length>0);
    if(hero===0||hero===5)for(const e of pulses){assert.equal(e.points.length,3);for(const p of e.points){const along=(p.x-e.x)*Math.cos(e.angle)+(p.y-e.y)*Math.sin(e.angle),side=-(p.x-e.x)*Math.sin(e.angle)+(p.y-e.y)*Math.cos(e.angle);
      assert(Math.abs((along-120)/38-Math.round((along-120)/38))<1e-5);assert(Math.abs(side)<=65.00001);assert.equal(p.r,72);}}
    if(hero===2)assert(pulses.some(e=>e.points.some(p=>Number.isInteger(p.target)&&p.generation>0)));
    if(hero===4)assert(pulses.every(e=>e.points.length===1&&e.points[0].r===98));
  }
});

test('Healing recipients and freeze shells come from successful combat results with pool generations',async()=>{
  const {heroRecipe,skillContext}=await recipes,{compilePreset}=await timeline;
  const s=simulation({visual:true});s.start({hero:4,companion:0});s.clear();const {P,actor}=s.raw();
  actor.x=P.x+249;actor.y=P.y;actor.hp-=10;s.skills.cast(P);
  const heal=s.skills.events.find(e=>e.kind==='heal');assert.equal(heal.points.length,1);assert.equal(heal.points[0].owner,actor.uid);
  actor.x=P.x+251;P.skillCD=0;s.skills.cast(P);assert.equal(s.skills.events.filter(e=>e.kind==='heal').length,1);
  actor.x=P.x;actor.downed=true;P.skillCD=0;s.skills.cast(P);assert.equal(s.skills.events.filter(e=>e.kind==='heal').length,1);
  const ice=simulation({visual:true});ice.start({hero:5});ice.clear();const leader=ice.raw().P;leader.damage=.01;leader.aim=0;
  const normal=ice.spawn(0,0,110,0),boss=ice.spawn(0,2,180,0);ice.enemies.hp[normal]=ice.enemies.hp[boss]=1e6;ice.hash();ice.skills.cast(leader);
  const freeze=ice.skills.events.find(e=>e.kind==='freeze'),c=skillContext(freeze);assert.equal(c.points.length,2);
  const durations=c.points.map(p=>p.duration).sort();assert(Math.abs(durations[0]-.35)<1e-6);assert(Math.abs(durations[1]-2.3)<1e-6);
  for(const cue of compilePreset(heroRecipe(5,'freeze',c),c)){assert(cue.spec.requireFreeze);assert.equal(cue.spec.generation,ice.enemies.gen[cue.spec.target]);assert.equal(cue.spec.life,ice.enemies.freeze[cue.spec.target]);}
  assert.equal(heroRecipe(5,'freeze',{...c,points:[{x:0,z:0,target:normal,generation:undefined,duration:2}]}).cues.length,0);
});

test('Six independent recipes align frame cues, stay pure and cannot invent targeted pulse locations',async()=>{
  const {HERO_SKILLS,heroRecipe}=await recipes,{FX_TIMING,compilePreset,createEffectTimeline}=await timeline;
  for(const h of HERO_SKILLS){
    const c=Object.freeze({hero:h.hero,owner:3,x:2,z:-1,angle:.8,seed:41,age:1.4,channelDuration:4.2,
      points:Object.freeze(Array.from({length:h.hero===3?4:3},(_,i)=>Object.freeze({x:4+i*2,z:-.8+i*.3,radius:2,duration:h.hero===3?.12+i*.12:2.3,target:i,generation:2,owner:i+1})))});
    const cast=compilePreset(heroRecipe(h.hero,'cast',c),c),channel=compilePreset(heroRecipe(h.hero,'channel',c),c);
    assert(cast.length<=20);assert(channel.length<=12);assert(cast.some(e=>e.at===FX_TIMING.castContact));
    assert(channel.some(e=>e.at===FX_TIMING.channelEnter));assert(channel.some(e=>e.at===FX_TIMING.channelHold));
    for(const kind of ['pulse','bomb','heal','freeze']){const definition=heroRecipe(h.hero,kind,c);assert.deepEqual(definition,heroRecipe(h.hero,kind,c));assert(compilePreset(definition,c).length<=24);}
    for(const kind of ['pulse','bomb','heal','freeze'])if((kind==='pulse'&&[0,2,4,5].includes(h.hero))||kind!=='pulse')assert.equal(heroRecipe(h.hero,kind,{...c,points:[]}).cues.length,0,h.key+':'+kind);
    const t=createEffectTimeline();t.add(channel,0);t.visit(100,()=>assert.fail('补帧不可重放已过期技能'));assert.equal(t.metrics().scheduled,0);
    const targets=compilePreset(heroRecipe(h.hero,'pulse',c),c).filter(e=>e.spec.kind==='bolt');for(const {spec}of targets)assert(c.points.some(p=>p.x===spec.end[0]&&p.z===spec.end[2]));
  }
});

test('Volt E observes only real surviving lane targets for leader and teammate without changing RNG or combat',async()=>{
  const {heroRecipe,skillContext}=await recipes,{compilePreset}=await timeline;
  for(const teammate of [false,true]){
    const results=[false,true].map(visual=>{
      const s=simulation({visual,seed:77321});s.start({hero:teammate?0:2,companion:2});s.clear();
      const {P,actor}=s.raw(),caster=teammate?actor:P;caster.x=caster.y=0;caster.aim=0;caster.damage=1;
      P.shotCD=999;actor.shotCD=999;actor.skillCD=999;caster.skillCD=0;
      const targets=[s.spawn(0,0,110,0),s.spawn(0,2,180,0),s.spawn(0,0,210,200),s.spawn(0,0,150,0)];
      for(const i of targets)s.enemies.hp[i]=1e6;s.enemies.hp[targets[3]]=1;
      s.hash();s.skills.cast(caster);return {s,caster,targets};
    });
    const [legacy,hd]=results,{s,caster,targets}=hd;
    assert.equal(s.randomState(),legacy.s.randomState());
    for(const key of ['x','y','hp','freeze','stagger','kx','ky','a'])assert.deepEqual(Array.from(s.enemies[key]),Array.from(legacy.s.enemies[key]),key);
    for(const key of ['hp','shield','skillCD','ult','damageDealt','kills'])assert.equal(caster[key],legacy.caster[key],key);
    const event=s.skills.events.find(e=>e.kind==='stun');assert(event);assert.equal(event.owner,caster.uid);
    assert.deepEqual(plain(event.points.map(p=>p.target).sort((a,b)=>a-b)),targets.slice(0,2).sort((a,b)=>a-b));
    const c=skillContext(event),compiled=compilePreset(heroRecipe(2,'stun',c),c);
    assert.equal(compiled.length,6);assert(compiled.every(e=>e.at===0&&e.spec.requireStun&&!e.spec.cancelOnOwnerLoss));
    for(const p of c.points){assert.equal(p.generation,s.enemies.gen[p.target]);assert.equal(p.duration,s.enemies.freeze[p.target]);
      for(const {spec}of compiled.filter(e=>e.spec.target===p.target))assert.equal(spec.life,p.duration);}
    assert(Math.abs(c.points.find(p=>p.target===targets[1]).duration-.22)<1e-6);
    assert.equal(c.points.find(p=>p.target===targets[0]).duration,1);
    assert.equal(heroRecipe(2,'stun',{...c,points:[{...c.points[0],generation:undefined}]}).cues.length,0);
    const dense={...c,points:Array.from({length:30},(_,i)=>({...c.points[0],target:i}))};
    assert.equal(compilePreset(heroRecipe(2,'stun',dense),dense).length,24);
  }
});

test('Volt paralysis follows target state with fixed pause phase and bounded reduced-quality decoration',async()=>{
  const THREE=await import('three'),{createSkillFX}=await import('../visual-game/skill-fx.mjs');
  const originalDocument=global.document;
  global.document={createElement:()=>({getContext:()=>new Proxy({}, {get:()=>()=>{},set:()=>true})})};
  let fx;
  try{
    fx=createSkillFX(new THREE.Scene(),{feedbackEnabled:false});
    const P={uid:0,heroId:2,x:0,y:0,aim:0},E={a:[1,1],gen:[1,1],freeze:[1,.22],x:[100,200],y:[0,0]};
    const event={id:1,kind:'stun',hero:2,owner:0,time:0,x:0,y:0,angle:0,points:[0,1].map(target=>({target,generation:1,x:E.x[target],y:0,r:18,duration:E.freeze[target]}))};
    const frame={run:{time:.1},P,E,agents:[],skillEvents:[event],options:{quality:'high',glow:false}};
    const update=()=>{fx.update(frame,{});return fx.metrics();};
    let m=update();assert.equal(m.counts.bolt,6);assert.equal(m.active.length,6);
    const first=plain(m.active);assert.deepEqual(plain(update().active),first,'paused time keeps phase and placement');
    E.x[0]+=25;E.y[0]+=10;m=update();
    for(const a of m.active.filter(a=>a.target===0)){const before=first.find(b=>b.label===a.label&&b.target===a.target);
      assert(Math.abs(a.position[0]-before.position[0]-.7)<1e-6);assert(Math.abs(a.position[2]-before.position[2]-.28)<1e-6);}
    frame.options.quality='low';assert.equal(update().counts.bolt,4);
    frame.options.quality='high';frame.options.reducedMotion=true;assert.equal(update().counts.bolt,4);
    frame.options.reducedMotion=false;P.downed=true;assert.equal(update().counts.bolt,6,'accepted stun survives caster loss');
    frame.run.time=.23;E.freeze[1]=0;m=update();assert.equal(m.counts.bolt,3);assert(m.active.every(a=>a.target===0));
    E.freeze[0]=0;assert.equal(update().counts.bolt,0,'clear immediately when frozen state ends');
    for(const reason of ['dead','generation','expired']){
      fx.reset(frame.run);P.downed=false;E.a[0]=1;E.gen[0]=1;E.freeze[0]=1;frame.run.time=.1;frame.skillEvents=[{...event,points:[event.points[0]]}];
      assert.equal(update().counts.bolt,3);
      if(reason==='dead')E.a[0]=0;if(reason==='generation')E.gen[0]++;if(reason==='expired')frame.run.time=1;
      assert.equal(update().counts.bolt,0,reason+' cancels target FX');assert.equal(fx.metrics().scheduled,0);
    }
    fx.reset(frame.run);frame.run.time=.1;E.gen[0]=1;E.a[0]=1;E.freeze[0]=1;frame.skillEvents=[{...event,points:[event.points[0]]}];update();
    frame.skillEvents.push({...event,id:2,time:.1,points:[{...event.points[0],duration:.22}]});
    assert.equal(update().counts.bolt,3,'repeat accepted stun replaces target instance');
    assert.equal(fx.metrics().scheduled,3);frame.run.time=.33;assert.equal(update().counts.bolt,0,'refresh uses new real duration');
  }finally{fx?.dispose();global.document=originalDocument;}
});
