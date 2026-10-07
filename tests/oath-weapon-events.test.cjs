const { test } = require('node:test');
const assert = require('node:assert/strict');
const { simulation } = require('./sim_harness.cjs');

test('A final piercing collision remains observable after the blade is released', () => {
  const s = simulation({ visual: true }); s.start({ hero: 1 }); s.clear();
  const P = s.raw().P, E = s.enemies, B = s.weapon.blades;
  s.spawn(0, 0, 35, 0); s.hash();
  const b = s.weapon.shoot(0, 0, 0, 0, 1, 0, 2, 0, P);
  B.x[b] = 60; B.pierce[b] = 1; s.weapon.collide(b, P);
  assert.equal(B.a[b], 0);
  const hit = s.weapon.events.find(e => e.kind === 'hit');
  assert.equal(hit.hero, 1); assert.equal(hit.owner, P.uid);
  assert.equal(hit.x, 35); assert.equal(hit.generation, E.gen[0]);
  assert.equal(hit.killed, false);
});

test('Life return events require real healing and retain the actual companion owner', () => {
  const s = simulation({ visual: true }); s.start({ hero: 0, companion: 4 }); s.clear();
  const a = s.raw().actor; a.hp = a.maxhp; s.spawn(0, 0, 30, 0); s.enemies.hp[0] = 1e8;
  for (let i = 0; i < 120; i++) s.damage(0, 1, 0, false, a);
  assert.equal(s.weapon.events.filter(e => e.kind === 'drain').length, 0);
  a.hp -= 5; const before = a.hp;
  for (let i = 0; i < 120; i++) s.damage(0, 1, 0, false, a);
  const drains = s.weapon.events.filter(e => e.kind === 'drain');
  assert(drains.length > 0); assert(drains.every(e => e.owner === a.uid && e.amount > 0));
  assert(Math.abs(drains.reduce((sum, e) => sum + e.amount, 0) - (a.hp - before)) < 1e-9);
});

test('A frosted death keeps its coordinates and generation when the enemy slot is reused', () => {
  const s = simulation({ visual: true }); s.start({ hero: 5 }); s.clear();
  s.spawn(0, 0, 44, 17); const E = s.enemies, generation = E.gen[0];
  E.freeze[0] = 1; s.damage(0, 10000, 0, false);
  s.spawn(0, 0, -100, -200);
  const event = s.weapon.events.find(e => e.kind === 'shatter');
  assert.equal(event.x, 44); assert.equal(event.y, 17); assert.equal(event.generation, generation);
  assert.notEqual(E.gen[0], event.generation);
});

test('Visual records are bounded, sequenced, and cleared before a new run', () => {
  const s = simulation({ visual: true }); s.start({ hero: 0 }); s.clear();
  const P = s.raw().P, B = s.weapon.blades;
  s.spawn(0, 0, 35, 0); s.hash(); s.enemies.hp[0] = 1e8;
  const b = s.weapon.shoot(0, 0, 0, 0, 1, 0, 2, 0, P); B.x[b] = 60; B.pierce[b] = 1000;
  for (let n = 0; n < 300; n++) { B.lastHit[b] = -1; s.weapon.collide(b, P); }
  assert.equal(s.weapon.events.length, 128);
  assert(s.weapon.events.every((e, n, list) => !n || e.id > list[n - 1].id));
  s.start({ hero: 3 }); assert.equal(s.weapon.events.length, 0);
});

test('Enabling visual event capture leaves seeded combat and its random stream identical', () => {
  for (const hero of [0, 2, 4, 5]) {
    const plain = simulation({ seed: 70421, visual: false }), hd = simulation({ seed: 70421, visual: true });
    for (const s of [plain, hd]) {
      s.start({ hero, companion: 5 }); s.raw().P.hp -= 10;
      for (let n = 0; n < 180; n++) s.tick(1 / 60);
    }
    for (const key of ['hp', 'damageDealt', 'kills', 'ult', 'x', 'y']) assert.equal(hd.raw().P[key], plain.raw().P[key], hero + ':' + key);
    for (const key of ['a', 'hp', 'x', 'y', 'slow', 'freeze']) assert.deepEqual(Array.from(hd.enemies[key]), Array.from(plain.enemies[key]), hero + ':E.' + key);
    for (const key of ['a', 'x', 'y', 'lastHit', 'target']) assert.deepEqual(Array.from(hd.weapon.blades[key]), Array.from(plain.weapon.blades[key]), hero + ':B.' + key);
    assert.equal(plain.weapon.events.length, 0);
  }
});
