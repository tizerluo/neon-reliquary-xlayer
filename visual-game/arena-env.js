// 场地环境层：地面、边界建筑、彩窗光柱画在一块独立的 three.js 画布上，叠放在原生画布**下面**。
// 场地加载完成后原生渲染器不再画地面和场景物件、背景透明（见 src/renderer.js 的 envOn），
// 于是层次从下到上是：场地 → 原生（敌弹、预警圈、技能光效）→ 高清角色画布。玩法信息永远不会被场景盖住。
import * as THREE from 'three';
import { battleEnvironment, createGlow, glowWeight, tuneMaterial } from './glow.js';
import { AMBIENT, createAmbient } from './arena-ambient.js';
import { createHeatHaze } from './arena-heat.js';
import { createRegionReflections } from './arena-reflections.mjs';

// run.stage 0–3 对应的区域；没有模型的区域自动回落原生地面
export const ARENAS = ['cathedral', 'archive', 'foundry', 'throne'];
const MOOD = [0x70bdca, 0x9ab7dd, 0xd8986d, 0xb89ccd];
const FOG = 0x05080d;

export function createArenaEnv(app, loader, assetUrl, camera, store = null) {
  const query = new URLSearchParams(location.search);
  const disabled = query.get('arena') === '0';
  const ambientOn = query.get('ambient') !== '0';
  const game = app.querySelector('#game');
  const canvas = document.createElement('canvas');
  canvas.id = 'visualArena';
  canvas.setAttribute('aria-hidden', 'true');
  Object.assign(canvas.style, { position: 'absolute', inset: '0', width: '100%', height: '100%', pointerEvents: 'none',
    display: 'none' });
  app.insertBefore(canvas, game || app.firstChild);
  // 暗角盖在场地上、原生画布下：原生后处理的暗角只作用于它自己画的东西
  const vignette = document.createElement('div');
  Object.assign(vignette.style, { position: 'absolute', inset: '0', pointerEvents: 'none', display: 'none',
    background: 'radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 42%, rgba(2,4,8,0.5) 100%)' });
  app.insertBefore(vignette, game || canvas.nextSibling);

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance',
    preserveDrawingBuffer: query.has('capture') });
  renderer.setPixelRatio(1);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;
  renderer.info.autoReset = false;
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(FOG);
  // 与原生着色器一致：离眼睛 28 单位开始起雾，到 100 单位基本融进背景
  scene.fog = new THREE.Fog(FOG, 40, 115);
  scene.environmentIntensity = 0.3;
  scene.add(new THREE.HemisphereLight(0x9fb6c8, 0x080b12, 0.35));
  // 地面占画面七成：灯光压低，让角色、飞剑和红色预警在上面跳出来
  const key = new THREE.DirectionalLight(0xe6eeff, 0.9);
  key.position.set(-24, 40, 20);
  scene.add(key);
  const rim = new THREE.DirectionalLight(0x70bdca, 0.45);
  rim.position.set(18, 24, -32);
  scene.add(rim);
  const glow = createGlow(renderer, scene, camera, { strength: 0.6, radius: 0.5, weight: glowWeight, followEmission: true });
  const envMaps = new Map();
  const reflections = createRegionReflections(renderer);
  let regionReflectionsOn = query.get('reflections') !== 'studio';

  function reflect(id) {
    const regional = regionReflectionsOn ? reflections.get(id) : null;
    const mood = MOOD[ARENAS.indexOf(id)] ?? MOOD[0];
    if (!regional && !envMaps.has(id)) envMaps.set(id, battleEnvironment(renderer, mood, 1));
    scene.environment = regional || envMaps.get(id);
  }

  const arenas = new Map();   // id -> { state, root }
  let shown = null, ambient = null, heat = null, stage = -1, error = null;
  function request(id, priority = 0) {
    if (arenas.has(id)) { const rec = arenas.get(id); rec.priority = Math.min(rec.priority ?? 0, priority); return rec; }
    const prepare = async gltf => {
      const rec = {};
      const root = gltf.scene;
      root.traverse(o => {
        if (!o.isMesh) return;
        o.matrixAutoUpdate = false;
        for (const m of [].concat(o.material)) tuneMaterial(m, 'arena');
      });
      root.updateMatrixWorld(true);
      rec.root = root;
      // 氛围与折射分别初始化；任一初始化失败都不影响场地或上层战斗信息。
      try {
        rec.ambient = ambientOn && AMBIENT[id] ? createAmbient(root, AMBIENT[id]) : null;
      } catch (e) {
        rec.ambient = null;   // 氛围层失败不影响场地本身
        rec.ambientError = String(e);
        console.warn('arena ambient', e);
      }
      try {
        rec.heat = ambientOn && AMBIENT[id]?.heat ? createHeatHaze(renderer, camera, root, AMBIENT[id].heat) : null;
      } catch (e) {
        rec.heatError = String(e);
        console.warn('arena heat', e);
      }
      await renderer.compileAsync(root, camera, scene);
      await glow.prepare(root);
      return rec;
    };
    const rec = store ? store.load('arena:' + id, `arenas/${id}.glb`, prepare, priority) : { state: 'loading' };
    arenas.set(id, rec);
    if (!store) loader.load(assetUrl(`arenas/${id}.glb`), gltf => {
      prepare(gltf).then(result => Object.assign(rec, result, { state: 'ready' }), () => { rec.state = 'missing'; });
    }, undefined, () => { rec.state = 'missing'; });
    return rec;
  }

  // 每帧在原生渲染之前调用：返回本帧是否由场地层负责地面（决定原生是否透明）
  function want(frame, visible, displayStage) {
    if (disabled || error || !visible || (!frame.run && displayStage == null)) return false;
    // ?arenaid=xxx 强制使用某个场地文件（预览 / 测试用）
    const s = displayStage ?? frame.run?.stage ?? 0, id = query.get('arenaid') || ARENAS[s];
    const rec = id ? request(id) : null;
    if (rec?.state !== 'ready') return false;
    if (s !== stage || shown !== rec.root) {
      stage = s;
      if (shown) scene.remove(shown);
      if (ambient) scene.remove(ambient.object);
      shown = rec.root;
      ambient = rec.ambient;
      heat = rec.heat;
      scene.add(shown);
      if (ambient) scene.add(ambient.object);
      const mood = MOOD[ARENAS.indexOf(id)] ?? MOOD[0];
      reflect(id);
      rim.color.setHex(mood);
    }
    return true;
  }

  function render(active, native, glowOn) {
    canvas.style.display = vignette.style.display = active ? 'block' : 'none';
    if (!active) return;
    const width = native.canvas.clientWidth, height = native.canvas.clientHeight;
    if (canvas.width !== width || canvas.height !== height) {
      renderer.setSize(width, height, false);
      glow.setSize(width, height);
    }
    try {
      renderer.info.reset();
      const now = performance.now() / 1000;
      if (ambient) ambient.update(now, height);
      renderer.render(scene, camera);
      if (glowOn) glow.render();
      if (heat) {
        try { heat.render(now); }
        catch (e) {
          const rec = arenas.get(query.get('arenaid') || ARENAS[stage]);
          rec.heatError = String(e);
          heat.dispose(); rec.heat = heat = null;
          console.warn('arena heat', e);
        }
      }
    } catch (e) {
      error = String(e);
      canvas.style.display = vignette.style.display = 'none';
    }
  }

  return {
    want, render,
    prefetch: stage => !disabled && !error && ARENAS[stage] ? request(ARENAS[stage], 2) : null,
    assetState(displayStage) {
      if (disabled) return 'disabled';
      if (error) return 'missing';
      return arenas.get(query.get('arenaid') || ARENAS[displayStage])?.state || 'loading';
    },
    setReflections(mode) {
      regionReflectionsOn = mode !== 'studio';
      const id = query.get('arenaid') || ARENAS[stage];
      if (shown && id) reflect(id);
    },
    metrics: () => ({ stage, error, arenas: Object.fromEntries([...arenas].map(([k, r]) => [k, r.state])),
      drawCalls: renderer.info.render.calls, triangles: renderer.info.render.triangles,
      ambient: ambient ? ambient.stats : null, heat: heat ? heat.stats : null,
      reflections: { region: query.get('arenaid') || ARENAS[stage] || null, ...reflections.metrics() },
      atmosphereErrors: Object.fromEntries([...arenas].filter(([, r]) => r.heatError || r.ambientError)
        .map(([k, r]) => [k, { ambient: r.ambientError || null, heat: r.heatError || null }])) }),
  };
}
