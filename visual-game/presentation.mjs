import * as THREE from 'three';

// 界面、战场和缩略图共享同一份当前游戏模型，避免另建一套过期角色。
export const HEROES = [
  { id: 'aurelian', glb: 'chars/aurelian-game.glb', height: 3.35, spin: ['AURELIAN_AEGIS'], region: 0 },
  { id: 'mordred', glb: 'chars/mordred-game.glb', height: 3.35, region: 2 },
  { id: 'volt', glb: 'chars/volt-game.glb', height: 3.3, region: 0 },
  { id: 'nyx', glb: 'nyx-void-artificer-game.glb', height: 3.25, move: 'Drift', spin: ['NYX_HALO'], turn: 9, region: 3 },
  { id: 'seraph', glb: 'chars/seraph-game.glb', height: 3.45, region: 0 },
  { id: 'isolde', glb: 'chars/isolde-game.glb', height: 3.3, region: 1 },
];
const BATTLE_BACKDROPS = new Set(['play', 'paused', 'route', 'camp', 'result']);
export function presentationFor(frame) {
  const hero = Math.max(0, Math.min(5, frame.selected | 0));
  if (frame.state === 'home' || frame.state === 'select') {
    return { kind: 'hero', key: `hero:${HEROES[hero].id}`, hero,
      stage: frame.state === 'home' ? 0 : HEROES[hero].region };
  }
  if (frame.state === 'inspect' && Number.isInteger(frame.inspection?.id) && frame.inspection.id >= 0 && frame.inspection.id < 8) {
    const boss = frame.inspection.id;
    return { kind: 'boss', key: `boss-${boss}`, boss, stage: Math.floor(boss / 2) };
  }
  if (BATTLE_BACKDROPS.has(frame.state) && frame.P && frame.run) {
    return { kind: 'battle', stage: frame.run.stage ?? 0 };
  }
  return null;
}

// 取 UI 为模型保留的画面区域；矩形用整块 app 的 0–1 坐标表示。
export function presentationRect(state, aspect) {
  if (aspect < 1) return state === 'home'
    ? { x: .16, y: .04, width: .76, height: .44 }
    : { x: .05, y: .10, width: .9, height: .23 };
  return state === 'home' ? { x: .55, y: .12, width: .42, height: .59 }
    : state === 'inspect' ? { x: .04, y: .16, width: .54, height: .69 }
      : { x: .04, y: .17, width: .44, height: .63 };
}

// 用八个包围盒角点求透视距离，宽翼、长尾、旋转与竖屏都不会被写死高度裁掉。
export function fitPresentationCamera(camera, box, aspect, rect, zoom = 1) {
  const center = box.getCenter(new THREE.Vector3());
  const direction = new THREE.Vector3(.22, .18, -1).normalize();
  camera.position.copy(center).add(direction);
  camera.lookAt(center);
  camera.updateMatrixWorld(true);
  const rotation = camera.matrixWorldInverse.clone();
  rotation.setPosition(0, 0, 0);
  const focal = 1 / Math.tan(THREE.MathUtils.degToRad(36) / 2);
  let distance = 1;
  for (const x of [box.min.x, box.max.x]) for (const y of [box.min.y, box.max.y]) for (const z of [box.min.z, box.max.z]) {
    const p = new THREE.Vector3(x, y, z).sub(center).applyMatrix4(rotation);
    distance = Math.max(distance, p.z + Math.abs(p.x) * focal / (aspect * rect.width * .88),
      p.z + Math.abs(p.y) * focal / (rect.height * .88));
  }
  camera.position.copy(center).addScaledVector(direction, distance / zoom);
  camera.lookAt(center);
  camera.updateMatrixWorld(true);
  const half = .1 / focal;
  camera.projectionMatrix.makePerspective(-half * aspect, half * aspect, half, -half, .1, 300);
  camera.projectionMatrix.elements[8] = 1 - 2 * (rect.x + rect.width / 2);
  camera.projectionMatrix.elements[9] = 2 * (rect.y + rect.height / 2) - 1;
  camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();
  return distance;
}
