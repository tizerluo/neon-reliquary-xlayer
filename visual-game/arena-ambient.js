// 四区网页氛围：微尘、贴地冷雾与冰晶、火星、星尘与嵌线呼吸。
// 独立场地画布位于原生预警 / 敌弹 / 高清角色下方，粒子不写深度。
import * as THREE from 'three';
import { radialTexture } from './glow.js';
import { collectSurface, seededRandom } from './arena-surface.mjs';

// r2 终审：r1 的大教堂 / 档案馆 / 王座氛围在实战截图里平均每像素只变 0.1–0.4 / 255，等于看不见；
// 王座星尘只从场外静态星点出生，战区里没有。r2 让每区效果在游戏机位下能被看到，但仍压在角色与预警之下。
export const AMBIENT = {
  cathedral: {
    from: /floor mosaic|emblem mosaic/i, kind: 'dust', seed: 719,
    bounds: [-42, 42, -38, 38], yRange: [-0.01, 0.1],
    // 暖白为主，少量带彩窗青 / 玫瑰色的微尘，像彩窗光里浮着的灰
    count: 300, color: 0xd8ccb2, palette: [0xd8ccb2, 0xd8ccb2, 0xd8ccb2, 0x9fd8e0, 0xe0a8c4],
    height: [0.35, 5.5],
    rise: [0.03, 0.12], life: [8, 16], size: 4.2, gain: 1.6,
    drift: 0.32, sway: 0.16, cooling: [0, 0], fade: 'float', flicker: 0.65,
    // 地面星座细线做缓慢的明暗起伏（±18%），彩窗 / 光柱不动
    pulse: /circuit trace/i, pulseRate: 0.45, pulseDepth: 1.8,
    // 彩窗投下的青 / 玫瑰光斑在地面上缓慢游移、明灭（加色、柔边、不进辉光）
    pools: {
      from: /floor mosaic/i, bounds: [-40, 40, -36, 36], yRange: [-0.01, 0.1],
      count: 9, palette: [0x3fb8c8, 0x3fb8c8, 0xc8508c], opacity: 0.12, seed: 727,
      additive: true, breakup: 0.25, width: [9, 14], depth: [5, 8], life: [16, 28], wind: 0.6,
    },
  },
  archive: {
    from: /floor ice|ice crust|snow drift/i, kind: 'iceglints', seed: 733,
    bounds: [-47, 47, -43, 43], yRange: [-0.01, 1.8],
    // 冰晶闪光：亮的时间只占寿命的一小段，所以数量要多，画面里同时才有二十来颗在闪
    count: 760, color: 0xdce9fb, height: [0.025, 0.12],
    rise: [0, 0], life: [2.5, 6], size: 8, gain: 1.9, glintWidth: 0.12,
    drift: 0.02, sway: 0, cooling: [0, 0], fade: 'glint',
    pulse: /rune trace/i, pulseRate: 0.6, pulseDepth: 1.6,
    fog: {
      from: /floor ice|snow drift/i, bounds: [-42, 42, -38, 38], yRange: [-0.01, 0.55],
      count: 22, color: 0xa3b6cc, opacity: 0.15, seed: 739,
    },
  },
  foundry: {
    from: /molten amber|furnace amber/i,
    count: 280, color: 0xffa040,
    rise: [0.9, 2.4], life: [2.0, 4.2], size: 4.4, gain: 1.5,
    pulse: /molten|furnace amber/i,
    heat: { from: /molten amber|furnace amber/i, count: 28, maxPixels: 0.85, seed: 751 },
  },
  throne: {
    // 星尘主要从虚空裂隙里缓缓升起（裂缝面积远大于场外星点），场外星点仍偶尔飘起一颗
    from: /null rift|astral dust/i, kind: 'stardust', seed: 761,
    count: 460, color: 0xbab4ec, palette: [0xbab4ec, 0xbab4ec, 0xdcdcf6],
    rise: [0.22, 0.6], life: [3.5, 7.0], size: 4.6, gain: 1.8,
    drift: 0.22, sway: 0.10, cooling: [0.15, 0],
    // 王座心跳：纹章先跳，电路晚 0.5 s、裂隙晚 1.0 s，像一道从中心向外的脉冲；双拍包络
    beat: {
      period: 4.2, lo: 0.9, amp: 0.6,
      groups: [[/throne inlay/i, 0], [/null circuit|obelisk inlay/i, 0.5], [/null rift/i, 1.0]],
    },
  },
};

let sprite = null, glintSprite = null;
function crystalTexture() {
  if (glintSprite) return glintSprite;
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = 128;
  const g = canvas.getContext('2d'), grad = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  for (const [at, alpha] of [[0, 1], [0.12, 0.9], [0.48, 0.28], [1, 0]]) {
    grad.addColorStop(at, 'rgba(255,255,255,' + alpha + ')');
  }
  g.fillStyle = grad;
  g.beginPath();
  for (const [i, p] of [[64, 3], [71, 57], [118, 64], [71, 71], [64, 125], [57, 71], [10, 64], [57, 57]].entries()) {
    if (i === 0) g.moveTo(...p); else g.lineTo(...p);
  }
  g.closePath(); g.fill();
  glintSprite = new THREE.CanvasTexture(canvas);
  glintSprite.colorSpace = THREE.SRGBColorSpace;
  return glintSprite;
}

// 贴地薄层：档案馆冷雾（普通混合、噪声撕碎边缘），或大教堂彩窗光斑（加色、柔和椭圆、按调色板着色）。
function createMist(root, cfg) {
  const surface = collectSurface(root, cfg);
  if (!surface.total) return null;
  const N = cfg.count, rng = seededRandom(cfg.seed);
  const geo = new THREE.PlaneGeometry(1, 1);
  const fade = new Float32Array(N), phase = new Float32Array(N), hue = new Float32Array(N * 3);
  geo.setAttribute('mistFade', new THREE.InstancedBufferAttribute(fade, 1).setUsage(THREE.DynamicDrawUsage));
  geo.setAttribute('mistPhase', new THREE.InstancedBufferAttribute(phase, 1));
  geo.setAttribute('mistColor', new THREE.InstancedBufferAttribute(hue, 3));
  const palette = (cfg.palette || [cfg.color]).map(c => new THREE.Color(c));
  const [w0, w1] = cfg.width || [12, 18], [d0, d1] = cfg.depth || [4, 7], [l0, l1] = cfg.life || [14, 26];
  const wind = cfg.wind ?? 1;
  const mat = new THREE.ShaderMaterial({
    uniforms: { time: { value: 0 }, opacity: { value: cfg.opacity }, breakup: { value: cfg.breakup ?? 1 } },
    vertexShader: `
      attribute float mistFade;
      attribute float mistPhase;
      attribute vec3 mistColor;
      varying vec2 vUv;
      varying float vFade;
      varying float vPhase;
      varying vec3 vTint;
      void main() {
        vUv = uv; vFade = mistFade; vPhase = mistPhase; vTint = mistColor;
        gl_Position = projectionMatrix * modelViewMatrix * instanceMatrix * vec4(position, 1.0);
      }`,
    fragmentShader: `
      uniform float time;
      uniform float opacity;
      uniform float breakup;
      varying vec2 vUv;
      varying float vFade;
      varying float vPhase;
      varying vec3 vTint;
      float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
      float noise(vec2 p) {
        vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
        return mix(mix(hash(i), hash(i + vec2(1, 0)), f.x),
                   mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), f.x), f.y);
      }
      void main() {
        vec2 q = (vUv - 0.5) * 2.0;
        float edge = 1.0 - smoothstep(0.45, 1.0, length(q * vec2(1.0, 1.1)));
        vec2 p = vUv * vec2(5.0, 2.8) + vec2(vPhase + time * 0.035, vPhase * 0.7);
        float n = 0.65 * noise(p) + 0.35 * noise(p * 2.1);
        float body = mix(1.0, smoothstep(0.22, 0.8, n), breakup);
        gl_FragColor = vec4(vTint, opacity * vFade * edge * body);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
    transparent: true, depthWrite: false, side: THREE.DoubleSide,
    blending: cfg.additive ? THREE.AdditiveBlending : THREE.NormalBlending,
  });
  const mesh = new THREE.InstancedMesh(geo, mat, N);
  mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  mesh.frustumCulled = false;
  mesh.matrixAutoUpdate = false;
  mesh.userData.noGlow = true; // 薄层只叠在场地上；不进入辉光，避免白幕。
  const origin = new Float32Array(N * 3), age = new Float32Array(N), life = new Float32Array(N);
  const width = new Float32Array(N), depth = new Float32Array(N), yaw = new Float32Array(N);
  const drift = new Float32Array(N * 2), point = new THREE.Vector3(), transform = new THREE.Object3D();
  function spawn(i, warm) {
    surface.sample(rng, point);
    origin.set([point.x, point.y + 0.14 + rng() * 0.18, point.z], i * 3);
    life[i] = l0 + rng() * (l1 - l0); age[i] = warm ? rng() * life[i] : 0;
    width[i] = w0 + rng() * (w1 - w0); depth[i] = d0 + rng() * (d1 - d0);
    yaw[i] = rng() * Math.PI * 2;
    drift[i * 2] = (0.08 + rng() * 0.1) * wind; drift[i * 2 + 1] = (rng() - 0.5) * 0.08 * wind;
    const c = palette[Math.floor(rng() * palette.length)];
    hue[i * 3] = c.r; hue[i * 3 + 1] = c.g; hue[i * 3 + 2] = c.b;
  }
  for (let i = 0; i < N; i++) { spawn(i, true); phase[i] = rng() * 30; }
  let colorsSent = false;
  return {
    object: mesh,
    stats: { patches: N, opacity: cfg.opacity, ...(cfg.additive ? { additive: true } : {}) },
    update(now, dt) {
      mat.uniforms.time.value = now;
      for (let i = 0; i < N; i++) {
        age[i] += dt;
        if (age[i] >= life[i]) { spawn(i, false); colorsSent = false; }
        fade[i] = Math.sin(Math.PI * age[i] / life[i]) ** 2;
        transform.position.set(origin[i * 3] + age[i] * drift[i * 2], origin[i * 3 + 1],
          origin[i * 3 + 2] + age[i] * drift[i * 2 + 1]);
        transform.rotation.set(-Math.PI / 2, yaw[i], 0, 'YXZ');
        transform.scale.set(width[i], depth[i], 1);
        transform.updateMatrix();
        mesh.setMatrixAt(i, transform.matrix);
      }
      mesh.instanceMatrix.needsUpdate = true;
      geo.attributes.mistFade.needsUpdate = true;
      if (!colorsSent) { geo.attributes.mistColor.needsUpdate = true; colorsSent = true; }
    },
    dispose() { geo.dispose(); mat.dispose(); },
  };
}

export function createAmbient(root, cfg) {
  const surface = collectSurface(root, cfg);
  if (!surface.total) return null;
  // 呼吸材质 → 初始强度；心跳材质 → [初始强度, 延迟秒]
  const pulsing = new Map(), beating = new Map();
  root.traverse(o => {
    if (!o.isMesh) return;
    for (const m of [].concat(o.material)) {
      const name = m.name || '';
      if (cfg.pulse) {
        cfg.pulse.lastIndex = 0;
        if (cfg.pulse.test(name) && !pulsing.has(m)) pulsing.set(m, m.emissiveIntensity);
      }
      for (const [re, delay] of cfg.beat?.groups || []) {
        re.lastIndex = 0;
        if (re.test(name) && !beating.has(m)) beating.set(m, [m.emissiveIntensity, delay]);
      }
    }
  });
  const N = cfg.count, rng = cfg.seed === undefined ? Math.random : seededRandom(cfg.seed);
  const geo = new THREE.BufferGeometry();
  const P = new Float32Array(N * 3), C = new Float32Array(N * 3);
  geo.setAttribute('position', new THREE.BufferAttribute(P, 3).setUsage(THREE.DynamicDrawUsage));
  geo.setAttribute('color', new THREE.BufferAttribute(C, 3).setUsage(THREE.DynamicDrawUsage));
  sprite ||= radialTexture([[0, 'rgba(255,255,255,1)'], [0.35, 'rgba(255,255,255,0.55)'], [1, 'rgba(255,255,255,0)']]);
  const mat = new THREE.PointsMaterial({ size: cfg.size, map: cfg.fade === 'glint' ? crystalTexture() : sprite,
    vertexColors: true, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    sizeAttenuation: false, fog: false });
  const points = new THREE.Points(geo, mat);
  points.frustumCulled = false;
  points.matrixAutoUpdate = false;
  const object = new THREE.Group();
  object.add(points);
  const mist = cfg.fog ? createMist(root, cfg.fog) : null;
  if (mist) object.add(mist.object);
  const pools = cfg.pools ? createMist(root, cfg.pools) : null;
  if (pools) object.add(pools.object);

  const point = new THREE.Vector3();
  const palette = (cfg.palette || [cfg.color]).map(c => new THREE.Color(c)), tint = new Float32Array(N * 3);
  const age = new Float32Array(N), life = new Float32Array(N), vy = new Float32Array(N);
  const drift = new Float32Array(N * 2), phase = new Float32Array(N), origin = new Float32Array(N * 3);
  const lerp = ([lo, hi]) => lo + rng() * (hi - lo);
  function spawn(i, warm) {
    surface.sample(rng, point);
    origin.set([point.x, point.y + (cfg.height ? lerp(cfg.height) : 0), point.z], i * 3);
    life[i] = lerp(cfg.life);
    age[i] = warm ? rng() * life[i] : 0;
    vy[i] = lerp(cfg.rise);
    drift[i * 2] = (rng() - 0.5) * (cfg.drift ?? 0.7);
    drift[i * 2 + 1] = (rng() - 0.5) * (cfg.drift ?? 0.7);
    phase[i] = rng() * Math.PI * 2;
    const c = palette[Math.floor(rng() * palette.length)];
    tint[i * 3] = c.r; tint[i * 3 + 1] = c.g; tint[i * 3 + 2] = c.b;
  }
  for (let i = 0; i < N; i++) spawn(i, true);
  let last = null;
  const reset = () => {
    last = null;
    for (const [m, i0] of pulsing) m.emissiveIntensity = i0;
    for (const [m, [i0]] of beating) m.emissiveIntensity = i0;
  };
  // 双拍心跳包络（0..1）：主拍 + 0.32 秒后较弱的第二拍，其余时间平静
  const beatEnv = t => {
    const T = cfg.beat.period, x = ((t % T) + T) % T;
    const pulse = (c, w) => Math.exp(-(((x - c) / w) ** 2)) + Math.exp(-(((x - c - T) / w) ** 2));
    return pulse(0.25, 0.16) + 0.55 * pulse(0.57, 0.14);
  };
  return {
    object,
    stats: {
      ...(cfg.kind ? { kind: cfg.kind, particles: N } : { embers: N }),
      emitArea: Math.round(surface.total), pulsing: pulsing.size + beating.size, ...(mist ? { fog: mist.stats } : {}), ...(pools ? { pools: pools.stats } : {}),
    },
    reset,
    update(now, height) {
      const dt = last === null ? 0 : Math.max(0, Math.min(0.1, now - last));
      last = now;
      mat.size = cfg.size * Math.max(0.6, height / 720);
      for (let i = 0; i < N; i++) {
        age[i] += dt;
        if (age[i] >= life[i]) spawn(i, false);
        const t = age[i], k = t / life[i];
        P[i * 3] = origin[i * 3] + drift[i * 2] * t + (cfg.sway ?? 0.25) * Math.sin(phase[i] + t * 2.1);
        P[i * 3 + 1] = origin[i * 3 + 1] + vy[i] * t * (1 - 0.25 * k);
        P[i * 3 + 2] = origin[i * 3 + 2] + drift[i * 2 + 1] * t + (cfg.sway ?? 0.25) * Math.cos(phase[i] + t * 1.7);
        const fade = cfg.fade === 'glint' ? Math.max(0, 1 - Math.abs(k - 0.55) / (cfg.glintWidth ?? 0.08)) ** 2
          : cfg.fade === 'float' ? Math.sin(Math.PI * k) * (0.78 + 0.22 * Math.sin(phase[i] + t * cfg.flicker))
            : Math.min(1, t / 0.2) * (1 - k) ** 2 * (0.75 + 0.25 * Math.sin(phase[i] + t * 13));
        const f = fade * (cfg.gain ?? 1);
        C[i * 3] = tint[i * 3] * f;
        C[i * 3 + 1] = tint[i * 3 + 1] * f * (1 - (cfg.cooling?.[0] ?? 0.35) * k);
        C[i * 3 + 2] = tint[i * 3 + 2] * f * (1 - (cfg.cooling?.[1] ?? 0.6) * k);
      }
      geo.attributes.position.needsUpdate = true;
      geo.attributes.color.needsUpdate = true;
      mist?.update(now, dt);
      pools?.update(now, dt);
      const pulseTime = now * (cfg.pulseRate ?? 1);
      // 铸造厂沿用 r1 的 0.92 基线；配置了 pulseDepth 的区域以原强度为中心上下起伏，平均亮度不变
      const breath = (cfg.pulseDepth ? 1 : 0.92)
        + (cfg.pulseDepth ?? 1) * (0.07 * Math.sin(pulseTime * 1.15) + 0.04 * Math.sin(pulseTime * 2.9 + 1.3));
      for (const [m, i0] of pulsing) m.emissiveIntensity = i0 * breath;
      for (const [m, [i0, delay]] of beating) m.emissiveIntensity = i0 * (cfg.beat.lo + cfg.beat.amp * beatEnv(now - delay));
    },
    dispose() { reset(); geo.dispose(); mat.dispose(); mist?.dispose(); pools?.dispose(); },
  };
}
