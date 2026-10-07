const { test } = require('node:test');
const assert = require('node:assert/strict');
const modules = Promise.all([import('three'),import('../visual-game/chest-rewards.mjs')]);
const event = (id=1,owner=0,rewards={overclock:8,energy:20,shield:12}) =>
  ({id,kind:'chest',time:0,owner,x:20,y:0,rewards});
const frame = () => ({run:{time:.4},P:{uid:0,x:0,y:0,downed:false},agents:[],options:{quality:'high'},pickupEvents:[event()]});

test('Reward silhouettes are real instanced meshes with shared metal/inlay materials and finite geometry', async () => {
  const [T,{createChestRewards}]=await modules,scene=new T.Scene(),fx=createChestRewards(scene),f=frame();
  fx.update(f);
  assert.deepEqual(fx.metrics().counts,{overclock:1,energy:1,shield:1});
  assert.equal(scene.children.length,6);assert.equal(fx.metrics().draws,6);
  assert.equal(new Set(scene.children.map(m=>m.material)).size,2);
  for(const mesh of scene.children){
    assert(mesh.isInstancedMesh);assert.equal(mesh.count,1);assert(mesh.material.depthWrite&&mesh.material.vertexColors);
    assert(mesh.geometry.getAttribute('color'));
    assert(mesh.geometry.getAttribute('position').array.every(Number.isFinite));
    assert(mesh.geometry.getAttribute('rewardOpacity').getX(0)>.9);
    assert.equal(typeof mesh.material.userData.createGlowMaterial,'function');
    const glow=mesh.material.userData.createGlowMaterial(.5);assert(glow.transparent);assert.equal(glow.depthWrite,false);
  }
  const shapes=scene.children.filter(m=>m.name.endsWith(' body')).map(m=>{m.geometry.computeBoundingBox();return m.geometry.boundingBox.getSize(new T.Vector3()).toArray();});
  assert.equal(new Set(shapes.map(v=>v.join(','))).size,3);
  fx.dispose();assert.equal(scene.children.length,0);
});

test('Objects represent actual positive grants, follow the actual recipient, and open once across toggles', async () => {
  const [T,{createChestRewards}]=await modules,scene=new T.Scene(),opened=[],fx=createChestRewards(scene,{onOpen:e=>opened.push(e.id)}),f=frame();
  f.agents=[{uid:7,x:100,y:0,downed:false}];f.pickupEvents=[event(1,7,{overclock:8,energy:0,shield:0})];fx.update(f);
  assert.deepEqual(fx.metrics().active.map(x=>[x.kind,x.amount,x.owner]),[['overclock',8,7]]);
  f.run.time=1.1;fx.update(f);const before=fx.metrics().active[0].position[0];
  f.agents[0].x=400;fx.update(f);assert(fx.metrics().active[0].position[0]>before+7);
  fx.update(f,.028,false,false);assert.equal(fx.metrics().active.length,0);
  fx.update(f,.028,false,true);assert.equal(fx.metrics().active.length,1);assert.deepEqual(opened,[1]);
  f.agents[0].downed=true;fx.update(f);assert.equal(fx.metrics().scheduled,0);assert.equal(fx.metrics().active.length,0);
  f.agents[0].downed=false;fx.update(f);assert.equal(fx.metrics().active.length,0);
  fx.dispose();
});

test('Pause, reduced motion, skipped time and reset cannot replay a finished or old reward', async () => {
  const [T,{createChestRewards,CHEST_REWARD_LIFE}]=await modules,fx=createChestRewards(new T.Scene()),f=frame();
  fx.update(f);const paused=JSON.stringify(fx.metrics());for(let i=0;i<12;i++)fx.update(f);assert.equal(JSON.stringify(fx.metrics()),paused);
  f.options.reducedMotion=true;fx.update(f);const still=fx.metrics().active.map(x=>x.position);
  f.run.time=.9;fx.update(f);assert.deepEqual(fx.metrics().active.map(x=>x.position),still);
  assert(fx.metrics().active.every(x=>x.phase==='still'&&x.rotation===0));
  fx.reset(f.run,1);fx.update(f);assert.equal(fx.metrics().active.length,0);
  f.run={time:.4};f.pickupEvents=[event(2)];fx.update(f);assert.equal(fx.metrics().active.length,3);
  f.run.time=CHEST_REWARD_LIFE+.01;fx.update(f);assert.equal(fx.metrics().scheduled,0);assert.equal(fx.metrics().active.length,0);
  fx.dispose();fx.dispose();assert(fx.metrics().disposed);fx.update(f);assert.equal(fx.metrics().active.length,0);
});

test('Dense rewards stay within fixed high/low budgets and reuse the same scene resources', async () => {
  const [T,{createChestRewards}]=await modules,scene=new T.Scene(),fx=createChestRewards(scene),f=frame();
  const meshes=[...scene.children],geometry=meshes.map(m=>m.geometry),materials=meshes.map(m=>m.material);
  f.pickupEvents=Array.from({length:32},(_,i)=>event(i+1));fx.update(f);
  assert.equal(fx.metrics().scheduled,12);assert.equal(fx.metrics().active.length,36);assert.equal(fx.metrics().dropped,20);
  f.options.quality='low';fx.update(f);assert.equal(fx.metrics().active.length,24);
  assert(scene.children.every((m,i)=>m===meshes[i]&&m.geometry===geometry[i]&&m.material===materials[i]));
  assert(scene.children.every(m=>m.count===8));assert.equal(fx.metrics().draws,6);
  f.pickupEvents=[event(NaN),event(33,0,{overclock:0,energy:Infinity,shield:-12})];fx.update(f);
  assert.equal(fx.metrics().scheduled,12);assert(fx.metrics().active.every(x=>Number.isFinite(x.amount)));
  fx.dispose();
});
