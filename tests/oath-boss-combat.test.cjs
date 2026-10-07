const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { simulation, ROOT } = require('./sim_harness.cjs');

function setup(type, rage = 0, sequence = 0, visual = true) {
  const s = simulation({ seed: 91037, visual });
  s.start({ hero: 0, difficulty: 0 }); s.clear(); s.boss.clear();
  s.raw().run.invincible = true;
  const i = s.spawn(type, 2, 250, -100);
  s.enemies.phase[i] = rage; s.enemies.cool[i] = sequence;
  return { s, i };
}
function counts(type, rage, seq) {
  if (type === 0) return seq % 3 === 0 ? [9 + rage * 6, 1, 0] : seq % 3 === 1 ? [0, 1, 0] : [20 + rage * 12, 3 + rage, 0];
  if (type === 1) return seq % 2 === 0 ? [16, 7 + rage * 4, 0] : [3 * (7 + rage * 3), 1, 0];
  if (type === 2) return seq % 3 < 2 ? [0, 2, 0] : [24 + rage * 12, 1, 0];
  if (type === 3) return [24 + rage * 16, seq % 2 ? 5 + rage * 3 : 0, seq % 2 ? 0 : 12 + rage * 8];
  if (type === 4) return seq % 2 === 0 ? [0, 5 + rage * 2, 0] : [32 + rage * 16, 5, 0];
  if (type === 5) return [20 + rage * 12, 4 + rage * 2, seq % 3 === 0 ? 8 : 0];
  if (type === 6) return [3 * (6 + rage * 3) + (seq % 3 === 0 ? 30 : 0), 4 + rage * 2, 0];
  return [36 + rage * 24, 8 + rage * 6 + (seq % 3 === 2 ? 1 : 0), 0];
}
function poolSnapshot(pool) {
  return Object.fromEntries(Object.entries(pool).filter(([,v]) => ArrayBuffer.isView(v)).map(([k,v]) => [k, Array.from(v)]));
}

test('All eight Boss patterns record only actual shots, warnings and accepted summon generations', () => {
  for (let type = 0; type < 8; type++) for (const rage of [0, 1]) for (let seq = 0; seq < 3; seq++) {
    const { s, i } = setup(type, rage, seq), E = s.enemies, H = s.boss.hostiles;
    s.boss.attack(i);
    const e = s.boss.events()[0], expected = counts(type, rage, seq);
    assert.deepEqual([e.shots, e.warnings.length, e.summons.length], expected, `${type}/${rage}/${seq}`);
    assert.equal(H.count, e.shots); assert.equal(s.warnings.length, e.warnings.length);
    assert.equal(e.sequence, seq); assert.equal(e.source, i); assert.equal(e.generation, E.gen[i]);
    assert.equal(E.cool[i], seq + 1);
    for (const p of e.summons) {
      assert.equal(E.a[p.target], 1); assert.equal(p.generation, E.gen[p.target]);
      assert.equal(p.x, E.x[p.target]); assert.equal(p.y, E.y[p.target]); assert.equal(p.r, E.radius[p.target]);
    }
    for (let j = 0; j < H.max; j++) if (H.a[j]) {
      assert.equal(H.boss[j], type + 1); assert.equal(H.source[j], i);
      assert.equal(H.sourceGen[j], E.gen[i]); assert.equal(H.attackSeq[j], seq); assert(H.gen[j] > 0);
    }
    for (let n = 0; n < e.warnings.length; n++) {
      const w = s.warnings[n], recorded = e.warnings[n];
      for (const key of Object.keys(recorded)) assert.equal(w[key], recorded[key]);
      assert.equal(w.boss.generation, E.gen[i]); assert.equal(w.boss.source, i);
    }
    if (type === 4 && seq % 2 === 0) for (const w of e.warnings.filter(w => w.type === 1)) {
      assert.equal(w.len * .028, 28); assert.equal(w.width * .028, 1.204);
    }
  }
});

test('Capacity rejection does not invent warning, shot or summon records; pooled shot generations advance', () => {
  const { s, i } = setup(3, 1), H = s.boss.hostiles;
  while (s.spawn(0, 0, 500, 500) >= 0) {}
  while (H.alloc() >= 0) {}
  while (s.warnings.length < 80) s.warnings.push({});
  s.boss.attack(i);
  assert.equal(s.boss.events()[0].shots, 0); assert.equal(s.boss.events()[0].summons.length, 0);
  s.enemies.type[i] = 5; s.boss.attack(i);
  assert.equal(s.boss.events()[1].warnings.length, 0);
  H.clear(); s.boss.clear(); s.enemies.type[i] = 3; s.boss.attack(i);
  const first = Array.from(H.gen); H.clear(); s.boss.attack(i);
  for (let j = 0; j < H.max; j++) if (H.a[j]) assert.equal(H.gen[j], first[j] + 1);
});

test('Impacts occur exactly once at real warning expiry, including true mechanical beam dimensions', () => {
  const { s, i } = setup(4, 1);
  s.boss.attack(i); const warnings = Array.from(s.warnings);
  s.boss.updateWarnings(.8);
  assert.equal(s.boss.events().filter(e => e.kind === 'impact').length, 0);
  s.boss.updateWarnings(.06);
  assert.equal(s.boss.events().filter(e => e.kind === 'impact').length, 1);
  s.boss.updateWarnings(.1);
  const impacts = s.boss.events().filter(e => e.kind === 'impact');
  assert.equal(impacts.length, warnings.length); assert.equal(s.warnings.length, 0);
  for (const impact of impacts) {
    const warning = warnings.find(w => w.type === (impact.shape === 'line' ? 1 : 0) && w.x === impact.x && w.y === impact.y && (w.type === 0 || w.angle === impact.angle));
    assert(warning); assert.equal(impact.source, i); assert.equal(impact.sequence, 0);
    if (impact.shape === 'line') { assert.equal(impact.len, warning.len); assert.equal(impact.width, warning.width); }
    else assert.equal(impact.r, warning.r);
  }
  s.boss.updateWarnings(1); assert.equal(s.boss.events().filter(e => e.kind === 'impact').length, warnings.length);
});

test('Actual void and venom zones retain 3.4s native TTL and survive Boss death and slot reuse', () => {
  for (const type of [5, 6]) {
    const { s, i } = setup(type), generation = s.enemies.gen[i];
    s.boss.attack(i);
    // Reach all pending impacts using normal simulation-sized steps, preserving native creation-frame age.
    for (let n = 0; n < 80; n++) s.boss.updateWarnings(.02);
    const events = s.boss.events().filter(e => e.kind === 'zone');
    assert.equal(events.length, 4); assert.equal(s.zones.length, 4);
    assert.equal(new Set(events.map(e => e.zoneId)).size, 4);
    for (const e of events) {
      const z = s.zones.find(z => z.id === e.zoneId);
      assert(z); assert.equal(e.duration, 3.4); assert.equal(z.life, 3.4); assert.equal(z.r, e.r);
      assert.equal(e.generation, generation); assert.equal(z.boss.generation, generation);
    }
    const live = Array.from(s.zones); s.damage(i, 1e9, 0, false); assert.equal(s.enemies.a[i], 0);
    assert.equal(s.spawn(0, 0, -400, -400), i); assert.notEqual(s.enemies.gen[i], generation);
    s.boss.updateWarnings(.02);
    for (const z of live) assert(s.zones.includes(z));
    for (const z of live) assert.equal(z.boss.generation, generation);
    for (let n = 0; n < 180; n++) {
      s.boss.updateWarnings(.02);
      for (const z of live) assert.equal(s.zones.includes(z), z.age < z.life);
    }
    assert.equal(s.zones.length, 0);
  }
});

test('Charge and enrage are emitted once at actual transitions; recording resets on restart and is bounded', () => {
  const { s, i } = setup(2); s.boss.attack(i);
  assert.equal(s.boss.events().filter(e => e.kind === 'charge').length, 0);
  for (let n = 0; n < 32; n++) s.boss.updateEnemies(.02);
  assert.equal(s.boss.events().filter(e => e.kind === 'charge').length, 0);
  s.boss.updateEnemies(.02);
  assert.equal(s.boss.events().filter(e => e.kind === 'charge').length, 1);
  assert.equal(s.boss.events().find(e => e.kind === 'charge').duration, .62);
  s.enemies.timer[i] = 100; s.enemies.hp[i] = s.enemies.maxhp[i] * .49;
  s.boss.updateEnemies(.02); s.boss.updateEnemies(.02);
  assert.equal(s.boss.events().filter(e => e.kind === 'enrage').length, 1);
  for (let n = 0; n < 140; n++) s.boss.attack(i);
  assert.equal(s.boss.events().length, 128);
  assert(s.boss.events().every((e, n, es) => !n || e.id > es[n - 1].id));
  s.start(); assert.equal(s.boss.events().length, 0);
});

test('Boss event capture consumes no RNG and leaves seeded gameplay identical with recording disabled', () => {
  for (let type = 0; type < 8; type++) {
    const plain = setup(type, 0, 0, false), hd = setup(type, 0, 0, true);
    for (const { s, i } of [plain, hd]) {
      for (let seq = 0; seq < 3; seq++) {
        s.enemies.phase[i] = seq === 2 ? 1 : 0;
        s.boss.attack(i);
        for (let n = 0; n < 100; n++) { s.boss.updateHostiles(.02); s.boss.updateWarnings(.02); }
      }
    }
    assert.equal(hd.s.randomState(), plain.s.randomState(), `Boss ${type} RNG`);
    assert.deepEqual(poolSnapshot(hd.s.enemies), poolSnapshot(plain.s.enemies));
    assert.deepEqual(poolSnapshot(hd.s.boss.hostiles), poolSnapshot(plain.s.boss.hostiles));
    assert.equal(hd.s.raw().P.hp, plain.s.raw().P.hp); assert.equal(hd.s.raw().run.damageTaken, plain.s.raw().run.damageTaken);
    assert.equal(hd.s.zones.length, plain.s.zones.length); assert.equal(plain.s.boss.events().length, 0);
  }
  // Optional source injection permits independent pre-change baselines without invoking git.
  const s = simulation({ coreSource: fs.readFileSync(path.join(ROOT, 'src/core.js'), 'utf8'), visual: true });
  s.start(); assert.equal(typeof s.boss.attack, 'function');
});
