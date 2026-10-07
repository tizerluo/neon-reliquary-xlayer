import * as THREE from 'three';
import { ADDITIVE } from './glow.js';
import { BOSS_EFFECTS } from './boss-effects/index.mjs';

const CAPACITY=950,HISTORY=4;
const SHAPES=['flame','ice','shell','wisp','lumen','void','venom','feather'];
const vertexShader=`
attribute vec4 bossParams;
attribute vec3 bossColor;
attribute vec3 bossCore;
varying vec2 vUv;
varying vec4 vParams;
varying vec3 vColor;
varying vec3 vCore;
void main(){vUv=uv;vParams=bossParams;vColor=bossColor;vCore=bossCore;
gl_Position=projectionMatrix*modelViewMatrix*instanceMatrix*vec4(position,1.0);}`;
const headShader=`
varying vec2 vUv; varying vec4 vParams; varying vec3 vColor; varying vec3 vCore;
float band(float d,float w){return 1.0-smoothstep(w,w+.035,abs(d));}
void main(){
  vec2 p=(vUv-.5)*2.0; float s=vParams.x,t=vParams.y,mask=0.0,line=0.0,core=0.0;
  float x=p.x,y=p.y;
  if(s<.5){
    float bend=vParams.w>.5?0.0:sin(x*9.0-t*16.0)*.06;
    float taper=(.36+.19*(1.0-x))*(1.0-smoothstep(.45,1.0,x));
    mask=(1.0-smoothstep(taper,taper+.08,abs(y+bend)))*(1.0-smoothstep(.65,1.0,abs(x)));
    line=band(abs(y+bend)-taper*.6,.045)+band(y+bend,.027)*.55;
    core=exp(-x*x*18.0-y*y*42.0)*.9;
  }else if(s<1.5){
    float d=abs(x)+abs(y)*1.26;
    mask=1.0-smoothstep(.82,.91,d);line=band(d-.75,.028)+band(y-x*.48,.021)*.45+band(y+x*.48,.017)*.35;
    core=exp(-dot(p,p)*27.0);
  }else if(s<2.5){
    float cap=1.0-smoothstep(.4,.92,x),w=.5*min(1.0,cap+.25);
    mask=(1.0-smoothstep(w,w+.045,abs(y)))*(1.0-smoothstep(.78,.88,abs(x)));
    line=band(abs(y)-w*.82,.023)+band(x+.50,.021)*.8+band(x-.04,.018)*.6;
    core=exp(-x*x*32.0-y*y*22.0)*.82;
  }else if(s<3.5){
    float bend=vParams.w>.5?0.0:sin(x*7.0-t*8.0)*.065;
    float d=length(vec2(x,y+bend)*vec2(.98,1.55));
    mask=1.0-smoothstep(.73,.95,d);line=band(d-.57,.045)+band(y+bend,.018)*.6;
    core=exp(-x*x*24.0-y*y*38.0)*.7;
  }else if(s<4.5){
    float d=abs(x)+abs(y)*1.25;
    mask=band(d-.65,.07)+exp(-dot(p,p)*20.0)*.45;
    line=band(y,.025)*(1.0-smoothstep(.62,.83,abs(x)))+band(x,.018)*(1.0-smoothstep(.50,.70,abs(y)));
    core=exp(-dot(p,p)*35.0)*.9;
  }else if(s<5.5){
    float d=length(p*vec2(1.1,1.45));
    mask=band(d-.68,.085)+band(d-.39,.029)*.35;
    line=band(d-.68,.025)*( .65+.35*cos(atan(y,x)*6.0+t*2.0));
    core=exp(-dot(p,p)*60.0)*.7;
  }else if(s<6.5){
    float d=length(vec2(x*.95,y*(1.45+.4*max(x,0.0))));
    mask=1.0-smoothstep(.62,.83,d);line=band(d-.58,.025)+band(y-sin(x*8.0)*.045,.02)*.25;
    core=exp(-dot(p,p)*26.0)*.82;
    line+=band(length(p-vec2(-.42,.16))-.095,.018)*.6;
  }else{
    float w=.57*pow(max(0.0,1.0-x*x),.7);
    mask=(1.0-smoothstep(w,w+.055,abs(y)))*(1.0-smoothstep(.84,.94,abs(x)));
    float veins=band(fract((x+abs(y)*.82)*5.5)-.5,.045);
    line=band(y,.022)+veins*.42+band(abs(y)-w*.87,.02)*.35;
    core=exp(-x*x*30.0-y*y*55.0)*.78;
  }
  float alpha=clamp(mask*(.3+line*.48)+core*.65,0.0,1.0)*vParams.z;
  if(alpha<.008)discard;
  vec3 rgb=vColor*(.38+line*.28)+vCore*core*.8;
  gl_FragColor=vec4(rgb,alpha);
}`;
const tailShader=`
varying vec2 vUv; varying vec4 vParams; varying vec3 vColor; varying vec3 vCore;
void main(){
  float y=(vUv.y-.5)*2.0,u=vUv.x;
  float taper=.28+.65*u;
  float line=exp(-y*y*36.0/(taper*taper));
  float shell=(1.0-smoothstep(.55*taper,taper,abs(y)))*.16;
  float gaps=vParams.x>6.5?.66+.34*sin(u*38.0):1.0;
  float alpha=(line*.58+shell)*(.22+.78*u)*vParams.z*gaps;
  if(alpha<.005)discard;
  gl_FragColor=vec4(mix(vColor,vCore,line*.25),alpha);
}`;
function batch(scene,name,capacity,fragmentShader){
  const geometry=new THREE.PlaneGeometry(1,1).rotateX(-Math.PI/2);
  const params=new THREE.InstancedBufferAttribute(new Float32Array(capacity*4),4).setUsage(THREE.DynamicDrawUsage);
  const color=new THREE.InstancedBufferAttribute(new Float32Array(capacity*3),3).setUsage(THREE.DynamicDrawUsage);
  const core=new THREE.InstancedBufferAttribute(new Float32Array(capacity*3),3).setUsage(THREE.DynamicDrawUsage);
  geometry.setAttribute('bossParams',params);geometry.setAttribute('bossColor',color);geometry.setAttribute('bossCore',core);
  const material=new THREE.ShaderMaterial({vertexShader,fragmentShader,transparent:true,depthWrite:false,
    side:THREE.DoubleSide,forceSinglePass:true,toneMapped:false,...ADDITIVE,
    blendSrcAlpha:THREE.OneFactor,blendDstAlpha:THREE.OneMinusSrcAlphaFactor});
  material.userData.glowSelf=true;
  const mesh=new THREE.InstancedMesh(geometry,material,capacity);
  mesh.name=name;mesh.frustumCulled=false;mesh.renderOrder=4;mesh.count=0;mesh.visible=false;
  mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);scene.add(mesh);
  let count=0;
  return {begin(){count=0;},write(matrix,c,k,shape,phase,gain,reduced){
    if(count>=capacity)return false;
    mesh.setMatrixAt(count,matrix);params.setXYZW(count,shape,phase,gain,reduced?1:0);
    color.setXYZ(count,c.r,c.g,c.b);core.setXYZ(count,k.r,k.g,k.b);count++;return true;
  },finish(){mesh.count=count;mesh.visible=count>0;
    for(const a of [mesh.instanceMatrix,params,color,core]){a.clearUpdateRanges();if(count)a.addUpdateRange(0,count*a.itemSize);a.needsUpdate=count>0;}
  },get count(){return count;},capacity,
  dispose(){mesh.removeFromParent();mesh.dispose();geometry.dispose();material.dispose();}};
}
export function createBossProjectiles(scene){
  // 危险头部预算等于完整 HB 池；低画质只缩短尾迹，不会漏掉实弹。
  const heads=batch(scene,'Boss real projectile heads',CAPACITY,headShader);
  const tails=batch(scene,'Boss real projectile history',CAPACITY*3,tailShader);
  const styles=BOSS_EFFECTS.map(r=>({...r.projectile,shapeId:SHAPES.indexOf(r.projectile.shape),
    c:new THREE.Color(r.projectile.color),k:new THREE.Color(r.projectile.core),t:new THREE.Color(r.projectile.tail)}));
  const generations=new Int32Array(CAPACITY),x=new Float32Array(CAPACITY*HISTORY),z=new Float32Array(CAPACITY*HISTORY),samples=new Uint8Array(CAPACITY);
  const object=new THREE.Object3D(),up=new THREE.Vector3(0,1,0);
  let run=null,lastTime=-1,lastSample=-1,disposed=false,stats={};
  function reset(nextRun=null){if(disposed)return;run=nextRun;lastTime=lastSample=-1;generations.fill(-1);samples.fill(0);
    heads.begin();tails.begin();heads.finish();tails.finish();stats={heads:0,tails:0,perBoss:Array(8).fill(0),active:[],clipped:0};}
  reset();
  function matrix(ax,az,angle,length,width){object.position.set(ax,.48,az);object.quaternion.setFromAxisAngle(up,-angle);object.scale.set(length,1,width);object.updateMatrix();return object.matrix;}
  function update(frame,native,S=.028){if(disposed)return;if(run!==frame.run)reset(frame.run);
    const now=frame.run?.time??0,HB=frame.HB,low=frame.options?.quality==='low',reduced=frame.options?.reducedMotion===true||!!globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    const moved=now>lastTime,stepSample=moved&&(now-lastSample>=.028||lastSample<0),jump=lastTime>=0&&now-lastTime>.15;
    heads.begin();tails.begin();stats={heads:0,tails:0,perBoss:Array(8).fill(0),active:[],clipped:0};
    const halfW=(native.viewWidth??1280)/2+150,halfH=(native.viewHeight??720)/(2*(native.sinElev??.8))+150;
    for(let i=0;i<HB.max;i++){
      if(!HB.a[i]||!HB.boss[i]){samples[i]=0;continue;}
      const style=styles[HB.boss[i]-1];if(!style)continue;
      const base=i*HISTORY,ax=HB.x[i]*S,az=HB.y[i]*S,newSlot=generations[i]!==HB.gen[i]||samples[i]===0;
      if(newSlot||jump){generations[i]=HB.gen[i];samples[i]=1;x[base]=ax;z[base]=az;
        // 仅可使用模拟刚保存的上一坐标，禁止从速度反推不存在的轨迹。
        if(Math.hypot(HB.x[i]-HB.px[i],HB.y[i]-HB.py[i])>0){x[base+1]=HB.px[i]*S;z[base+1]=HB.py[i]*S;samples[i]=2;}
      }else if(stepSample){for(let k=Math.min(3,samples[i]);k>0;k--){x[base+k]=x[base+k-1];z[base+k]=z[base+k-1];}x[base]=ax;z[base]=az;samples[i]=Math.min(HISTORY,samples[i]+1);}
      if(frame.camera&&(Math.abs(HB.x[i]-frame.camera.x)>halfW||Math.abs(HB.y[i]-frame.camera.y)>halfH))continue;
      const angle=Math.atan2(HB.vy[i],HB.vx[i]);
      heads.write(matrix(ax,az,angle,style.length,style.size*2),style.c,style.k,style.shapeId,HB.age[i],style.gain,reduced);
      stats.perBoss[HB.boss[i]-1]++;
      if(stats.active.length<64)stats.active.push({index:i,generation:HB.gen[i],boss:HB.boss[i]-1,source:HB.source[i],sourceGen:HB.sourceGen[i],sequence:HB.attackSeq[i],age:HB.age[i],position:[ax,.48,az],angle});
      if(reduced)continue;
      // 当前头部 → 保存的真实路径；暂停不写历史，复用槽位不串尾。
      let bx=ax,bz=az,written=0;
      for(let k=0;k<samples[i]&&written<(low?1:3);k++){
        const cx=x[base+k],cz=z[base+k],length=Math.hypot(bx-cx,bz-cz);
        if(length>.002&&length<2.5){const gain=style.gain*(low?.24:.38)*(1-k*.23);
          if(!tails.write(matrix((bx+cx)/2,(bz+cz)/2,Math.atan2(bz-cz,bx-cx),length,style.size*.55),style.t,style.c,style.shapeId,HB.age[i],gain,false))stats.clipped++;written++;}
        bx=cx;bz=cz;
      }
    }
    heads.finish();tails.finish();stats.heads=heads.count;stats.tails=tails.count;
    if(stepSample)lastSample=now;lastTime=now;
  }
  return {update,reset,metrics:()=>({...stats,perBoss:[...stats.perBoss],headCapacity:heads.capacity,tailCapacity:tails.capacity,historySamples:HISTORY,disposed}),
    dispose(){if(disposed)return;reset();heads.dispose();tails.dispose();disposed=true;}};
}
