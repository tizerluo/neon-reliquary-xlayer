import { BOSS_NAMES, cue, effect, caster } from './common.mjs';

const DARK = '#214f3c', GREEN = '#67bb77', CORE = '#b1eac2';
const TAU = Math.PI * 2;

// 毒冠始终是三瓣：只沿本体出膛，不预约毒池位置或复制危险弹。
function attack(c) {
  const cues = [
    cue(0, caster(c, 'petals', '三位毒冠暗瓣', { petals: 3, radius: 1.5, length: .8, width: .09, height: .13, y: 1.1, life: .48, chargeTime: .22, gain: .36, color: DARK })),
    cue(0, caster(c, 'petals', '三位毒冠叶脉', { petals: 3, radius: 1.5, length: .68, width: .025, height: .10, y: 1.14, life: .38, chargeTime: .18, gain: .55, color: GREEN })),
  ];
  for (let i = 0; i < 3; i++) {
    const a = (c.angle ?? 0) + i * TAU / 3;
    cues.push(cue(0, caster(c, 'arc', '毒扇出膛唇沿', { angle: a, radius: 1.22, halfAngle: .34, width: .045, y: .65, life: .30, chargeTime: .16, motion: 'expand', gain: .47, color: CORE })));
  }
  if (c.rage) cues.push(cue(0, caster(c, 'petals', '狂暴三瓣逆冠', { angle: (c.angle ?? 0) + Math.PI / 3, petals: 3, radius: 1.85, length: .55, width: .023, height: .12, y: 1.5, life: .42, chargeTime: .2, gain: .40, color: GREEN })));
  return { cues };
}

// 真正到期的落击以三瓣裂口和低矮液珠回应；所有几何都收在真实半径内。
function impact(c) {
  const r = c.radius ?? 2.072;
  return { cues: [
    cue(0, effect(c, 'decal', '毒液三位裂底', { shape: 'seal', pattern: 'fault', radius: r, life: .48, chargeTime: .1, gain: .32, color: DARK })),
    cue(0, effect(c, 'petals', '三瓣毒液外溅', { petals: 3, radius: r * .62, length: r * .29, width: .085, height: .08, y: .11, life: .38, chargeTime: .18, motion: 'expand', gain: .51, color: GREEN })),
    cue(0, effect(c, 'petals', '三瓣毒液亮脉', { petals: 3, radius: r * .62, length: r * .24, width: .021, height: .055, y: .14, life: .25, chargeTime: .12, motion: 'expand', gain: .48, color: CORE })),
    cue(0, effect(c, 'shard', '低矮毒液碎滴', { count: c.rage ? 6 : 3, spread: r * .58, width: .11, height: .24, y: .12, life: .30, chargeTime: .15, motion: 'rise', gain: .38, color: GREEN })),
  ] };
}

// 危险区是世界锚点，Boss 死亡不会抹掉仍有伤害的 3.4 秒毒池。
// 外裂纹给出实际边界，液脉三瓣留出地面；三轮泡壳均在期满前结束。
function zone(c) {
  const r = c.radius ?? 2.072, duration = c.duration ?? 3.4;
  const cues = [
    cue(0, effect(c, 'decal', '真实毒池外裂纹', { pattern: 'fault', radius: r, life: duration, chargeTime: .16, fadeIn: .08, fadeOut: .20, gain: .34, color: GREEN })),
    cue(0, effect(c, 'petals', '毒池三瓣液脉', { petals: 3, radius: r * .63, length: r * .30, width: .036, height: .025, y: .085, life: duration, chargeTime: .22, fadeOut: .20, gain: .30, color: DARK })),
  ];
  for (let i = 0; i < 3; i++) {
    const a = (c.angle ?? 0) + i * TAU / 3;
    cues.push(cue(i * duration / 3, effect(c, 'orb', '毒池稀疏泡壳', { offset: [Math.cos(a) * r * .45, .13, Math.sin(a) * r * .45], angle: 0, radius: r * .11, y: .08, life: Math.min(.68, duration / 3), chargeTime: .42, fadeOut: .24, motion: 'expand', pattern: 'void', gain: .29, color: CORE })));
  }
  return { cues };
}

function enrage(c) {
  return { cues: [
    cue(0, caster(c, 'petals', '狂暴三位裂冠', { petals: 3, radius: 1.8, length: .86, width: .045, height: .2, y: 1.05, life: .65, chargeTime: .28, gain: .48, color: GREEN })),
    cue(0, caster(c, 'orb', '三位毒核内缩', { radius: .5, y: 1.25, motion: 'collapse', pattern: 'void', life: .52, chargeTime: .48, gain: .38, color: CORE })),
  ] };
}

export default {
  boss: 6, name: BOSS_NAMES[6], attack, impact, zone, enrage,
  charge: () => ({ cues: [] }),
  projectile: { shape: 'venom', color: '#67bb77', core: '#b1eac2', tail: '#214f3c', size: .34, length: .62, gain: .58 },
};
