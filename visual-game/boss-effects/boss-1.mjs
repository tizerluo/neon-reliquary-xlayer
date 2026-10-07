import { BOSS_NAMES, cue, effect, caster } from './common.mjs';

const DARK = '#23576d', ICE = '#91e6ff', EDGE = '#d7f5ff';
const empty = () => ({ cues: [] });

export default {
  boss: 1, name: BOSS_NAMES[1],
  projectile: { shape: 'ice', color: ICE, core: EDGE, tail: DARK, size: .34, length: 1.12, gain: .59 },
  attack(c) {
    const even = (c.sequence ?? 0) % 2 === 0;
    // 两层扭转冰冠绕本体凝结；奇数扇射只在口部留三支短霜枝，不伪造冰弹。
    const cues = [
      cue(0, caster(c, 'shard', '龙颈暗冰螺旋', { color: DARK, y: 1.5, width: .29, height: 1.25, count: c.rage ? 10 : 7, spread: 1.6, motion: 'orbit', spin: -.8, life: .55, gain: .49 })),
      cue(0, caster(c, 'arc', '龙冠扭霜上弧', { color: ICE, y: 2.5, radius: 1.5, width: .05, halfAngle: 1.7, tilt: .48, motion: 'rise', life: .46, gain: .43 })),
      cue(.04, caster(c, 'arc', '龙冠扭霜下弧', { color: DARK, y: 1.25, radius: 1.85, width: .07, halfAngle: 1.45, angle: c.angle + Math.PI, tilt: -.48, life: .46, gain: .41 })),
      cue(.04, caster(c, 'shard', even ? '陨冰起手晶核' : '三扇起手冰牙', { color: EDGE, offset: [even ? .2 : 1.05, 1.4, 0], width: .15, height: .72, count: even ? 3 : 6, spread: even ? .4 : .68, motion: 'rise', life: .3, gain: .48 })),
    ];
    if (!even) cues.push(cue(.045, caster(c, 'ribbon', '龙吻三支霜枝', { color: ICE, pattern: 'frost', offset: [1, 1.15, 0], count: 3, halfAngle: .48, length: 1.65, width: .045, motion: 'expand', chargeTime: .1, life: .24, gain: .43 })));
    if (c.rage) cues.push(cue(.075, caster(c, 'shard', '狂龙冠锋晶', { color: ICE, y: 2.6, width: .16, height: 1.05, count: 6, spread: 1.4, spin: .8, life: .39, gain: .46 })));
    return { cues };
  },
  impact(c) {
    const r = c.radius, large = r > 3;
    // 冰陨已到真实结算时刻：从地面裂晶向外断开，不再播放提前落下的假陨石。
    return { cues: [
      cue(0, effect(c, 'decal', '龙霜枝裂印', { color: DARK, pattern: 'frost', radius: r, life: .43, chargeTime: .04, gain: .44 })),
      cue(0, effect(c, 'shard', large ? '龙足扭转晶脊' : '冰陨暗刻面', { color: DARK, width: large ? .46 : .4, height: large ? 1.8 : 1.22, count: large ? 10 : 5, spread: r * .68, motion: 'rise', spin: -.65, life: .41, chargeTime: .19, gain: .54 })),
      cue(.025, effect(c, 'shard', '冰断口亮晶', { color: ICE, width: .15, height: large ? 1.15 : .72, count: large ? 12 : 7, spread: r * .79, motion: 'expand', spin: .8, life: .32, chargeTime: .12, gain: .5 })),
      cue(.025, effect(c, 'ribbon', '径向霜枝断裂', { color: ICE, pattern: 'frost', length: r * .92, width: .045, count: large ? 7 : 5, halfAngle: Math.PI, motion: 'expand', chargeTime: .13, life: .28, gain: .41 })),
      cue(.04, effect(c, 'arc', '扭冰螺旋断口', { color: EDGE, radius: r, width: .035, halfAngle: .7, tilt: .15, angle: c.angle + .8, motion: 'expand', chargeTime: .14, life: .25, gain: .4 })),
    ] };
  },
  charge: empty,
  enrage(c) { return { cues: [
    cue(0, caster(c, 'dome', '狂龙暗霜穹', { color: DARK, pattern: 'frost', radius: 2.35, height: 3.3, motion: 'collapse', chargeTime: .35, life: .5, gain: .33 })),
    cue(.07, caster(c, 'shard', '狂龙十二棱冠', { color: ICE, y: 2.5, width: .24, height: 1.3, count: 12, spread: 1.65, motion: 'rise', spin: -.9, life: .65, gain: .51 })),
    cue(.09, caster(c, 'arc', '狂龙斜上螺旋', { color: DARK, y: 2.6, radius: 2.1, width: .07, halfAngle: 2, tilt: .6, life: .65, gain: .4 })),
    cue(.12, caster(c, 'arc', '狂龙细霜断弧', { color: EDGE, y: 2.8, radius: 1.9, width: .03, halfAngle: 1.1, tilt: -.6, angle: c.angle + Math.PI, life: .48, gain: .38 })),
  ] }; },
  zone: empty,
};
