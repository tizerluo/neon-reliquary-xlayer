import { BOSS_NAMES, cue, effect, caster } from './common.mjs';

const ASH = '#725c48', GOLD = '#cdaa79', EMBER = '#ffad8c';

// 炽天使以短寿命的两层裂翼发射真实羽刃；羽数克制，地面留白。
function attack(c) {
  const cues = [
    cue(0, caster(c, 'wing', '灰烬炽天使暗翼骨', { radius: 2.9, length: .92, height: .28, y: 1.25, petals: c.rage ? 5 : 4, motion: 'expand', life: .48, chargeTime: .19, gain: .36, color: ASH })),
    cue(0, caster(c, 'wing', '灰金窄羽刃冠', { radius: 2.65, length: .61, height: .15, y: 1.31, petals: c.rage ? 5 : 4, motion: 'expand', life: .36, chargeTime: .15, gain: .55, color: GOLD })),
    cue(0, caster(c, 'arc', '羽刃出膛断弧', { radius: 1.5, width: .036, halfAngle: .62, y: .9, tilt: .22, life: .24, chargeTime: .13, motion: 'expand', gain: .49, color: EMBER })),
  ];
  if (c.rage) cues.push(cue(0, caster(c, 'wing', '狂暴裂翼细刃', { angle: (c.angle ?? 0) + Math.PI, radius: 2.3, length: .45, height: .10, y: 1.8, petals: 3, motion: 'expand', life: .29, chargeTime: .14, gain: .42, color: GOLD })));
  return { cues };
}

function impact(c) {
  if (c.shape === 'line') {
    const length = c.length ?? 25.2, width = c.width ?? 2.8;
    // 真实长击从根部向 +X，外层断轨全宽与战斗一致，窄芯只占中央。
    return { cues: [
      cue(0, effect(c, 'decal', '炽天使长击裂轨', { shape: 'lane', pattern: 'fault', length, width, life: .46, chargeTime: .08, gain: .32, color: ASH })),
      cue(0, effect(c, 'ribbon', '灰金长击刀背', { length, width: .14, count: 1, life: .32, chargeTime: .07, gain: .51, color: GOLD, pattern: 'rail' })),
      cue(0, effect(c, 'ribbon', '橙芯裂翼切线', { length, width: .036, count: 1, y: .10, life: .21, chargeTime: .06, gain: .52, color: EMBER, pattern: 'fault' })),
      cue(0, effect(c, 'wing', '长击根部折羽', { radius: Math.min(1.1, width * .36), length: .45, height: .08, y: .14, petals: 3, life: .33, chargeTime: .15, motion: 'expand', gain: .37, color: GOLD })),
    ] };
  }
  const r = c.radius ?? 1.596;
  // 连续落击不是又一圈：三枚破羽压入落点，随后裂翼在真实圈内摊开。
  return { cues: [
    cue(0, effect(c, 'decal', '陨羽落点断痕', { pattern: 'fault', radius: r, life: .38, chargeTime: .06, gain: .30, color: ASH })),
    cue(0, effect(c, 'shard', '灰金陨羽冲击刃', { count: 3, spread: r * .36, width: .13, height: 1.1, y: .48, tilt: .28, life: .25, chargeTime: .13, motion: 'fall', gain: .58, color: GOLD })),
    cue(0, effect(c, 'wing', '落击裂翼余刃', { radius: r * .55, length: r * .28, height: .06, y: .12, petals: 3, life: .34, chargeTime: .17, motion: 'expand', gain: .44, color: EMBER })),
    cue(0, effect(c, 'shard', '陨羽低亮灰片', { count: c.rage ? 5 : 3, spread: r * .58, width: .08, height: .22, y: .08, life: .36, chargeTime: .20, motion: 'rise', gain: .28, color: ASH })),
  ] };
}

// .62 秒真实冲锋只附着本体：一段锋面加两片短尾羽，不投射未来路径。
function charge(c) {
  const duration = c.duration ?? .62, width = c.width ?? 2.8;
  return { cues: [
    cue(0, caster(c, 'arc', '炽天使冲锋灰金锋面', { offset: [.48, .20, 0], radius: width / 2, halfAngle: .62, width: .065, life: duration, chargeTime: .1, fadeOut: .12, gain: .55, color: GOLD })),
    cue(0, caster(c, 'arc', '冲锋橙芯断锋', { offset: [.48, .23, 0], radius: width / 2 * .94, halfAngle: .42, width: .023, life: duration, chargeTime: .08, fadeOut: .12, gain: .49, color: EMBER })),
    cue(0, caster(c, 'wing', '冲锋收束尾羽', { angle: (c.angle ?? 0) + Math.PI, offset: [.35, .32, 0], radius: width * .36, length: .52, height: .07, petals: 3, life: duration, chargeTime: .12, fadeOut: .12, gain: .33, color: ASH })),
  ] };
}

function enrage(c) {
  return { cues: [
    cue(0, caster(c, 'wing', '炽天使狂暴灰金外翼', { radius: 3.3, length: .82, height: .26, y: 1.15, petals: 5, life: .72, chargeTime: .3, motion: 'expand', gain: .42, color: GOLD })),
    cue(0, caster(c, 'wing', '狂暴橙芯短羽', { radius: 2.65, length: .44, height: .13, y: 1.21, petals: 3, life: .48, chargeTime: .24, motion: 'expand', gain: .48, color: EMBER })),
    cue(0, caster(c, 'shard', '狂暴灰烬冠刺', { count: 3, spread: .52, width: .09, height: .62, y: 1.65, life: .52, chargeTime: .25, motion: 'rise', gain: .29, color: ASH })),
  ] };
}

export default {
  boss: 7, name: BOSS_NAMES[7], attack, impact, charge, enrage,
  zone: () => ({ cues: [] }),
  projectile: { shape: 'feather', color: '#cdaa79', core: '#ffad8c', tail: '#725c48', size: .29, length: 1.08, gain: .64 },
};
