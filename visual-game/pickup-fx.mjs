// 碎片亮度、真实吸取尾迹与瓶内流光：同一场景 / 时间 / 实例批次，不创建逐道具材质。
import * as THREE from 'three';
import { ADDITIVE } from './glow.js';
import { createPickupHistory, pickupStyle, PICKUP_TRAIL_LIFE } from './pickup-fx-data.mjs';

const CAPACITY = 2800, LOW_CAPACITY = 420;
const CYAN = new THREE.Color('#86d9e6');

// Standard 与其选择性辉光副材质读取同一实例属性，亮度与流光不会只出现在一个通道。
function patchMaterial(material, kind, uniforms, basic = false) {
  material.onBeforeCompile = shader => {
    Object.assign(shader.uniforms, uniforms);
    shader.vertexShader = 'attribute float pickupGain; attribute float pickupPhase;\n'
      + 'varying float nrPickupGain; varying float nrPickupPhase; varying vec3 nrPickupLocal;\n' + shader.vertexShader;
    shader.vertexShader = shader.vertexShader.replace('#include <begin_vertex>',
      '#include <begin_vertex>\nnrPickupGain=pickupGain; nrPickupPhase=pickupPhase; nrPickupLocal=position;');
    const flow = kind === 1 ? `
      float a=atan(nrPickupLocal.z,nrPickupLocal.x);
      float phase=nrPickupLocal.y*18.0-a*1.6-nrPickupTime*1.65+nrPickupPhase;
      float band=pow(.5+.5*sin(phase),5.0);
      float fine=pow(.5+.5*sin(phase*1.7+.8),12.0)*nrPickupFine*.15;
      float liquid=.36+.76*band+fine;
      return mix(1.0,liquid,nrPickupEnabled);
    ` : 'return mix(1.0,nrPickupGain,nrPickupEnabled);';
    shader.fragmentShader = 'uniform float nrPickupTime; uniform float nrPickupFine; uniform float nrPickupEnabled;\n'
      + 'varying float nrPickupGain; varying float nrPickupPhase; varying vec3 nrPickupLocal;\n'
      + `float nrPickupLight(){${flow}}\n` + shader.fragmentShader;
    shader.fragmentShader = basic
      ? shader.fragmentShader.replace('#include <opaque_fragment>', 'outgoingLight*=nrPickupLight();\n#include <opaque_fragment>')
      : shader.fragmentShader.replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\ntotalEmissiveRadiance*=nrPickupLight();');
  };
  material.customProgramCacheKey = () => `nr-pickup-${kind}-${basic ? 'glow' : 'pbr'}`;
  material.needsUpdate = true;
}

export function createPickupDetails(scene) {
  const history = createPickupHistory();
  const uniforms = { nrPickupTime: { value: 0 }, nrPickupFine: { value: 1 }, nrPickupEnabled: { value: 1 } };
  const position = new Float32Array(CAPACITY * 18), color = new Float32Array(CAPACITY * 18);
  const uv = new Float32Array(CAPACITY * 12);
  const geometry = new THREE.BufferGeometry();
  for (const [name, array, size] of [['position', position, 3], ['color', color, 3], ['uv', uv, 2]])
    geometry.setAttribute(name, new THREE.BufferAttribute(array, size).setUsage(THREE.DynamicDrawUsage));
  geometry.setDrawRange(0, 0);
  const material = new THREE.ShaderMaterial({
    vertexShader: 'varying vec2 vUv; varying vec3 vColor; attribute vec3 color; void main(){vUv=uv;vColor=color;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
    fragmentShader: 'varying vec2 vUv; varying vec3 vColor; void main(){float side=abs(vUv.y-.5)*2.0;float body=pow(1.0-side,2.0);float core=1.0-smoothstep(.06,.22,side);float a=(body*.28+core*.55)*pow(1.0-vUv.x,.65);gl_FragColor=vec4(vColor,a);}',
    transparent: true, depthWrite: false, depthTest: true, side: THREE.DoubleSide,
    forceSinglePass: true, toneMapped: false, ...ADDITIVE,
    blendSrcAlpha: THREE.OneFactor, blendDstAlpha: THREE.OneMinusSrcAlphaFactor,
  });
  // 尾迹只靠自身细亮芯，不进辉光，避免上百个拾取物糊成青雾。
  const mesh = new THREE.Mesh(geometry, material); mesh.name = 'Pickup absorption trails';
  mesh.userData.noGlow = true; mesh.renderOrder = 2; mesh.frustumCulled = false; mesh.visible = false; scene.add(mesh);
  const decorated = new WeakSet();
  let count = 0, disposed = false, active = [], tierCounts = [0, 0, 0], low = false, reduced = false;
  function configure(rec, kind) {
    if (kind > 1) return;
    for (const part of rec.parts) {
      // 700 是真实 O 池上限，与 growParts 扩容共用，不能把属性留在旧容量。
      if (!part.geo.getAttribute('pickupGain')) {
        part.geo.setAttribute('pickupGain', new THREE.InstancedBufferAttribute(new Float32Array(700).fill(1), 1).setUsage(THREE.DynamicDrawUsage));
        part.geo.setAttribute('pickupPhase', new THREE.InstancedBufferAttribute(new Float32Array(700), 1).setUsage(THREE.DynamicDrawUsage));
      }
      for (const m of [].concat(part.mat)) {
        if (decorated.has(m) || !m.emissive || m.emissive.getHex() === 0) continue;
        decorated.add(m); patchMaterial(m, kind, uniforms);
        m.userData.createGlowMaterial = weight => {
          const glowing = new THREE.MeshBasicMaterial({ map: m.emissiveMap || null,
            color: m.emissive.clone().multiplyScalar(m.emissiveIntensity * weight) });
          patchMaterial(glowing, kind, uniforms, true); return glowing;
        };
      }
    }
  }
  function instance(rec, n, slot, value, kind) {
    const gain = kind === 0 ? pickupStyle(value).emission : 1;
    for (const part of rec.parts) {
      part.geo.getAttribute('pickupGain').setX(n, gain);
      part.geo.getAttribute('pickupPhase').setX(n, slot * 2.399963);
    }
  }
  function flush(rec) {
    for (const p of rec.parts) for (const key of ['pickupGain', 'pickupPhase']) p.geo.getAttribute(key).needsUpdate = true;
  }
  function segment(a, b, width, y, gain) {
    const dx = b.x - a.x, dz = b.z - a.z, length = Math.hypot(dx, dz);
    if (length < .008) return;
    const nx = -dz / length * width / 2, nz = dx / length * width / 2;
    const points = [[a.x + nx, y, a.z + nz], [a.x - nx, y, a.z - nz],
      [b.x + nx * .32, y, b.z + nz * .32], [b.x - nx * .32, y, b.z - nz * .32]];
    const order = [0, 1, 2, 2, 1, 3], tex = [[0, 0], [0, 1], [1, 0], [1, 1]];
    for (let k = 0; k < 6; k++) {
      const index = count * 18 + k * 3, p = points[order[k]], u = tex[order[k]];
      position.set(p, index); color.set([CYAN.r * gain, CYAN.g * gain, CYAN.b * gain], index);
      uv.set(u, count * 12 + k * 2);
    }
    count++;
  }
  function update(frame, native, S, ready, enabled = true, time = frame.run?.time ?? 0, systemReduced = false) {
    if (disposed) return;
    low = frame.options?.quality === 'low'; reduced = frame.options?.reducedMotion === true || systemReduced;
    uniforms.nrPickupTime.value = reduced ? 0 : time;
    uniforms.nrPickupFine.value = low ? 0 : 1; uniforms.nrPickupEnabled.value = enabled ? 1 : 0;
    const states = history.update(frame, time); count = 0; active = []; tierCounts = [0, 0, 0];
    const limit = low ? LOW_CAPACITY : CAPACITY, halfW = (native.viewWidth ?? 1280) / 2 + 100;
    const halfH = (native.viewHeight ?? 720) / (2 * (native.sinElev ?? .8)) + 100;
    for (const state of states) {
      tierCounts[state.tier]++;
      if (!enabled || reduced || !ready || state.points.length < 2) continue;
      const ps = state.points.slice(-(low ? 3 : 5)).reverse();
      for (let i = 0; i < ps.length - 1 && count < limit; i++) {
        const a = ps[i], b = ps[i + 1];
        if (frame.camera && Math.abs(a.x - frame.camera.x) > halfW && Math.abs(b.x - frame.camera.x) > halfW) continue;
        if (frame.camera && Math.abs(a.y - frame.camera.y) > halfH && Math.abs(b.y - frame.camera.y) > halfH) continue;
        const fade = Math.max(0, 1 - (time - a.time) / PICKUP_TRAIL_LIFE);
        if (fade <= 0) continue;
        const head = { x: a.x * S, z: a.y * S }, tail = { x: b.x * S, z: b.y * S };
        segment(head, tail, .12 * state.scale * (1 - i * .12), .45 * state.scale, fade * .56 * state.emission);
      }
      if (active.length < 12) active.push({ index: state.index, tier: state.tier, emission: state.emission, points: ps.map(p => [p.x, p.y, p.time]) });
    }
    geometry.setDrawRange(0, count * 6); mesh.visible = count > 0;
    for (const attr of Object.values(geometry.attributes)) attr.needsUpdate = true;
  }
  function reset() { history.reset(); count = 0; active = []; tierCounts = [0, 0, 0]; mesh.visible = false; geometry.setDrawRange(0, 0); }
  function dispose() { if (disposed) return; disposed = true; reset(); scene.remove(mesh); geometry.dispose(); material.dispose(); }
  return { configure, instance, flush, update, reset, dispose, metrics: () => ({ count, capacity: CAPACITY,
    lowCapacity: LOW_CAPACITY, tracked: history.size(), tierCounts: [...tierCounts], active, low, reducedMotion: reduced,
    time: uniforms.nrPickupTime.value, fine: uniforms.nrPickupFine.value, enabled: uniforms.nrPickupEnabled.value === 1, disposed }) };
}
