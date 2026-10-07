// 区域 IBL：反射的形状与方位来自彩窗、冰墙、炉口和虚空碑，不把整身角色染成一个主题色。
// 只在第一次进入区域时烘焙；角色与场地各自的 WebGL 上下文持有自己的 PMREM。
import * as THREE from 'three';

export const REFLECTION_REGIONS = {
  cathedral: { name: 'Stained glass / warm vault', background: 0x030608 },
  archive: { name: 'Ice walls / cold skylight', background: 0x04070d },
  foundry: { name: 'Amber furnace / iron vault', background: 0x090502 },
  throne: { name: 'Void obelisks / silver stars', background: 0x020206 },
};
const FOCUS = new THREE.Vector3(0, 1.4, 0);

// 可单独审图的辐射场；MeshBasicMaterial 的 gain 是线性 HDR 辐射，不是新增战斗光源。
export function reflectionScene(id) {
  const profile = REFLECTION_REGIONS[id];
  if (!Object.hasOwn(REFLECTION_REGIONS, id)) return null;
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(profile.background);
  const panel = (name, w, h, color, gain, position) => {
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({
      color: new THREE.Color(color).multiplyScalar(gain), side: THREE.DoubleSide,
    }));
    mesh.name = name;
    mesh.position.set(...position);
    mesh.lookAt(FOCUS);
    scene.add(mesh);
    return mesh;
  };
  // 中性的上方大光源保留金属本色；区域色由较小的侧面 / 低处光源落在曲面上。
  if (id === 'cathedral') {
    panel('warm vault', 6.5, 4.0, 0xf3ecda, 1.65, [0, 7.5, 3]);
    for (const side of [-1, 1]) {
      for (const [z, tint] of [[-3.2, 0x61c7d6], [2.6, 0xd886ad]]) {
        const window = panel('stained glass window', 2.6, 5.2, tint, 2.6, [side * 6, 2.8, z]);
        // 窗格铅条把高光分成数块，镜面上能读到彩窗，粗糙金属上融合为青 / 玫瑰边色。
        for (const y of [-1.6, 0, 1.6]) {
          const bar = new THREE.Mesh(new THREE.PlaneGeometry(2.6, 0.10),
            new THREE.MeshBasicMaterial({ color: 0x05080b, side: THREE.DoubleSide }));
          bar.position.set(0, y, 0.015); window.add(bar);
        }
      }
    }
    panel('mosaic bounce', 10, 8, 0x426574, 0.38, [0, -3, 0]);
    panel('stone aisle', 8, 1.4, 0xa9afa7, 0.42, [0, 0.1, 7]);
  } else if (id === 'archive') {
    panel('ice skylight', 6, 5, 0xe3f1ff, 1.9, [0, 7.5, 2]);
    for (const side of [-1, 1]) {
      panel('frosted ice wall', 3.5, 5.6, 0x85b5db, 1.6, [side * 6, 2.2, 1]);
      panel('ice rib', 0.55, 6.5, 0xd4ecff, 2.2, [side * 4.2, 2.7, -4]);
      panel('dark shelf', 3.6, 4, 0x182635, 0.42, [side * 5.5, 1, 6]);
    }
    panel('ice floor bounce', 11, 9, 0x4d709d, 0.48, [0, -3, 0]);
  } else if (id === 'foundry') {
    panel('neutral roof opening', 6, 4.5, 0xf2ece2, 1.65, [0, 7.5, 3]);
    for (const side of [-1, 1]) {
      panel('iron wall', 5, 6, 0x333943, 0.5, [side * 7, 2.5, 1]);
      panel('molten floor channel', 7, 0.8, 0xffa64c, 3.8, [side * 3.5, -2.2, 0]);
      panel('furnace mouth', 2.2, 1.7, 0xffb961, 3.0, [side * 6, -0.2, -4]);
      panel('furnace core', 0.9, 0.7, 0xffe0a1, 3.4, [side * 5.9, -0.15, -3.9]);
    }
    panel('iron floor', 10, 8, 0x36302c, 0.34, [0, -3.2, 1]);
  } else {
    panel('silver vault', 5.5, 3.5, 0xe6e8f6, 1.7, [0, 7.5, 3]);
    for (const side of [-1, 1]) {
      panel('obelisk inlay', 0.7, 6, 0xb1a4d6, 2.3, [side * 5.5, 2.3, -3]);
      panel('void rift', 4.5, 0.35, 0x9380bd, 1.8, [side * 3.8, -1.5, 2]);
      panel('dark marble', 4, 5, 0x242234, 0.35, [side * 7, 1.5, 3]);
    }
    for (let i = 0; i < 12; i++) {
      const angle = i * Math.PI * 2 / 12;
      panel('silver star', 0.14, 0.14, 0xe2e2fa, 5,
        [Math.cos(angle) * 6, 3.3 + (i % 3) * 1.4, Math.sin(angle) * 6]);
    }
    panel('void floor', 11, 9, 0x161222, 0.3, [0, -3, 0]);
  }
  scene.updateMatrixWorld(true);
  return scene;
}

export function disposeReflectionScene(scene) {
  scene.traverse(o => {
    if (!o.isMesh) return;
    o.geometry.dispose();
    for (const m of [].concat(o.material)) m.dispose();
  });
}

export function createRegionReflections(renderer) {
  const maps = new Map(), failures = new Map();
  let disposed = false;
  return {
    get(id) {
      if (disposed || !Object.hasOwn(REFLECTION_REGIONS, id) || failures.has(id)) return null;
      if (maps.has(id)) return maps.get(id).texture;
      const source = reflectionScene(id);
      const old = {
        target: renderer.getRenderTarget(), face: renderer.getActiveCubeFace(), mip: renderer.getActiveMipmapLevel(),
        toneMapping: renderer.toneMapping, autoClear: renderer.autoClear, xr: renderer.xr.enabled,
        color: renderer.getClearColor(new THREE.Color()).clone(), alpha: renderer.getClearAlpha(),
        viewport: renderer.getViewport(new THREE.Vector4()), scissor: renderer.getScissor(new THREE.Vector4()),
        scissorTest: renderer.getScissorTest(),
      };
      const pmrem = new THREE.PMREMGenerator(renderer);
      let target;
      const start = performance.now();
      try {
        // 128 px / cube face 已足够游戏距离下的宽高光；4 张 RGBA16F CubeUV 约 6 MiB / 上下文。
        target = pmrem.fromScene(source, 0.025, 0.1, 40, { size: 128, position: FOCUS });
        target.texture.name = `reflection:${id}`;
        maps.set(id, { target, texture: target.texture, ms: performance.now() - start });
        return target.texture;
      } catch (e) {
        target?.dispose();
        failures.set(id, String(e));
        console.warn('region reflection', id, e);
        return null; // 上层保留影棚反射，单区烘焙失败不让角色或场地消失。
      } finally {
        pmrem.dispose();
        disposeReflectionScene(source);
        // PMREM 正常会还原状态；失败路径也显式还原，避免污染后续透明画布或热浪。
        renderer.setRenderTarget(old.target, old.face, old.mip);
        renderer.setViewport(old.viewport);
        renderer.setScissor(old.scissor);
        renderer.setScissorTest(old.scissorTest);
        renderer.setClearColor(old.color, old.alpha);
        renderer.toneMapping = old.toneMapping;
        renderer.autoClear = old.autoClear;
        renderer.xr.enabled = old.xr;
      }
    },
    metrics: () => ({ cubeSize: 128, cached: [...maps.keys()], errors: Object.fromEntries(failures),
      bakes: Object.fromEntries([...maps].map(([id, r]) => [id, { ms: r.ms, size: [r.target.width, r.target.height] }])) }),
    dispose() {
      if (disposed) return;
      disposed = true;
      for (const r of maps.values()) r.target.dispose();
      maps.clear(); failures.clear();
    },
  };
}
