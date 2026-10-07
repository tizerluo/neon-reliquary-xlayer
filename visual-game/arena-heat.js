// 熔流附近的局部空气折射：只拷贝并重绘场地画布，不触碰上层战斗信息。
// 位移遮罩为 1/4 分辨率、单批次实例；RGBA8 分别存储 +X/-X/+Y/-Y，无浮点扩展要求。
import * as THREE from 'three';
import { collectSurface, seededRandom } from './arena-surface.mjs';

export function createHeatHaze(renderer, camera, root, cfg) {
  const surface = collectSurface(root, cfg);
  if (!surface.total) return null;
  const rng = seededRandom(cfg.seed), N = cfg.count, candidates = [];
  for (let i = 0; i < N * 12; i++) candidates.push(surface.sample(rng));
  // 最大间距取样让热浪覆盖不同热源，而不是随机堆在一处炉床。
  const sources = [candidates.shift()];
  while (sources.length < N && candidates.length) {
    let best = 0, farthest = -1;
    for (let i = 0; i < candidates.length; i++) {
      const p = candidates[i];
      let distance = Infinity;
      for (const q of sources) distance = Math.min(distance, (p.x - q.x) ** 2 + (p.z - q.z) ** 2);
      if (distance > farthest) { farthest = distance; best = i; }
    }
    sources.push(candidates.splice(best, 1)[0]);
  }
  const maskScene = new THREE.Scene(), geo = new THREE.PlaneGeometry(1, 1);
  const phases = new Float32Array(N), widths = new Float32Array(N), heights = new Float32Array(N);
  for (let i = 0; i < N; i++) {
    phases[i] = rng() * Math.PI * 2; widths[i] = 2.8 + rng() * 1.2; heights[i] = 3.0 + rng() * 1.5;
  }
  geo.setAttribute('heatPhase', new THREE.InstancedBufferAttribute(phases, 1));
  const maskMat = new THREE.ShaderMaterial({
    uniforms: { time: { value: 0 } },
    vertexShader: `
      attribute float heatPhase;
      varying vec2 vUv;
      varying float vPhase;
      void main() {
        vUv = uv; vPhase = heatPhase;
        gl_Position = projectionMatrix * modelViewMatrix * instanceMatrix * vec4(position, 1.0);
      }`,
    fragmentShader: `
      uniform float time;
      varying vec2 vUv;
      varying float vPhase;
      void main() {
        vec2 q = (vUv - 0.5) * 2.0;
        float edge = 1.0 - smoothstep(0.25, 1.0, abs(q.x));
        edge *= smoothstep(0.0, 0.18, vUv.y) * (1.0 - smoothstep(0.45, 1.0, vUv.y));
        float flow = vUv.y * 18.0 - time * 2.6 + vPhase;
        vec2 shift = vec2(sin(flow + sin(vUv.x * 7.0 + time * 0.6)),
                          0.35 * sin(flow * 0.7 + vPhase + vUv.x * 9.0)) * edge * 0.7;
        gl_FragColor = vec4(max(shift.x, 0.0), max(-shift.x, 0.0), max(shift.y, 0.0), max(-shift.y, 0.0));
      }`,
    transparent: true, toneMapped: false, depthTest: false, depthWrite: false, side: THREE.DoubleSide,
    blending: THREE.CustomBlending, blendEquation: THREE.AddEquation,
    blendSrc: THREE.OneFactor, blendDst: THREE.OneFactor,
    blendEquationAlpha: THREE.AddEquation, blendSrcAlpha: THREE.OneFactor, blendDstAlpha: THREE.OneFactor,
  });
  const plumes = new THREE.InstancedMesh(geo, maskMat, N);
  plumes.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  plumes.frustumCulled = false;
  maskScene.add(plumes);
  const transform = new THREE.Object3D(), rotation = new THREE.Quaternion(), size = new THREE.Vector2();
  const maskTarget = new THREE.WebGLRenderTarget(1, 1, {
    type: THREE.UnsignedByteType, format: THREE.RGBAFormat,
    minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, depthBuffer: false, stencilBuffer: false,
  });
  const screenGeo = new THREE.BufferGeometry();
  screenGeo.setAttribute('position', new THREE.Float32BufferAttribute([-1, -1, 0, 3, -1, 0, -1, 3, 0], 3));
  screenGeo.setAttribute('uv', new THREE.Float32BufferAttribute([0, 0, 2, 0, 0, 2], 2));
  const composite = new THREE.RawShaderMaterial({
    uniforms: { sceneFrame: { value: null }, heatMask: { value: maskTarget.texture },
      inverseSize: { value: new THREE.Vector2(1, 1) }, maxPixels: { value: cfg.maxPixels } },
    vertexShader: `
      precision highp float;
      attribute vec3 position;
      attribute vec2 uv;
      varying vec2 vUv;
      void main() { vUv = uv; gl_Position = vec4(position, 1.0); }`,
    fragmentShader: `
      precision highp float;
      uniform sampler2D sceneFrame;
      uniform sampler2D heatMask;
      uniform vec2 inverseSize;
      uniform float maxPixels;
      varying vec2 vUv;
      void main() {
        vec4 mask = texture2D(heatMask, vUv);
        vec2 shift = vec2(mask.r - mask.g, mask.b - mask.a);
        shift /= max(1.0, length(shift));
        vec2 sampleUv = clamp(vUv + shift * maxPixels * inverseSize, 0.5 * inverseSize, 1.0 - 0.5 * inverseSize);
        // 已经完成色调映射的帧必须原样输出，包括 alpha；不再转色域或再次曝光。
        gl_FragColor = texture2D(sceneFrame, sampleUv);
      }`,
    toneMapped: false, blending: THREE.NoBlending, depthTest: false, depthWrite: false,
  });
  const screenScene = new THREE.Scene(), screenCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  const screen = new THREE.Mesh(screenGeo, composite);
  screen.frustumCulled = false; screenScene.add(screen);
  const clearColor = new THREE.Color();
  let frameTexture = null, width = 0, height = 0;
  const stats = { sources: N, emitArea: Math.round(surface.total), maxPixels: cfg.maxPixels, mask: [1, 1] };
  return {
    stats,
    setStrength(pixels) { composite.uniforms.maxPixels.value = Math.max(0, Math.min(cfg.maxPixels, pixels)); },
    render(now) {
      // 只允许从场地的默认帧缓冲取图；辉光已在调用前叠回。
      if (renderer.getRenderTarget() !== null) return;
      renderer.getDrawingBufferSize(size);
      if (width !== size.x || height !== size.y) {
        width = size.x; height = size.y;
        frameTexture?.dispose();
        frameTexture = new THREE.FramebufferTexture(width, height);
        frameTexture.minFilter = frameTexture.magFilter = THREE.LinearFilter;
        composite.uniforms.sceneFrame.value = frameTexture;
        composite.uniforms.inverseSize.value.set(1 / width, 1 / height);
        maskTarget.setSize(Math.max(1, Math.ceil(width / 4)), Math.max(1, Math.ceil(height / 4)));
        stats.mask = [maskTarget.width, maskTarget.height];
      }
      renderer.copyFramebufferToTexture(frameTexture);
      camera.getWorldQuaternion(rotation);
      for (let i = 0; i < N; i++) {
        transform.position.copy(sources[i]);
        transform.position.y += heights[i] * 0.42;
        transform.quaternion.copy(rotation);
        transform.scale.set(widths[i], heights[i], 1);
        transform.updateMatrix(); plumes.setMatrixAt(i, transform.matrix);
      }
      plumes.instanceMatrix.needsUpdate = true;
      maskMat.uniforms.time.value = now;
      const autoClear = renderer.autoClear, clearAlpha = renderer.getClearAlpha(), scissor = renderer.getScissorTest();
      renderer.getClearColor(clearColor);
      try {
        renderer.autoClear = false;
        renderer.setScissorTest(false);
        renderer.setRenderTarget(maskTarget);
        renderer.setClearColor(0x000000, 0);
        renderer.clear(true, false, false);
        renderer.render(maskScene, camera);
        renderer.setRenderTarget(null);
        renderer.render(screenScene, screenCamera);
      } finally {
        renderer.setRenderTarget(null);
        renderer.setClearColor(clearColor, clearAlpha);
        renderer.setScissorTest(scissor);
        renderer.autoClear = autoClear;
      }
    },
    dispose() { frameTexture?.dispose(); maskTarget.dispose(); geo.dispose(); maskMat.dispose(); screenGeo.dispose(); composite.dispose(); },
  };
}
