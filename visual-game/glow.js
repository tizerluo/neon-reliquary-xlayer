// 透明叠加画布共用的渲染工具：纯加色混合、选择性辉光、径向渐变贴图、影棚反射、材质标定。
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { FullScreenQuad } from 'three/addons/postprocessing/Pass.js';

// 颜色叠加到下方游戏画面，画布 alpha 不变，不会压暗敌人和地面
export const ADDITIVE = { blending: THREE.CustomBlending, blendSrc: THREE.SrcAlphaFactor, blendDst: THREE.OneFactor,
  blendSrcAlpha: THREE.ZeroFactor, blendDstAlpha: THREE.OneFactor };

// 选择性辉光：半分辨率只渲染自发光部件（其余涂黑保留遮挡），模糊后加色叠回画布
export function createGlow(renderer, scene, camera, settings) {
  const composer = new EffectComposer(renderer);
  composer.renderToScreen = false;
  composer.setPixelRatio(0.5);
  composer.addPass(new RenderPass(scene, camera));
  const bloom = new UnrealBloomPass(new THREE.Vector2(1, 1), settings.strength, settings.radius, 0);
  composer.addPass(bloom);
  const dark = new THREE.MeshBasicMaterial({ color: 0x000000 });
  const swaps = new Map(), swapped = [];
  const glowMaterial = m => {
    // 自带加色材质的特效（飞剑拖尾、命中火花）在辉光通道里原样渲染
    if (m.userData.glowSelf) return m;
    if (!swaps.has(m)) {
      const lit = m.emissive && m.emissiveIntensity > 0 && (m.emissiveMap || m.emissive.getHex() !== 0);
      swaps.set(m, lit && m.userData.createGlowMaterial ? m.userData.createGlowMaterial(settings.weight(m.name || '', m)) : lit ? new THREE.MeshBasicMaterial({ map: m.emissiveMap || null,
        color: m.emissive.clone().multiplyScalar(m.emissiveIntensity * settings.weight(m.name || '', m)) }) : dark);
    }
    const result = swaps.get(m);
    if (settings.followEmission && result !== dark) {
      result.color.copy(m.emissive).multiplyScalar(m.emissiveIntensity * settings.weight(m.name || '', m));
    }
    return result;
  };
  // 辉光是线性 HDR，先做指数压缩再轻微提亮，避免暗部被伽马抬成一层雾
  const quad = new FullScreenQuad(new THREE.ShaderMaterial({
    uniforms: { tGlow: { value: null } },
    vertexShader: 'varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
    fragmentShader: 'uniform sampler2D tGlow; varying vec2 vUv;'
      + 'void main() { vec3 c = 1.0 - exp(-texture2D(tGlow, vUv).rgb); gl_FragColor = vec4(pow(c, vec3(0.8)), 0.0); }',
    ...ADDITIVE, blendSrc: THREE.OneFactor, depthTest: false, depthWrite: false,
  }));
  let postReady = false;
  return {
    setSize: (width, height) => composer.setSize(width, height),
    async prepare(root) {
      // 在加载阶段编译辉光材质与全屏通道；不改正在显示的场景材质。
      const warm = new THREE.Scene(), materials = new Set();
      root.traverse(o => {
        if (!o.isMesh || o.userData.noGlow) return;
        const list = [].concat(o.material), lit = list.map(glowMaterial);
        if (lit.every(m => materials.has(m))) return;
        lit.forEach(m => materials.add(m));
        const mesh = o.clone(false); mesh.material = Array.isArray(o.material) ? lit : lit[0]; warm.add(mesh);
      });
      await renderer.compileAsync(warm, camera);
      if (postReady) return;
      const geometry = new THREE.PlaneGeometry(2, 2), post = new THREE.Scene();
      post.add(new THREE.Mesh(geometry, [bloom.materialHighPassFilter, ...bloom.separableBlurMaterials,
        bloom.compositeMaterial, bloom.blendMaterial]));
      const previous = renderer.getRenderTarget();
      let pending;
      try {
        renderer.setRenderTarget(composer.readBuffer);
        pending = renderer.compileAsync(post, camera);
      } finally { renderer.setRenderTarget(previous); }
      await pending;
      post.children[0].material = quad.material;
      await renderer.compileAsync(post, camera);
      geometry.dispose(); postReady = true;
    },
    render() {
      scene.traverse(o => {
        if (o.userData.noGlow && o.visible) {
          swapped.push(o, null);
          o.visible = false;
        } else if (o.isMesh) {
          swapped.push(o, o.material);
          o.material = glowMaterial(o.material);
        }
      });
      composer.render();
      for (let i = 0; i < swapped.length; i += 2) {
        if (swapped[i + 1]) swapped[i].material = swapped[i + 1];
        else swapped[i].visible = true;
      }
      swapped.length = 0;
      quad.material.uniforms.tGlow.value = composer.readBuffer.texture;
      const autoClear = renderer.autoClear;
      renderer.autoClear = false;
      renderer.setRenderTarget(null);
      quad.render(renderer);
      renderer.autoClear = autoClear;
    },
  };
}

export function radialTexture(stops) {
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = 128;
  const g = canvas.getContext('2d'), grad = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  for (const [at, color] of stops) grad.addColorStop(at, color);
  g.fillStyle = grad;
  g.fillRect(0, 0, 128, 128);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

// 战斗镜头从 +Z 高处俯视：影棚柔光箱放在镜头一侧，主题色 / 冷色灯条在身后勾边
export function battleEnvironment(renderer, accent = 0x8b5cf6, bright = 1) {
  const env = new THREE.Scene();
  env.background = new THREE.Color(0x020205);
  const panel = (w, h, color, gain, pos) => {
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(w, h),
      new THREE.MeshBasicMaterial({ color: new THREE.Color(color).multiplyScalar(gain), side: THREE.DoubleSide }));
    mesh.position.set(...pos);
    mesh.lookAt(0, 1, 0);
    env.add(mesh);
  };
  panel(6 * bright, 3 * bright, 0xece6ff, 1.5 * bright, [0, 6, 3]);
  panel(1.2, 7, accent, 3.2, [-4.5, 2, -3]);
  panel(1.2, 7, 0x2ee6ff, 2.0, [4.5, 2, -3]);
  panel(8, 1.4, 0x3b2a66, 1.1, [0, 0.4, 6]);
  if (bright > 1) panel(10, 4, 0xdfe6ff, 0.5 * bright, [0, 2.4, 7]);
  const pmrem = new THREE.PMREMGenerator(renderer);
  const texture = pmrem.fromScene(env, 0.035).texture;
  pmrem.dispose();
  return texture;
}

// 图鉴同款材质标定：按材质名关键字设反射强度、补回 sheen 权重、校准发光
export function tuneMaterial(m, id = '') {
  const n = (m.name || '').toLowerCase();
  m.envMapIntensity = /glass|visor|mask|crystal|ice/.test(n) ? 1.6 : /obsidian|lacquer|enamel/.test(n) ? 1.2
    : /silver|platinum|steel|chrome/.test(n) ? 0.7 : /brass|gold|bronze|copper/.test(n) ? 0.75
      : /velvet|tabard|robe|cloth|cape|silk|satin|lining|banner/.test(n) ? 0.35 : /suit|leather/.test(n) ? 0.45 : 0.8;
  if (m.sheenColor && m.sheen > 0) m.sheenColor.multiplyScalar(/lining/.test(n) ? 0.3 : 0.12);
  if (id === 'nyx') {
    if (n.includes('lining')) { m.color.multiplyScalar(0.5); m.roughness = 0.7; }
    if (n.includes('halo')) { m.color.setRGB(0.42, 0.40, 0.48); m.metalness = 1; m.roughness = 0.26; }
  }
  // 叠加画布的辉光比展示页弱，发光件略提亮，俯视距离下仍能读出光缝与核心
  if (m.emissive && (m.emissive.getHex() !== 0 || m.emissiveMap)) {
    m.emissiveIntensity *= /core|glow/.test(n) ? 1.2 : /hem/.test(n) ? 1.1 : /inlay/.test(n) ? 1.4 : 1.1;
  }
}

export function glowWeight(name, m) {
  const n = name.toLowerCase();
  if (m.emissiveMap) return 0.12;
  if (/core|glow|eye|heart|slit/.test(n)) return 0.5;
  if (/hem/.test(n)) return 0.3;
  if (/inlay|circuit|rune|vein|seam/.test(n)) return 0.25;
  return 0.06;
}
