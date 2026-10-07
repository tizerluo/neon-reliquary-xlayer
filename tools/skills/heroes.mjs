import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { createSkillFX } from '/visual-game/skill-fx.mjs';
import { FX_TIMING } from '/visual-game/skill-fx-timeline.mjs';
import { HERO_SKILLS } from '/visual-game/hero-skills/index.mjs';
import { HEROES } from '/visual-game/presentation.mjs';
import { createRegionReflections } from '/visual-game/arena-reflections.mjs';
import { createGlow, glowWeight, tuneMaterial } from '/visual-game/glow.js';

const $=id=>document.getElementById(id),q=new URLSearchParams(location.search),errors=[];
window.addEventListener('error',e=>errors.push(e.message));window.addEventListener('unhandledrejection',e=>errors.push(String(e.reason)));
const renderer=new THREE.WebGLRenderer({canvas:$('c'),alpha:true,antialias:true,preserveDrawingBuffer:true});
renderer.setPixelRatio(1);renderer.setSize(1280,720,false);renderer.outputColorSpace=THREE.SRGBColorSpace;
renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.2;renderer.info.autoReset=false;
const scene=new THREE.Scene(),camera=new THREE.OrthographicCamera(-18,18,10.125,-10.125,.1,150),reflections=createRegionReflections(renderer);
scene.environmentIntensity=.9;scene.add(new THREE.HemisphereLight(0x9d8cff,0x0a0612,.6));
for(const [color,intensity,pos] of [[0xefe8ff,2.2,[-2,4.8,3.4]],[0xa070ff,1.5,[-2.3,3.3,-3.3]],[0x40e0ff,.8,[2.5,2.7,-2.9]]]){const l=new THREE.DirectionalLight(color,intensity);l.position.set(...pos);scene.add(l);}
const ground=new THREE.Mesh(new THREE.PlaneGeometry(70,50).rotateX(-Math.PI/2),new THREE.MeshStandardMaterial({color:0x0a111d,roughness:.85,metalness:.15}));ground.position.y=-.025;ground.userData.noGlow=true;scene.add(ground);
const grid=new THREE.GridHelper(60,60,0x233346,0x182534);grid.material.transparent=true;grid.material.opacity=.16;grid.userData.noGlow=true;scene.add(grid);
const telegraph=new THREE.Group();for(const [r,opacity] of [[1.8,.8],[.95,.48]]){const m=new THREE.Mesh(new THREE.RingGeometry(r-.025,r,64).rotateX(-Math.PI/2),new THREE.MeshBasicMaterial({color:0xff596b,transparent:true,opacity,depthWrite:false}));m.position.set(6.6,.08,-.45);m.userData.noGlow=true;telegraph.add(m);}scene.add(telegraph);
const glow=createGlow(renderer,scene,camera,{strength:.85,radius:.4,weight:glowWeight});glow.setSize(1280,720);
const fx=createSkillFX(scene,{feedbackRoot:$('stage')}),loader=new GLTFLoader(),models=new Map();
const run={time:0},P={uid:0,x:0,y:0,aim:0,ultAim:0,ultTime:0,downed:false},companion={uid:1,x:-60,y:-70,aim:0,ultTime:0,downed:false};
const E={a:new Uint8Array(12).fill(1),gen:new Uint32Array(12).fill(1),x:new Float32Array(12),y:new Float32Array(12),freeze:new Float32Array(12)};
const frame={run,P,E,agents:[companion],skillEvents:[],options:{quality:'high',shake:true}},native={viewWidth:1280,viewHeight:720,sinElev:.783};
let heroIndex=Math.max(0,Math.min(5,Number(q.get('hero'))||0)),kind=q.get('kind')==='channel'?'channel':'cast',time=Number(q.get('time'))||0,playing=q.get('paused')!=='1',model=null,cycle=-1,angle=-.12;
const length=()=>kind==='channel'?4.8:3.0;
async function loadHero(index){
  if(models.has(index))return models.get(index);
  const def=HEROES[index],gltf=await loader.loadAsync('/visual-lab/assets/'+def.glb),root=gltf.scene;
  root.traverse(o=>{if(o.isMesh)for(const m of [].concat(o.material))tuneMaterial(m,def.id);});
  const size=new THREE.Box3().setFromObject(root).getSize(new THREE.Vector3());root.scale.setScalar(def.height/size.y);
  root.rotation.y=-angle-Math.PI/2;scene.add(root);root.visible=false;
  const mixer=new THREE.AnimationMixer(root),clips=Object.fromEntries(gltf.animations.map(c=>[c.name,c]));
  const rec={root,mixer,clips,action:null};models.set(index,rec);return rec;
}
function event(kind,at,data={}){return {id:frame.skillEvents.length+1,kind,time:at,owner:0,hero:heroIndex,x:P.x,y:P.y,angle,duration:kind==='channel'?4.2:1.02,...data};}
function along(distance,side=0,r=72){return {x:Math.cos(angle)*distance-Math.sin(angle)*side,y:Math.sin(angle)*distance+Math.cos(angle)*side,r};}
function schedule(base){
  fx.reset(run);frame.skillEvents=[];P.downed=false;E.freeze.fill(0);
  const points=heroIndex===1?[100,220,340].map(d=>({...along(d,0,62),duration:2.5})):heroIndex===3?[85,167,249,331].map((d,i)=>({...along(d,0,80),duration:.12+i*.12})):[];
  frame.skillEvents.push(event(kind,base,{points}));
  if(kind==='cast'){
    if(heroIndex===3)points.forEach(p=>frame.skillEvents.push(event('bomb',base+p.duration,{points:[p]})));
    if(heroIndex===4)frame.skillEvents.push(event('heal',base,{points:[{x:companion.x,y:companion.y,owner:1}]}));
    if(heroIndex===5){const frozen=[140,240,320].map((d,i)=>({...along(d,(i-1)*47,18),target:i,generation:1,duration:2.3}));
      frozen.forEach(p=>{E.x[p.target]=p.x;E.y[p.target]=p.y;E.freeze[p.target]=p.duration;});frame.skillEvents.push(event('freeze',base,{points:frozen}));}
  }else{
    const interval=heroIndex===3?11/60:22/60;
    for(let t=1/60;t<4.2;t+=interval){let actual=[];
      if(heroIndex===0||heroIndex===5)actual=[0,1,2].map(j=>along(120+((Math.floor(t*9)+j*3)%9)*38,[-43,19,52][j]));
      if(heroIndex===2)actual=[170,280,410].map((d,i)=>({...along(d,(i-1)*52,18),target:i,generation:1}));
      if(heroIndex===4)actual=[along(140+(Math.floor(t*8)%4)*70,0,98)];
      frame.skillEvents.push(event('pulse',base+t,{points:actual,age:t,angle:heroIndex===1?angle+Math.sin(t*12)*.18:angle}));
    }
  }
  frame.skillEvents.sort((a,b)=>a.time-b.time);frame.skillEvents.forEach((e,i)=>e.id=i+1);
  if(model){model.mixer.stopAllAction();const clip=model.clips[kind==='cast'?'Cast':'Channel'];model.action=clip?model.mixer.clipAction(clip):null;
    if(model.action){model.action.reset().setLoop(THREE.LoopOnce,1);model.action.clampWhenFinished=true;model.action.play();}}
}
function render(){
  run.time=time;const nextCycle=Math.floor(time/length()),age=time-nextCycle*length(),base=nextCycle*length();
  if(nextCycle!==cycle){cycle=nextCycle;schedule(base);}P.ultTime=kind==='channel'?Math.max(0,4.2-age):0;
  if(heroIndex===5&&kind==='cast')for(let i=0;i<3;i++)E.freeze[i]=Math.max(0,2.3-age);
  if(model?.action){model.action.time=kind==='channel'&&age>FX_TIMING.channelHold&&age<3.6?FX_TIMING.channelHold:kind==='channel'&&age>=3.6?FX_TIMING.channelHold+age-3.6:age;model.mixer.update(0);}
  const half=$('detail').checked?10.8:17.92;camera.left=-half;camera.right=half;camera.top=half*9/16;camera.bottom=-camera.top;camera.updateProjectionMatrix();camera.position.set(4.3,34,27);camera.lookAt(4.3,0,0);
  // 审图可以拖动时间轴；只把已经发生的演示事件交给同一个实战渲染器。
  fx.update({...frame,skillEvents:frame.skillEvents.filter(e=>e.time<=time)},native);
  renderer.info.reset();renderer.render(scene,camera);if($('bloom').checked)glow.render();
  $('caption').textContent=['奥瑞利安','莫德雷德','沃尔特','尼克斯','塞拉芙','伊索尔德'][heroIndex]+' · '+HERO_SKILLS[heroIndex].name;
  $('time').max=length();$('time').value=age;$('seconds').textContent=age.toFixed(3)+' s';
  $('cue').textContent=(kind==='cast'?'CAST · 接触 14/26 = .538 s':'CHANNEL · 进入 13/26 = .500 s · 保持 28/26 = 1.077 s')+' · '+(age*26).toFixed(1)+' frame';
  $('status').textContent=renderer.info.render.calls+' draws · '+fx.metrics().scheduled+' cues · errors '+errors.length;
}
async function select(index=heroIndex,nextKind=kind){playing=false;heroIndex=index;kind=nextKind;model=await loadHero(index);for(const [i,m] of models)m.root.visible=i===index;
  scene.environment=reflections.get(['cathedral','foundry','cathedral','throne','cathedral','archive'][index]);
  $('hero').value=index;$('kind').value=kind;seek(0);}
function seek(t){playing=false;time=Math.max(0,t);cycle=-1;render();$('play').textContent='播放';}
const stats=()=>({hero:heroIndex,kind,time,errors:[...errors],fx:fx.metrics(),drawCalls:renderer.info.render.calls,
  geometries:renderer.info.memory.geometries,textures:renderer.info.memory.textures,programs:renderer.info.programs.map(p=>({runnable:p.diagnostics?.runnable!==false}))});
window.heroSkillReview={select,seek,advance(dt){time+=dt;render();},stats,angle(v){angle=v;P.aim=P.ultAim=v;if(model)model.root.rotation.y=-v-Math.PI/2;seek(time);},
  bloom(v){$('bloom').checked=v;render();},low(v){frame.options.quality=v?'low':'high';$('low').checked=v;render();},reduced(v){frame.options.reducedMotion=v;$('reduced').checked=v;render();},detail(v){$('detail').checked=v;render();},
  cancel(){P.ultTime=0;P.downed=true;fx.update({...frame,skillEvents:[]},native);renderer.render(scene,camera);return fx.metrics();},
  lifecycle(){const before={geometries:renderer.info.memory.geometries,textures:renderer.info.memory.textures};const temp=createSkillFX(scene);temp.play('aurelian.cast',{owner:0,hero:0,angle:0},0);temp.update({...frame,run:{time:.65},skillEvents:[]},native);renderer.render(scene,camera);
    const during={geometries:renderer.info.memory.geometries,textures:renderer.info.memory.textures};temp.dispose();temp.dispose();renderer.render(scene,camera);return {before,during,after:{geometries:renderer.info.memory.geometries,textures:renderer.info.memory.textures},disposed:temp.metrics().disposed};},
};
$('hero').onchange=e=>select(+e.target.value);$('kind').onchange=e=>select(heroIndex,e.target.value);
$('time').oninput=e=>seek(+e.target.value);$('play').onclick=()=>{playing=!playing;$('play').textContent=playing?'暂停':'播放';};$('restart').onclick=()=>{seek(0);playing=true;$('play').textContent='暂停';};
$('bloom').onchange=render;$('low').onchange=e=>heroSkillReview.low(e.target.checked);$('reduced').onchange=e=>heroSkillReview.reduced(e.target.checked);$('detail').onchange=render;
$('cast14').onclick=async()=>{await select(heroIndex,'cast');seek(FX_TIMING.castContact);};$('channel13').onclick=async()=>{await select(heroIndex,'channel');seek(FX_TIMING.channelEnter);};$('channel28').onclick=async()=>{await select(heroIndex,'channel');seek(FX_TIMING.channelHold);};
const requestedTime=time,requestedPlaying=playing;await select();seek(requestedTime);playing=requestedPlaying;$('play').textContent=playing?'暂停':'播放';window.__done=true;
let last=performance.now();function animate(now){const dt=Math.min(.05,(now-last)/1000);last=now;if(playing){time+=dt;render();}requestAnimationFrame(animate);}requestAnimationFrame(animate);
