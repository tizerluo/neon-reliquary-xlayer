import { BOSS_NAMES, cue, effect, caster } from './common.mjs';

// 军阵只在成功召唤的真实位置立起碎符；起手不预演之后的地击。
function attack(c) {
  const cues = [
    cue(0, caster(c, 'wing', '元帅肋骨军旗', { radius: 2.15, length: 1.55, height: 1.9, petals: c.rage ? 7 : 5, y: 1.15, color: '#584366', gain: .42, life: .65, motion: 'expand' })),
    cue(0, caster(c, 'wing', '魂刃军旗亮棱', { radius: 1.9, length: 1.15, height: 1.65, petals: 3, y: 1.18, color: '#c5a1f4', gain: .46, life: .45, motion: 'expand' })),
    cue(0, caster(c, 'orb', '魂弹出膛空壳', { radius: 1.2, y: 1.3, pattern: 'void', color: '#8764b2', gain: .34, life: .4, motion: 'collapse' })),
    cue(0, caster(c, 'arc', '军令谱线', { radius: 2.55, width: .045, halfAngle: Math.PI, y: .13, color: '#b5a0d5', gain: .4, life: .48, motion: 'expand' })),
  ];
  // 狂暴最多二十个真实召唤点，单点一个稀疏碎符，完整军阵不超过 24 cue。
  for (const p of (c.summons ?? []).slice(0, 20)) {
    cues.push(cue(0, effect(c, 'decal', '成功召唤亡灵军符', { x: p.x, z: p.z, radius: p.radius ?? .65, pattern: 'void', color: '#ad8cda', gain: .5, life: .78, chargeTime: .1, fadeOut: .4, motion: 'still' })));
  }
  return { cues };
}

function impact(c) {
  const radius = c.radius ?? 2.128;
  return { cues: [
    cue(0, effect(c, 'decal', '地击断裂军谱', { radius, pattern: 'void', color: '#6d4c91', gain: .48, life: .55, chargeTime: .05 })),
    cue(0, effect(c, 'shard', '肋骨魂刃刺起', { radius, count: c.rage ? 7 : 5, spread: radius * .65, width: .12, height: 1.55, y: .08, color: '#baa0e5', gain: .56, life: .4, motion: 'rise' })),
    cue(0, effect(c, 'arc', '前半军令断弧', { radius, width: .07, halfAngle: .88, color: '#c5a1f4', gain: .45, life: .38, motion: 'expand' })),
    cue(0, effect(c, 'arc', '后半军令断弧', { radius, width: .045, angle: (c.angle ?? 0) + Math.PI, halfAngle: .66, color: '#8764b2', gain: .4, life: .46, motion: 'expand' })),
  ] };
}

function enrage(c) {
  return { cues: [
    cue(0, caster(c, 'wing', '狂暴亡军裂旗', { radius: 3.1, length: 1.8, height: 2.5, petals: 7, y: .9, color: '#63427c', gain: .42, life: .9, motion: 'expand' })),
    cue(0, caster(c, 'shard', '元帅冠上魂刃', { count: 7, spread: 1.1, width: .11, height: 1.5, y: 2.2, color: '#d1b0ee', gain: .52, life: .72, motion: 'rise' })),
    cue(0, caster(c, 'orb', '军魂收束', { radius: 2.45, y: 1.2, color: '#9672c0', gain: .32, life: .8, motion: 'collapse' })),
  ] };
}

export default { boss: 3, name: BOSS_NAMES[3], attack, impact, charge: () => ({ cues: [] }), enrage, zone: () => ({ cues: [] }),
  projectile: { shape: 'wisp', color: '#c5a1f4', core: '#e4cdf6', tail: '#64417e', size: .3, length: .84, gain: .61 } };
