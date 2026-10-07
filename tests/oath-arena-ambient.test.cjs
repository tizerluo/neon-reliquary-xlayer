const { test } = require('node:test');
const assert = require('node:assert/strict');
let THREE;
const surfaceModule = Promise.all([import('../visual-game/arena-surface.mjs'), import('three')])
  .then(([surface, three]) => { THREE = three; return surface; });
const floor = () => new THREE.MeshBasicMaterial({ name: 'test floor' });
function plane(width, height) {
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(width, height), floor());
  mesh.rotation.x = -Math.PI / 2;
  return mesh;
}
function near(actual, expected) { assert(Math.abs(actual - expected) < 1e-6, actual + ' != ' + expected); }

test('Ambient surfaces use world area under nested rotation, nonuniform and mirrored scale', async () => {
  const { collectSurface, seededRandom } = await surfaceModule;
  for (const mirror of [1, -1]) {
    const root = new THREE.Group(), mesh = plane(2, 2);
    root.position.set(9, 3, -7); root.rotation.y = 0.63; root.scale.set(3 * mirror, 2, 4);
    root.add(mesh);
    const surface = collectSurface(root, { from: /test floor/ });
    near(surface.total, 48);
    const rng = seededRandom(19);
    root.updateMatrixWorld(true);
    const inverse = mesh.matrixWorld.clone().invert();
    for (let i = 0; i < 100; i++) {
      const point = surface.sample(rng);
      near(point.y, 3);
      point.applyMatrix4(inverse);
      assert(Math.abs(point.x) <= 1.000001 && Math.abs(point.y) <= 1.000001);
      near(point.z, 0);
    }
  }
  const upsideDown = new THREE.Group(); upsideDown.scale.y = -1; upsideDown.add(plane(2, 2));
  near(collectSurface(upsideDown).total, 0);
});

test('Material groups, top normals and draw range exclude walls and unrendered faces', async () => {
  const { collectSurface } = await surfaceModule;
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(4, 2, 4), Array.from({ length: 6 }, floor));
  const options = { from: /test floor/g };
  near(collectSurface(mesh, options).total, 16); // 六面同材质仍只从顶面出生
  mesh.material[2] = new THREE.MeshBasicMaterial({ name: 'not a source' });
  near(collectSurface(mesh, options).total, 0);
  mesh.material[2] = floor();
  mesh.geometry.setDrawRange(12, 3); // 顶面一个三角形
  near(collectSurface(mesh, options).total, 8);
  mesh.geometry.setDrawRange(0, 6); // 侧墙
  const empty = collectSurface(mesh, options);
  near(empty.total, 0); assert.equal(empty.sample(), null);
});

test('World clipping preserves edge area and sampled footprint for indexed and nonindexed geometry', async () => {
  const { collectSurface, seededRandom } = await surfaceModule;
  for (const indexed of [true, false]) {
    const mesh = plane(10, 10);
    if (!indexed) mesh.geometry = mesh.geometry.toNonIndexed();
    const surface = collectSurface(mesh, { from: /test floor/, bounds: [-2, 1, -1, 3], yRange: [-0.1, 0.1] });
    near(surface.total, 12);
    const rng = seededRandom(41);
    for (let i = 0; i < 500; i++) {
      const p = surface.sample(rng);
      assert(p.x >= -2.000001 && p.x <= 1.000001 && p.z >= -1.000001 && p.z <= 3.000001);
      near(p.y, 0);
    }
    near(collectSurface(mesh, { bounds: [20, 21, 20, 21] }).total, 0);
    near(collectSurface(mesh, { yRange: [2, 3] }).total, 0);
  }
});

test('Area-weighted births and seeded replay remain finite and reproducible', async () => {
  const { collectSurface, seededRandom } = await surfaceModule;
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute([
    0, 0, 0, 0, 0, 2, 1, 0, 0, // 1 m²
    10, 0, 0, 10, 0, 4, 12, 0, 0, // 4 m²
    0, 0, 0, 0, 0, 0, 0, 0, 0, // 退化面
  ], 3));
  const surface = collectSurface(new THREE.Mesh(geo, floor()));
  near(surface.total, 5);
  const first = seededRandom(57), second = seededRandom(57);
  let larger = 0;
  for (let i = 0; i < 6000; i++) {
    const p = surface.sample(first), replay = surface.sample(second);
    assert.deepEqual(p.toArray(), replay.toArray());
    assert(p.toArray().every(Number.isFinite));
    if (p.x >= 10) larger++;
  }
  assert(Math.abs(larger / 6000 - 0.8) < 0.02, 'births must follow source area, not triangle count');
});
