const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');

// Exercise the actual native renderer's dispatch and Canvas preview, without a GPU.
function previewHarness(){
  const draws=[],texts=[],calls=[];
  const ink=new Proxy({drawImage:image=>draws.push(image.name),fillText:text=>texts.push(text),
    createRadialGradient:()=>({addColorStop(){}})}, {get:(o,k)=>o[k]||((...xs)=>calls.push([k,...xs])),set:(o,k,v)=>(o[k]=v,true)});
  const canvas={width:1280,height:720,clientWidth:1280,clientHeight:720,style:{},getContext:()=>ink};
  const context={window:{},document:{getElementById:()=>canvas},URLSearchParams,location:{search:''}};
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/renderer.js'),'utf8')+'\nthis.Renderer=NRRenderer;',context);
  const renderer=Object.create(context.Renderer.prototype);
  Object.assign(renderer,{hdUI:true,options:{backend:'auto'},gl:{},hadContextLoss:false,
    canvas,fallback:canvas,time:0,viewWidth:1280,viewHeight:720,aspect:16/9,sinElev:.8,
    meshes:{hero0:{count:1},boss0:{count:1},menu:{count:1}},uiImages:new Map()});
  const manifest=JSON.parse(fs.readFileSync(path.join(__dirname,'../visual-lab/assets/ui/manifest.json')));
  for(const entry of Object.values(manifest.assets)){
    const name=entry.file.replace('.png','');
    renderer.uiImages.set(name,{name,complete:true,naturalWidth:512,naturalHeight:512,
      uiState:'ready',uiBounds:{x:0,y:0,width:512,height:512}});
  }
  return{renderer,context,draws,texts,calls};
}

test('Cold startup and failed GLBs use current portraits and arenas for every menu subject',()=>{
  const heroes=['aurelian','mordred','volt','nyx','seraph','isolde'],regions=['cathedral','archive','foundry','throne'];
  for(const assetState of [undefined,'loading','missing']){
    for(const state of ['home','select','inspect'])for(let id=0;id<(state==='inspect'?8:6);id++){
      const {renderer,context,draws}=previewHarness();
      if(assetState)context.window.__NR_VISUAL={presentation:null,presentationState:assetState};
      renderer.render({state,selected:id,inspection:{id},language:'en'});
      const stage=state==='home'?0:state==='select'?[0,2,0,3,0,1][id]:Math.floor(id/2);
      assert.deepEqual(draws,['arena-'+regions[stage],state==='inspect'?'boss-'+id:'hero-'+heroes[id]]);
      assert.equal(renderer.presentationInfo.mode,'static');
      assert.equal(renderer.drawCalls,0);
      assert(Object.values(renderer.meshes).every(mesh=>mesh.count===0),'old native meshes submitted');
      assert.equal(renderer.canvas.style.visibility,'visible','Canvas input surface must remain usable');
    }
  }
});

test('Portrait load and failure show a neutral placeholder, including compatibility mode',()=>{
  for(const uiState of ['loading','missing'])for(const backend of ['auto','canvas']){
    const {renderer,texts,calls}=previewHarness();renderer.options.backend=backend;
    Object.assign(renderer.uiImages.get('hero-aurelian'),{complete:uiState==='missing',naturalWidth:0,uiState});
    renderer.render({state:'home',selected:0,language:'zh'});
    assert.equal(renderer.presentationInfo.mode,uiState==='missing'?'unavailable':'loading');
    assert.deepEqual(texts,[uiState==='missing'?'预览暂不可用':'正在载入预览']);
    assert(!calls.some(([name])=>name==='translate'||name==='scale'),'legacy knight drawn');
  }
});

test('A ready previous subject does not remove the new subject preview',()=>{
  const {renderer,context,draws}=previewHarness();
  context.window.__NR_VISUAL={presentation:'hero',presentationKey:'hero:aurelian',presentationState:'loading'};
  renderer.render({state:'select',selected:3,language:'en'});
  assert.deepEqual(draws,['arena-throne','hero-nyx']);
  assert.equal(renderer.presentationInfo.key,'hero:nyx');
});

test('Only a matching ready presentation enters the live renderer; explicit legacy stays opt-in',()=>{
  for(const hdUI of [true,false]){
    const {renderer,context}=previewHarness();renderer.hdUI=hdUI;
    if(hdUI)context.window.__NR_VISUAL={presentation:'hero',presentationKey:'hero:aurelian'};
    const reachedLive=new Error('live rendering reached');renderer.setupScene=()=>{throw reachedLive;};
    assert.throws(()=>renderer.render({state:'home',selected:0}),e=>e===reachedLive);
    assert.equal(renderer.presentationInfo.mode,hdUI?'live':'legacy');
  }
});

test('Inspector controls follow the current Boss readiness, failure and recovery',()=>{
  const labels={inspectModel:{},inspectHint:{}},panel={dataset:{},querySelector:s=>labels[s.includes('inspectModel')?'inspectModel':'inspectHint']};
  const elements={inspect:panel,inspectRotation:{},inspectAuto:{}};
  const context={window:{},renderer:{gl:{},hdUI:true},options:{backend:'auto'},inspection:{id:7,auto:true},language:'en',
    $:id=>elements[id],tx:key=>key,coopText:en=>en};
  vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/inspector.js'),'utf8'),context);
  const sync=()=>vm.runInContext('syncInspectorRendering()',context);
  sync();assert.equal(panel.dataset.renderMode,'loadingen');assert.equal(elements.inspectRotation.disabled,true);
  context.window.__NR_VISUAL={presentation:'boss',presentationKey:'boss-0',presentationState:'loading'};
  sync();assert.equal(elements.inspectAuto.disabled,true,'previous Boss readiness leaked');
  context.window.__NR_VISUAL={presentation:null,presentationState:'missing'};
  sync();assert.equal(panel.dataset.renderMode,'staticen');assert.match(labels.inspectHint.textContent,/UNAVAILABLE/);
  context.window.__NR_VISUAL={presentation:'boss',presentationKey:'boss-7',presentationState:'ready'};
  sync();assert.equal(panel.dataset.renderMode,'liveen');assert.equal(elements.inspectRotation.disabled,false);
  context.window.__NR_VISUAL=null;context.window.__NR_VISUAL_LOAD_ERROR='module fetch failed';
  sync();assert.equal(panel.dataset.renderMode,'staticen');assert.equal(elements.inspectAuto.disabled,true);
});
