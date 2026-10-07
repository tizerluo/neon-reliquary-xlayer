const { test } = require('node:test');
const assert = require('node:assert/strict');
const recipes = import('../visual-game/boss-effects/index.mjs');
const timeline = import('../visual-game/skill-fx-timeline.mjs');
const methods = ['attack', 'impact', 'charge', 'enrage', 'zone'];
const freeze = value => {
  if (value && typeof value === 'object') {
    for (const child of Object.values(value)) freeze(child);
    Object.freeze(value);
  }
  return value;
};
const context = (boss, fields = {}) => ({ boss, owner: 37, x: 3.5, z: -2.8, angle: .73,
  seed: 41, sequence: 0, rage: false, duration: .62, shape: 'circle', radius: 2,
  length: 4, width: 1, summons: [], ...fields });

// These are combat dimensions, not a snapshot of ornamental cue counts or colors.
const circles = [[5.32, 6.72, 1.68], [1.484, 6.86], [2.576, 7.28, 8.82],
  [2.128], [3.5, 1.96], [2.408], [2.072], [1.596]];
const lines = [[0, 18.2, 1.848], [2, 20.16, 2.184], [4, 28, 1.204], [7, 25.2, 2.8]];

test('Boss event adapter scales actual dimensions and sanitizes core circle/line shape', async () => {
  const { bossContext, primitiveContext, BOSS_EFFECTS } = await recipes;
  const { compilePreset } = await timeline;
  const near = (actual, expected) => assert(Math.abs(actual - expected) < 1e-10);
  for (const [boss, length, width] of lines) {
    const event = freeze({ boss, source: 15, generation: 4, sequence: 2, rage: 1,
      x: 125, y: -100, angle: 9 * Math.PI, r: 92, time: 6.3, id: 91,
      shape: 'line', len: length / .028, width: width / .028, duration: .62,
      summons: [{ x: 400, y: -500, r: 22, target: 9, generation: 3 }] });
    const before = JSON.stringify(event), c = bossContext(event);
    near(c.x, 3.5); near(c.z, -2.8); near(c.radius, 2.576);
    near(c.length, length); near(c.width, width);
    assert.equal(c.shape, 'line'); assert.equal(c.sequence, 2); assert(c.rage);
    assert.equal(c.owner, ((4 * 2048 + 15) * 4)); assert.equal(c.seed, 91);
    assert(c.angle >= -Math.PI && c.angle <= Math.PI);
    near(c.summons[0].x, 11.2); near(c.summons[0].z, -14);
    near(c.summons[0].radius, .616);
    assert.equal(c.summons[0].target, 9); assert.equal(c.summons[0].generation, 3);
    const primitive = primitiveContext(c);
    assert.deepEqual(Object.keys(primitive).sort(), ['angle','boss','hero','owner','seed','x','z']);
    compilePreset(BOSS_EFFECTS[boss].impact(c), primitive);
    const circle = bossContext({ ...event, shape: 'circle', r: circles[boss][0] / .028 });
    near(circle.radius, circles[boss][0]);
    compilePreset(BOSS_EFFECTS[boss].impact(circle), primitiveContext(circle));
    assert.equal(JSON.stringify(event), before);
    const customScale = bossContext(event, .014); near(customScale.length, length / 2);
    assert.notEqual(bossContext({ ...event, generation: 5 }).owner, c.owner, 'reused enemy slot has a new visual identity');
  }
  const zone = bossContext({ kind: 'zone', boss: 5, source: 15, generation: 4, x: 125, y: -100,
    angle: 0, id: 99, shape: 'circle', r: 86, duration: 3.4, zoneId: 20, summons: [] });
  assert.equal(zone.owner, 20 * 4 + 3);
  assert.equal(zone.duration, 3.4);
});

test('All eight Boss recipes normalize normal/rage events, remain pure and respect capacity', async () => {
  const { BOSS_EFFECTS } = await recipes, { compilePreset } = await timeline;
  assert.equal(BOSS_EFFECTS.length, 8);
  for (let boss = 0; boss < 8; boss++) {
    const recipe = BOSS_EFFECTS[boss];
    assert.equal(recipe.boss, boss);
    for (const rage of [false, true]) for (let sequence = 0; sequence < 6; sequence++) {
      const cases = circles[boss].map(radius => context(boss, { radius, rage, sequence }));
      const line = lines.find(item => item[0] === boss);
      if (line) cases.push(context(boss, { shape: 'line', length: line[1], width: line[2], rage, sequence }));
      for (const c of cases) {
        freeze(c);
        const before = JSON.stringify(c);
        for (const method of methods) {
          const event = method === 'zone' ? freeze({ ...c, duration: 3.4 }) : c;
          const definition = recipe[method](event);
          assert.deepEqual(definition, recipe[method](event), `${boss}/${method}: deterministic`);
          const compiled = compilePreset(definition);
          assert(compiled.length <= 24, `${boss}/${method}: atomic event capacity`);
          for (const { at, spec } of compiled) {
            assert(at >= 0);
            assert.notEqual(spec.kind, 'feedback', 'Boss effects cannot flash the full screen');
            assert.equal(spec.owner, c.owner);
            if (spec.attach) assert.equal(spec.cancelOnOwnerLoss, true);
          }
        }
        assert.equal(JSON.stringify(c), before);
      }
    }
    const p = recipe.projectile;
    assert(['flame','ice','shell','wisp','lumen','void','venom','feather'].includes(p.shape));
    for (const key of ['color','core','tail']) assert.match(p[key], /^#[0-9a-f]{6}$/i);
    assert(p.size >= .26 && p.size <= .48);
    assert(p.length >= .4 && p.length <= 1.2);
    assert(p.gain >= .45 && p.gain <= .85);
  }
});

test('Impact boundaries retain exact combat radii and full line dimensions including 28m', async () => {
  const { BOSS_EFFECTS } = await recipes, { compilePreset } = await timeline;
  for (let boss = 0; boss < 8; boss++) for (const radius of circles[boss]) {
    const c = context(boss, { radius });
    const compiled = compilePreset(BOSS_EFFECTS[boss].impact(c));
    assert(compiled.some(({ at }) => at === 0), `${boss}: respond when damage resolves`);
    assert(compiled.some(({ spec }) => spec.radius === radius), `${boss}: exact circle boundary`);
    assert(compiled.every(({ spec }) => !spec.attach && !spec.cancelOnOwnerLoss));
  }
  for (const [boss, length, width] of lines) {
    const compiled = compilePreset(BOSS_EFFECTS[boss].impact(context(boss, { shape: 'line', length, width })));
    const boundary = compiled.find(({ spec }) => spec.kind === 'decal' && spec.shape === 'lane');
    assert(boundary);
    assert.equal(boundary.spec.length, length);
    assert.equal(boundary.spec.width, width);
    assert.equal(boundary.at, 0);
  }
});

test('Attack origins cannot invent world impact locations or schedule future ground damage', async () => {
  const { BOSS_EFFECTS } = await recipes, { compilePreset } = await timeline;
  for (const recipe of BOSS_EFFECTS) for (const rage of [false, true]) {
    const c = freeze(context(recipe.boss, { rage, sequence: 2, summons: [],
      points: [{ x: 70, z: 70, radius: 9 }], duration: 1.2 }));
    const attack = compilePreset(recipe.attack(c));
    assert(attack.length > 0);
    assert(attack.every(({ spec }) => spec.attach && spec.x === c.x && spec.z === c.z),
      `${recipe.boss}: non-summoning attack effects belong to the actual caster`);
    assert(attack.every(({ at }) => at < .2), `${recipe.boss}: no scheduled warning expiration impact`);
  }
});

test('Only accepted marshal 12/20 and prophet 8 summon locations receive world effects', async () => {
  const { BOSS_EFFECTS } = await recipes, { compilePreset } = await timeline;
  for (const [boss, total, rage] of [[3, 12, false], [3, 20, true], [5, 8, false], [5, 8, true]]) {
    const summons = Array.from({ length: total }, (_, i) => ({ x: 11 + i * .4, z: -8 + i * .2,
      radius: .6, target: i, generation: 3 }));
    const c = freeze(context(boss, { rage, summons }));
    const compiled = compilePreset(BOSS_EFFECTS[boss].attack(c));
    const world = compiled.filter(({ spec }) => !spec.attach);
    assert.equal(world.length, total);
    assert(compiled.length <= 24);
    for (const { at, spec } of world) {
      assert.equal(at, 0);
      assert(summons.some(p => p.x === spec.x && p.z === spec.z));
      assert.equal(spec.cancelOnOwnerLoss, false);
    }
    const accepted = summons.slice(0, 2);
    const sparse = compilePreset(BOSS_EFFECTS[boss].attack(context(boss, { summons: accepted })));
    assert.equal(sparse.filter(({ spec }) => !spec.attach).length, 2, 'failed spawns create no extra pattern');
  }
});

test('Actual 3.4s void/poison zones persist in world coordinates until hazard expiration', async () => {
  const { BOSS_EFFECTS } = await recipes, { compilePreset, createEffectTimeline } = await timeline;
  for (const boss of [5, 6]) for (const rage of [false, true]) {
    const duration = 3.4, radius = circles[boss][0];
    const c = freeze(context(boss, { owner: 901, duration, radius, rage, zone: true }));
    const compiled = compilePreset(BOSS_EFFECTS[boss].zone(c));
    assert(compiled.length > 0 && compiled.length <= 8);
    assert(compiled.some(({ at, spec }) => at === 0 && spec.life === duration && spec.radius === radius));
    for (const { at, spec } of compiled) {
      assert.equal(spec.attach, false);
      assert.equal(spec.cancelOnOwnerLoss, false);
      assert(at + spec.life <= duration + 1e-10);
      assert.equal(spec.x, c.x); assert.equal(spec.z, c.z);
    }
    const t = createEffectTimeline();
    t.add(compiled, 10);
    let visible = 0;
    t.visit(11.7, () => visible++, spec => spec.cancelOnOwnerLoss);
    assert(visible > 0, 'Boss death cannot hide an active world hazard');
    t.visit(13.40001, () => assert.fail('zone remained after expiration'));
    assert.equal(t.metrics().scheduled, 0);
  }
});

test('Real charge forms follow owner for .62s and cancel without leaving a fake lane', async () => {
  const { BOSS_EFFECTS } = await recipes, { compilePreset, createEffectTimeline } = await timeline;
  for (const boss of [0, 2, 7]) {
    const compiled = compilePreset(BOSS_EFFECTS[boss].charge(context(boss, { duration: .62, width: 2.8 })));
    assert(compiled.length > 0);
    for (const { at, spec } of compiled) {
      assert.equal(at, 0); assert.equal(spec.life, .62);
      assert(spec.attach && spec.cancelOnOwnerLoss);
    }
    const t = createEffectTimeline(); t.add(compiled, 0);
    t.visit(.3, () => assert.fail('dead caster charge remained'), spec => spec.owner === 37 && spec.cancelOnOwnerLoss);
    assert.equal(t.metrics().scheduled, 0);
  }
  for (const boss of [1,3,4,5,6]) assert.equal(BOSS_EFFECTS[boss].charge(context(boss)).cues.length, 0);
});

test('Actual source-only events preserve omitted dimensions so charge defaults remain valid', async () => {
  const { BOSS_EFFECTS, bossContext, primitiveContext } = await recipes;
  const { compilePreset } = await timeline;
  for (const boss of [0, 2, 7]) {
    // corebossMeta carries the source body radius, not warning lane width/length.
    const event = freeze({ kind: 'charge', boss, source: 12, generation: 7,
      sequence: 2, rage: 1, x: 125, y: -100, angle: .8, r: 58,
      duration: .62, time: 7, id: 115 });
    const c = bossContext(event);
    assert.equal(c.length, undefined);
    assert.equal(c.width, undefined);
    assert.equal(c.shape, undefined);
    const compiled = compilePreset(BOSS_EFFECTS[boss].charge(c), primitiveContext(c));
    assert(compiled.length > 0);
    for (const { spec } of compiled) {
      assert.equal(spec.life, .62);
      assert(spec.attach && spec.cancelOnOwnerLoss);
      assert(spec.radius > 0 && spec.width > 0 && spec.length > 0);
    }
  }
  for (let boss = 0; boss < 8; boss++) for (const kind of ['attack', 'enrage']) {
    const c = bossContext(freeze({ kind, boss, source: 12, generation: 7,
      sequence: 0, rage: 1, x: 125, y: -100, angle: .8, time: 7, id: 116 }));
    assert.equal(c.radius, undefined);
    assert.equal(c.length, undefined);
    assert.equal(c.width, undefined);
    assert.equal(c.shape, undefined);
    const compiled = compilePreset(BOSS_EFFECTS[boss][kind](c), primitiveContext(c));
    assert(compiled.length > 0 && compiled.length <= 24);
  }
});
