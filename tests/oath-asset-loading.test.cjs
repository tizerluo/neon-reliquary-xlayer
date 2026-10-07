const {test}=require('node:test');
const assert=require('node:assert/strict');
const {simulation}=require('./sim_harness.cjs');
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function until(fn){for(let i=0;i<200;i++){if(fn())return;await sleep(5);}assert.fail('Asset pipeline did not settle');}
const library=()=>import('../visual-game/asset-loading.mjs');
const response=()=>new Response(new Uint8Array([1,2,3,4]),{headers:{'content-length':'4'}});
const url=path=>'https://game.example/'+path;

test('Download completion is distinct from model preparation and the first actual frame',async()=>{
  const {describeAssets}=await library(), records=new Map([['hero',{state:'loading',phase:'download',loaded:2,total:4}],['arena',{state:'preparing',phase:'prepare',loaded:8,total:8}]]);
  let status=describeAssets(records,['hero','arena','hero']);
  assert.equal(status.progress,10/12);assert.equal(status.count,2);assert.equal(status.phase,'download');
  records.get('hero').state='ready';records.get('hero').loaded=4;
  assert.equal(describeAssets(records,['hero','arena']).phase,'prepare');
  records.get('arena').state='ready';
  assert.equal(describeAssets(records,['hero','arena']).phase,'frame');
  assert.equal(describeAssets(records,['hero','arena'],true).state,'ready');
  records.get('arena').state='missing';
  assert.deepEqual(describeAssets(records,['hero','arena'],true).failed,['arena']);
  records.get('hero').state='loading';
  assert.equal(describeAssets(records,['hero','arena']).state,'missing');
  assert.equal(describeAssets(records,['hero','arena']).phase,'failed');
  records.get('hero').total=0;assert.equal(describeAssets(records,['hero','arena']).progress,null);
});

test('Bounded downloads prioritize the selected subject and serialize preparation',async()=>{
  const {createAssetStore}=await library();let fetching=0,maxFetching=0,preparing=0,maxPreparing=0;const order=[];
  const store=createAssetStore({url,concurrency:2,yieldPaint:async()=>{},fetcher:async path=>{
    fetching++;maxFetching=Math.max(maxFetching,fetching);order.push(path);await sleep(6);fetching--;return response();
  },loader:{parseAsync:async()=>{preparing++;maxPreparing=Math.max(maxPreparing,preparing);await sleep(5);preparing--;return{};}}});
  store.load('later','later.glb',async()=>({}),2);store.load('selected','selected.glb',async()=>({}),0);
  store.load('arena','arena.glb',async()=>({}),0);store.load('extra','extra.glb',async()=>({}),2);
  await until(()=>[...store.records.values()].every(r=>r.state==='ready'));
  assert.deepEqual(order.slice(0,2),[url('selected.glb'),url('arena.glb')]);
  assert(maxFetching<=2);assert.equal(maxPreparing,1);
  assert.equal(store.records.get('selected').loaded,4);
  assert.equal(store.load('selected','selected.glb',()=>assert.fail('cached subject re-prepared')),store.records.get('selected'));
});

test('HTTP failures settle, retry a new request, and preserve the record used by the arena',async()=>{
  const {createAssetStore}=await library();let count=0;const urls=[];
  const store=createAssetStore({url,yieldPaint:async()=>{},fetcher:async path=>{urls.push(path);return ++count===1?new Response('',{status:503}):response();},loader:{parseAsync:async()=>({})}});
  const rec=store.load('arena','arena.glb',()=>({root:'current'}));await until(()=>rec.state==='missing');
  assert.match(rec.error,/503/);store.retry(['arena']);await until(()=>rec.state==='ready');
  assert.equal(store.records.get('arena'),rec);assert.equal(rec.root,'current');assert.equal(rec.attempt,1);
  assert.equal(urls[1],url('arena.glb')+'?retry=1');
});

test('Rapid selection promotes the newest queued subject over former selections',async()=>{
  const {createAssetStore}=await library();let release;const order=[];
  const store=createAssetStore({url,concurrency:1,yieldPaint:async()=>{},fetcher:async path=>{
    order.push(path);if(path.endsWith('active.glb'))await new Promise(resolve=>{release=resolve;});return response();
  },loader:{parseAsync:async()=>({})}});
  store.load('active','active.glb',()=>({}));await until(()=>release);
  store.load('previous','previous.glb',()=>({}));store.load('newest','newest.glb',()=>({}));
  store.prioritize(['newest']);release();await until(()=>[...store.records.values()].every(r=>r.state==='ready'));
  assert.deepEqual(order,[url('active.glb'),url('newest.glb'),url('previous.glb')]);
});

test('A timed out preparation cannot overwrite a successful retry when it eventually finishes',async()=>{
  const {createAssetStore}=await library();let releaseOld,attempt=0;
  const store=createAssetStore({url,timeout:25,yieldPaint:async()=>{},fetcher:async()=>response(),loader:{parseAsync:async()=>({})}});
  const rec=store.load('hero','hero.glb',async()=>++attempt===1?new Promise(resolve=>{releaseOld=()=>resolve({root:'stale'});}):{root:'new'});
  await until(()=>rec.state==='missing');assert.equal(rec.error,'timeout');
  store.retry(['hero']);await until(()=>rec.state==='ready');releaseOld();await sleep(5);
  assert.equal(rec.root,'new');assert.equal(rec.attempt,1);
});

test('No Content-Length keeps download progress indeterminate until the bytes really arrive',async()=>{
  const {createAssetStore}=await library();let push;
  const stream=new ReadableStream({start(controller){push=controller;}});
  const store=createAssetStore({url,yieldPaint:async()=>{},fetcher:async()=>new Response(stream),loader:{parseAsync:async()=>({})}});
  const rec=store.load('hero','hero.glb',()=>({}));await until(()=>rec.phase==='download');
  push.enqueue(new Uint8Array([1,2]));await until(()=>rec.loaded===2);
  assert.equal(store.describe(['hero']).progress,null);push.close();await until(()=>rec.state==='ready');
  assert.equal(rec.total,2);assert.equal(store.describe(['hero']).phase,'frame');
});

test('A visual loading hold freezes real combat, timers and manual skills, then resumes normally',()=>{
  const sim=simulation();sim.start({difficulty:0});const {P,run}=sim.raw();
  sim.bindInputs();sim.inputEvent('document','keydown',{key:'d'});P.ult=100;
  const before={time:run.time,wave:run.waveClock,x:P.x,hp:P.hp,ult:P.ult,inv:P.inv,skill:P.skillCD};
  sim.loadingHold(true);for(let i=0;i<120;i++)sim.tick(1/60);
  sim.skills.cast(P);sim.skills.ultimate(P);
  assert.deepEqual({time:run.time,wave:run.waveClock,x:P.x,hp:P.hp,ult:P.ult,inv:P.inv,skill:P.skillCD},before);
  sim.loadingHold(false);sim.tick(1/60);assert(run.time>before.time);assert(P.x>before.x);
});
