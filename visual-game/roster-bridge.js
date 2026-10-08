// 默认高清桥接：首页 / 选角 / 图鉴与战场共用当前角色和场地资产；?visual=legacy 可对照旧版。
// 菜单待载入 / 失败时使用当前素材静帧；战斗按类别保留原生兼容回退。
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { clone as cloneSkinned } from 'three/addons/utils/SkeletonUtils.js';
import { ADDITIVE, battleEnvironment, createGlow, glowWeight, radialTexture, tuneMaterial } from './glow.js';
import { ARENAS, createArenaEnv } from './arena-env.js';
import { createRegionReflections, REFLECTION_REGIONS } from './arena-reflections.mjs';
import { createHeroWeaponFX } from './hero-weapon-fx.mjs';
import { createSkillFX } from './skill-fx.mjs';
import { createBossFX } from './boss-fx.mjs';
import { createWarningDecals } from './warning-decals.mjs';
import { createPickupDetails } from './pickup-fx.mjs';
import { pickupStyle } from './pickup-fx-data.mjs';
import { createChestRewards } from './chest-rewards.mjs';
import { HEROES, presentationFor, presentationRect, fitPresentationCamera } from './presentation.mjs';
import { createPresentationActors } from './presentation-actors.mjs';
import { createAssetStore, yieldForPaint } from './asset-loading.mjs';

const query = new URLSearchParams(location.search);
const VERSION = query.get('hdv') || 'hd-1';
const assetUrl = path => {
  const u = globalThis.NRAssets ? NRAssets.url(path) : new URL(`../visual-lab/assets/${path}`, import.meta.url).href;
  return `${u}${u.includes('?') ? '&' : '?'}v=${VERSION}`;
};
const wrap = a => Math.atan2(Math.sin(a), Math.cos(a));

// 模型米 → 游戏世界单位（原生缩放 0.028/像素）；杂兵略缩小，保证主角在人群里仍然醒目
const METERS = { mob: 1.2, elite: 1.2, boss: 1.0 };
// 按 Boss 单独缩放：Boss 1 / Boss 7 翼展约 15 m、Boss 2 身长约 11 m，原尺寸会盖住半个战场；
// 收到 9–10 m 级占地，仍明显大于其余 Boss 和英雄（原生判定半径约 1.6 单位）
const BOSS_SCALE = { 1: 0.66, 2: 0.85, 7: 0.66 };
// Boss 自转件：刚性挂在骨上、自身无动画轨道的网格节点，由网页端绕最薄轴旋转
const BOSS_SPIN = { 7: ['BOSS_7_HALO'] };

export async function createRosterBridge(app) {
  await yieldForPaint();
  const canvas = document.createElement('canvas');
  canvas.id = 'visualRoster';
  canvas.setAttribute('aria-hidden', 'true');
  Object.assign(canvas.style, { position: 'absolute', inset: '0', width: '100%', height: '100%',
    pointerEvents: 'none', zIndex: '1', display: 'none' });
  app.insertBefore(canvas, document.getElementById('overlay'));
  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true, powerPreference: 'high-performance',
    preserveDrawingBuffer: query.has('capture') });
  renderer.setPixelRatio(1);
  renderer.setClearColor(0, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.2;
  renderer.info.autoReset = false;
  const scene = new THREE.Scene();
  const reflections = createRegionReflections(renderer);
  let regionReflectionsOn = query.get('reflections') !== 'studio';
  let reflectionId = null, studioReflection = null, reflectionMode = null;
  function reflectRegion(frame) {
    const candidate = query.get('arenaid') || ARENAS[presentation?.stage ?? frame.run?.stage ?? 0];
    const id = regionReflectionsOn && Object.hasOwn(REFLECTION_REGIONS, candidate) ? candidate : 'studio';
    if (id === reflectionId) return;
    const regional = id !== 'studio' ? reflections.get(id) : null;
    if (!regional && !studioReflection) studioReflection = battleEnvironment(renderer, 0x8b5cf6, 1.3);
    scene.environment = regional || studioReflection;
    reflectionId = id;
    reflectionMode = regional ? 'region' : 'studio';
  }
  scene.environmentIntensity = 0.9;
  scene.add(new THREE.HemisphereLight(0x9d8cff, 0x0a0612, 0.6));
  for (const [color, intensity, pos] of [[0xefe8ff, 2.2, [-2.0, 4.8, 3.4]], [0xa070ff, 1.5, [-2.3, 3.3, -3.3]],
    [0x40e0ff, 0.8, [2.5, 2.7, -2.9]], [0x8f86c8, 0.5, [3, 1.5, 4]]]) {
    const l = new THREE.DirectionalLight(color, intensity);
    l.position.set(...pos);
    scene.add(l);
  }
  const camera = new THREE.OrthographicCamera(-18, 18, 10, -10, 0.1, 150);
  const glow = createGlow(renderer, scene, camera, { strength: 0.85, radius: 0.4, weight: glowWeight });
  await yieldForPaint();
  let glowOn = false, visible = false, error = null, now = 0;
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  canvas.addEventListener('webglcontextlost', () => { error = 'Three.js WebGL context lost'; visible = false; });

  // ----- 资产加载 -----
  const loader = new GLTFLoader();
  const store = createAssetStore({ verify: (path, bytes) => globalThis.NRAssets?.verify(path, bytes), loader, url: assetUrl, discard: (rec, gltf) => {
    for (const mesh of [...(rec?.inst || []), ...(rec?.bins || [])]) { mesh.removeFromParent(); mesh.dispose?.(); }
    rec?.heat?.dispose?.(); rec?.ambient?.dispose?.();
    const disposed = new Set();
    gltf?.scene?.traverse(o => {
      if (!o.isMesh) return;
      o.geometry.dispose();
      for (const material of [].concat(o.material)) if (!disposed.has(material)) {
        disposed.add(material);
        for (const value of Object.values(material)) if (value?.isTexture && !disposed.has(value)) { disposed.add(value); value.dispose(); }
        material.dispose();
      }
    });
  } });
  // 场地环境层（地面 / 边界建筑）：独立画布，叠在原生画布下面
  const env = createArenaEnv(app, loader, assetUrl, camera, store);
  await yieldForPaint();
  const assets = store.records;
  const load = (key, path, prepareFn, priority = 0) => store.load(key, path, async (gltf, id) => {
    const rec = await prepareFn(gltf, id);
    // 提前准备基础材质；完整画面仍以首次实际渲染作为就绪条件。
    if (rec.root) { await renderer.compileAsync(rec.root, camera, scene); await glow.prepare(rec.root); }
    return rec;
  }, priority);
  const ready = key => assets.get(key)?.state === 'ready';

  function prepareSkinned(gltf, key) {
    const root = gltf.scene;
    const id = key.replace(/^hero:/, '');
    root.traverse(o => {
      if (!o.isMesh) return;
      o.frustumCulled = false;
      for (const m of [].concat(o.material)) tuneMaterial(m, id);
    });
    root.getObjectByName('NYX_NEEDLE')?.removeFromParent();
    const size = new THREE.Box3().setFromObject(root).getSize(new THREE.Vector3());
    return { root, clips: new Map(gltf.animations.map(c => [c.name, c])), size };
  }

  // 刚性部件杂兵：把每段动作逐帧、逐部件相对根节点的矩阵烘焙成图集，运行时一部件一次实例化绘制
  async function prepareInstanced(gltf) {
    const root = gltf.scene;
    const meshes = [];
    root.traverse(o => {
      if (!o.isMesh) return;
      for (const m of [].concat(o.material)) tuneMaterial(m);
      meshes.push(o);
    });
    const mixer = new THREE.AnimationMixer(root);
    const inv = new THREE.Matrix4();
    const clips = {};
    let slice = performance.now();
    for (const clip of gltf.animations) {
      const frames = Math.max(8, Math.round(clip.duration * 24));
      mixer.stopAllAction();
      mixer.clipAction(clip).play();
      const mats = meshes.map(() => []);
      for (let f = 0; f < frames; f++) {
        mixer.setTime(f / frames * clip.duration);
        root.updateMatrixWorld(true);
        inv.copy(root.matrixWorld).invert();
        meshes.forEach((m, k) => mats[k].push(new THREE.Matrix4().multiplyMatrices(inv, m.matrixWorld)));
        if (performance.now() - slice > 5) { await yieldForPaint(); slice = performance.now(); }
      }
      clips[clip.name] = { frames, duration: clip.duration, mats };
    }
    mixer.stopAllAction();
    const size = new THREE.Box3().setFromObject(root).getSize(new THREE.Vector3());
    const rec = { meshes, clips, size, capacity: 0, inst: [], count: 0 };
    grow(rec, 64);
    return rec;
  }
  function grow(rec, capacity) {
    for (const old of rec.inst) { scene.remove(old); old.dispose(); }
    rec.inst = rec.meshes.map(m => {
      const im = new THREE.InstancedMesh(m.geometry, m.material, capacity);
      im.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      im.frustumCulled = false;
      im.count = 0;
      im.setColorAt(0, new THREE.Color(1, 1, 1));
      scene.add(im);
      return im;
    });
    rec.capacity = capacity;
  }

  // ----- 骨骼角色实例（英雄 / Boss） -----
  class Actor {
    constructor(rec, def) {
      this.def = def;
      this.rec = rec;
      this.root = cloneSkinned(rec.root);
      this.mixer = new THREE.AnimationMixer(this.root);
      this.action = null;
      this.motion = '';
      this.rest = 'Idle';
      this.yaw = null;
      this.last = { cast: 0, ult: 0, cool: -1, phase: 0 };
      this.channel = 0;
      this.spins = (def.spin || []).map(n => this.root.getObjectByName(n)).filter(Boolean)
        .map(node => ({ node, axis: thinAxis(node, this.root), q0: node.quaternion.clone(), a: 0 }));
      this.mixer.addEventListener('finished', e => { if (e.action === this.action) this.play(this.rest); });
      scene.add(this.root);
    }
    play(name, fade = 0.2) {
      const clip = this.rec.clips.get(name);
      if (!clip) return false;
      const loop = name === 'Idle' || name === 'Move' || name === 'Drift';
      if (name === this.motion && this.action?.isRunning() && loop) return true;
      const next = this.mixer.clipAction(clip);
      next.reset();
      next.setLoop(loop ? THREE.LoopRepeat : THREE.LoopOnce);
      next.clampWhenFinished = false;
      next.play();
      if (this.action && this.action !== next) next.crossFadeFrom(this.action, fade, false);
      this.action = next;
      this.motion = name;
      return true;
    }
    dispose() {
      scene.remove(this.root); this.mixer.stopAllAction();
      const skeletons = new Set();
      this.root.traverse(o => { if (o.isSkinnedMesh) skeletons.add(o.skeleton); });
      skeletons.forEach(skeleton => skeleton.dispose());
    }
  }
  function thinAxis(node, root) {
    root.updateMatrixWorld(true);
    const inv = node.matrixWorld.clone().invert(), box = new THREE.Box3();
    node.traverse(o => {
      if (!o.isMesh) return;
      o.geometry.computeBoundingBox();
      box.union(o.geometry.boundingBox.clone().applyMatrix4(new THREE.Matrix4().multiplyMatrices(inv, o.matrixWorld)));
    });
    const s = box.getSize(new THREE.Vector3());
    return s.x < s.y && s.x < s.z ? new THREE.Vector3(1, 0, 0) : s.y < s.z ? new THREE.Vector3(0, 1, 0) : new THREE.Vector3(0, 0, 1);
  }

  const heroActors = new Map();   // 'leader' / 'a{uid}' -> Actor
  const bossActors = new Map();   // 敌人槽位 -> { gen, actor }
  let displayActor = null, presentation = null;
  const displayActors = createPresentationActors(); // 最近四个展示对象复用独立骨骼实例。
  const displayBox = new THREE.Box3();
  const spinQ = new THREE.Quaternion();
  const afterimages = [];
  function updateAfterimages(frame, leader, S) {
    for (const image of afterimages) image.root.visible = false;
    const traces = frame.traces || [];
    if (!leader || !traces.length || reducedMotion.matches || !['play', 'paused'].includes(frame.state)) return;
    if (afterimages[0]?.source !== leader.root) {
      for (const image of afterimages) {
        scene.remove(image.root); image.material.dispose();
        const skeletons = new Set();
        image.root.traverse(o => { if (o.isSkinnedMesh) skeletons.add(o.skeleton); });
        skeletons.forEach(skeleton => skeleton.dispose());
      }
      afterimages.length = 0;
    }
    const count = Math.min(traces.length, frame.options.quality === 'low' ? 1 : 2);
    const sourceNodes = []; leader.root.traverse(o => sourceNodes.push(o));
    for (let i = 0; i < count; i++) {
      if (!afterimages[i]) {
        const root = cloneSkinned(leader.root), targetNodes = [];
        const material = new THREE.MeshBasicMaterial({ color: HERO_RGB[frame.selected], transparent: true,
          opacity: .1, depthWrite: false, side: THREE.DoubleSide, forceSinglePass: true });
        root.traverse(o => { targetNodes.push(o); if (o.isMesh) { o.material = material; o.userData.noGlow = true; } });
        root.userData.noGlow = true;
        scene.add(root); afterimages.push({ root, material, source: leader.root, targetNodes });
      }
      const image = afterimages[i];
      for (let k = 0; k < sourceNodes.length; k++) {
        const source = sourceNodes[k], target = image.targetNodes[k];
        target.position.copy(source.position); target.quaternion.copy(source.quaternion); target.scale.copy(source.scale);
      }
      const trace = traces[Math.floor((i + .5) * traces.length / count)];
      image.root.position.set(trace.x * S, 0, trace.y * S);
      image.material.opacity = .16 * Math.max(0, 1 - trace.age / trace.life);
      image.root.visible = image.material.opacity > .005;
    }
  }

  function heroActor(slot, heroId) {
    const def = HEROES[heroId];
    if (!def || !ready(`hero:${def.id}`)) return null;
    let a = heroActors.get(slot);
    if (a && a.heroId !== heroId) { a.dispose(); a = null; }
    if (!a) {
      a = new Actor(assets.get(`hero:${def.id}`), def);
      a.heroId = heroId;
      a.scale = def.height / a.rec.size.y;
      heroActors.set(slot, a);
    }
    a.seen = true;
    return a;
  }

  function updateHero(a, unit, dt, S) {
    const def = a.def, move = def.move || 'Move';
    a.rest = unit.moving ? move : 'Idle';
    a.root.position.set(unit.x * S, unit.downed ? -1.0 : 0, unit.y * S);
    const aim = -(unit.moving ? unit.moveAim : unit.aim) - Math.PI / 2;
    a.yaw = a.yaw === null ? aim : a.yaw + wrap(aim - a.yaw) * Math.min(1, dt * (def.turn || 12));
    a.root.rotation.y = a.yaw;
    a.root.scale.setScalar(a.scale * (unit.downed ? 0.76 : 1.0));
    const ult = unit.ultTime || 0, cast = unit.castAnim || 0;
    if (ult > a.last.ult + 1 && a.rec.clips.has('Channel')) a.play('Channel');
    else if (a.motion === 'Channel' && ult > 0) { /* 终结技期间保持引导姿态 */ }
    else if (cast > a.last.cast + 0.1 && a.rec.clips.has('Cast')) a.play('Cast');
    else if (a.motion !== 'Cast' && a.motion !== 'Channel') a.play(a.rest);
    a.last.ult = ult;
    a.last.cast = cast;
    // Channel 第 13–28 帧是保持段：终结技剩余时间足够收势时停在 1.1 s
    if (a.motion === 'Channel' && a.action && ult > 0.6 && a.action.time > 1.1) a.action.time = 1.1;
    a.mixer.update(dt);
    a.channel += ((a.motion === 'Channel' ? 1 : 0) - a.channel) * Math.min(1, dt * 3);
    for (const s of a.spins) {
      s.a += dt * (0.3 + a.channel * 1.6);
      s.node.quaternion.copy(s.q0).multiply(spinQ.setFromAxisAngle(s.axis, s.a));
    }
  }

  function updateBoss(i, E, targets, dt, S) {
    const type = E.type[i], key = `boss-${type}`;
    if (!ready(key)) return false;
    let slot = bossActors.get(i);
    if (slot && slot.gen !== E.gen[i]) { slot.actor.dispose(); bossActors.delete(i); slot = null; }
    if (!slot) {
      const actor = new Actor(assets.get(key), { id: key, spin: BOSS_SPIN[type] });
      actor.scale = METERS.boss * (BOSS_SCALE[type] ?? 1);
      actor.last.cool = E.cool[i];
      actor.last.phase = E.phase[i];
      slot = { gen: E.gen[i], actor };
      bossActors.set(i, slot);
    }
    slot.seen = true;
    const a = slot.actor, x = E.x[i], y = E.y[i];
    let best = null, bd = 1e12;
    for (const t of targets) { const d = (t.x - x) ** 2 + (t.y - y) ** 2; if (d < bd) { bd = d; best = t; } }
    a.root.position.set(x * S, 0, y * S);
    if (best) {
      const aim = -Math.atan2(best.y - y, best.x - x) - Math.PI / 2;
      a.yaw = a.yaw === null ? aim : a.yaw + wrap(aim - a.yaw) * Math.min(1, dt * 2.5);
      a.root.rotation.y = a.yaw;
    }
    a.root.scale.setScalar(a.scale);
    a.rest = Math.sqrt(bd) < 210 ? 'Idle' : 'Move';
    if (E.phase[i] !== a.last.phase && a.rec.clips.has('Enrage')) a.play('Enrage');
    else if (E.cool[i] !== a.last.cool && a.motion !== 'Enrage' && a.rec.clips.has('Attack')) a.play('Attack', 0.15);
    else if (a.motion !== 'Attack' && a.motion !== 'Enrage') a.play(a.rest);
    a.last.phase = E.phase[i];
    a.last.cool = E.cool[i];
    a.mixer.update(E.freeze[i] > 0 ? dt * 0.25 : dt);
    for (const s of a.spins) {
      s.a += dt * (a.motion === 'Enrage' ? 1.9 : 0.3);
      s.node.quaternion.copy(s.q0).multiply(spinQ.setFromAxisAngle(s.axis, s.a));
    }
    shadowAt(x * S, y * S, Math.max(a.rec.size.x, a.rec.size.z) * a.scale * 0.42);
    return true;
  }

  // ----- 杂兵 / 精英状态（按敌人槽位） -----
  let EMAX = 0, gen = null, yawArr = null, attackAt = null, prevTimer = null, prevCharge = null;
  function ensureState(E) {
    if (EMAX === E.max) return;
    EMAX = E.max;
    gen = new Int32Array(EMAX).fill(-1);
    yawArr = new Float32Array(EMAX);
    // 出手时刻必须用双精度：Float32 舍入后可能比当前 now 略大，since 变成极小负数，帧号算成 -1
    attackAt = new Float64Array(EMAX).fill(-99);
    prevTimer = new Float32Array(EMAX);
    prevCharge = new Float32Array(EMAX);
  }
  const RANGED = new Set([4, 6]);
  const rootM = new THREE.Matrix4(), partM = new THREE.Matrix4(), quat = new THREE.Quaternion(), pos = new THREE.Vector3();
  const scl = new THREE.Vector3(), up = new THREE.Vector3(0, 1, 0), col = new THREE.Color();
  const FROZEN = new THREE.Color(0.55, 0.85, 1.35), WHITE = new THREE.Color(1, 1, 1);

  // 落地阴影：所有高清单位共用一个实例化圆斑（正常混合压暗地面）
  const SHADOW_MAX = 1600;
  const shadowMesh = new THREE.InstancedMesh(new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2),
    new THREE.MeshBasicMaterial({ map: radialTexture([[0, 'rgba(0,0,0,0.55)'], [0.55, 'rgba(0,0,0,0.30)'], [1, 'rgba(0,0,0,0)']]),
      transparent: true, depthWrite: false }), SHADOW_MAX);
  shadowMesh.frustumCulled = false;
  shadowMesh.renderOrder = -1;
  shadowMesh.userData.noGlow = true;
  shadowMesh.count = 0;
  scene.add(shadowMesh);
  let shadowCount = 0;
  function shadowAt(x, z, r) {
    if (shadowCount >= SHADOW_MAX) return;
    rootM.compose(pos.set(x, 0.015, z), quat.identity(), scl.set(r * 2, 1, r * 2));
    shadowMesh.setMatrixAt(shadowCount++, rootM);
  }

  function updateLegion(frame, native, dt, S, targets) {
    const E = frame.E, cam = frame.camera;
    ensureState(E);
    for (const rec of assets.values()) if (rec.inst) rec.count = 0;
    const halfW = native.viewWidth / 2 + 130 + 150, halfH = native.viewHeight / (2 * native.sinElev) + 140 + 150;
    for (let i = 0; i < E.max; i++) {
      if (!E.a[i]) continue;
      const tier = E.tier[i];
      if (tier === 2) {
        if (updateBoss(i, E, targets, dt, S)) continue;
        continue;
      }
      const x = E.x[i], y = E.y[i];
      if (Math.abs(x - cam.x) > halfW || Math.abs(y - cam.y) > halfH) continue;
      const type = E.type[i], rec = assets.get(`${tier ? 'elite' : 'mob'}-${type}`);
      if (!rec || rec.state !== 'ready') continue;
      if (gen[i] !== E.gen[i]) {
        gen[i] = E.gen[i];
        attackAt[i] = -99;
        prevTimer[i] = E.timer[i];
        prevCharge[i] = E.charge[i];
        yawArr[i] = NaN;
      }
      let best = null, bd = 1e12;
      for (const t of targets) { const d = (t.x - x) ** 2 + (t.y - y) ** 2; if (d < bd) { bd = d; best = t; } }
      const aim = best ? -Math.atan2(best.y - y, best.x - x) - Math.PI / 2 : 0;
      yawArr[i] = Number.isNaN(yawArr[i]) ? aim : yawArr[i] + wrap(aim - yawArr[i]) * Math.min(1, dt * 8);
      // 攻击触发：计时器重置（远程 / 精英出手）、冲锋开始、近战贴身
      const atk = rec.clips.Attack;
      if (atk) {
        const since = now - attackAt[i];
        const fired = E.timer[i] > prevTimer[i] + 0.5 && (tier === 1 || RANGED.has(type));
        const charged = E.charge[i] < 0 && prevCharge[i] >= 0;
        const melee = !RANGED.has(type) && Math.sqrt(bd) < E.radius[i] + 34 && since > atk.duration + 0.35;
        if ((fired || charged || melee) && since > atk.duration * 0.8) attackAt[i] = now;
      }
      prevTimer[i] = E.timer[i];
      prevCharge[i] = E.charge[i];
      let clip = rec.clips.Move || rec.clips.Idle, f;
      const since = now - attackAt[i];
      if (atk && since < atk.duration) {
        clip = atk;
        f = Math.max(0, Math.min(atk.frames - 1, Math.floor(since / atk.duration * atk.frames)));
      } else {
        const rate = E.freeze[i] > 0 ? 0 : Math.min(1.6, Math.max(0.7, E.speed[i] / 90));
        const phase = (now * rate + (i * 0.618) % 1 * clip.duration) % clip.duration;
        f = Math.floor(phase / clip.duration * clip.frames) % clip.frames;
      }
      if (rec.count >= rec.capacity) grow(rec, rec.capacity * 2);
      const n = rec.count++;
      quat.setFromAxisAngle(up, yawArr[i]);
      const s = METERS[tier ? 'elite' : 'mob'];
      rootM.compose(pos.set(x * S, 0, y * S), quat, scl.set(s, s, s));
      const frozen = E.freeze[i] > 0, hit = Math.min(0.9, E.hit[i] * 7);
      col.copy(frozen ? FROZEN : WHITE);
      if (!frozen && E.slow[i] > 0) col.lerp(FROZEN, Math.min(.22, E.slow[i] * .16));
      col.multiplyScalar(1 + hit * 1.6);
      for (let k = 0; k < rec.inst.length; k++) {
        partM.multiplyMatrices(rootM, clip.mats[k][f]);
        rec.inst[k].setMatrixAt(n, partM);
        rec.inst[k].setColorAt(n, col);
      }
      shadowAt(x * S, y * S, Math.max(rec.size.x, rec.size.z) * s * 0.45);
    }
    for (const rec of assets.values()) {
      if (!rec.inst) continue;
      for (const im of rec.inst) {
        im.count = rec.count;
        im.instanceMatrix.needsUpdate = true;
        if (im.instanceColor) im.instanceColor.needsUpdate = true;
      }
    }
  }

  // ----- 飞剑：每名英雄一种游戏版飞剑（visual-lab/assets/blades/），每个材质一次实例化绘制 -----
  // 模型约定与原生 blade 网格一致：剑尖朝 +X、平躺、原点在护手；位置、朝向、缩放照搬原生渲染器
  function prepareBlade(gltf) {
    const root = gltf.scene;
    root.updateMatrixWorld(true);
    const parts = [];
    root.traverse(o => {
      if (!o.isMesh) return;
      for (const m of [].concat(o.material)) tuneMaterial(m, 'blade');
      parts.push({ geo: o.geometry, mat: o.material, local: o.matrixWorld.clone() });
    });
    const rec = { parts, bins: [], bcap: 0, bcount: 0 };
    growParts(rec, 128);
    return rec;
  }
  function growParts(rec, capacity) {
    for (const old of rec.bins) { scene.remove(old); old.dispose(); }
    rec.bins = rec.parts.map(p => {
      const im = new THREE.InstancedMesh(p.geo, p.mat, capacity);
      im.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      im.frustumCulled = false;
      im.count = 0;
      scene.add(im);
      return im;
    });
    rec.bcap = capacity;
  }
  // 拖尾：贴地平铺的加色面片，x ∈ [-1, 0]，x=0 是剑的位置（最亮），x=-1 是尾端（全透明）
  function trailTexture() {
    const c = document.createElement('canvas');
    c.width = 128;
    c.height = 32;
    const g = c.getContext('2d');
    const along = g.createLinearGradient(0, 0, 128, 0);
    along.addColorStop(0, 'rgba(255,255,255,0)');
    along.addColorStop(0.7, 'rgba(255,255,255,0.55)');
    along.addColorStop(1, 'rgba(255,255,255,1)');
    g.fillStyle = along;
    g.fillRect(0, 0, 128, 32);
    // 横向收边：中心亮、两侧软
    g.globalCompositeOperation = 'destination-in';
    const across = g.createLinearGradient(0, 0, 0, 32);
    across.addColorStop(0, 'rgba(0,0,0,0)');
    across.addColorStop(0.5, 'rgba(0,0,0,1)');
    across.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = across;
    g.fillRect(0, 0, 128, 32);
    const t = new THREE.CanvasTexture(c);
    t.colorSpace = THREE.SRGBColorSpace;
    return t;
  }
  const fxMaterial = map => {
    const m = new THREE.MeshBasicMaterial({ map, transparent: true, depthWrite: false, toneMapped: false, ...ADDITIVE });
    m.userData.glowSelf = true;
    return m;
  };
  function fxMesh(geo, mat, capacity) {
    const im = new THREE.InstancedMesh(geo, mat, capacity);
    im.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    im.frustumCulled = false;
    im.count = 0;
    im.renderOrder = 2;
    im.setColorAt(0, new THREE.Color(1, 1, 1));
    scene.add(im);
    return im;
  }
  const TRAIL_MAX = 2400, SPARK_MAX = 900;
  const trailMesh = fxMesh(new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2).translate(-0.5, 0, 0),
    fxMaterial(trailTexture()), TRAIL_MAX);
  // 命中火花：沿速度方向拉长的光点
  const sparkMesh = fxMesh(new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2),
    fxMaterial(radialTexture([[0, 'rgba(255,255,255,1)'], [0.35, 'rgba(255,255,255,0.6)'], [1, 'rgba(255,255,255,0)']])), SPARK_MAX);
  const HERO_RGB = HEROES.map((_, h) => new THREE.Color(['#7cece1', '#ffac64', '#86b9ff', '#c39bff', '#ff8ea8', '#9beefb'][h]));
  // 通用光点（飞剑命中火花、道具拾取闪光）：{ x, y, z, vx, vy, vz, age, life, size, c, flash, gain }
  const sparks = [];
  const weaponFX = createHeroWeaponFX(scene);
  await yieldForPaint();
  const skillFX = createSkillFX(scene, { feedbackRoot: app, feedbackEnabled: query.get('feedback') !== '0' });
  await yieldForPaint();
  const bossFX = createBossFX(scene);
  const warningDecals = createWarningDecals(scene);
  const pickupDetails = createPickupDetails(scene);
  let pickupOn = query.get('pickupfx') !== 'legacy', pickupFrame = null, pickupRun = null;
  let rewardObjectsOn = query.get('rewardfx') !== '0', rewardScale = .028;
  const chestRewards = createChestRewards(scene, { onOpen: (event, age) =>
    spawnPickupFx(2, event.x * rewardScale, event.y * rewardScale, 0, event, age) });
  let warningOn = query.get('warningfx') !== '0';
  let bossOn = query.get('bossfx') !== '0', bossFrame = null;
  let skillOn = query.get('skillfx') !== '0', skillFrame = null;
  let heroWeaponOn = query.get('weaponfx') !== 'legacy', weaponFrame = null;
  let lastHit = null;
  const BLADE_SCALE = 1.2;   // 游戏版飞剑比原生 blade 大 20%
  function trailSegment(n, ax, az, bx, bz, width, color, gain) {
    const dx = bx - ax, dz = bz - az, len = Math.hypot(dx, dz);
    if (len < 0.02) return n;
    // 面片 x 轴从头（剑）指向尾：绕 Y 旋转到 (dx, dz) 的反方向
    quat.setFromAxisAngle(up, Math.atan2(dz, -dx));
    rootM.compose(pos.set(ax, 0.63, az), quat, scl.set(len, 1, width));
    trailMesh.setMatrixAt(n, rootM);
    trailMesh.setColorAt(n, col.copy(color).multiplyScalar(gain));
    return n + 1;
  }
  // 几百把飞剑同时命中时火花会铺满屏幕：每帧最多处理 HIT_BUDGET 次命中，其余只记不画
  const HIT_BUDGET = 14;
  let hitsThisFrame = 0;
  function spawnHit(x, z, h) {
    if (hitsThisFrame++ >= HIT_BUDGET) return;
    if (sparks.length > SPARK_MAX - 3) sparks.splice(0, 3);
    const c = HERO_RGB[h] || WHITE;
    sparks.push({ x, y: 0.66, z, vx: 0, vy: 0, vz: 0, age: 0, life: 0.12, size: 0.42, c, flash: true, gain: 0.8 });
    for (let k = 0; k < 2; k++) {
      const a = Math.random() * Math.PI * 2, v = 5 + Math.random() * 7;
      sparks.push({ x, y: 0.66, z, vx: Math.cos(a) * v, vy: 0, vz: Math.sin(a) * v, age: 0, life: 0.18 + Math.random() * 0.14,
        size: 0.16 + Math.random() * 0.08, c, flash: false, gain: 1.6 });
    }
  }
  function updateSparks(dt) {
    let n = 0;
    for (let i = sparks.length - 1; i >= 0; i--) {
      const p = sparks[i];
      p.age += dt;
      if (p.age >= p.life) { sparks.splice(i, 1); continue; }
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.z += p.vz * dt;
      p.vx *= 0.86;
      p.vz *= 0.86;
      const t = 1 - p.age / p.life, speed = Math.hypot(p.vx, p.vz);
      quat.setFromAxisAngle(up, p.flash ? 0 : Math.atan2(-p.vz, p.vx));
      const len = p.flash ? p.size * (1.4 - 0.4 * t) : p.size * (1 + speed * 0.08);
      rootM.compose(pos.set(p.x, p.y, p.z), quat, scl.set(len, 1, p.flash ? len : p.size * 0.45));
      sparkMesh.setMatrixAt(n, rootM);
      sparkMesh.setColorAt(n, col.copy(p.c).lerp(WHITE, p.flash ? 0.5 : 0.25).multiplyScalar(t * p.gain));
      n++;
    }
    sparkMesh.count = n;
    sparkMesh.instanceMatrix.needsUpdate = true;
    if (sparkMesh.instanceColor) sparkMesh.instanceColor.needsUpdate = true;
  }

  function updateBlades(frame, native, S, dt) {
    const B = frame.B;
    if (!B) return;
    if (!lastHit || lastHit.length !== B.max) lastHit = new Int32Array(B.max).fill(-1);
    let trails = 0;
    hitsThisFrame = 0;
    const recs = HEROES.map(h => assets.get(`blade-${h.id}`)).map(r => (r?.state === 'ready' ? r : null));
    weaponFrame = frame;
    if (heroWeaponOn) weaponFX.update(frame, native, S, dt, recs.map(Boolean));
    // 先数一遍，容量不够时一次扩到位，避免循环中途扩容丢掉本帧已写入的矩阵
    const need = recs.map(() => 0);
    for (let i = 0; i < B.max; i++) if (B.a[i]) need[B.hero[i] ?? frame.selected]++;
    recs.forEach((r, h) => {
      if (!r) return;
      r.bcount = 0;
      if (need[h] > r.bcap) growParts(r, Math.max(need[h], r.bcap * 2));
    });
    const cam = frame.camera;
    const halfW = native.viewWidth / 2 + 150, halfH = native.viewHeight / (2 * native.sinElev) + 150;
    for (let i = 0; i < B.max; i++) {
      if (!B.a[i]) { lastHit[i] = -1; continue; }
      const x = B.x[i], y = B.y[i];
      const h = B.hero[i] ?? frame.selected, rec = recs[h];
      // 命中：lastHit 记录最近一次命中的敌人槽位，变成新的非负值就是一次新命中
      const hit = B.lastHit[i];
      if (!heroWeaponOn && rec && hit >= 0 && hit !== lastHit[i]) spawnHit(x * S, y * S, h);
      lastHit[i] = hit;
      if (Math.abs(x - cam.x) > halfW || Math.abs(y - cam.y) > halfH) continue;
      if (!rec) continue;
      const n = rec.bcount++, s = (B.flags[i] ? 1.15 : 0.58) * BLADE_SCALE;
      quat.setFromAxisAngle(up, -(heroWeaponOn && h === 3 ? weaponFX.bladeHeading(i, B.angle[i]) : B.angle[i]));
      rootM.compose(pos.set(x * S, 0.65 + Math.sin(B.age[i] * 9 + i) * 0.09, y * S), quat, scl.set(s, s, s));
      for (let k = 0; k < rec.parts.length; k++) rec.bins[k].setMatrixAt(n, partM.multiplyMatrices(rootM, rec.parts[k].local));
      // 拖尾：沿历史轨迹两段，第二段更淡更细；跨度过大（瞬移 / 重生）时不画
      if (!heroWeaponOn && trails < TRAIL_MAX - 2) {
        const w = 0.2 * s, c = HERO_RGB[h];
        const p0x = x, p0y = y, p1x = B.tx1[i], p1y = B.ty1[i], p2x = B.tx2[i], p2y = B.ty2[i];
        if (Math.hypot(p1x - p0x, p1y - p0y) < 150) {
          trails = trailSegment(trails, p0x * S, p0y * S, p1x * S, p1y * S, w, c, 1.3);
          if (Math.hypot(p2x - p1x, p2y - p1y) < 150) trails = trailSegment(trails, p1x * S, p1y * S, p2x * S, p2y * S, w * 0.7, c, 0.55);
        }
      }
    }
    for (const r of recs) {
      if (!r) continue;
      for (const im of r.bins) { im.count = r.bcount; im.instanceMatrix.needsUpdate = true; }
    }
    trailMesh.count = trails;
    trailMesh.instanceMatrix.needsUpdate = true;
    if (trailMesh.instanceColor) trailMesh.instanceColor.needsUpdate = true;
    updateSparks(dt);
  }

  // ----- 掉落道具（O.kind：0 成长碎片 / 1 回复圣瓶 / 2 圣物匣）-----
  // 模型在 visual-lab/assets/pickups/，不带动画；浮动、自转、开盖、拾取特效都在这里驱动
  const PICKUP_KEYS = ['pickup-shard', 'pickup-vial', 'pickup-chest'];
  const PICKUP_RGB = [new THREE.Color('#86d9e6'), new THREE.Color('#87ffb5'), new THREE.Color('#f3d287')];
  function preparePickup(gltf, key) {
    const root = gltf.scene;
    root.updateMatrixWorld(true);
    root.traverse(o => {
      if (!o.isMesh) return;
      o.frustumCulled = false;
      for (const m of [].concat(o.material)) {
        tuneMaterial(m, 'pickup');
        // 圣瓶液体名含 Glow（辉光权重 0.5），在战斗辉光下会糊成白绿光球、看不出瓶形，压到约 40%
        // 浅薄荷色发光经 ACES 后发白，战斗环境的青色灯条又把它染青，和成长碎片撞色：
        // 改成同色相、更饱和的绿，压低环境反射，底色压成深绿
        if (key === 'pickup-vial' && /glow/i.test(m.name)) {
          m.emissiveIntensity *= 0.45;
          m.emissive.setRGB(0.06, 0.9, 0.22);
          m.color.setRGB(0.04, 0.3, 0.1);
          m.envMapIntensity = 0.15;
        }
      }
    });
    if (key === 'pickup-chest') return { root };
    const parts = [];
    root.traverse(o => { if (o.isMesh) parts.push({ geo: o.geometry, mat: o.material, local: o.matrixWorld.clone() }); });
    const rec = { parts, bins: [], bcap: 0, bcount: 0 };
    pickupDetails.configure(rec, key === 'pickup-shard' ? 0 : 1);
    growParts(rec, key === 'pickup-shard' ? 256 : 32);
    return rec;
  }
  // 成长碎片按价值分三档：杂兵 3.5 / 精英 16 / Boss 90
  const shardScale = v => pickupStyle(v).scale;

  // 圣物匣：数量很少，每个槽位克隆一份整体（匣身、可开的盖、自转光环）
  const chests = new Map();   // O 槽位 -> { group, lid, halo, lid0, halo0, seen }
  const groundGlowMat = fxMaterial(radialTexture([[0, 'rgba(255,225,160,0.9)'], [0.5, 'rgba(255,200,120,0.25)'], [1, 'rgba(255,200,120,0)']]));
  const groundGlowGeo = new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2);
  function makeChest(rec) {
    const group = rec.root.clone(true);
    const lid = group.getObjectByName('CHEST_LID'), halo = group.getObjectByName('CHEST_HALO');
    const glow = new THREE.Mesh(groundGlowGeo, groundGlowMat);
    glow.scale.setScalar(2.4);
    glow.position.y = 0.02;
    glow.renderOrder = 1;
    group.add(glow);
    scene.add(group);
    return { group, lid, halo, glow, lid0: lid?.quaternion.clone(), halo0: halo?.position.clone(), haloQ0: halo?.quaternion.clone() };
  }
  const xAxis = new THREE.Vector3(1, 0, 0), spinQ2 = new THREE.Quaternion();
  function poseChest(c, t, open) {
    if (c.halo) {
      c.halo.quaternion.copy(c.haloQ0).multiply(spinQ2.setFromAxisAngle(up, t * 1.4));
      c.halo.position.copy(c.halo0);
      c.halo.position.y += Math.sin(t * 2.2) * 0.05 + open * 0.9;
      c.halo.scale.setScalar(1 + open * 0.6);
    }
    // 开盖：盖子节点原点在后侧铰链上，绕 X 轴旋转（方向见 pickups-r1 汇报）
    if (c.lid) c.lid.quaternion.copy(c.lid0).multiply(spinQ2.setFromAxisAngle(xAxis, -open * LID_OPEN));
  }
  const LID_OPEN = 110 * Math.PI / 180;

  // 拾取特效：圣物匣开盖 + 金色光柱 + 冲击环；碎片 / 圣瓶是一团对应颜色的光点
  function pillarTexture() {
    const c = document.createElement('canvas');
    c.width = 4;
    c.height = 128;
    const g = c.getContext('2d'), grad = g.createLinearGradient(0, 0, 0, 128);
    grad.addColorStop(0, 'rgba(255,255,255,0)');
    grad.addColorStop(0.75, 'rgba(255,255,255,0.55)');
    grad.addColorStop(1, 'rgba(255,255,255,1)');
    g.fillStyle = grad;
    g.fillRect(0, 0, 4, 128);
    const t = new THREE.CanvasTexture(c);
    t.colorSpace = THREE.SRGBColorSpace;
    return t;
  }
  const pillarGeo = new THREE.CylinderGeometry(0.22, 0.38, 7, 20, 1, true).translate(0, 3.5, 0);
  const pillarMap = pillarTexture();
  const shockGeo = new THREE.RingGeometry(0.82, 1, 48).rotateX(-Math.PI / 2);
  const openings = [];   // { chest, pillar, shock, age }
  const OPEN_LIFE = 1.1, OPEN_CAPACITY = 12;
  function spawnPickupFx(kind, x, z, value, event = null, age = 0) {
    const c = PICKUP_RGB[kind];
    if (kind === 2) {
      if (!event || age >= OPEN_LIFE) return;
      // 回流因倒地 / 退席取消后，源开盖仍会自然播完；独立限制匣体总量。
      updateOpenings(pickupFrame);
      if (openings.length >= OPEN_CAPACITY) return;
      const rec = assets.get('pickup-chest');
      if (rec?.state !== 'ready') return;
      const chest = makeChest(rec);
      chest.group.position.set(x, 0, z);
      const pillarMat = fxMaterial(pillarMap);
      pillarMat.side = THREE.DoubleSide;
      const pillar = new THREE.Mesh(pillarGeo, pillarMat);
      pillar.position.set(x, 0, z);
      pillar.renderOrder = 3;
      const shock = new THREE.Mesh(shockGeo, fxMaterial(null));
      shock.position.set(x, 0.05, z);
      shock.renderOrder = 3;
      scene.add(pillar, shock);
      openings.push({ chest, pillar, shock, age, time: event.time, owner: event.owner });
      const reduced = pickupFrame?.options?.reducedMotion === true || reducedMotion.matches;
      for (let k = 0; k < 10; k++) {
        const a = k / 10 * Math.PI * 2;
        const vy = 2 + Math.random() * 3, life = 0.5 + Math.random() * 0.3;
        if (!reduced) sparks.push({ x, y: 0.6, z, vx: Math.cos(a) * 6, vy, vz: Math.sin(a) * 6, age: 0,
          life, size: rewardObjectsOn ? 0.07 : 0.22, c, flash: false, gain: rewardObjectsOn ? 0.6 : 1.6 });
      }
      return;
    }
    const big = kind === 0 ? shardScale(value) : 1.2;
    sparks.push({ x, y: 0.5, z, vx: 0, vy: 0, vz: 0, age: 0, life: 0.18, size: 0.5 * big, c, flash: true, gain: 0.9 });
    const n = kind === 1 ? 6 : big > 1.2 ? 6 : 2;
    for (let k = 0; k < n; k++) {
      const a = Math.random() * Math.PI * 2, v = 1.5 + Math.random() * 2;
      // 回复：光点向上飘；碎片：向四周溅开
      sparks.push({ x, y: 0.5, z, vx: Math.cos(a) * v, vy: kind === 1 ? 2.5 + Math.random() * 1.5 : 0.5, vz: Math.sin(a) * v,
        age: 0, life: 0.35 + Math.random() * 0.25, size: 0.12, c, flash: false, gain: 1.4 });
    }
  }
  function clearOpenings() {
    for (const o of openings) {
      scene.remove(o.chest.group, o.pillar, o.shock);
      o.pillar.material.dispose(); o.shock.material.dispose();
    }
    openings.length = 0;
  }
  function updateOpenings(frame) {
    const reduced = frame.options?.reducedMotion === true || reducedMotion.matches;
    for (let i = openings.length - 1; i >= 0; i--) {
      const o = openings[i];
      o.age = Math.max(0, (frame.run?.time ?? 0) - o.time);
      const t = o.age / OPEN_LIFE;
      if (t >= 1) {
        scene.remove(o.chest.group, o.pillar, o.shock);
        o.pillar.material.dispose();
        o.shock.material.dispose();
        openings.splice(i, 1);
        continue;
      }
      // 0–0.25 弹开盖子，之后光柱与冲击环渐隐，匣子在最后 30% 沉入地面
      const open = Math.min(1, t / 0.25);
      poseChest(o.chest, reduced ? o.time : frame.run.time, reduced ? 1 : 1 - (1 - open) ** 3);
      o.chest.group.position.y = reduced ? 0 : -Math.max(0, (t - 0.7) / 0.3) * 0.8;
      o.chest.glow.visible = !rewardObjectsOn && !reduced;
      o.pillar.visible = o.shock.visible = !reduced;
      const fade = Math.max(0, 1 - t);
      // 光柱在盖子开到一半后才升起，避免一开始就把开盖动作盖住
      const rise = Math.max(0, Math.min(1, (t - 0.12) / 0.2));
      o.pillar.scale.set(0.7 + rise * 0.3, rise, 0.7 + rise * 0.3);
      o.pillar.material.color.copy(PICKUP_RGB[2]).multiplyScalar((rewardObjectsOn ? 0.18 : 0.55) * fade);
      o.shock.scale.setScalar(0.6 + t * 4.5);
      o.shock.material.color.copy(PICKUP_RGB[2]).multiplyScalar((rewardObjectsOn ? 0.4 : 0.8) * fade * fade);
    }
  }

  let prevO = null;   // 每个 O 槽位上一帧的 { a, kind, x, y, value, age }
  function updatePickups(frame, native, S, dt) {
    const O = frame.O;
    if (!O) return;
    pickupFrame = frame;
    if (frame.run !== pickupRun) {
      pickupRun = frame.run; prevO = null; pickupDetails.reset();
      // 奖励模块自己识别新局；不能覆盖 Canvas / 菜单分支已消费的事件游标。
      for (const c of chests.values()) scene.remove(c.group);
      chests.clear();
      clearOpenings();
    }
    if (!prevO || prevO.a.length !== O.max) {
      prevO = { a: new Uint8Array(O.max), kind: new Int8Array(O.max), x: new Float64Array(O.max), y: new Float64Array(O.max),
        value: new Float64Array(O.max), age: new Float64Array(O.max) };
    }
    const shard = assets.get('pickup-shard'), vial = assets.get('pickup-vial'), chestRec = assets.get('pickup-chest');
    const instRecs = [shard?.state === 'ready' ? shard : null, vial?.state === 'ready' ? vial : null];
    const needed = [0, 0];
    for (let i = 0; i < O.max; i++) if (O.a[i] && O.kind[i] < 2) needed[O.kind[i]]++;
    instRecs.forEach((r, k) => { if (r && needed[k] > r.bcap) growParts(r, Math.min(O.max, Math.max(needed[k], r.bcap * 2))); });
    for (const r of instRecs) if (r) r.bcount = 0;
    for (const c of chests.values()) c.seen = false;
    const cam = frame.camera;
    const halfW = native.viewWidth / 2 + 150, halfH = native.viewHeight / (2 * native.sinElev) + 150;
    for (let i = 0; i < O.max; i++) {
      const alive = !!O.a[i], kind = O.kind[i];
      // 槽位从有到无（或被同帧复用，age 变小）= 被拾取：在最后的位置放拾取特效
      if (prevO.a[i] && (!alive || O.age[i] < prevO.age[i])) {
        const pk = prevO.kind[i];
        // 圣物匣只读实际发放事件；清池 / 槽位复用不能凭空开盖或奖励。
        if (pk !== 2 && ready(PICKUP_KEYS[pk])) spawnPickupFx(pk, prevO.x[i] * S, prevO.y[i] * S, prevO.value[i]);
      }
      prevO.a[i] = alive ? 1 : 0;
      if (!alive) continue;
      prevO.kind[i] = kind;
      prevO.x[i] = O.x[i];
      prevO.y[i] = O.y[i];
      prevO.value[i] = O.value[i];
      prevO.age[i] = O.age[i];
      const x = O.x[i], y = O.y[i];
      if (Math.abs(x - cam.x) > halfW || Math.abs(y - cam.y) > halfH) continue;
      const t = (frame.run?.time ?? now) + i * 0.37;
      if (kind === 2) {
        if (chestRec?.state !== 'ready') continue;
        let c = chests.get(i);
        if (!c) { c = makeChest(chestRec); chests.set(i, c); }
        c.seen = true;
        c.group.position.set(x * S, 0, y * S);
        poseChest(c, t, 0);
        continue;
      }
      const rec = instRecs[kind];
      if (!rec) continue;
      if (rec.bcount >= rec.bcap) continue;
      const n = rec.bcount++;
      const s = kind === 0 ? shardScale(O.value[i]) : 1;
      // 碎片：自转 + 轻微倾斜；圣瓶：上下浮动 + 小幅摇摆
      if (kind === 0) quat.setFromEuler(eul.set(0.25, t * 1.6, 0));
      else quat.setFromEuler(eul.set(0, t * 0.6, Math.sin(t * 1.8) * 0.12));
      rootM.compose(pos.set(x * S, (kind === 0 ? 0.45 : 0.5) * s + Math.sin(t * 3) * 0.09, y * S), quat, scl.set(s, s, s));
      pickupDetails.instance(rec, n, i, O.value[i], kind);
      for (let k = 0; k < rec.parts.length; k++) rec.bins[k].setMatrixAt(n, partM.multiplyMatrices(rootM, rec.parts[k].local));
      shadowAt(x * S, y * S, 0.22 * s);
    }
    for (const r of instRecs) {
      if (!r) continue;
      for (const im of r.bins) { im.count = r.bcount; im.instanceMatrix.needsUpdate = true; }
      pickupDetails.flush(r);
    }
    for (const [i, c] of chests) if (!c.seen) { scene.remove(c.group); chests.delete(i); }
    rewardScale = S;
    chestRewards.update(frame, S, reducedMotion.matches, rewardObjectsOn);
    updateOpenings(frame);
    pickupDetails.update(frame, native, S, !!instRecs[0], pickupOn, frame.run?.time ?? now, reducedMotion.matches);
  }
  const eul = new THREE.Euler();

  // ----- 每帧：先声明哪些类别由高清画布负责，再渲染 -----
  const flags = { hero: {}, enemy: {}, blade: {}, pickup: {}, env: false, weaponFx: false, skillFx: false, bossFx: false, warningFx: false };
  let started = false, presentedToken = null, battleToken = null, activeRun = null, runSerial = 0;
  let currentFrame = null, neighborAt = 0, neighborToken = null;
  const arenaKey = stage => 'arena:' + (query.get('arenaid') || ARENAS[stage]);
  function requiredKeys(frame) {
    const p = presentationFor(frame), keys = [];
    if (!p) return keys;
    if (query.get('arena') !== '0') keys.push(arenaKey(p.stage));
    if (p.kind !== 'battle') return [...keys, p.key];
    for (const h of [frame.selected, ...(frame.agents || []).map(a => a.heroId)]) {
      keys.push('hero:' + HEROES[h].id, 'blade-' + HEROES[h].id);
    }
    // 等待实际首帧需要的敌人；其余杂兵 / 精英留到后台，避免首局等待整套资产。
    const E = frame.E;
    for (let i = 0; i < E.max; i++) if (E.a[i]) {
      keys.push((E.tier[i] === 2 ? 'boss-' : E.tier[i] === 1 ? 'elite-' : 'mob-') + E.type[i]);
    }
    keys.push(...PICKUP_KEYS);
    if (frame.mode === 'bossrush' && frame.run?.time === 0) keys.push('boss-0');
    return [...new Set(keys)];
  }
  function frameToken(frame) {
    const p = presentationFor(frame);
    return p?.kind === 'battle' ? `${runSerial}:${p.stage}:${requiredKeys(frame).sort().join('|')}`
      : p ? `${frame.state}:${p.key}:${p.stage}` : null;
  }
  function loadingStatus(frame) {
    if (error) return { state: 'missing', phase: 'failed', failed: [], fatal: true };
    if (!frame || !frame.options || frame.options.backend === 'canvas') return { state: 'unavailable', phase: 'failed', failed: [] };
    const p = presentationFor(frame), token = frameToken(frame);
    return { ...store.describe(requiredKeys(frame), p?.kind === 'battle' ? battleToken === token : presentedToken === token),
      key: token, stage: p?.stage, kind: p?.kind };
  }
  function prefetch(frame) {
    const p = presentationFor(frame);
    if (!p) return;
    if (p.kind !== 'battle') {
      const token = frameToken(frame);
      if (neighborToken !== token) { neighborToken = token; neighborAt = performance.now() + 800; }
      if (performance.now() < neighborAt || presentedToken !== token) return;
      if (frame.state === 'select') {
        const def = HEROES[(p.hero + 1) % HEROES.length];
        load('hero:' + def.id, def.glb, prepareSkinned, 2);
      } else if (p.kind === 'boss') {
        const next = (p.boss + 1) % 8;
        load('boss-' + next, `chars/boss-${next}-game.glb`, prepareSkinned, 2);
      }
      return;
    }
    const r = frame.run, ex = r.expedition;
    const boss = ex ? [1, 4, 7][ex.chapter] : frame.mode === 'bossrush' ? r.bosses : Math.floor((r.wave + r.wave % 2) / 2) - 1;
    if (Number.isInteger(boss) && boss >= 0 && boss < 8) load('boss-' + boss, `chars/boss-${boss}-game.glb`, prepareSkinned, 1);
    if (ex && ['camp', 'route'].includes(frame.state)) env.prefetch(ex.chapter);
    else if (!ex && frame.mode === 'bossrush' && r.bosses % 2 === 1) env.prefetch(Math.min(3, Math.floor((r.bosses + 1) / 2)));
    else if (!ex && frame.mode !== 'bossrush' && r.wave % 4 === 0 && r.waveClock > 12) env.prefetch((r.stage + 1) % 4);
  }
  function requestAssets(frame) {
    if (presentation.kind === 'hero') {
      const def = HEROES[presentation.hero];
      load(presentation.key, def.glb, prepareSkinned);
      load(`blade-${def.id}`, `blades/${def.id}-blade.glb`, prepareBlade);
      return;
    }
    if (presentation.kind === 'boss') {
      load(presentation.key, `chars/boss-${presentation.boss}-game.glb`, prepareSkinned);
      return;
    }
    if (!started) {
      started = true;
      for (let t = 0; t < 8; t++) load(`mob-${t}`, `chars/mob-${t}-game.glb`, prepareInstanced, 2);
      for (let t = 0; t < 6; t++) load(`elite-${t}`, `chars/elite-${t}-game.glb`, prepareInstanced, 2);
      // 道具文件缺失时记为 missing，原生道具继续绘制
      for (const key of PICKUP_KEYS) load(key, `pickups/${key.slice(7)}.glb`, preparePickup);
    }
    const ids = [frame.selected, ...(frame.agents || []).map(a => a.heroId)];
    for (const id of ids) {
      const def = HEROES[id];
      if (def) load(`hero:${def.id}`, def.glb, prepareSkinned);
      // 飞剑文件缺失时 load 记为 missing，原生飞剑继续绘制
      if (def) load(`blade-${def.id}`, `blades/${def.id}-blade.glb`, prepareBlade);
    }
    const E = frame.E;
    for (let i = 0; i < E.max; i++) {
      if (E.a[i] && E.tier[i] === 2) load(`boss-${E.type[i]}`, `chars/boss-${E.type[i]}-game.glb`, prepareSkinned);
      else if (E.a[i]) {
        const key = (E.tier[i] === 1 ? 'elite-' : 'mob-') + E.type[i];
        load(key, `chars/${key}-game.glb`, prepareInstanced);
      }
    }
  }

  function prepare(frame, native) {
    currentFrame = frame;
    if (frame.run !== activeRun) { activeRun = frame.run; runSerial++; battleToken = null; }
    native.warningProgress = warningOn;
    presentation = presentationFor(frame);
    visible = !!(!error && native.gl && !native.hadContextLoss && frame.options.backend !== 'canvas' && presentation);
    if (visible) {
      reflectRegion(frame);
      requestAssets(frame);
      prefetch(frame);
      flags.weaponFx = heroWeaponOn && ready('blade-volt');
      flags.skillFx = skillOn && presentation.kind === 'battle';
      flags.bossFx = bossOn && presentation.kind === 'battle';
      flags.warningFx = warningOn && presentation.kind === 'battle';
      for (let h = 0; h < HEROES.length; h++) {
        flags.hero[h] = ready(`hero:${HEROES[h].id}`);
        flags.blade[h] = ready(`blade-${HEROES[h].id}`);
      }
      PICKUP_KEYS.forEach((key, k) => { flags.pickup[k] = ready(key); });
      for (let t = 0; t < 8; t++) {
        flags.enemy[t] = ready(`mob-${t}`);
        flags.enemy[8 + t] = t < 6 && ready(`elite-${t}`);
        flags.enemy[16 + t] = ready(`boss-${t}`);
      }
    }
    // 场地必须在原生渲染之前定下来：原生据此决定是否画自己的地面、背景是否透明
    flags.env = env.want(frame, visible, presentation?.stage);
    if (visible) store.prioritize(requiredKeys(frame));
    const display = visible && presentation.kind !== 'battle';
    const modelState = display ? assets.get(presentation.key)?.state || 'loading' : null;
    const envState = display ? env.assetState(presentation.stage) : null;
    const prepared = modelState === 'ready' && (flags.env || envState === 'disabled');
    flags.presentationFirstFrame = prepared && presentedToken === frameToken(frame);
    flags.presentationState = !visible ? 'unavailable' : !display ? 'ready'
      : modelState === 'missing' || envState === 'missing' ? 'missing'
        : flags.presentationFirstFrame ? 'ready' : 'loading';
    flags.presentation = display && modelState === 'ready' && (flags.env || envState === 'disabled') ? presentation.kind : null;
    flags.presentationKey = flags.presentation ? presentation.key : null;
    if (!visible || presentation.kind !== 'battle') {
      env.render(false);
      if (weaponFrame) { weaponFX.reset(frame.run, frame.weaponEvents?.at(-1)?.id || 0); weaponFrame = null; }
      if (skillFrame) { skillFX.reset(frame.run, frame.skillEvents?.at(-1)?.id || 0); skillFrame = null; }
      if (bossFrame) { bossFX.reset(frame.run, frame.bossEvents?.at(-1)?.id || 0); bossFrame = null; }
      warningDecals.reset();
      pickupDetails.reset(); prevO = null; pickupFrame = null;
      chestRewards.reset(frame.run, frame.pickupEvents?.at(-1)?.id || 0);
      clearOpenings();
      for (const c of chests.values()) scene.remove(c.group);
      chests.clear();
    }
    if (error) window.__NR_VISUAL_LOAD_ERROR = error;
    window.__NR_VISUAL = visible ? flags : null;
    window.__NR_VISUAL_ACTIVE = !!(visible && (presentation.kind === 'battle' ? flags.hero[frame.selected] : flags.presentation));
    canvas.style.display = visible && (presentation.kind === 'battle' || flags.presentation) ? 'block' : 'none';
    canvas.dataset.presentation = presentation?.key || presentation?.kind || '';
    canvas.dataset.assetState = flags.presentation || visible && presentation.kind === 'battle' ? 'ready' : flags.presentationState;
  }

  const measure = { frames: 0, renderMsTotal: 0, renderMsMax: 0 };
  function render(frame, dt, native) {
    if (!visible || presentation.kind !== 'battle' && !flags.presentation) return;
    const started = performance.now();
    const step = Math.min(Math.max(dt, 0), 0.05);
    now += step;
    const width = native.canvas.clientWidth, height = native.canvas.clientHeight;
    if (canvas.width !== width || canvas.height !== height) {
      renderer.setSize(width, height, false);
      glow.setSize(width, height);
    }
    const S = native.scale;
    shadowCount = 0;
    // 从界面返回战场时恢复正交相机；界面模型不写入战斗池或施法时间线。
    if (presentation.kind !== 'battle') {
      for (const image of afterimages) image.root.visible = false;
      for (const a of heroActors.values()) a.root.visible = false;
      for (const b of bossActors.values()) b.actor.root.visible = false;
      for (const rec of assets.values()) {
        for (const im of rec.inst || []) im.count = 0;
        for (const im of rec.bins || []) im.count = 0;
      }
      trailMesh.count = sparkMesh.count = 0;
      displayActor = displayActors.show(presentation.key, () => {
        if (!ready(presentation.key)) return null;
        const def = presentation.kind === 'hero' ? HEROES[presentation.hero]
          : { id: presentation.key, spin: BOSS_SPIN[presentation.boss] };
        const actor = new Actor(assets.get(presentation.key), def);
        actor.play('Idle');
        return actor;
      });
      if (displayActor) {
        const a = displayActor;
        a.root.scale.setScalar(7.8 / a.rec.size.y);
        a.root.rotation.y = presentation.kind === 'boss' ? frame.inspection.yaw : .16 + (reducedMotion.matches ? 0 : Math.sin(now * .12) * .05);
        a.mixer.update(reducedMotion.matches ? 0 : step);
        for (const s of a.spins) {
          s.a += reducedMotion.matches ? 0 : step * .3;
          s.node.quaternion.copy(s.q0).multiply(spinQ.setFromAxisAngle(s.axis, s.a));
        }
        a.root.updateMatrixWorld(true);
        displayBox.setFromObject(a.root);
        let rect = presentationRect(frame.state, width / height);
        if (width < height) {
          const panel = app.querySelector(frame.state === 'home' ? '.home-model-stage' : frame.state === 'inspect' ? '.inspect-reticle' : '.hero-stage');
          if (panel) {
            const r = panel.getBoundingClientRect(), base = app.getBoundingClientRect();
            rect = { x: (r.x - base.x) / width, y: (r.y - base.y) / height,
              width: r.width / width, height: r.height / height };
            if (frame.state === 'select') { rect.y += 25 / height; rect.height -= 78 / height; }
          }
        }
        fitPresentationCamera(camera, displayBox, width / height, rect, frame.inspection && presentation.kind === 'boss' ? frame.inspection.zoom : 1);
        shadowAt(0, 0, 2.4);
        if (presentation.kind === 'hero') {
          const rec = assets.get(`blade-${a.def.id}`);
          if (rec?.state === 'ready') {
            for (let i = 0; i < 6; i++) {
              const angle = (reducedMotion.matches ? 0 : now * .14) + i * Math.PI / 3;
              rootM.compose(pos.set(Math.cos(angle) * 2.6, 1.0 + (i % 3) * .7, Math.sin(angle) * 2.6),
                quat.setFromAxisAngle(up, -angle), scl.setScalar(.7));
              for (let k = 0; k < rec.parts.length; k++) rec.bins[k].setMatrixAt(i, partM.multiplyMatrices(rootM, rec.parts[k].local));
            }
            for (const im of rec.bins) { im.count = 6; im.instanceMatrix.needsUpdate = true; }
          }
        }
      } else {
        camera.position.set(0, 12, -30); camera.lookAt(0, 3, 0);
        fitPresentationCamera(camera, new THREE.Box3(new THREE.Vector3(-3, 0, -2), new THREE.Vector3(3, 8, 2)), width / height, presentationRect(frame.state, width / height));
      }
    } else {
    displayActors.hide(); displayActor = null;
    for (const a of heroActors.values()) a.root.visible = true;
    for (const b of bossActors.values()) b.actor.root.visible = true;
    camera.left = -native.width / 2;
    camera.right = native.width / 2;
    camera.top = native.height / 2;
    camera.bottom = -native.height / 2;
    camera.updateProjectionMatrix();
    camera.position.set(...native.eye);
    camera.lookAt(...native.target);
    for (const a of heroActors.values()) a.seen = false;
    for (const b of bossActors.values()) b.seen = false;
    const units = [];
    const P = frame.P;
    const leader = heroActor('leader', frame.selected);
    if (leader) { updateHero(leader, P, step, S); units.push(P); shadowAt(P.x * S, P.y * S, 0.9); }
    updateAfterimages(frame, leader, S);
    for (const a of frame.agents || []) {
      const actor = heroActor(`a${a.uid}`, a.heroId);
      if (actor) { updateHero(actor, a, step, S); shadowAt(a.x * S, a.y * S, 0.85); }
      units.push(a);
    }
    const targets = [P, ...(frame.agents || [])].filter(u => !u.downed);
    updateLegion(frame, native, step, S, targets.length ? targets : [P]);
    updateBlades(frame, native, S, step);
    updatePickups(frame, native, S, step);
    skillFrame = frame;
    if (skillOn) skillFX.update(frame, native, S);
    bossFrame = frame;
    if (bossOn) bossFX.update(frame, native, S);
    if (warningOn) warningDecals.update(frame, S);
    for (const [slot, a] of heroActors) if (!a.seen) { a.dispose(); heroActors.delete(slot); }
    for (const [i, b] of bossActors) if (!b.seen) { b.actor.dispose(); bossActors.delete(i); }
    }
    env.render(flags.env, native, frame.options.bloom !== false);
    shadowMesh.count = shadowCount;
    shadowMesh.instanceMatrix.needsUpdate = true;
    glowOn = frame.options.bloom !== false;
    try {
      renderer.info.reset();
      renderer.render(scene, camera);
      if (glowOn) glow.render();
    } catch (e) {
      error = String(e);
      visible = false;
      window.__NR_VISUAL = null;
      canvas.style.display = 'none';
      return;
    }
    const ms = performance.now() - started;
    measure.frames++;
    measure.renderMsTotal += ms;
    measure.renderMsMax = Math.max(measure.renderMsMax, ms);
    if (presentation.kind === 'battle') battleToken = frameToken(frame);
    else presentedToken = frameToken(frame);
  }

  return {
    prepare, render, loadingStatus,
    retry: frame => { store.retry(requiredKeys(frame)); presentedToken = battleToken = null; },
    loadingMetrics: store.metrics,
    // 后续英雄技能只需要登记配方与绑定，不必再创建新的渲染器或全屏后处理。
    registerSkillFX: (id, definition) => skillFX.register(id, definition),
    bindSkillFX: (hero, kind, id) => skillFX.bind(hero, kind, id),
    // 仅测试局可在同一帧切换旧 / 新反射，用相同姿态和敌人状态做对照。
    ...(query.has('test') ? { setReflections(mode) {
      regionReflectionsOn = mode !== 'studio';
      reflectionId = null;
      env.setReflections(mode);
    } } : {}),
    ...(query.has('test') ? { setWeaponFX(mode) {
      heroWeaponOn = mode !== 'legacy';
      weaponFX.reset(weaponFrame?.run, weaponFrame?.weaponEvents?.at(-1)?.id || 0);
      // 对照时清掉瞬态，不把切换前的旧命中重新当作一次攻击。
      sparks.length = 0;
      if (lastHit && weaponFrame?.B) lastHit.set(weaponFrame.B.lastHit);
    } } : {}),
    ...(query.has('test') ? { setSkillFX(enabled) {
      skillOn = !!enabled;
      skillFX.reset(skillFrame?.run, skillFrame?.skillEvents?.at(-1)?.id || 0);
    } } : {}),
    ...(query.has('test') ? { setBossFX(enabled) {
      bossOn = !!enabled;
      bossFX.reset(bossFrame?.run, bossFrame?.bossEvents?.at(-1)?.id || 0);
    }, probeBossFX() {
      if(!bossFrame)return null;
      const memory=()=>({geometries:renderer.info.memory.geometries,textures:renderer.info.memory.textures});
      const before=memory(),temp=createBossFX(scene);
      temp.update(bossFrame,{viewWidth:1280,viewHeight:720,sinElev:.783},.028);
      renderer.render(scene,camera);const during=memory();
      temp.dispose();temp.dispose();renderer.render(scene,camera);
      return {before,during,after:memory(),disposed:temp.metrics().disposed};
    } } : {}),
    ...(query.has('test') ? { setWarningFX(enabled) {
      warningOn = !!enabled; warningDecals.reset();
    }, probeWarningFX() {
      if (!bossFrame && !skillFrame) return null;
      const frame = bossFrame || skillFrame;
      const memory = () => ({ geometries: renderer.info.memory.geometries, textures: renderer.info.memory.textures });
      const before = memory(), temp = createWarningDecals(scene);
      temp.update(frame, .028); renderer.render(scene, camera); const during = memory();
      temp.dispose(); temp.dispose(); renderer.render(scene, camera);
      return { before, during, after: memory(), disposed: temp.metrics().disposed };
    } } : {}),
    ...(query.has('test') ? { setPickupFX(enabled) {
      pickupOn = !!enabled; pickupDetails.reset(); prevO = null;
    }, probePickupFX() {
      if (!pickupFrame) return null;
      const memory = () => ({ geometries: renderer.info.memory.geometries, textures: renderer.info.memory.textures });
      const before = memory(), temp = createPickupDetails(scene);
      // 独立的两帧资源探针，确保尾迹实际上传 / 绘制；不改真实 O 池或随机流。
      const O = { max: 1, a: [1], kind: [0], x: [pickupFrame.camera.x + 150],
        y: [pickupFrame.camera.y], age: [1], value: [18] };
      const sample = { ...pickupFrame, O, options: { quality: 'high', reducedMotion: false } };
      const native = { viewWidth: 1280, viewHeight: 720, sinElev: .783 }, at = pickupFrame.run.time;
      temp.update(sample, native, .028, true, true, at);
      O.x[0] -= 8; O.age[0] += 1 / 60;
      temp.update(sample, native, .028, true, true, at + 1 / 60);
      renderer.render(scene, camera); const during = memory(), rendered = temp.metrics().count;
      temp.dispose(); temp.dispose(); renderer.render(scene, camera);
      return { before, during, after: memory(), rendered, disposed: temp.metrics().disposed };
    } } : {}),
    ...(query.has('test') ? { setChestRewards(enabled) { rewardObjectsOn = !!enabled; }, probeChestRewards() {
      if (!pickupFrame?.P) return null;
      const memory = () => ({ geometries: renderer.info.memory.geometries, textures: renderer.info.memory.textures });
      const before = memory(), temp = createChestRewards(scene);
      const actor = pickupFrame.P, at = pickupFrame.run.time;
      const sample = { ...pickupFrame, pickupEvents: [{ id: 1, kind: 'chest', time: at - .4, owner: actor.uid ?? 0,
        x: actor.x, y: actor.y, rewards: { overclock: 8, energy: 20, shield: 12 } }] };
      temp.update(sample, rewardScale); renderer.render(scene, camera);
      const during = memory(), rendered = temp.metrics().active.length;
      temp.dispose(); temp.dispose(); renderer.render(scene, camera);
      return { before, during, after: memory(), rendered, disposed: temp.metrics().disposed };
    } } : {}),
    metrics: () => ({
      mode: 'hd', visible, error, glow: glowOn,
      presentation: presentation ? { ...presentation, state: flags.presentationState,
        ready: presentation.kind === 'battle' || !!(flags.presentation && displayActors.metrics().active === presentation.key && displayActor?.root.visible && displayActor.root.parent === scene) } : null,
      presentationActors: displayActors.metrics(),
      assets: Object.fromEntries([...assets].map(([k, r]) => [k, r.state + (r.count ? `:${r.count}` : '')])),
      heroes: heroActors.size, bosses: bossActors.size, shadows: shadowCount,
      afterimages: afterimages.filter(image => image.root.visible).length,
      trails: trailMesh.count, sparks: sparkMesh.count, env: env.metrics(),
      weaponFX: { ...weaponFX.metrics(), mode: heroWeaponOn ? 'hero' : 'legacy' },
      skillFX: { ...skillFX.metrics(), enabled: skillOn },
      bossFX: { ...bossFX.metrics(), enabled: bossOn },
      warningDecals: { ...warningDecals.metrics(), enabled: warningOn },
      pickupDetails: pickupDetails.metrics(),
      chestRewards: { ...chestRewards.metrics(), openings: openings.length, openingCapacity: OPEN_CAPACITY,
        openingAges: openings.map(o => o.age) },
      reflections: { region: reflectionId, mode: reflectionMode, ...reflections.metrics() },
      drawCalls: renderer.info.render.calls, renderedTriangles: renderer.info.render.triangles,
      geometries: renderer.info.memory.geometries, gpuTextures: renderer.info.memory.textures,
      ...measure, renderMsMean: measure.frames ? measure.renderMsTotal / measure.frames : 0,
      resolution: [canvas.width, canvas.height],
    }),
  };
}
