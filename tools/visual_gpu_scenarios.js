/* GPU 验收的可复现战斗夹具；仅手动注入 ?test 页，不属于玩家游戏。 */
(() => {
  if (!new URLSearchParams(location.search).has('test')) throw new Error('GPU QA requires ?test');
  const N = window.__NR, V = window.__NR_VISUAL_BRIDGE;
  const regions = ['cathedral', 'archive', 'foundry', 'throne'];
  const heroes = ['aurelian', 'mordred', 'volt', 'nyx', 'seraph', 'isolde'];
  async function ready(predicate, timeoutMs = 12000) {
    const deadline = performance.now() + timeoutMs;
    while (!predicate(V.metrics())) {
      if (performance.now() > deadline) throw new Error('GPU fixture assets not ready');
      await new Promise(resolve => requestAnimationFrame(resolve));
    }
  }
  async function setup({ hero = 0, stage = 0, party = [], enemies = 0, boss = null, swords = 12 } = {}) {
    window.__NR_MANUAL_TEST = true;
    for (let slot = 1; slot <= 3; slot++) N.coop.config(slot, party[slot - 1] == null ? 'off' : 'bot', party[slot - 1] ?? slot);
    N.start({ hero, mode: 'bossrush', difficulty: 1, invincible: true });
    N.bossEffects.isolate(); N.coop.clear(); N.pickupEffects.clear();
    N.quality('high'); N.skills.options({ bloom: true, shake: false, reducedMotion: false });
    V.setWeaponFX('hero'); V.setSkillFX(true); V.setBossFX(true); V.setWarningFX(true); V.setPickupFX(true); V.setChestRewards(true);
    N.setPlayer({ x: 0, y: 0, aim: 0, swords, ult: 100, shield: 0, skillCD: 0 });
    N.coop.raw().units.filter(a => a.id !== 'human').forEach((a, i) => N.coop.setAgent(a.id, {
      x: [-110, 95, 0][i], y: [65, 65, -110][i], aim: 0, swords, ult: 100, shield: 0, skillCD: 0,
      order: { tactic: 'hold', autoSkills: false },
    }));
    N.bossEffects.stage(stage);
    if (enemies) N.saturate(enemies);
    if (boss != null) { N.spawnBoss(boss); N.bossEffects.place({ x: 230, y: -80, timer: 30, speed: 0 }); }
    N.advance(.1);
    const keys = [hero, ...party].flatMap(h => [`hero:${heroes[h]}`, `blade-${heroes[h]}`]);
    if (boss != null) keys.push(`boss-${boss}`);
    await ready(m => m.presentation?.kind === 'battle' && keys.every(k => m.assets[k] === 'ready') && m.env.arenas[regions[stage]] === 'ready');
    return { snapshot: N.snapshot(), metrics: V.metrics() };
  }
  function chest() {
    N.setPlayer({ ult: 45, shield: 0 });
    N.pickupEffects.spawn({ kind: 2, x: 0, y: 0 });
    N.advance(1 / 60);
  }
  function warnings(count = 12) {
    for (let i = 0; i < count; i++) {
      const x = -260 + (i % 6) * 95, y = -190 + Math.floor(i / 6) * 115;
      if (i % 2) N.warningEffects.lane({ x, y, angle: .15 * i, len: 270, width: 48, delay: 20 });
      else N.warningEffects.circle({ x, y, r: 75, delay: 20 });
    }
  }
  function castParty() {
    for (const a of N.coop.raw().units) {
      if (a.id === 'human') N.setPlayer({ skillCD: 0, ult: 100 });
      else N.coop.setAgent(a.id, { skillCD: 0, ult: 100 });
      const uid = a.id === 'human' ? 0 : +a.id.slice(1);
      N.skills.cast(uid); N.skills.ultimate(uid);
    }
  }
  function pickups(count = 120) {
    for (let i = 0; i < count; i++) N.pickupEffects.spawn({ kind: i % 11 === 0 ? 1 : 0,
      x: -380 + i % 16 * 49, y: -250 + Math.floor(i / 16) * 60, value: [2, 12, 35][i % 3] });
  }
  async function bossLive(boss, rage) {
    await setup({ hero: 0, stage: Math.floor(boss / 2), boss, enemies: 48, swords: 8 });
    const triggered = [], phaseSamples = [];
    const startTime = N.snapshot().time;
    let sequence = 0, watching = true, nextPhase = 0;
    function observe() {
      if (!watching) return;
      const t = N.snapshot().time - startTime;
      if (sequence < 3 && t >= sequence * .8) {
        N.bossEffects.attack({ sequence, rage });
        triggered.push({ sequence: sequence++, time: N.snapshot().time });
      }
      if (t >= nextPhase) {
        const m = V.metrics(), b = N.bossEffects.observe();
        phaseSamples.push({ time: N.snapshot().time, active: m.bossFX.active.length,
          heads: m.bossFX.projectiles.heads, warnings: b.warnings.length, zones: b.zones.length,
          dropped: m.bossFX.dropped, clipped: m.bossFX.clipped });
        nextPhase += .2;
      }
      requestAnimationFrame(observe);
    }
    window.__NR_MANUAL_TEST = false; observe();
    try {
      const report = await window.__NR_GPU_PROBE.measure(`boss-${boss}-${rage ? 'rage' : 'normal'}-live`, { samples: 360, warmup: 30 });
      report.scenario = { boss, rage, triggered, phaseSamples, simulation: 'real RAF, invincible, director isolated; three real attacks at .8 s intervals' };
      return report;
    } finally { watching = false; window.__NR_MANUAL_TEST = true; }
  }
  window.__NR_GPU_QA = { ready, setup, chest, warnings, castParty, pickups, bossLive, heroes, regions };
})();
