import { BOSS_NAMES, cue, effect, caster } from './common.mjs';

const DARK = '#752f24', FIRE = '#e96e36', CORE = '#ffd395';
const empty = () => ({ cues: [] });

export default {
  boss: 0, name: BOSS_NAMES[0],
  projectile: { shape: 'flame', color: FIRE, core: CORE, tail: DARK, size: .37, length: .93, gain: .65 },
  attack(c) {
    const branch = (c.sequence ?? 0) % 3, fierce = !!c.rage;
    // 炉冠只在真实起手时围绕本体建立；短叉舌是口焰，不预约地面落击或装饰弹。
    const cues = [
      cue(0, caster(c, 'petals', '炉冠暗刃', { color: DARK, radius: 1.4, length: .68, width: .07, height: .22, petals: fierce ? 9 : 6, y: 1.1, life: .48, chargeTime: .18, gain: .46 })),
      cue(0, caster(c, 'shard', '炉冠火齿', { color: FIRE, offset: [0, 2.15, 0], width: .16, height: .8, count: fierce ? 9 : 6, spread: 1.12, motion: 'rise', spin: .5, life: .4, gain: .53 })),
      cue(0, caster(c, 'orb', '胸炉收火', { color: DARK, radius: .68, offset: [.3, 1.3, 0], pattern: 'fault', motion: 'collapse', chargeTime: .18, life: .3, gain: .38 })),
    ];
    cues.push(cue(.04, caster(c, 'ribbon', branch === 1 ? '冲锋起手叉焰' : '弹口叉焰', { color: FIRE, pattern: 'fault', offset: [.65, 1.1, 0], length: branch === 1 ? 2.3 : 1.65, width: .07, count: branch === 2 ? 5 : 3, halfAngle: branch === 2 ? 1.15 : .42, motion: 'expand', chargeTime: .1, life: .23, gain: .55 })));
    if (fierce) cues.push(cue(.06, caster(c, 'petals', '狂炉冠细亮芯', { color: CORE, radius: 1.28, length: .46, width: .025, height: .15, petals: 9, y: 1.18, life: .25, gain: .38 })));
    return { cues };
  },
  impact(c) {
    // 线击按真实全宽刻熔边，圈击则用稀疏刃瓣；不把地击复制成完整亮环。
    if (c.shape === 'line') return { cues: [
      cue(0, effect(c, 'decal', '熔击断槽', { shape: 'lane', pattern: 'fault', color: DARK, length: c.length, width: c.width, life: .4, chargeTime: .04, gain: .45 })),
      ...[-1, 1].map(side => cue(0, effect(c, 'ribbon', `熔击侧边${side}`, { color: FIRE, pattern: 'fault', offset: [0, .04, side * c.width * .46], length: c.length, width: .065, life: .28, chargeTime: .06, gain: .58 }))),
      cue(.035, effect(c, 'ribbon', '熔击窄芯', { color: CORE, length: c.length, width: .028, pattern: 'fault', life: .17, gain: .34 })),
      cue(.045, effect(c, 'shard', '熔口裂火', { color: FIRE, offset: [c.length * .55, .14, 0], width: .22, height: 1.15, count: 7, spread: c.width * .42, motion: 'rise', life: .32, gain: .48 })),
    ] };
    const r = c.radius;
    return { cues: [
      cue(0, effect(c, 'decal', '炉底暗熔断纹', { color: DARK, pattern: 'fault', radius: r, life: .43, chargeTime: .04, gain: .43 })),
      cue(0, effect(c, 'petals', '地火分叉刃瓣', { color: FIRE, radius: r * .7, length: r * .23, width: .06, height: .18, petals: c.rage ? 9 : 6, motion: 'expand', chargeTime: .12, life: .3, gain: .57 })),
      cue(0, effect(c, 'arc', '熔边断弧', { color: FIRE, radius: r, width: .08, halfAngle: 1.08, angle: c.angle + .65, motion: 'expand', chargeTime: .14, life: .29, gain: .52 })),
      cue(.025, effect(c, 'shard', '炉渣短热流', { color: DARK, count: c.rage ? 10 : 7, spread: r * .68, width: .21, height: r > 3 ? 1.3 : .73, motion: 'rise', life: .37, gain: .42 })),
      cue(.035, effect(c, 'arc', '断弧火芯', { color: CORE, radius: r * .97, width: .025, halfAngle: .5, angle: c.angle - 1.2, motion: 'expand', chargeTime: .13, life: .19, gain: .4 })),
    ] };
  },
  charge(c) {
    const life = c.duration ?? .62;
    return { cues: [
      cue(0, caster(c, 'arc', '冲锋炉口前刃', { color: DARK, offset: [.7, .55, 0], radius: 1.9, width: .19, halfAngle: .85, life, fadeOut: .18, gain: .5 })),
      cue(0, caster(c, 'ribbon', '冲锋三叉热流', { color: FIRE, angle: c.angle + Math.PI, offset: [0, .4, 0], count: 3, spread: .6, halfAngle: .11, length: 2.6, width: .06, pattern: 'fault', life, fadeOut: .2, gain: .49 })),
      cue(0, caster(c, 'arc', '冲锋窄火唇', { color: CORE, offset: [.75, .57, 0], radius: 1.84, width: .035, halfAngle: .68, life, fadeOut: .18, gain: .36 })),
    ] };
  },
  enrage(c) { return { cues: [
    cue(0, caster(c, 'orb', '狂炉收束', { color: DARK, radius: 2.1, pattern: 'fault', motion: 'collapse', life: .48, chargeTime: .3, gain: .42 })),
    cue(.08, caster(c, 'petals', '狂炉九刃冠', { color: FIRE, radius: 1.9, length: .88, width: .065, height: .28, y: 1.35, petals: 9, life: .65, gain: .54 })),
    cue(.12, caster(c, 'shard', '狂炉上升火齿', { color: DARK, y: 1.35, width: .25, height: 1.25, count: 9, spread: 1.5, motion: 'rise', life: .62, gain: .46 })),
    cue(.16, caster(c, 'arc', '狂炉冠亮断口', { color: CORE, y: 2.8, radius: 1.55, width: .035, halfAngle: .8, life: .35, gain: .4 })),
  ] }; },
  zone: empty,
};
