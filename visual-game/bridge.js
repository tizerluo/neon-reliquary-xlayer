// 本地视觉实验：只有 ?visual=knight（Aurelian）或 ?visual=nyx（Nyx）才会加载；发布版游戏仍是自包含单文件。
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { ADDITIVE, createGlow, radialTexture } from './glow.js';

const asset = name => new URL(`../visual-lab/assets/${name}`, import.meta.url).href;
const wrap = a => Math.atan2(Math.sin(a), Math.cos(a));

// Aurelian 骑士：保留首轮实机测试时的灯光、材质与动作映射
function knightProfile() {
  return {
    hero: 0, url: asset('cathedral-slice.glb'), group: 'HERO', height: 3.1, exposure: 1.45,
    clips: ['Idle', 'Stride', 'Slash', 'Guard'], once: ['Slash', 'Guard'], fade: 0.12, turnRate: 0,
    stage(scene, renderer) {
      scene.add(new THREE.HemisphereLight(0x8fc7e2, 0x342726, 1.6));
      const key = new THREE.DirectionalLight(0xffe8c6, 3.0);
      key.position.set(-4, 9, -5);
      scene.add(key);
      const cyan = new THREE.DirectionalLight(0x36ebef, 1.7);
      cyan.position.set(-3, 3, 2);
      scene.add(cyan);
      const warm = new THREE.DirectionalLight(0xff306c, 0.65);
      warm.position.set(3, 2, 1);
      scene.add(warm);
      const pmrem = new THREE.PMREMGenerator(renderer);
      const room = new RoomEnvironment();
      this.reflection = pmrem.fromScene(room).texture;
      room.dispose();
      pmrem.dispose();
    },
    dress(root, character) {
      const arena = root.getObjectByName('ARENA'), enemy = root.getObjectByName('ENEMY');
      if (!arena || !enemy) return 'Character GLB is missing the HERO, ARENA, or ENEMY group';
      arena.visible = false;
      enemy.visible = false;
      character.traverse(object => {
        if (!object.isMesh) return;
        object.material = object.material.clone();
        const material = object.material, name = material.name;
        material.envMap = this.reflection;
        material.envMapIntensity = name.includes('mantle') ? 0.08
          : name.includes('brass') || name.includes('Polished') ? 0.34 : 0.56;
        if (name.includes('Visor smoked glass')) {
          material.metalness = 0;
          material.roughness = 1;
          material.envMapIntensity = 0;
        }
        if (material.emissiveIntensity > 0) material.emissiveIntensity *= 1.15;
        material.needsUpdate = true;
      });
      return null;
    },
    choose(player, last, active) {
      if (player.castAnim > last.cast + 0.1 || player.attackAnim > last.attack + 0.08) return 'Slash';
      if (player.shield > last.shield + 10) return 'Guard';
      if (active !== 'Slash' && active !== 'Guard') return player.moving ? 'Stride' : 'Idle';
      return null;
    },
    rest: moving => moving ? 'Stride' : 'Idle',
    update() {},
  };
}

// Nyx 虚空工匠：飞剑由原生战斗画面绘制，这里只替换本体、光环和材质
function nyxProfile() {
  let halo = null, haloQ0 = null, haloAngle = 0, channel = 0, pool = null, clock = 0;
  const haloAxis = new THREE.Vector3(0, 0, 1), spin = new THREE.Quaternion();
  // 默认用减面 + 半尺寸贴图的游戏版；加 &nyxlod=full 可换回展示页高模做对照
  const full = new URLSearchParams(location.search).get('nyxlod') === 'full';
  return {
    hero: 3, group: 'NYX', height: 3.25, exposure: 1.2,
    url: asset(full ? 'nyx-void-artificer.glb?v=nyx-20260925-c' : 'nyx-void-artificer-game.glb?v=nyx-game-20260925-a'),
    clips: ['Idle', 'Drift', 'Cast', 'Channel'], once: ['Cast', 'Channel'], fade: 0.22, turnRate: 9,
    // 各部件光晕权重沿用展示页：电路贴图只留轻微光晕，胸核与下摆最强
    glow: { strength: 0.9, radius: 0.4, weight: (name, m) => m.emissiveMap ? 0.12 : name.includes('core glow') ? 0.5
      : name.includes('hem') ? 0.3 : name.includes('inlay') ? 0.25 : 0.02 },
    stage(scene, renderer) {
      // 与展示页同一套影棚反射，但绕 Y 轴转 180°：战斗镜头从 +Z 高处俯视，柔光箱要落在镜头一侧
      const env = new THREE.Scene();
      env.background = new THREE.Color(0x020205);
      const panel = (w, h, color, gain, pos) => {
        const mesh = new THREE.Mesh(new THREE.PlaneGeometry(w, h),
          new THREE.MeshBasicMaterial({ color: new THREE.Color(color).multiplyScalar(gain), side: THREE.DoubleSide }));
        mesh.position.set(...pos);
        mesh.lookAt(0, 1, 0);
        env.add(mesh);
      };
      panel(6, 3, 0xece6ff, 1.5, [0, 6, 3]);
      panel(1.2, 7, 0x8b5cf6, 3.2, [-4.5, 2, -3]);
      panel(1.2, 7, 0x2ee6ff, 2.0, [4.5, 2, -3]);
      panel(8, 1.4, 0x3b2a66, 1.1, [0, 0.4, 6]);
      const pmrem = new THREE.PMREMGenerator(renderer);
      scene.environment = pmrem.fromScene(env, 0.035).texture;
      pmrem.dispose();
      scene.environmentIntensity = 0.9;
      scene.add(new THREE.HemisphereLight(0x9d8cff, 0x0a0612, 0.55));
      const light = (color, intensity, pos) => {
        const l = new THREE.DirectionalLight(color, intensity);
        l.position.set(...pos);
        scene.add(l);
      };
      light(0xefe8ff, 2.1, [-2.0, 4.8, 3.4]);    // 主光：镜头左上
      light(0xa070ff, 1.7, [-2.3, 3.3, -3.3]);   // 紫色轮廓光：从身后勾出兜帽与肩甲边缘
      light(0x40e0ff, 0.8, [2.5, 2.7, -2.9]);    // 青色轮廓光
      light(0x8f86c8, 0.45, [3, 1.5, 4]);        // 补光
    },
    dress(root, character) {
      // 展示页里环绕身体的针刃在战斗中由原生飞剑承担，移出场景避免重复，也不计入包围盒
      character.getObjectByName('NYX_NEEDLE')?.removeFromParent();
      character.traverse(object => {
        if (!object.isMesh) return;
        object.frustumCulled = false;
        const m = object.material, name = m.name || '';
        m.envMapIntensity = name.includes('glass mask') ? 1.8 : name.includes('obsidian') ? 1.25
          : name.includes('platinum') ? 0.6 : name.includes('halo') ? 0.9
          : name.includes('velvet') || name.includes('tabard') ? 0.35 : name.includes('bodysuit') ? 0.45 : 0.8;
        // glTF 导出的 sheen 颜色未乘 Blender 的 Sheen Weight，按权重补回
        if (m.sheenColor && m.sheen > 0) m.sheenColor.multiplyScalar(name.includes('lining') ? 0.3 : 0.12);
        if (name.includes('lining')) { m.color.multiplyScalar(0.5); m.roughness = 0.7; }
        if (name.includes('halo')) { m.color.setRGB(0.42, 0.40, 0.48); m.metalness = 1; m.roughness = 0.26; }
        // 叠加画布没有辉光后期，发光件比展示页略亮，俯视距离下仍能读出光缝、下摆和胸核
        if (m.emissive && (m.emissive.getHex() !== 0 || m.emissiveMap)) {
          m.emissiveIntensity *= name.includes('core glow') ? 1.2 : name.includes('hem') ? 1.1
            : name.includes('inlay') ? 1.4 : 1.1;
        }
      });
      // 光环：取包围盒最薄的轴作为环法线，绕它自转
      halo = root.getObjectByName('NYX_HALO');
      if (halo) {
        root.updateMatrixWorld(true);
        const inv = halo.matrixWorld.clone().invert(), box = new THREE.Box3();
        halo.traverse(o => {
          if (!o.isMesh) return;
          o.geometry.computeBoundingBox();
          box.union(o.geometry.boundingBox.clone().applyMatrix4(new THREE.Matrix4().multiplyMatrices(inv, o.matrixWorld)));
        });
        const size = box.getSize(new THREE.Vector3());
        if (size.x < size.y && size.x < size.z) haloAxis.set(1, 0, 0);
        else if (size.y < size.z) haloAxis.set(0, 1, 0);
        haloQ0 = halo.quaternion.clone();
      }
      // 贴地虚空光池：挂在根节点而非角色组上，不影响按身高换算的缩放
      pool = new THREE.Mesh(new THREE.CircleGeometry(0.95, 48), new THREE.MeshBasicMaterial({
        map: radialTexture([[0, 'rgba(190,150,255,0.85)'], [0.35, 'rgba(130,80,255,0.38)'], [1, 'rgba(90,40,220,0)']]),
        transparent: true, depthWrite: false, ...ADDITIVE }));
      pool.rotation.x = -Math.PI / 2;
      pool.position.y = 0.02;
      pool.renderOrder = -1;
      pool.userData.noGlow = true;
      root.add(pool);
      return null;
    },
    choose(player, last, active) {
      // 终结技开启时 ultTime 从 0 跳到 4.2；引导期间技能不打断姿态
      if (player.ultTime > last.ult + 1) return 'Channel';
      if (active === 'Channel' && player.ultTime > 0) return null;
      if (player.castAnim > last.cast + 0.1) return 'Cast';
      if (active !== 'Cast' && active !== 'Channel') return player.moving ? 'Drift' : 'Idle';
      return null;
    },
    rest: moving => moving ? 'Drift' : 'Idle',
    update(dt, player, motion, action) {
      // Channel 片段第 13–28 帧是举手保持段；终结技剩余时间足够收势时，把播放头停在保持段末尾
      if (motion === 'Channel' && action && player.ultTime > 0.6 && action.time > 1.1) action.time = 1.1;
      channel += ((motion === 'Channel' ? 1 : 0) - channel) * Math.min(1, dt * 3);
      clock += dt;
      if (pool) {
        pool.material.opacity = 0.55 + 0.1 * Math.sin(clock * 2.1) + channel * 0.45;
        pool.scale.setScalar(1 + channel * 0.35);
      }
      if (halo && haloQ0) {
        haloAngle += dt * (0.3 + channel * 1.6);
        halo.quaternion.copy(haloQ0).multiply(spin.setFromAxisAngle(haloAxis, haloAngle));
      }
    },
  };
}

const PROFILES = { knight: knightProfile, nyx: nyxProfile };

export function createVisualBridge(app, name = 'knight') {
  const profile = (PROFILES[name] || knightProfile)();
  const canvas = document.createElement('canvas');
  canvas.id = 'visualCharacter';
  canvas.dataset.profile = PROFILES[name] ? name : 'knight';
  canvas.setAttribute('aria-hidden', 'true');
  Object.assign(canvas.style, {
    position: 'absolute', inset: '0', width: '100%', height: '100%',
    pointerEvents: 'none', zIndex: '1', display: 'none',
  });
  app.insertBefore(canvas, document.getElementById('overlay'));

  const renderer = new THREE.WebGLRenderer({
    canvas, alpha: true, antialias: true, powerPreference: 'high-performance',
    preserveDrawingBuffer: new URLSearchParams(location.search).has('capture'),
  });
  renderer.setPixelRatio(1);
  renderer.setClearColor(0, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = profile.exposure;
  renderer.info.autoReset = false;
  const scene = new THREE.Scene();
  const camera = new THREE.OrthographicCamera(-18, 18, 10, -10, 0.1, 150);
  profile.stage(scene, renderer);
  const glow = profile.glow ? createGlow(renderer, scene, camera, profile.glow) : null;

  let root = null, mixer = null, activeAction = null, activeMotion = '';
  let ready = false, visible = false, error = null, yaw = null, glowOn = false;
  let modelScale = 1, moving = false;
  const last = { attack: 0, cast: 0, shield: 0, ult: 0 };
  const clips = new Map();
  const measurements = { assetBytes: 0, meshes: 0, triangles: 0, textures: 0,
    decodedTextureBytes: 0, frames: 0, renderMsTotal: 0, renderMsMax: 0 };
  canvas.addEventListener('webglcontextlost', () => {
    ready = false;
    window.__NR_VISUAL_ACTIVE = false;
    error = 'Three.js WebGL context lost';
  });

  function play(motion) {
    if (!mixer || !clips.has(motion)) return;
    if (motion === activeMotion && activeAction?.isRunning()) return;
    const next = mixer.clipAction(clips.get(motion));
    next.reset();
    next.setLoop(profile.once.includes(motion) ? THREE.LoopOnce : THREE.LoopRepeat);
    next.clampWhenFinished = false;
    next.play();
    if (activeAction && activeAction !== next) next.crossFadeFrom(activeAction, profile.fade, false);
    activeAction = next;
    activeMotion = motion;
  }

  new GLTFLoader().load(profile.url, gltf => {
    root = gltf.scene;
    const character = root.getObjectByName(profile.group);
    if (!character) {
      error = `Character GLB is missing the ${profile.group} group`;
      return;
    }
    const dressError = profile.dress(root, character);
    if (dressError) {
      error = dressError;
      return;
    }
    const textures = new Set();
    character.traverse(object => {
      if (!object.isMesh) return;
      measurements.meshes++;
      measurements.triangles += object.geometry.index
        ? object.geometry.index.count / 3 : object.geometry.attributes.position.count / 3;
      for (const slot of ['map', 'normalMap', 'roughnessMap', 'metalnessMap', 'emissiveMap']) {
        const texture = object.material[slot];
        if (texture) textures.add(texture);
      }
    });
    measurements.textures = textures.size;
    measurements.decodedTextureBytes = [...textures].reduce((sum, texture) =>
      sum + (texture.image?.width || 0) * (texture.image?.height || 0) * 4, 0);
    measurements.assetBytes = performance.getEntriesByName(profile.url).at(-1)?.decodedBodySize || 0;
    const bounds = new THREE.Box3().setFromObject(character);
    modelScale = profile.height / bounds.getSize(new THREE.Vector3()).y;
    mixer = new THREE.AnimationMixer(root);
    for (const clip of gltf.animations) clips.set(clip.name, clip);
    if (!profile.clips.every(clip => clips.has(clip))) {
      error = 'Character GLB is missing a required animation';
      return;
    }
    mixer.addEventListener('finished', event => {
      if (event.action === activeAction) play(profile.rest(moving));
    });
    scene.add(root);
    play(profile.rest(false));
    ready = true;
  }, undefined, loadError => { error = String(loadError); });

  function prepare(frame, native) {
    visible = !!(ready && native.gl && !native.hadContextLoss &&
      frame.options.backend !== 'canvas' && frame.P && frame.selected === profile.hero &&
      (frame.state === 'play' || frame.state === 'paused'));
    window.__NR_VISUAL_ACTIVE = visible;
    window.__NR_VISUAL = visible ? { hero: { [profile.hero]: true }, leaderOnly: true, enemy: {} } : null;
    canvas.style.display = visible ? 'block' : 'none';
    if (!visible) yaw = null;
  }

  function render(frame, dt, native) {
    if (!visible) return;
    const started = performance.now();
    const step = Math.min(Math.max(dt, 0), 0.05);
    const width = native.canvas.clientWidth, height = native.canvas.clientHeight;
    if (canvas.width !== width || canvas.height !== height) {
      renderer.setSize(width, height, false);
      glow?.setSize(width, height);
    }
    camera.left = -native.width / 2;
    camera.right = native.width / 2;
    camera.top = native.height / 2;
    camera.bottom = -native.height / 2;
    camera.updateProjectionMatrix();
    camera.position.set(...native.eye);
    camera.lookAt(...native.target);
    const player = frame.P;
    moving = !!player.moving;
    root.position.set(player.x * native.scale, player.downed ? -1.0 : 0,
      player.y * native.scale);
    // 两套模型都面向 -Z，朝向换算与原生英雄一致；Nyx 漂浮转身带一点阻尼
    const aim = -(player.moving ? player.moveAim : player.aim) - Math.PI / 2;
    yaw = yaw === null || !profile.turnRate ? aim : yaw + wrap(aim - yaw) * Math.min(1, step * profile.turnRate);
    root.rotation.y = yaw;
    root.scale.setScalar(modelScale * (player.downed ? 0.76 : 1.03));
    const next = profile.choose(player, last, activeMotion);
    if (next) play(next);
    last.attack = player.attackAnim;
    last.cast = player.castAnim;
    last.shield = player.shield;
    last.ult = player.ultTime || 0;
    mixer.update(step);
    profile.update(step, player, activeMotion, activeAction);
    // 辉光跟随游戏设置里的 Neon bloom 开关
    glowOn = !!glow && frame.options.bloom !== false;
    try {
      renderer.info.reset();
      renderer.render(scene, camera);
      if (glowOn) glow.render();
    } catch (renderError) {
      error = String(renderError);
      ready = false;
      visible = false;
      window.__NR_VISUAL_ACTIVE = false;
      canvas.style.display = 'none';
      return;
    }
    const elapsed = performance.now() - started;
    measurements.frames++;
    measurements.renderMsTotal += elapsed;
    measurements.renderMsMax = Math.max(measurements.renderMsMax, elapsed);
  }

  return {
    prepare, render,
    metrics: () => ({ profile: canvas.dataset.profile, hero: profile.hero, ready, visible, error, glow: glowOn,
      motion: activeMotion, modelScale, ...measurements, renderMsMean: measurements.frames
        ? measurements.renderMsTotal / measurements.frames : 0,
      drawCalls: renderer.info.render.calls, renderedTriangles: renderer.info.render.triangles,
      geometries: renderer.info.memory.geometries, gpuTextures: renderer.info.memory.textures,
      resolution: [canvas.width, canvas.height] }),
  };
}
