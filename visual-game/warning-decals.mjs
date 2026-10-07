// 危险贴花只读真实 warnings；全部预警共用一批次，边界不会随画质或进度缩小。
import * as THREE from 'three';

// 纯接口由游戏 HTML 内嵌，在高清模块加载前就绪；部署不额外依赖 src 目录。
const { WARNING_CAPACITY, snapshotWarnings } = globalThis.NRWarningData;

function warningTexture() {
  const canvas = document.createElement('canvas'); canvas.width = canvas.height = 256;
  const g = canvas.getContext('2d');
  // 可平铺的机械危险纹理：斜切条带、细刻线与断口。没有滚动、随机闪烁或白色大面。
  g.strokeStyle = '#fff'; g.lineWidth = 28;
  for (let x = -256; x <= 512; x += 128) {
    g.beginPath(); g.moveTo(x, 0); g.lineTo(x + 256, 256); g.stroke();
  }
  g.strokeStyle = 'rgba(255,255,255,.35)'; g.lineWidth = 2;
  for (let x = -256; x <= 512; x += 128) {
    g.beginPath(); g.moveTo(x + 27, 0); g.lineTo(x + 283, 256); g.stroke();
  }
  g.globalCompositeOperation = 'destination-out';
  for (let x = 32; x < 256; x += 64) for (let y = 32; y < 256; y += 64) g.clearRect(x - 3, y - 3, 6, 6);
  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
  texture.generateMipmaps = true; texture.minFilter = THREE.LinearMipmapLinearFilter;
  return texture;
}

const vertexShader = `
attribute vec4 warningParams;
varying vec2 vUv; varying vec4 vWarning;
void main(){vUv=uv;vWarning=warningParams;
 gl_Position=projectionMatrix*modelViewMatrix*instanceMatrix*vec4(position,1.0);}`;

const fragmentShader = `
uniform sampler2D hatch; uniform vec3 red; uniform float lowDetail;
varying vec2 vUv; varying vec4 vWarning;
float ink(float d,float width){float aa=max(fwidth(d),.001);return 1.0-smoothstep(width,width+aa,abs(d));}
void main(){
 vec2 q=vUv*2.0-1.0;float p=vWarning.y;
 float mask=1.0,border=0.0,shadow=0.0,filled=0.0,front=0.0,ticks=0.0,clock=0.0;
 if(vWarning.x<.5){
  float r=length(q),aa=max(fwidth(r),.001);
  mask=1.0-smoothstep(1.0-aa,1.0,r);
  border=ink(r-.983,max(.006,aa*.75));shadow=ink(r-.956,max(.017,aa*1.1));
  filled=(1.0-smoothstep(p-aa,p+aa,r))*step(.001,p);
  front=ink(r-p,max(.005,aa))*(1.0-smoothstep(.955,.98,r))*step(.02,p);
  float a=atan(q.y,q.x),phase=fract(.25-a/6.2831853+1.0);
  clock=ink(r-.91,.012)*(1.0-smoothstep(p-.003,p+.003,phase))*step(.001,p);
  float ray=sin((a-1.5707963)*12.0);
  float tick=1.0-smoothstep(.035,.035+max(fwidth(ray),.04),abs(ray));
  ticks=tick*smoothstep(.827,.84,r)*(1.0-smoothstep(.887,.897,r));
 }else{
  vec2 size=vWarning.zw,edge=min(vUv,1.0-vUv)*size;
  float d=min(edge.x,edge.y),aa=max(fwidth(d),.002);
  mask=smoothstep(0.0,aa,d);border=ink(d-.017,max(.010,aa*.65));shadow=ink(d-.054,max(.022,aa));
  float pa=max(fwidth(vUv.x),.001);
  filled=(1.0-smoothstep(p-pa,p+pa,vUv.x))*step(.001,p);
  front=ink((vUv.x-p)*size.x,max(.025,aa))*step(.02,p)*step(p,.995);
  float mark=ink(fract(vUv.x*size.x/.70)-.5,.025);
  ticks=mark*step(edge.y,.16)*step(.08,edge.x);
  clock=ink(edge.y-.10,.015)*filled;
 }
 float hatchInk=texture2D(hatch,vUv*vWarning.zw/1.65).a;
 hatchInk=mix(hatchInk,smoothstep(.45,.70,hatchInk),lowDetail);
 float urgent=smoothstep(.72,1.0,p);
 float base=.022+.025*urgent;
 float fill=(.060+.040*urgent)*filled + hatchInk*(.23+.10*urgent)*filled;
 float opacity=max(base+fill,max(border*.90,max(shadow*.68,max(clock*.77,max(front*.64,ticks*(.28+.30*filled))))));
 float bright=max(border,max(clock,max(front,ticks*.55)));
 vec3 color=mix(red*.22,red,clamp(bright+hatchInk*filled*.82+filled*.32,0.0,1.0));
 // 低画质仅去掉次级刻线，真实边界、填充前沿和全部 80 个预警始终保留。
 opacity*=mask; if(opacity<.004)discard;
 gl_FragColor=vec4(color,opacity);
 #include <colorspace_fragment>
}`;

export function createWarningDecals(scene) {
  const geometry = new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2);
  const params = new THREE.InstancedBufferAttribute(new Float32Array(WARNING_CAPACITY * 4), 4);
  params.setUsage(THREE.DynamicDrawUsage); geometry.setAttribute('warningParams', params);
  const texture = warningTexture();
  const material = new THREE.ShaderMaterial({
    uniforms: { hatch: { value: texture }, red: { value: new THREE.Color('#ff5268') }, lowDetail: { value: 0 } },
    vertexShader, fragmentShader, transparent: true, depthWrite: false, depthTest: true,
    side: THREE.DoubleSide, forceSinglePass: true, toneMapped: false,
  });
  const mesh = new THREE.InstancedMesh(geometry, material, WARNING_CAPACITY);
  mesh.name = 'Enemy warning progress decals'; mesh.frustumCulled = false; mesh.renderOrder = 5;
  mesh.userData.noGlow = true; mesh.count = 0; mesh.visible = false;
  mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage); scene.add(mesh);
  const object = new THREE.Object3D();
  let active = [], disposed = false, quality = 'high', reducedMotion = false;
  function reset() { active = []; mesh.count = 0; mesh.visible = false; }
  function update(frame, scale = .028) {
    if (disposed) return;
    active = snapshotWarnings(frame.warnings || [], scale);
    quality = frame.options?.quality || 'high'; reducedMotion = !!frame.options?.reducedMotion;
    material.uniforms.lowDetail.value = quality === 'low' ? 1 : 0;
    for (let i = 0; i < active.length; i++) {
      const w = active[i];
      object.position.set(w.x, .16, w.z); object.rotation.set(0, -w.angle, 0);
      object.scale.set(w.sizeX, 1, w.sizeZ); object.updateMatrix(); mesh.setMatrixAt(i, object.matrix);
      params.setXYZW(i, w.type === 'circle' ? 0 : 1, w.progress, w.sizeX, w.sizeZ);
    }
    mesh.count = active.length; mesh.visible = !!mesh.count;
    params.needsUpdate = true; mesh.instanceMatrix.needsUpdate = true;
  }
  return { update, reset,
    metrics: () => ({ count: active.length, capacity: WARNING_CAPACITY, quality, reducedMotion,
      circles: active.filter(w => w.type === 'circle').length, lanes: active.filter(w => w.type === 'lane').length,
      color: '#ff5268', glow: false, active: active.map(w => ({ ...w })), disposed }),
    dispose() { if (disposed) return; reset(); scene.remove(mesh); geometry.dispose(); material.dispose(); texture.dispose(); disposed = true; },
  };
}
