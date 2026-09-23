// Control-plane regression fixtures. These are not model or browser play evidence.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const {simulation} = require('./sim_harness.cjs');

function party(externalSlots) {
  const s = simulation();
  s.oath.profile.loadout.leader = 'external';
  for (const slot of externalSlots) s.oath.profile.loadout.slots[slot - 1].mode = 'external';
  s.startFull();
  const identities = [0, ...externalSlots].map(slot => {
    const joined = s.call('nr_join', {slot, name: `Fixture ${slot}`});
    assert.equal(joined.ok, true);
    return joined;
  });
  s.chooseRoute('clear');
  return {s, identities};
}
function command(s, identity, seq, values = {}) {
  return s.call('nr_command', {
    agentId: identity.agentId, token: identity.token, runId: identity.runId,
    seq, tactic: 'guard', autoSkills: false, duration: 1, ...values,
  });
}

for (const slots of [[], [2], [1, 2], [1, 2, 3]]) {
  test(`${slots.length} external companions + ${3 - slots.length} chips keep independent control and upgrades`, () => {
    const {s, identities} = party(slots);
    const before = s.call('nr_observe');
    assert.equal(before.units.length, 4);
    assert.equal(before.scaling.agents, 3);
    assert.equal(before.units.filter(u => u.controller === 'chip').length, 3 - slots.length);
    identities.forEach((id, index) => {
      const result = command(s, id, 1, {tactic: index ? 'follow' : 'assault', upgradePath: index % 3});
      assert.equal(result.ok, true, result.error);
    });
    if (identities.length > 1) {
      const forged = {...identities[1], token: identities[0].token};
      assert.match(command(s, forged, 2).error, /UNAUTHORIZED/);
    }
    // A level event is a unit fixture, not XP/combat acceleration in the browser.
    s.level();
    identities.forEach((id, index) => {
      const unit = s.call('nr_observe').units.find(u => u.id === id.agentId);
      assert.equal(unit.level, 2);
      assert.equal(unit.upgradePath, index % 3);
      assert.equal(unit.pendingUpgrades, 0);
    });
    for (let frame = 0; frame < 90; frame++) s.tick(1 / 60);
    const after = s.call('nr_observe');
    identities.forEach(id => assert.equal(after.units.find(u => u.id === id.agentId).tactic, 'guard'));
    for (const unit of after.units.filter(u => u.controller === 'chip')) {
      assert(unit.chip.decisions > 0);
      assert.equal(unit.chip.fault, null);
    }
    const clock = after.time;
    const decisions = after.units.map(u => u.chip?.decisions ?? null);
    s.pause();
    assert.equal(command(s, identities[0], 2).error, 'NOT_PLAYING');
    for (let frame = 0; frame < 60; frame++) s.tick(1 / 60);
    assert.equal(s.call('nr_observe').time, clock);
    assert.deepEqual(Array.from(s.call('nr_observe').units, u => u.chip?.decisions ?? null), Array.from(decisions));
  });
}

test('An external companion leaving and rejoining cannot reuse its identity or lower active encounter difficulty', () => {
  const {s, identities} = party([1, 2]);
  const original = identities[1], scaling = JSON.stringify(s.call('nr_observe').scaling);
  assert.equal(s.call('nr_leave', {agentId: original.agentId, token: original.token}).ok, true);
  assert.match(command(s, original, 1).error, /UNAUTHORIZED/);
  assert.equal(JSON.stringify(s.call('nr_observe').scaling), scaling);
  const replacement = s.call('nr_join', {slot: 1, name: 'Replacement'});
  assert.equal(replacement.ok, true);
  assert.equal(replacement.pending, true);
  assert.notEqual(replacement.agentId, original.agentId);
  assert.equal(command(s, replacement, 1).error, 'DEPLOYMENT_PENDING');
  // Starting a new run exercises identity/run isolation independently of combat.
  s.startFull();
  s.chooseRoute('clear');
  assert.equal(command(s, replacement, 2).error, 'STALE_RUN');
  const current = {...replacement, runId: s.call('nr_observe').runId};
  assert.equal(command(s, current, 3).ok, true);
  assert.equal(s.call('nr_observe').units.length, 4);
});

test('Expedition event names preserve encounter type as separate metadata', () => {
  const {s} = party([]);
  const started = s.call('nr_events', {limit: 64}).events.find(e => e.type === 'expedition_encounter');
  assert.equal(started.encounterType, 'clear');
  // Boundary fixture only: live browser acceptance never sets kills or time.
  const {run} = s.raw();
  run.expedition.clock = 100;
  run.kills = run.expedition.startKills + 200;
  s.tick(1 / 60);
  const completed = s.call('nr_events', {limit: 64}).events.find(e => e.type === 'encounter_complete');
  assert.equal(completed.encounterType, 'clear');
  assert.equal(s.raw().state, 'camp');
});
