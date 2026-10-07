const { test } = require('node:test');
const assert = require('node:assert/strict');
const data = import('../visual-game/pickup-fx-data.mjs');
const renderer = import('../visual-game/pickup-fx.mjs');
const three = import('three');

function fixture(max = 4) {
  const O = { max };
  for (const key of ['a', 'kind', 'x', 'y', 'age', 'value']) O[key] = new Float32Array(max);
  O.a.fill(1); O.value.fill(3.5);
  return { run: { time: 0 }, O, options: { quality: 'high' }, camera: { x: 0, y: 0 } };
}
function move(frame, dt = 1 / 60, dx = 6) {
  frame.run.time += dt;
  for (let i = 0; i < frame.O.max; i++) { frame.O.x[i] += dx; frame.O.age[i] += dt; }
}

test('Pickup value tiers retain separate size and restrained monotonic light levels', async () => {
  const { pickupStyle, pickupTier } = await data;
  assert.equal(pickupTier(9.99), 0); assert.equal(pickupTier(10), 1);
  assert.equal(pickupTier(49.99), 1); assert.equal(pickupTier(50), 2);
  const styles = [3.5, 16, 90].map(pickupStyle);
  for (let i = 1; i < styles.length; i++) {
    assert(styles[i].scale > styles[i - 1].scale);
    assert(styles[i].emission > styles[i - 1].emission);
  }
  assert(styles.every(s => s.emission > 0 && s.emission <= 1.2));
});

test('Absorption history reads real movement, stays fixed on pause, and does not mutate the pool', async () => {
  const { createPickupHistory } = await data, h = createPickupHistory(), f = fixture(1);
  assert.equal(h.update(f)[0].points.length, 0);
  move(f); const actual = h.update(f)[0].points;
  assert.equal(actual.length, 2);
  assert.deepEqual(actual.map(p => p.x), [0, 6]);
  const original = JSON.stringify(f.O), paused = JSON.stringify(h.update(f));
  for (let i = 0; i < 20; i++) assert.equal(JSON.stringify(h.update(f)), paused);
  assert.equal(JSON.stringify(f.O), original);
  f.run.time += .2; assert.equal(h.update(f)[0].points.length, 0);
});

test('Slot release, reuse, teleport, skipped simulation and a new run cannot create false pickup tails', async () => {
  const { createPickupHistory } = await data, h = createPickupHistory(), f = fixture(1);
  h.update(f); move(f); h.update(f);
  f.O.age[0] = 0; f.O.x[0] = -50; assert.equal(h.update(f)[0].points.length, 0);
  move(f); h.update(f); f.O.a[0] = 0; assert.equal(h.update(f).length, 0);
  f.O.a[0] = 1; assert.equal(h.update(f)[0].points.length, 0);
  move(f); h.update(f); move(f, 1 / 60, 500); assert.equal(h.update(f)[0].points.length, 0);
  move(f, .5); assert.equal(h.update(f)[0].points.length, 0);
  move(f); h.update(f); f.run = { time: 0 }; assert.equal(h.update(f)[0].points.length, 0);
  move(f); h.update(f); h.reset(); assert.equal(h.update(f)[0].points.length, 0);
  // 新物与旧物同值、同龄，仍应识别同帧释放并复用，不能跨物体连线。
  const same = fixture(1), reuse = createPickupHistory();
  move(same); reuse.update(same); same.run.time += 1 / 60; same.O.x[0] = 70;
  assert.equal(reuse.update(same)[0].points.length, 0);
});

test('Real Three pickup attributes share materials and trail batches obey lifecycle and quality budgets', async () => {
  const { createPickupDetails } = await renderer, T = await three;
  const scene = new T.Scene(), fx = createPickupDetails(scene);
  const rec = { parts: [{ geo: new T.BoxGeometry(), mat: new T.MeshStandardMaterial({ emissive: '#86d9e6' }) }] };
  fx.configure(rec, 0);
  [3.5, 16, 90].forEach((v, i) => fx.instance(rec, i, i, v, 0)); fx.flush(rec);
  const gains = Array.from(rec.parts[0].geo.getAttribute('pickupGain').array.slice(0, 3));
  assert(gains[0] < gains[1] && gains[1] < gains[2]);
  assert.equal(typeof rec.parts[0].mat.userData.createGlowMaterial, 'function');
  const f = fixture(700), native = { viewWidth: 3000, viewHeight: 3000, sinElev: .8 };
  fx.update(f, native, .028, true);
  for (let i = 0; i < 8; i++) { move(f); fx.update(f, native, .028, true); }
  assert.equal(fx.metrics().tracked, 700);
  assert(fx.metrics().count > 1000 && fx.metrics().count <= fx.metrics().capacity);
  const mesh = scene.children[0]; assert(mesh.userData.noGlow);
  assert.equal(mesh.geometry.drawRange.count, fx.metrics().count * 6);
  const positions = Array.from(mesh.geometry.getAttribute('position').array), paused = JSON.stringify(fx.metrics());
  fx.update(f, native, .028, true); assert.equal(JSON.stringify(fx.metrics()), paused);
  assert.deepEqual(Array.from(mesh.geometry.getAttribute('position').array), positions);
  f.options.quality = 'low'; fx.update(f, native, .028, true);
  assert(fx.metrics().count > 0 && fx.metrics().count <= fx.metrics().lowCapacity);
  f.options.reducedMotion = true; fx.update(f, native, .028, true);
  assert.equal(fx.metrics().count, 0); assert.equal(fx.metrics().time, 0);
  fx.reset(); assert.equal(fx.metrics().tracked, 0); assert.equal(mesh.visible, false);
  fx.dispose(); fx.dispose(); assert.equal(scene.children.length, 0); assert(fx.metrics().disposed);
  rec.parts[0].geo.dispose(); rec.parts[0].mat.dispose();
});
