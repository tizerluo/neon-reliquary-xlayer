const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const { WARNING_CAPACITY, warningState, snapshotWarnings } = require('../src/warning-data.js');
const { simulation } = require('./sim_harness.cjs');
const near = (a, b) => assert(Math.abs(a - b) < 1e-10, `${a} != ${b}`);
const circle = fields => ({ type: 0, x: 125, y: -100, r: 92, age: .3, delay: 1.2, ...fields });
const lane = fields => ({ type: 1, x: 125, y: -100, angle: .73, len: 1000, width: 43, age: .3, delay: 1.2, ...fields });

test('Pure warning adapter works as an independent classic script and CJS module', () => {
  const context = vm.createContext({});
  vm.runInContext(fs.readFileSync(require.resolve('../src/warning-data.js'), 'utf8'), context);
  assert.equal(context.NRWarningData.WARNING_CAPACITY, WARNING_CAPACITY);
  assert.equal(context.NRWarningData.warningState(circle()).progress, .25);
  assert.equal(globalThis.NRWarningData.warningState, warningState);
});

test('Circle progress uses simulation radius and retains its complete boundary', () => {
  const w = Object.freeze(circle({ boss: Object.freeze({ boss: 0 }), color: '#00ff00' }));
  for (const age of [0, .3, 1.199]) {
    const state = warningState({ ...w, age }, .028);
    near(state.radius, 2.576); near(state.sizeX, 5.152); near(state.sizeZ, 5.152);
    near(state.x, 3.5); near(state.z, -2.8);
    assert.equal(state.startX, state.endX); assert.equal(state.startZ, state.endZ);
    near(state.radius * state.progress, w.r * .028 * age / w.delay);
    assert.equal(state.boss, 0); assert.equal(state.angle, 0);
    assert.equal(Object.hasOwn(state, 'color'), false);
  }
  assert.deepEqual(warningState(w), warningState({ ...w, color: '#ffffff' }));
});

test('Rotated lanes preserve origin, endpoint, midpoint, full width and linear fill', () => {
  for (const angle of [0, Math.PI / 2, .73, -2.17, Math.PI * 9, -Math.PI * 14 + .31]) {
    const w = Object.freeze(lane({ angle })), state = warningState(w, .028);
    near(state.startX, 3.5); near(state.startZ, -2.8);
    near(state.endX, (w.x + Math.cos(angle) * w.len) * .028);
    near(state.endZ, (w.y + Math.sin(angle) * w.len) * .028);
    near(state.x, (state.startX + state.endX) / 2);
    near(state.z, (state.startZ + state.endZ) / 2);
    assert(state.angle >= -Math.PI && state.angle < Math.PI);
    near(state.length, 28); near(state.width, 1.204);
    assert.equal(state.sizeX, state.length); assert.equal(state.sizeZ, state.width);
    near(Math.hypot(state.endX - state.startX, state.endZ - state.startZ) * state.progress, 7);
    const halfX = -Math.sin(state.angle) * state.width / 2;
    const halfZ = Math.cos(state.angle) * state.width / 2;
    near(Math.hypot(halfX * 2, halfZ * 2), w.width * .028);
  }
});

test('Repeated render reads remain stable while paused and expired warnings have no tail', () => {
  const w = circle(), first = warningState(w);
  for (let frame = 0; frame < 100; frame++) assert.deepEqual(warningState(w), first);
  assert.equal(w.age, .3); assert.equal(first.progress, .25);
  near(first.remaining, .9); assert.equal(first.age, w.age); assert.equal(first.delay, w.delay);
  w.age = .6; assert.equal(warningState(w).progress, .5);
  w.age = w.delay; assert.equal(warningState(w), null); assert.deepEqual(snapshotWarnings([w]), []);
  w.age += .01; assert.equal(warningState(w), null);
});

test('Invalid native data and invalid scaled geometry are excluded without coercion', () => {
  const invalid = [null, {}, circle({ type: '0' }), circle({ type: 2 }), circle({ age: -1 }),
    circle({ age: NaN }), circle({ age: '0' }), circle({ delay: 0 }), circle({ delay: Infinity }),
    circle({ x: NaN }), circle({ y: Infinity }), circle({ r: 0 }), circle({ r: -1 }),
    circle({ r: '92' }), lane({ angle: NaN }), lane({ len: 0 }), lane({ width: -1 }),
    lane({ width: Infinity }), circle({ x: Number.MAX_VALUE }), circle({ r: Number.MAX_VALUE })];
  for (const w of invalid) assert.equal(warningState(w, 2), null);
  for (const scale of [0, -1, NaN, Infinity, '1']) assert.equal(warningState(circle(), scale), null);
  assert.deepEqual(snapshotWarnings(undefined), []);
});

test('Snapshots take 80 actual active warnings, skip expired entries and never mutate inputs', () => {
  assert.equal(WARNING_CAPACITY, 80);
  const warnings = Object.freeze([
    Object.freeze(circle({ age: 1.2 })), Object.freeze({}),
    ...Array.from({ length: 85 }, (_, x) => Object.freeze(circle({ x })))
  ]);
  const before = JSON.stringify(warnings), states = snapshotWarnings(warnings);
  assert.equal(states.length, 80); assert.deepEqual(states.map(s => s.x), Array.from({ length: 80 }, (_, x) => x));
  assert.equal(JSON.stringify(warnings), before);
  states[0].x = 999; assert.equal(warnings[2].x, 0);
});

test('All 48 native Boss attacks retain exact warning shape, timing and expiry', () => {
  let checked = 0;
  for (let boss = 0; boss < 8; boss++) for (const rage of [0, 1]) for (let sequence = 0; sequence < 3; sequence++) {
    const s = simulation({ seed: 91037, visual: true });
    s.start({ hero: 0, difficulty: 0 }); s.clear(); s.boss.clear(); s.raw().run.invincible = true;
    const i = s.spawn(boss, 2, 250, -100);
    s.enemies.phase[i] = rage; s.enemies.cool[i] = sequence; s.boss.attack(i);
    const native = Array.from(s.warnings), states = snapshotWarnings(s.warnings, .028);
    assert.equal(states.length, native.length);
    native.forEach((w, n) => {
      const state = states[n]; checked++;
      assert.equal(state.boss, boss); assert.equal(state.age, 0); assert.equal(state.progress, 0);
      assert.equal(state.remaining, w.delay); assert.equal(state.delay, w.delay);
      near(state.startX, w.x * .028); near(state.startZ, w.y * .028);
      if (w.type === 0) near(state.radius, w.r * .028);
      else {
        near(state.length, w.len * .028); near(state.width, w.width * .028);
        near(state.endX, (w.x + Math.cos(w.angle) * w.len) * .028);
        near(state.endZ, (w.y + Math.sin(w.angle) * w.len) * .028);
      }
    });
    const dt = native.length ? Math.min(...native.map(w => w.delay)) / 2 : .1;
    s.boss.updateWarnings(dt);
    for (const w of native) {
      const state = warningState(w, .028);
      near(state.progress, dt / w.delay); near(state.remaining, w.delay - dt);
      assert.deepEqual(warningState(w, .028), state, 'pause does not advance render state');
    }
    s.boss.updateWarnings(10);
    assert.deepEqual(snapshotWarnings(s.warnings), []);
    for (const w of native) assert.equal(warningState(w), null, 'expired references never create a visual tail');
  }
  assert(checked > 200, 'exercise native warnings across all attack cases');
});
