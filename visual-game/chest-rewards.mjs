// 圣物匣的真实奖励：金剑 / 紫晶 / 银盾各有独立色相，先读剪影，再用亮芯与扫光点出“宝物”。
// 全部曲线读取游戏绝对时间，目标是真正受益者；没有新增战斗或随机采样。
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

export const CHEST_REWARD_LIFE = 1.32;
const CAPACITY = 12, LOW_CAPACITY = 8;
const KINDS = ['overclock', 'energy', 'shield'];
const smooth = v => { v = Math.max(0, Math.min(1, v)); return v * v * (3 - 2 * v); };

function shape(points) {
  const s = new THREE.Shape(); s.moveTo(...points[0]);
  for (const p of points.slice(1)) s.lineTo(...p);
  s.closePath(); return s;
}
// 大倒角、单段：截面成菱形，刃口和盾缘能接住反射高光，不再是一张硬纸片。
function solid(outline, depth, bevel, thickness = bevel, segments = 1, curves = 1) {
  return new THREE.ExtrudeGeometry(outline.curves ? outline : shape(outline), { depth, steps: 1, bevelEnabled: true,
    bevelSize: bevel, bevelThickness: thickness, bevelSegments: segments, curveSegments: curves }).translate(0, 0, -depth / 2);
}
// 顶点色决定每件奖励自己的金属 / 晶体颜色；两份共享材质不变，批次仍是六个。
function paint(geo, color) {
  const g = geo.index ? geo.toNonIndexed() : geo; if (g !== geo) geo.dispose();
  const pos = g.getAttribute('position'), out = new Float32Array(pos.count * 3), c = new THREE.Color();
  for (let i = 0; i < pos.count; i++) {
    if (typeof color === 'function') color(c, pos.getX(i), pos.getY(i), pos.getZ(i)); else c.set(color);
    out.set([c.r, c.g, c.b], i * 3);
  }
  g.setAttribute('color', new THREE.BufferAttribute(out, 3));
  for (const key of Object.keys(g.attributes)) if (!['position', 'normal', 'color'].includes(key)) g.deleteAttribute(key);
  return g;
}
function merge(parts) {
  const joined = mergeGeometries(parts, false);
  for (const g of parts) g.dispose();
  joined.computeVertexNormals(); joined.computeBoundingSphere(); return joined;
}
const both = (geo, z) => [geo.clone().translate(0, 0, z), geo.translate(0, 0, -z)];
function geometries(kind) {
  if (kind === 'overclock') {
    // 超频：修长亮金剑，菱形截面刃、下弯护手、皮革握柄；剑脊与宝石是炽金亮芯。
    const blade = paint(solid([[0,.98],[-.085,.80],[-.075,-.12],[.075,-.12],[.085,.80]], .015, .05, .055), '#f6e2ae');
    const guard = paint(solid([[-.46,-.08],[-.40,-.17],[-.14,-.21],[0,-.29],[.14,-.21],[.40,-.17],[.46,-.08],[.34,-.12],[.12,-.13],[0,-.11],[-.12,-.13],[-.34,-.12]], .06, .025, .025, 2), '#d49a32');
    const grip = paint(new THREE.CylinderGeometry(.048, .056, .34, 8).translate(0, -.47, 0), '#4a2c1c');
    const wraps = [-.38, -.47, -.56].map(y => paint(new THREE.TorusGeometry(.058, .014, 4, 8).rotateX(Math.PI / 2).translate(0, y, 0), '#c48a2c'));
    const pommel = paint(new THREE.IcosahedronGeometry(.085, 0).scale(1, 1.15, .8).translate(0, -.69, 0), '#d49a32');
    const fuller = both(paint(new THREE.BoxGeometry(.026, .78, .01).translate(0, .32, 0), '#ffc45a'), .062);
    const gem = both(paint(new THREE.OctahedronGeometry(.062).scale(1, 1.3, .5).translate(0, -.2, 0), '#fff1c2'), .055);
    return [merge([blade, guard, grip, ...wraps, pommel]), merge([...fuller, ...gem])];
  }
  if (kind === 'energy') {
    // 蓄能：六棱双锥晶体本身就是亮芯（尖端发白、腰部饱和紫），金属只做腰箍与底托。
    const crystal = paint(new THREE.LatheGeometry([[0,-.80],[.24,-.24],[.29,.10],[.23,.40],[0,.86]].map(p => new THREE.Vector2(p[0] * 1.15, p[1])), 6),
      (c, x, y) => c.set('#6236e8').lerp(new THREE.Color('#c7b2ff'), Math.min(1, Math.abs(y - .05) / .8) ** 1.4));
    const girdle = paint(new THREE.CylinderGeometry(.35, .345, .07, 6, 1, true).translate(0, .1, 0), '#e9cf8e');
    const cup = paint(new THREE.CylinderGeometry(.19, .07, .2, 6).translate(0, -.66, 0), '#e9cf8e');
    const prongs = [0, 1, 2].map(k => paint(new THREE.BoxGeometry(.03, .5, .03).translate(0, .25, 0).rotateZ(-.42)
      .translate(.08, -.6, 0).rotateY(k * Math.PI * 2 / 3 + Math.PI / 6), '#e9cf8e'));
    return [merge([girdle, cup, ...prongs]), merge([crystal])];
  }
  // 护盾：银色鸢形盾，弧顶尖底，正面蓝釉盾心 + 凸起银十字 + 中央冰蓝盾钉。
  const outline = s => {
    const p = new THREE.Shape(); p.moveTo(-.47 * s, .5 * s); p.quadraticCurveTo(0, .63 * s, .47 * s, .5 * s);
    p.lineTo(.45 * s, .04 * s); p.quadraticCurveTo(.4 * s, -.44 * s, 0, -.72 * s);
    p.quadraticCurveTo(-.4 * s, -.44 * s, -.45 * s, .04 * s); p.closePath(); return p;
  };
  const body = paint(solid(outline(1), .05, .035, .045, 2, 6), '#dfe7f0');
  const field = paint(solid(outline(.8), .02, .012, .012, 1, 6).translate(0, .015, .072),
    (c, x, y) => c.set('#0f2f8a').lerp(new THREE.Color('#3a7cf0'), Math.max(0, Math.min(1, (y + .55) / 1.05))));
  const cross = paint(solid([[-.045,.42],[.045,.42],[.045,.08],[.27,.08],[.27,-.01],[.045,-.01],[.045,-.46],[-.045,-.46],[-.045,-.01],[-.27,-.01],[-.27,.08],[-.045,.08]],
    .02, .014, .014).translate(0, .01, .1), '#eef3f8');
  const boss = paint(new THREE.IcosahedronGeometry(.075, 0).scale(1, 1, .6).translate(0, .035, .13), '#9fdcff');
  return [merge([body, cross]), merge([field, boss])];
}

// 每实例透明度与扫光位置：辉光材质用同一段补丁，扫过金属时也进辉光。
const GLINT = 'float nrBand=exp(-pow((nrLocal.y+nrLocal.x*.55-nrRewardGlint)*10.,2.))*step(-5.,nrRewardGlint);';
function fadeMaterial(material, basic = false) {
  material.onBeforeCompile = shader => {
    shader.vertexShader = 'attribute float rewardOpacity; attribute float rewardGlint; varying float nrRewardOpacity; varying float nrRewardGlint; varying vec2 nrLocal;\n' + shader.vertexShader;
    shader.vertexShader = shader.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\nnrRewardOpacity=rewardOpacity;nrRewardGlint=rewardGlint;nrLocal=position.xy;');
    shader.fragmentShader = 'varying float nrRewardOpacity; varying float nrRewardGlint; varying vec2 nrLocal;\n' + shader.fragmentShader;
    shader.fragmentShader = shader.fragmentShader.replace('#include <color_fragment>', '#include <color_fragment>\ndiffuseColor.a*=nrRewardOpacity;'
      + (basic ? GLINT + 'diffuseColor.rgb+=vec3(1.,.92,.75)*nrBand*.18;' : ''));
    if (!basic) shader.fragmentShader = shader.fragmentShader.replace('#include <emissivemap_fragment>',
      '#include <emissivemap_fragment>\ntotalEmissiveRadiance*=vColor.rgb;' + GLINT + 'totalEmissiveRadiance+=vec3(1.,.92,.75)*nrBand*.45;');
  };
  material.customProgramCacheKey = () => 'nr-chest-reward-v2-' + (basic ? 'glow' : 'pbr');
}

const backOut = v => { v = Math.max(0, Math.min(1, v)); const s = 1.9; return 1 + (s + 1) * (v - 1) ** 3 + s * (v - 1) ** 2; };
// 扇形展开到匣口上方：中间件更高、两侧外倾，依次弹出并转身亮相，再收向受益者胸前。
// 减少动态只显示静止的扇形实体与轻淡入淡出。
export function sampleChestReward(event, kind, age, actor, scale = .028, reduced = false) {
  const available = KINDS.filter(k => Number.isFinite(event.rewards[k]) && event.rewards[k] > 0), rank = available.indexOf(kind);
  const side = rank - (available.length - 1) / 2, edge = available.length > 1 ? Math.abs(side) / ((available.length - 1) / 2) : 0;
  const delay = rank * .05, pop = (age - .10 - delay) / .26;
  const rise = smooth(pop), flight = reduced ? 0 : smooth((age - .58 - delay * .8) / .5);
  const spread = reduced ? 1 : rise, hover = reduced ? 0 : Math.sin(age * 5 + rank * 1.7) * .06 * rise * (1 - flight);
  const source = [event.x * scale + side * 1.6 * spread, 2.75 + .38 * (1 - edge), event.y * scale - 1.65 * spread];
  const target = [actor.x * scale, 1.15, actor.y * scale];
  const position = [source[0] + (target[0] - source[0]) * flight,
    reduced ? source[1] : .42 + (source[1] - .42) * rise + hover + (target[1] - source[1]) * flight + Math.sin(flight * Math.PI) * .65,
    source[2] + (target[2] - source[2]) * flight];
  const opacity = smooth((age - .10 - delay) / .09) * (1 - smooth((age - 1.13) / .19));
  const spin = reduced ? 0 : (1 - smooth(pop)) * Math.PI * 1.6 + Math.sin(age * 3.1 + rank) * .26 * rise * (1 - flight) + flight * flight * Math.PI * 2.5;
  return { position, opacity, scale: (reduced ? 1 : backOut(pop)) * (1 - flight * .55),
    rotation: spin, roll: -side * .2 * (1 - flight),
    glint: reduced ? -9 : -1.7 + Math.max(0, age - .30 - delay) * 6,
    phase: reduced ? 'still' : age < .37 + delay ? 'rise' : age < .58 + delay * .8 ? 'present' : 'receive' };
}

export function createChestRewards(scene, { onOpen = () => {} } = {}) {
  const glowMaterials = new Set();
  // 颜色全部来自顶点色；金属保留少量自照明，暗场地也不会沉成褐色。
  // 写深度：盾面十字、晶体金托与亮芯互相遮挡要正确，不能让后画的亮芯盖住金属。
  const metal = new THREE.MeshStandardMaterial({name:'RewardMetal',color:'#ffffff',vertexColors:true,metalness:.88,roughness:.24,
    envMapIntensity:1.3,emissive:'#ffffff',emissiveIntensity:.16,transparent:true});
  const light = new THREE.MeshStandardMaterial({name:'RewardInlay',color:'#ffffff',vertexColors:true,metalness:.15,roughness:.16,
    envMapIntensity:.9,emissive:'#ffffff',emissiveIntensity:.42,transparent:true});
  for (const m of [metal,light]) {
    fadeMaterial(m);
    m.userData.createGlowMaterial = weight => {
      const glow = new THREE.MeshBasicMaterial({color:m.emissive.clone().multiplyScalar(m.emissiveIntensity*weight),
        vertexColors:true,transparent:true,depthWrite:false});
      fadeMaterial(glow,true); glowMaterials.add(glow); return glow;
    };
  }
  const batches = new Map();
  for (const kind of KINDS) {
    const alpha = new THREE.InstancedBufferAttribute(new Float32Array(CAPACITY),1).setUsage(THREE.DynamicDrawUsage);
    const glint = new THREE.InstancedBufferAttribute(new Float32Array(CAPACITY).fill(-9),1).setUsage(THREE.DynamicDrawUsage);
    const meshes = geometries(kind).map((geo,i) => {
      geo.setAttribute('rewardOpacity',alpha);geo.setAttribute('rewardGlint',glint);
      const mesh = new THREE.InstancedMesh(geo,i ? light : metal,CAPACITY);
      mesh.name = 'Chest reward ' + kind + (i ? ' inlay' : ' body');
      mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage); mesh.frustumCulled=false;
      mesh.count=0;mesh.renderOrder=4;scene.add(mesh);return mesh;
    });
    batches.set(kind,{alpha,glint,meshes,count:0});
  }
  const object = new THREE.Object3D();
  let run = null, cursor = 0, records = [], active = [], disposed = false, dropped = 0, low = false, reduced = false, enabled = true;
  function reset(nextRun = null, nextCursor = 0) {
    run=nextRun;cursor=nextCursor;records=[];active=[];dropped=0;
    for (const b of batches.values()) { b.count=0;for(const mesh of b.meshes)mesh.count=0; }
  }
  function update(frame, scale = .028, systemReduced = false, showObjects = true) {
    if(disposed)return;
    if(frame.run!==run)reset(frame.run);
    const time=frame.run?.time??0;
    low=frame.options?.quality==='low'; reduced=frame.options?.reducedMotion===true||systemReduced;
    enabled=showObjects;
    const actors=new Map([frame.P,...(frame.agents||[])].filter(Boolean).map(a=>[a.uid??0,a]));
    records=records.filter(e=>time-e.time<CHEST_REWARD_LIFE&&actors.has(e.owner)&&!actors.get(e.owner).downed);
    for(const event of frame.pickupEvents||[]) {
      if(!Number.isSafeInteger(event.id)||event.id<=cursor)continue;cursor=event.id;
      const actor=actors.get(event.owner),age=time-event.time;
      if(event.kind!=='chest'||!actor||actor.downed||!event.rewards||![event.x,event.y,event.time].every(Number.isFinite)
        ||age<0||age>=CHEST_REWARD_LIFE)continue;
      if(!KINDS.some(k=>Number.isFinite(event.rewards[k])&&event.rewards[k]>0))continue;
      if(records.length>=CAPACITY){dropped++;continue;}
      records.push(event);onOpen(event,age);
    }
    for(const b of batches.values())b.count=0;
    active=[];
    const limit=low?LOW_CAPACITY:CAPACITY;
    for(const event of enabled ? records.slice(-limit) : []) {
      const actor=actors.get(event.owner),age=time-event.time;
      for(const kind of KINDS) {
        if(!Number.isFinite(event.rewards[kind])||!(event.rewards[kind]>0))continue;
        const sample=sampleChestReward(event,kind,age,actor,scale,reduced);
        if(sample.opacity<.002)continue;
        const b=batches.get(kind),n=b.count++;
        object.position.set(...sample.position);object.rotation.set(-.82,sample.rotation,sample.roll);
        object.scale.setScalar(sample.scale);object.updateMatrix();
        b.alpha.setX(n,sample.opacity);b.glint.setX(n,sample.glint);
        for(const mesh of b.meshes)mesh.setMatrixAt(n,object.matrix);
        active.push({id:event.id,kind,amount:event.rewards[kind],owner:event.owner,age,...sample});
      }
    }
    for(const b of batches.values()) {
      b.alpha.needsUpdate=true;b.glint.needsUpdate=true;
      for(const mesh of b.meshes){mesh.count=b.count;mesh.instanceMatrix.needsUpdate=true;}
    }
  }
  function dispose() {
    if(disposed)return;reset();disposed=true;
    for(const b of batches.values())for(const mesh of b.meshes){scene.remove(mesh);mesh.geometry.dispose();mesh.dispose();}
    metal.dispose();light.dispose();for(const m of glowMaterials)m.dispose();glowMaterials.clear();
  }
  return {update,reset,dispose,metrics:()=>({scheduled:records.length,active,capacity:CAPACITY,lowCapacity:LOW_CAPACITY,
    counts:Object.fromEntries([...batches].map(([k,b])=>[k,b.count])),draws:[...batches.values()].filter(b=>b.count).length*2,
    dropped,low,reducedMotion:reduced,enabled,disposed,cursor})};
}
