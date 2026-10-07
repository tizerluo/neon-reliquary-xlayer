// 三层技能特效工具：贴花 / 实例化网格 / 轻屏幕反馈。坐标用米，时间只取 run.time。
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { ADDITIVE } from './glow.js';
import { FX_COLORS, FX_PATTERNS, COMMON_SKILL_PRESETS, compilePreset, normalizeEffect, createEffectTimeline } from './skill-fx-timeline.mjs';
import { HERO_SKILLS, skillContext, heroRecipe } from './hero-skills/index.mjs';

function sigilAtlas() {
  const c = document.createElement('canvas'); c.width = 1536; c.height = 512;
  const g = c.getContext('2d'); g.strokeStyle = '#fff'; g.fillStyle = '#fff';
  const circle = (r, width = 3, dashed = []) => { g.lineWidth = width; g.setLineDash(dashed); g.beginPath(); g.arc(256, 256, r, 0, Math.PI * 2); g.stroke(); g.setLineDash([]); };
  const segment = (a, b, width = 3) => { g.lineWidth = width; g.beginPath(); g.moveTo(...a); g.lineTo(...b); g.stroke(); };
  const radial = (angle, r) => [256 + Math.cos(angle) * r, 256 + Math.sin(angle) * r];
  // 圣印：三圈分层边框、断续符文与六向棱形。留大面积空隙给地面和红色预警。
  circle(222, 2); circle(208, 4, [17, 9]); circle(174, 2); circle(85, 2);
  for (let i = 0; i < 24; i++) {
    const a = i * Math.PI / 12, p = radial(a, 192); g.save(); g.translate(...p); g.rotate(a);
    segment([-7, -4], [7, -4], 2); segment([0, -8], [0, 7], 2);
    if (i % 3 === 0) { segment([-6, 6], [6, 6], 2); segment([6, -4], [6, 6], 2); } g.restore();
  }
  for (let i = 0; i < 6; i++) {
    const a = i * Math.PI / 3, b = a + Math.PI / 3; segment(radial(a, 151), radial(b, 151), 3);
    segment(radial(a, 92), radial(a, 163), 3);
    const p = radial(a, 163); g.save(); g.translate(...p); g.rotate(a + Math.PI / 4); g.strokeRect(-5, -5, 10, 10); g.restore();
  }
  g.lineWidth = 4; g.beginPath(); g.moveTo(256, 206); g.lineTo(280, 256); g.lineTo(256, 306); g.lineTo(232, 256); g.closePath(); g.stroke();
  // 轨道：沿 +X 方向填充，双侧线、门环、箭头都属于同一进度遮罩。
  g.setTransform(1, 0, 0, 1, 512, 0);
  for (const y of [82, 112, 400, 430]) segment([24, y], [488, y], y === 82 || y === 430 ? 2 : 4);
  for (let x = 56; x < 485; x += 80) {
    segment([x, 105], [x, 160], 3); segment([x, 352], [x, 407], 3);
    segment([x - 17, 219], [x + 17, 256], 4); segment([x + 17, 256], [x - 17, 293], 4);
    g.lineWidth = 2; g.beginPath(); g.ellipse(x, 256, 17, 151, 0, -.55, .55); g.stroke();
  }
  // 扇面：细轮廓与稀疏放射格，角度进度只改变图案亮度，不伪装为敌人倒计时。
  g.setTransform(1, 0, 0, 1, 1024, 0);
  const half = 1.0;
  for (const r of [132, 188, 222]) { g.lineWidth = r === 188 ? 4 : 2; g.beginPath(); g.arc(256, 256, r, -half, half); g.stroke(); }
  for (let j = 0; j < 9; j++) {
    const a = -half + j * half / 4; segment(radial(a, j === 0 || j === 8 ? 32 : 136), radial(a, 224), j === 0 || j === 8 ? 3 : 2);
    const p = radial(a, 203); g.save(); g.translate(...p); g.rotate(a + Math.PI / 4); g.strokeRect(-5, -5, 10, 10); g.restore();
  }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.generateMipmaps = false; t.minFilter = THREE.LinearFilter; return t;
}

const vertexShader = `
uniform float mode;
attribute vec4 fxParams; attribute vec4 fxStyle; attribute vec3 fxColor; attribute float fxShape;
varying vec2 vUv; varying vec4 vFx; varying vec4 vStyle; varying vec3 vColor; varying float vShape; varying vec3 vNormal;
void main(){vUv=uv;vFx=fxParams;vStyle=fxStyle;vColor=fxColor;vShape=fxShape;
  vNormal=normalize(mat3(modelViewMatrix*instanceMatrix)*normal);
  vec3 p=position;
  if(mode>=0.0&&mode<.5){float a=(uv.x-.5)*fxStyle.x*2.0;p.xz=vec2(cos(a),sin(a))*(1.0-(1.0-uv.y)*fxShape);}
  if(mode>6.5&&mode<7.5){float pin=sin(uv.x*3.14159265);p.z+=sin(uv.x*47.0+fxParams.w*2.31)*pin*fxStyle.w;p.y+=cos(uv.x*39.0+fxParams.w)*pin*fxStyle.w*.32;}
  if(mode>7.5&&mode<8.5)p.z+=sin(uv.x*15.0-fxStyle.z*9.0+fxParams.w)*sin(uv.x*3.14159265)*.13;
  gl_Position=projectionMatrix*modelViewMatrix*instanceMatrix*vec4(p,1.0);}`;
const noiseShader = `
float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float noise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);
 return mix(mix(hash(i),hash(i+vec2(1,0)),f.x),mix(hash(i+vec2(0,1)),hash(i+vec2(1,1)),f.x),f.y);}
float erosion(vec2 uv){return smoothstep(vFx.z-.035,vFx.z+.035,noise(uv*27.0+vFx.w*.01));}`;
const decalShader = `
uniform sampler2D atlas; varying vec2 vUv; varying vec4 vFx; varying vec4 vStyle; varying vec3 vColor; varying float vShape;
${noiseShader}
float stroke(float d,float w){return 1.0-smoothstep(w,w+.008,abs(d));}
float theme(vec2 q,float a,float r){
 float pat=vStyle.y,ink=0.0;
 if(pat<1.5){
  float fiss=q.y-(sin(q.x*18.0+vFx.w)*.13+sin(q.x*39.0)*.035);
  ink=stroke(fiss,.016)*smoothstep(.03,.12,abs(q.x));
  ink+=stroke(abs(q.y)-.48-abs(sin(q.x*13.0))*.17,.009)*step(.1,abs(q.x));
  ink*=1.0-smoothstep(.85,1.0,abs(q.x));
 }else if(pat<2.5){
  ink=stroke(abs(q.y)-.75,.009)+stroke(abs(q.y)-.47,.014);
  float gate=stroke(fract((q.x+1.0)*3.0)-.08,.016);ink+=gate*stroke(abs(q.y)-.61,.13);
  ink+=stroke(q.y,.008)*step(.14,fract(q.x*9.0-vStyle.z));
 }else if(pat<3.5){
  vec2 p=q*5.0;float row=floor(p.x);float jog=fract(row*.618+vFx.w*.01)*.8-.4;
  ink=stroke(q.y-jog,.010)*step(.18,fract(p.x));
  ink+=stroke(fract(p.x)-.05,.018)*step(.22,abs(q.y-jog))*step(abs(q.y-jog),.58);
  ink+=stroke(length(vec2(fract(p.x)-.5,q.y-jog))-.05,.010);
 }else if(pat<4.5){
  ink=stroke(r-(.58+.15*cos(a*8.0)),.014)+stroke(r-.91,.009)+stroke(r-.86,.006);
  ink+=stroke(r-.31,.012)+stroke(sin(a*8.0),.024)*smoothstep(.58,.8,r)*(1.0-smoothstep(.9,1.0,r));
 }else{
  float axis=mod(a+.5235988,1.0471976)-.5235988;vec2 p=r*vec2(cos(axis),sin(axis));
  ink=stroke(p.y,.006)*smoothstep(.13,.22,p.x)*(1.0-smoothstep(.85,.9,p.x));
  ink+=stroke(abs(p.y)-(p.x-.39)*.75,.008)*step(.40,p.x)*step(p.x,.63);
  ink+=stroke(abs(p.y)-(p.x-.61)*.75,.008)*step(.62,p.x)*step(p.x,.82);
  ink+=stroke(r-.88,.009)*step(.25,fract(a*9.55));
  ink+=stroke(r-.38,.008)+stroke(r-.12,.014);
 }
 return clamp(ink,0.0,1.0);
}
void main(){
 vec2 q=vUv*2.0-1.0;float angle=atan(q.y,q.x),r=length(q);float polar=fract(angle/6.2831853+1.0);
 float position=vShape<.5?polar:vShape<1.5?vUv.x:clamp((angle+vStyle.x)/(vStyle.x*2.0),0.0,1.0);
 float filled=1.0-smoothstep(vFx.x-.01,vFx.x+.01,position);
 float head=(1.0-smoothstep(.005,.024,abs(position-vFx.x)))*step(.01,vFx.x)*step(vFx.x,.99);
 vec2 tex=vec2((clamp(vUv.x,.002,.998)+vShape)/3.0,clamp(vUv.y,.002,.998));
 float ink=texture2D(atlas,tex).a;
 if(vStyle.y>.5)ink=theme(q,angle,r);
 if(vShape>1.5){ink=theme(q,angle,r)*(vStyle.y>.5?1.0:0.0)+ink*(vStyle.y<.5?1.0:0.0);
   ink*=1.0-smoothstep(vStyle.x-.01,vStyle.x+.01,abs(angle));ink*=1.0-smoothstep(.97,1.0,r);
   ink+=((stroke(r-.97,.007)+stroke(abs(angle)-vStyle.x,.009))*step(r,.98)*step(abs(angle),vStyle.x));}
 if(vShape<.5)ink*=1.0-smoothstep(.97,1.0,r);
 float cut=erosion(vUv);
 float edge=(1.0-smoothstep(.025,.07,abs(noise(vUv*27.0+vFx.w*.01)-vFx.z)))*step(.03,vFx.z);
 float alpha=ink*(.18+.72*filled+.35*head)*vFx.y*cut;
 if(alpha<.002)discard;
 gl_FragColor=vec4(vColor*(.78+.22*filled)+vec3(.12)*head+vColor*.24*edge,alpha);
 #include <colorspace_fragment>
}`;
const meshShader = `
uniform float mode;varying vec2 vUv;varying vec4 vFx;varying vec4 vStyle;varying vec3 vColor;varying vec3 vNormal;
${noiseShader}
void main(){
 float soft=pow(max(0.0,sin(vUv.y*3.14159265)),.45);
 float core=0.0;
 if(mode<.5){soft*=smoothstep(0.0,.06,vUv.x)*(1.0-smoothstep(vFx.x-.13,vFx.x+.10,vUv.x));core=pow(max(0.0,sin(vUv.y*3.14159265)),9.0);}
 else if(mode<1.5){soft=max(.22,soft);core=pow(max(0.0,sin(vUv.x*25.132741)),10.0)*.25;}
 else if(mode<2.5){soft*=.2+.8*pow(max(0.0,sin(vUv.x*25.132741+vFx.w)),14.0);core=soft*.25;}
 else if(mode<3.5){soft*=.65*smoothstep(0.0,.06,vUv.x)*(1.0-smoothstep(.65,1.0,vUv.x));core=pow(max(0.0,sin(vUv.y*3.14159265)),12.0)*.16;}
 else if(mode<4.5){float edge=min(vUv.y,min(vUv.x-vUv.y*.5,1.0-vUv.x-vUv.y*.5));
   soft=.16+.45*abs(normalize(vNormal).z);core=(1.0-smoothstep(.012,.045,edge))*.44;}
 else if(mode<6.5){
   float gridX=1.0-smoothstep(.015,.065,abs(sin(vUv.x*37.6991))),gridY=1.0-smoothstep(.02,.065,abs(sin(vUv.y*31.4159)));
   float rim=pow(1.0-abs(normalize(vNormal).z),3.0);
   soft=(mode<5.5?.025:.012)+.3*rim+.30*max(gridX,gridY);
   if(vStyle.y>4.5)soft*=.45+.55*step(.33,fract(vUv.x*13.0+vUv.y*17.0));
   core=max(gridX,gridY)*.15;
 }else if(mode<7.5){soft=pow(max(0.0,sin(vUv.y*3.14159265)),.7);core=pow(max(0.0,sin(vUv.y*3.14159265)),10.0)*.5;}
 else if(mode<8.5){soft=pow(max(0.0,sin(vUv.y*3.14159265)),5.0)*sin(vUv.x*3.14159265);core=soft*.27;}
 else if(mode<9.5){soft*=.55*(1.0-smoothstep(.65,1.0,vUv.x));core=pow(max(0.0,sin(vUv.y*3.14159265)),18.0)*.27;}
 else{
   vec2 q=abs(vUv*2.0-1.0);float hex=max(q.y,max(q.x*.866025+q.y*.5,q.x*.866025));
   float edge=1.0-smoothstep(.016,.034,abs(hex-.91)),inner=1.0-smoothstep(.008,.019,abs(hex-.75));
   float grid=(1.0-smoothstep(.025,.06,abs(sin((vUv.x+vUv.y)*37.6991))))*(1.0-smoothstep(.62,.74,hex));
   soft=(.025+edge*.9+inner*.3+grid*.12)*(1.0-smoothstep(.96,1.0,hex));core=edge*.35;
 }
 float alpha=soft*vFx.y*erosion(vUv);
 if(alpha<.002)discard;
 float facet=.65+.35*abs(normalize(vNormal).z);
 gl_FragColor=vec4(vColor*facet+vec3(.25)*core,alpha);
 #include <colorspace_fragment>
}`;

function arcGeometry() {
  const p = [], uv = [], indices = [], n = 40;
  for (let j = 0; j <= n; j++) for (const side of [0, 1]) {
    const angle = -Math.PI / 2 + j / n * Math.PI, r = side ? 1 : .84;
    p.push(Math.cos(angle) * r, 0, Math.sin(angle) * r); uv.push(j / n, side);
  }
  for (let j = 0; j < n; j++) { const k = j * 2; indices.push(k, k + 1, k + 2, k + 1, k + 3, k + 2); }
  const g = new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(p,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));g.setIndex(indices);g.computeVertexNormals();return g;
}
function petalGeometry() {
  const p = [], uv = [], indices = [], n = 16;
  for (let j = 0; j <= n; j++) for (const side of [-1, 1]) {
    const t = j / n;p.push(t, Math.sin(Math.PI * t) * .25, Math.sin(Math.PI * t) * .23 * side);uv.push(t,(side+1)/2);
  }
  for (let j=0;j<n;j++){const k=j*2;indices.push(k,k+1,k+2,k+1,k+3,k+2);}
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(p,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));g.setIndex(indices);g.computeVertexNormals();return g;
}
function lanceGeometry() {
  // 枪尖朝向地面，根点就是下落的触地点，便于与落点贴花共用坐标。
  const shaft = new THREE.CylinderGeometry(.31,.53,.82,8,1,true).translate(0,.65,0);
  const tip = new THREE.ConeGeometry(1,.24,8).rotateZ(Math.PI).translate(0,.12,0);
  const g = mergeGeometries([shaft,tip]);shaft.dispose();tip.dispose();return g;
}
function boltGeometry() {
  // 两个互相垂直的细芯，加两条汇入同一终点的副叉。共享实例，不创建临时 Line 对象。
  const p=[],uv=[],indices=[],n=24;
  for(let strip=0;strip<4;strip++){
    const base=p.length/3,start=strip<2?0:strip===2?.35:.57;
    for(let j=0;j<=n;j++)for(const side of [-1,1]){
      const t=j/n,x=start+(1-start)*t,branch=strip<2?0:(strip===2?1:-1)*Math.sin(t*Math.PI)*2.3;
      p.push(x,strip===1?side*.5:0,strip===1?0:side*(strip<2?.5:.23)+branch);uv.push(x,(side+1)/2);
    }
    for(let j=0;j<n;j++){const k=base+j*2;indices.push(k,k+1,k+2,k+1,k+3,k+2);}
  }
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(p,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));g.setIndex(indices);g.computeVertexNormals();return g;
}
function ribbonGeometry(){const g=new THREE.PlaneGeometry(1,1,32,1).rotateX(-Math.PI/2).translate(.5,0,0);return g;}
function shardGeometry(){
  const p=[],uv=[],corners=[[1,.8,0],[0,.8,1],[-1,.8,0],[0,.8,-1]];
  for(let i=0;i<4;i++)for(const tip of [[0,2,0],[0,0,0]]){
    const tri=[corners[i],corners[(i+1)%4],tip];for(let j=0;j<3;j++){p.push(...tri[j]);uv.push(...[[0,0],[1,0],[.5,1]][j]);}
  }
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(p,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));g.computeVertexNormals();return g;
}
function batch(scene, kind, geometry, capacity, lowCapacity, atlas, mode) {
  const params = new THREE.InstancedBufferAttribute(new Float32Array(capacity*4),4).setUsage(THREE.DynamicDrawUsage);
  const color = new THREE.InstancedBufferAttribute(new Float32Array(capacity*3),3).setUsage(THREE.DynamicDrawUsage);
  const shape = new THREE.InstancedBufferAttribute(new Float32Array(capacity),1).setUsage(THREE.DynamicDrawUsage);
  const style = new THREE.InstancedBufferAttribute(new Float32Array(capacity*4),4).setUsage(THREE.DynamicDrawUsage);
  geometry.setAttribute('fxParams',params);geometry.setAttribute('fxColor',color);geometry.setAttribute('fxShape',shape);geometry.setAttribute('fxStyle',style);
  const material = new THREE.ShaderMaterial({uniforms:atlas?{atlas:{value:atlas},mode:{value:-1}}:{mode:{value:mode}},
    vertexShader,fragmentShader:atlas?decalShader:meshShader,transparent:true,depthWrite:false,side:THREE.DoubleSide,forceSinglePass:true,toneMapped:false,...ADDITIVE,
    // 实战是透明画布叠在独立场地下方之上：必须写入线条自己的 alpha，
    // 否则浏览器会丢弃 alpha=0 的 RGB，效果只会出现在已有模型 / 阴影像素内。
    blendSrcAlpha:THREE.OneFactor,blendDstAlpha:THREE.OneMinusSrcAlphaFactor});
  material.userData.glowSelf=true;
  const mesh = new THREE.InstancedMesh(geometry,material,capacity);mesh.name='Skill FX '+kind;mesh.count=0;mesh.visible=false;mesh.frustumCulled=false;mesh.renderOrder=kind==='decal'?1:3;
  mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);scene.add(mesh);
  let count=0,limit=capacity;
  return {mesh,begin(low){count=0;limit=low?lowCapacity:capacity;},
    write(matrix,c,sample,spec,tile=0){if(count>=limit)return false;mesh.setMatrixAt(count,matrix);
      params.setXYZW(count,sample.progress,sample.opacity,sample.dissolve,spec.seed);color.setXYZ(count,c.r,c.g,c.b);shape.setX(count,tile);
      style.setXYZW(count,spec.halfAngle,FX_PATTERNS.indexOf(spec.pattern),sample.phase,spec.kind==='bolt'?spec.spread/Math.max(.01,spec.width):0);count++;return true;},
    finish(){mesh.count=count;mesh.visible=count>0;for(const a of [mesh.instanceMatrix,params,color,shape,style]){a.clearUpdateRanges();if(count)a.addUpdateRange(0,count*a.itemSize);a.needsUpdate=count>0;}},
    get count(){return count;},capacity,lowCapacity,
    dispose(){mesh.removeFromParent();mesh.dispose();geometry.dispose();material.dispose();},
  };
}

// 单独的透明画布，只画短暂暗角。中心完全透明、HUD 在其上方，不移动画面或敌方预警。
function screenFeedback(root) {
  const canvas = root ? document.createElement('canvas') : null;
  if(canvas){canvas.id='visualSkillFeedback';canvas.setAttribute('aria-hidden','true');Object.assign(canvas.style,{position:'absolute',inset:'0',width:'100%',height:'100%',zIndex:'2',pointerEvents:'none',display:'none'});root.append(canvas);}
  let gain=0,draws=0;
  return {draw(amount,low){gain=amount;if(!canvas)return;
    if(amount<.001){canvas.style.display='none';return;}
    const scale=low?.5:1,w=Math.max(1,Math.round(root.clientWidth*scale)),h=Math.max(1,Math.round(root.clientHeight*scale));
    if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}
    const g=canvas.getContext('2d');g.clearRect(0,0,w,h);g.save();g.translate(w/2,h/2);g.scale(w,h);
    const gradient=g.createRadialGradient(0,0,.36,0,0,.72);gradient.addColorStop(0,'rgba(2,4,9,0)');gradient.addColorStop(.45,`rgba(2,4,9,${amount*.35})`);gradient.addColorStop(1,`rgba(2,4,9,${amount})`);
    g.fillStyle=gradient;g.fillRect(-.5,-.5,1,1);g.restore();canvas.style.display='block';draws++;},
    metrics:()=>({gain,draws,visible:canvas?.style.display==='block',resolution:canvas?[canvas.width,canvas.height]:null}),
    dispose(){canvas?.remove();},
  };
}

export function createSkillFX(scene, { feedbackRoot = null, feedbackEnabled = true, heroBindings = true, timelineCapacity = 256, lowBudgets = {} } = {}) {
  // 四人可在同一帧连续释放 E / R；预约池还要容纳未来动作 cue 与真实攻击脉冲。
  // 预约上限不增加 GPU 实例或绘制预算，避免引导开始时挤掉已发生的攻击。
  const atlas=sigilAtlas(),timeline=createEffectTimeline(timelineCapacity),presets=new Map(Object.entries(COMMON_SKILL_PRESETS)),bindings=new Map();
  for(const recipe of heroBindings?HERO_SKILLS:[])for(const kind of ['cast','channel']){
    const id=recipe.key+'.'+kind;presets.set(id,c=>heroRecipe(recipe.hero,kind,c));bindings.set(recipe.hero+':'+kind,id);
  }
  const batches={
    decal:batch(scene,'decal',new THREE.PlaneGeometry(2,2).rotateX(-Math.PI/2),48,20,atlas),
    arc:batch(scene,'arc',arcGeometry(),32,12,null,0),lance:batch(scene,'lance',lanceGeometry(),24,10,null,1),
    pillar:batch(scene,'pillar',new THREE.CylinderGeometry(1,1,1,16,1,true).translate(0,.5,0),16,6,null,2),
    petals:batch(scene,'petals',petalGeometry(),128,48,null,3),
    shield:batch(scene,'shield',new THREE.PlaneGeometry(2,2).rotateY(Math.PI/2),16,lowBudgets.shield??6,null,10),
    orb:batch(scene,'orb',new THREE.SphereGeometry(1,24,12),20,8,null,5),
    shard:batch(scene,'shard',shardGeometry(),128,lowBudgets.shard??48,null,4),
    dome:batch(scene,'dome',new THREE.SphereGeometry(1,24,12,0,Math.PI*2,0,Math.PI/2),24,10,null,6),
    bolt:batch(scene,'bolt',boltGeometry(),80,32,null,7),
    ribbon:batch(scene,'ribbon',ribbonGeometry(),80,32,null,8),
    wing:batch(scene,'wing',petalGeometry(),96,lowBudgets.wing??36,null,9),
  };
  const feedback=screenFeedback(feedbackRoot),media=typeof matchMedia==='function'?matchMedia('(prefers-reduced-motion: reduce)'):null;
  const actorMap=new Map(),colors=new Map(),object=new THREE.Object3D(),tilt=new THREE.Quaternion(),yaw=new THREE.Quaternion();
  const up=new THREE.Vector3(0,1,0),right=new THREE.Vector3(1,0,0),forwardAxis=new THREE.Vector3(1,0,0),direction=new THREE.Vector3();
  let run=null,cursor=0,time=0,disposed=false,stats;
  const colorOf=hex=>{if(!colors.has(hex))colors.set(hex,new THREE.Color(hex));return colors.get(hex);};
  function reset(nextRun=null,nextCursor=0){if(disposed)return;run=nextRun;cursor=nextCursor;time=nextRun?.time||0;timeline.clear();
    for(const b of Object.values(batches)){b.begin(false);b.finish();}feedback.draw(0,false);
    stats={events:0,clipped:0,active:[],reducedMotion:!!media?.matches};}
  reset();
  const enqueue=(cues,at)=>timeline.add(cues.filter(c=>at+c.at+c.spec.life>time),at);
  function sequence(definition,context={},at=time){if(disposed)return false;
    let cues=compilePreset(definition,context);
    if(context.owner!==null&&context.owner!==undefined&&context.owner!==0)cues=cues.filter(c=>c.spec.kind!=='feedback');
    return enqueue(cues,at);}
  function play(id,context={},at=time){if(disposed)return false;const preset=presets.get(id);if(!preset)throw new TypeError('未知技能配方 '+id);
    return sequence(typeof preset==='function'?preset(context):preset,context,at);}
  function emit(effect,at=time){if(disposed)return false;return enqueue([{at:0,spec:normalizeEffect(effect)}],at);}
  function update(frame,native,S=.028){
    if(disposed)return;
    if(frame.run!==run){if(run)reset(frame.run);else run=frame.run;}time=frame.run?.time??0;
    const low=frame.options?.quality==='low',reduced=frame.options?.reducedMotion===true||!!media?.matches;
    actorMap.clear();for(const a of [frame.P,...(frame.agents||[])])if(a)actorMap.set(a.uid,a);
    const cancel=(spec,start,origin)=>{
      const a=actorMap.get(spec.owner),E=frame.E;
      return spec.cancelOnOwnerLoss&&(!a||a.downed)||(spec.channel&&a&&a.ultTime<=0&&time<origin+spec.channelDuration-.001)
        ||(spec.requireFreeze||spec.requireStun)&&(!E?.a[spec.target]||E.gen[spec.target]!==spec.generation||E.freeze[spec.target]<=0);
    };
    // 补帧先回收已结束的效果，再预约新事件，不让过期 cue 占用下一次技能的预算。
    timeline.visit(time,()=>{},cancel);
    for(const event of frame.skillEvents||[]){if(event.id<=cursor)continue;cursor=event.id;
      if(!Number.isFinite(event.time)||!FX_COLORS[event.hero])continue;
      const context=skillContext(event,S);
      if(['cast','channel'].includes(event.kind))play(bindings.get(event.hero+':'+event.kind)||event.kind,context,event.time);
      else if(['pulse','bomb','heal','freeze','stun'].includes(event.kind)){
        if(event.kind==='freeze'||event.kind==='stun')timeline.removeWhere(spec=>(event.kind==='freeze'?spec.requireFreeze:spec.requireStun)&&context.points.some(p=>p.target===spec.target&&p.generation===spec.generation));
        enqueue(compilePreset(heroRecipe(event.hero,event.kind,context),context),event.time);
      }
      else continue;
      stats.events++;}
    for(const b of Object.values(batches))b.begin(low);
    stats.active=[];stats.clipped=0;stats.reducedMotion=reduced;
    let feedbackGain=0;
    const halfW=(native.viewWidth??1280)/2+120,halfH=(native.viewHeight??720)/(2*(native.sinElev??.8))+120;
    timeline.visit(time,(spec,sample)=>{
      if(spec.decoration&&(low||reduced))return;
      if(spec.kind==='feedback'){if(feedbackEnabled&&!reduced&&frame.options?.shake!==false)feedbackGain=Math.max(feedbackGain,sample.opacity);return;}
      const actor=actorMap.get(spec.owner),baseAngle=spec.attach&&actor?((actor.ultTime>0?actor.ultAim??actor.aim:actor.aim)??spec.angle)+spec.aimOffset:spec.angle;
      const angle=baseAngle+(reduced?0:spec.spin*sample.age);
      const co=Math.cos(angle),si=Math.sin(angle),[forward,height,side]=spec.offset;
      const anchorX=(spec.requireFreeze||spec.requireStun)?frame.E.x[spec.target]*S:spec.attach&&actor?actor.x*S:spec.x;
      const anchorZ=(spec.requireFreeze||spec.requireStun)?frame.E.y[spec.target]*S:spec.attach&&actor?actor.y*S:spec.z;
      const x=anchorX+co*forward-si*side,z=anchorZ+si*forward+co*side;
      // 长轨道和高光柱的根部在屏外时，伸入画面的部分仍要保留。
      const extent=Math.max(spec.radius,spec.length,spec.width,spec.height)/S;
      if(frame.camera&&(Math.abs(x/S-frame.camera.x)>halfW+extent||Math.abs(z/S-frame.camera.y)>halfH+extent))return;
      const y=spec.y+height,progress=sample.progress;
      if(stats.active.length<64)stats.active.push({kind:spec.kind,label:spec.label,hero:spec.hero,boss:spec.boss,owner:spec.owner,target:spec.target,age:sample.age,progress,opacity:sample.opacity,dissolve:sample.dissolve,position:[x,y,z],end:spec.end});
      object.position.set(x,y,z);object.quaternion.copy(yaw.setFromAxisAngle(up,-angle)).multiply(tilt.setFromAxisAngle(right,spec.tilt));
      const color=colorOf(spec.color),b=batches[spec.kind];
      const write=(tile=0)=>{object.updateMatrix();if(!b.write(object.matrix,color,sample,spec,tile))stats.clipped++;};
      const growth=spec.motion==='expand'?.18+.82*progress:spec.motion==='collapse'?1-.85*progress:1;
      if(spec.kind==='decal'){if(spec.shape==='lane')object.position.set(x+co*spec.length/2,y,z+si*spec.length/2);
        object.scale.set(spec.shape==='lane'?spec.length/2:spec.radius,1,spec.shape==='lane'?spec.width/2:spec.radius);write(['seal','lane','sector'].indexOf(spec.shape));}
      if(spec.kind==='arc'){if(spec.motion==='sweep')object.position.set(x+co*spec.length*progress,y,z+si*spec.length*progress);
        if(spec.motion==='rise')object.position.y+=progress*.8;
        object.scale.setScalar(spec.radius*growth);write(Math.min(.8,spec.width/(spec.radius*growth)));}
      if(spec.kind==='lance'){object.position.y+=spec.height*(1-sample.phase);object.scale.set(spec.width,spec.length,spec.width);write();}
      if(spec.kind==='pillar'){object.scale.set(spec.radius,spec.height*(.4+.6*Math.sin(Math.PI*sample.phase)),spec.radius);write();}
      if(spec.kind==='petals')for(let i=0;i<spec.petals;i++){
        const a=angle+i/spec.petals*Math.PI*2+(reduced?0:sample.phase*.25),r=spec.radius*(.22+.55*progress);
        object.position.set(x+Math.cos(a)*r,y,z+Math.sin(a)*r);object.quaternion.setFromAxisAngle(up,-a);
        // 瓣的厚度独立于长度；窄层能成为金色叶脉，而非重复覆盖整片花瓣。
        object.scale.set(spec.length,spec.height*4,spec.length*Math.min(1,spec.width/.14));write();}
      if(spec.kind==='shield'){object.position.y+=spec.motion==='rise'?(progress-1)*.65:0;object.scale.set(1,spec.height/2,spec.radius);write();}
      if(spec.kind==='orb'){if(spec.motion==='rise')object.position.y-=(1-progress)*.8;object.scale.setScalar(spec.radius*growth);write();}
      if(spec.kind==='dome'){object.scale.set(spec.radius*growth,spec.height*growth,spec.radius*growth);write();}
      if(spec.kind==='shard')for(let i=0;i<(low?Math.min(spec.count,5):spec.count);i++){
        const t=(i+.37)*2.399963+spec.seed*.71,a=t+(reduced?0:spec.spin*sample.age),r=spec.spread*Math.sqrt((i+.5)/spec.count);
        const outward=spec.motion==='expand'?progress:spec.motion==='collapse'?1-progress:1;
        object.position.set(x+Math.cos(a)*r*outward,spec.motion==='fall'?y*(1-progress)+.08*progress:y+(spec.motion==='rise'?progress*Math.max(.6,spec.height)*1.25:0),z+Math.sin(a)*r*outward);
        object.quaternion.copy(yaw.setFromAxisAngle(up,-a)).multiply(tilt.setFromAxisAngle(right,spec.tilt+(spec.count>1?.25*Math.sin(t):0)));
        object.scale.set(spec.width/2,spec.height/2,spec.width*.4);write();}
      if(spec.kind==='bolt'){
        const end=spec.end??[x+co*spec.length,y,z+si*spec.length];direction.set(end[0]-x,end[1]-y,end[2]-z);
        const length=direction.length();if(length>.001){object.quaternion.setFromUnitVectors(forwardAxis,direction.normalize());object.scale.set(length,spec.width,spec.width);write();}}
      if(spec.kind==='ribbon')for(let i=0;i<(low?Math.min(spec.count,8):spec.count);i++){
        const t=spec.count===1?0:i/(spec.count-1)*2-1,a=angle+t*spec.halfAngle,coA=Math.cos(a),siA=Math.sin(a);
        const move=spec.motion==='sweep'?sample.phase*spec.length*.55:0;
        object.position.set(x-si*t*spec.spread+coA*move,y,z+co*t*spec.spread+siA*move);object.quaternion.setFromAxisAngle(up,-a);
        object.scale.set(spec.length*(spec.motion==='expand'?growth:1),1,spec.width);write();}
      if(spec.kind==='wing')for(const side of [-1,1])for(let i=0;i<(low?Math.min(spec.petals,4):spec.petals);i++){
        const t=i/Math.max(1,spec.petals-1),a=angle+side*(.58+t*.92),r=spec.radius*(.28+.58*t)*growth;
        object.position.set(x+Math.cos(a)*r,y+spec.height*(1-t)*growth,z+Math.sin(a)*r);
        object.quaternion.setFromAxisAngle(up,-a);object.scale.set(spec.length*(.65+.35*t),spec.height*2,spec.length*.5);write();}
    },cancel);
    for(const b of Object.values(batches))b.finish();feedback.draw(Math.min(low?.07:.12,feedbackGain),low);
  }
  return {play,sequence,emit,update,reset,
    register(id,definition){if(disposed)return false;compilePreset(definition,{owner:0});presets.set(id,structuredClone(definition));return true;},
    bind(hero,kind,id){if(disposed)return false;if(!Number.isInteger(hero)||hero<0||hero>5||!['cast','channel'].includes(kind)||!presets.has(id))throw new TypeError('无效英雄技能绑定');bindings.set(hero+':'+kind,id);return true;},
    metrics:()=>({...stats,...timeline.metrics(),counts:Object.fromEntries(Object.entries(batches).map(([k,b])=>[k,b.count])),
      capacities:Object.fromEntries(Object.entries(batches).map(([k,b])=>[k,[b.capacity,b.lowCapacity]])),feedback:feedback.metrics(),disposed}),
    dispose(){if(disposed)return;reset();for(const b of Object.values(batches))b.dispose();atlas.dispose();feedback.dispose();disposed=true;},
  };
}
