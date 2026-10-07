import { BOSS_NAMES, cue, effect, caster } from './common.mjs';

const DARK = '#635343', METAL = '#bc9d70', EDGE = '#efcf8c';
const empty = () => ({ cues: [] });

export default {
  boss: 2, name: BOSS_NAMES[2],
  projectile: { shape: 'shell', color: METAL, core: EDGE, tail: DARK, size: .43, length: .66, gain: .52 },
  attack(c) {
    const ram = (c.sequence ?? 0) % 3 < 2;
    // 装甲板贴身抬起，重机起手没有提前画20米车道或未来目标重击。
    return { cues: [
      cue(0, caster(c, 'shield', '重装前闸', { color: DARK, radius: ram ? 1.7 : 2.1, height: 2.4, offset: [.6, 1.15, 0], motion: 'rise', life: .5, chargeTime: .25, gain: .52 })),
      cue(0, caster(c, 'shard', '重装锁块', { color: DARK, y: .7, width: .56, height: 1.1, count: c.rage ? 9 : 6, spread: 1.6, motion: 'rise', spin: .08, life: .48, gain: .52 })),
      cue(.05, caster(c, 'decal', '重装机座细轨', { color: METAL, pattern: 'rail', radius: 1.85, life: .42, chargeTime: .15, gain: .4 })),
      cue(.08, caster(c, 'shield', '重装闸口亮边', { color: EDGE, radius: ram ? 1.62 : 2.02, height: 2.22, offset: [.64, 1.16, 0], life: .27, gain: .29 })),
    ] };
  },
  impact(c) {
    if (c.shape === 'line') {
      const cues = [
        cue(0, effect(c, 'decal', '钢犁重压轨槽', { color: DARK, shape: 'lane', pattern: 'rail', length: c.length, width: c.width, life: .48, chargeTime: .04, gain: .49 })),
        ...[-1, 1].map(side => cue(0, effect(c, 'ribbon', `钢犁断轨${side}`, { color: METAL, pattern: 'rail', offset: [0, .03, side * c.width * .46], length: c.length, width: .07, life: .29, gain: .43 }))),
      ];
      // 三个碎块簇落在已结算真实车道内部；不沿车道预约后续伤害。
      for (let i = 0; i < 3; i++) cues.push(cue(i * .025, effect(c, 'shard', `钢犁断块${i + 1}`, { color: i === 1 ? METAL : DARK, offset: [c.length * (.2 + i * .3), .12, 0], width: .42, height: .85, spread: c.width * .34, count: 4, motion: 'rise', spin: .15, life: .4, gain: .5 })));
      cues.push(cue(.035, effect(c, 'ribbon', '钢犁窄金中缝', { color: EDGE, pattern: 'rail', length: c.length, width: .026, life: .17, gain: .32 })));
      return { cues };
    }
    const r = c.radius, big = r > 4;
    const cues = [
      cue(0, effect(c, 'decal', '重击金属断裂纹', { color: DARK, pattern: 'fault', radius: r, life: .48, chargeTime: .04, gain: .48 })),
      cue(0, effect(c, 'shard', '重击装甲碎块', { color: DARK, width: big ? .57 : .43, height: big ? 1.25 : .92, count: c.rage ? 12 : 8, spread: r * .71, motion: 'expand', spin: .18, chargeTime: .2, life: .43, gain: .53 })),
      cue(.035, effect(c, 'shard', '碎块金棱', { color: METAL, width: .18, height: .68, count: big ? 10 : 6, spread: r * .62, motion: 'rise', spin: -.2, life: .37, gain: .47 })),
    ];
    // 三段不闭合的金属波前有重叠断口；短促推进保留大圈内地面可读性。
    for (let i = 0; i < 3; i++) cues.push(cue(i * .022, effect(c, 'arc', `重波断钢段${i + 1}`, { color: i === 1 ? EDGE : METAL, radius: r, width: i === 1 ? .035 : .1, angle: c.angle + i * Math.PI * 2 / 3, halfAngle: .56, motion: 'expand', chargeTime: .2, life: .31, gain: i === 1 ? .33 : .46 })));
    return { cues };
  },
  charge(c) {
    const life = c.duration ?? .62;
    return { cues: [
      cue(0, caster(c, 'shield', '钢兽冲锋前闸', { color: DARK, radius: 1.75, height: 1.9, offset: [1.05, .93, 0], life, fadeOut: .18, gain: .54 })),
      cue(0, caster(c, 'shield', '钢兽冲锋金缝', { color: METAL, radius: 1.67, height: 1.75, offset: [1.09, .95, 0], life, fadeOut: .18, gain: .31 })),
      cue(0, caster(c, 'ribbon', '履带短轨迹', { color: DARK, pattern: 'rail', angle: c.angle + Math.PI, length: 2.7, width: .075, count: 2, spread: 1.02, halfAngle: .025, y: .11, life, fadeOut: .2, gain: .43 })),
      cue(0, caster(c, 'shard', '前闸重装震屑', { color: METAL, offset: [1.2, .14, 0], width: .24, height: .6, count: 5, spread: 1.3, motion: 'rise', spin: .16, life, fadeOut: .2, gain: .42 })),
    ] };
  },
  enrage(c) { return { cues: [
    cue(0, caster(c, 'shield', '超载双重装甲闸', { color: DARK, radius: 2.15, height: 2.8, offset: [.6, 1.4, 0], motion: 'rise', life: .7, chargeTime: .3, gain: .51 })),
    cue(.07, caster(c, 'shard', '超载十二锁块', { color: METAL, y: .4, width: .47, height: 1.4, count: 12, spread: 2, motion: 'rise', spin: .12, life: .63, gain: .48 })),
    cue(.1, caster(c, 'decal', '超载机座断轨', { color: DARK, pattern: 'rail', radius: 2.55, life: .68, chargeTime: .2, gain: .39 })),
    cue(.16, caster(c, 'shield', '超载闸缝窄金', { color: EDGE, radius: 2.06, height: 2.59, offset: [.65, 1.43, 0], life: .39, gain: .29 })),
  ] }; },
  zone: empty,
};
