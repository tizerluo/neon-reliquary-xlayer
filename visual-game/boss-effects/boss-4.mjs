import { BOSS_NAMES, cue, effect, caster } from './common.mjs';

// 光学门只贴在本体；28m 的交叉光束由真实 line impact 分别传入。
function attack(c) {
  return { cues: [
    cue(0, caster(c, 'orb', '神祇暗金光学门', { radius: 1.8, y: 1.4, pattern: 'rail', color: '#776039', gain: .32, life: .68, motion: 'collapse' })),
    cue(0, caster(c, 'arc', '光学上环', { radius: 2.1, width: .055, halfAngle: Math.PI, y: 2.05, tilt: .75, color: '#f4c76c', gain: .45, life: .6, motion: 'orbit', spin: 1.7 })),
    cue(0, caster(c, 'arc', '光学下环', { radius: 1.65, width: .035, halfAngle: Math.PI, y: .55, tilt: -.75, color: '#c39652', gain: .4, life: .6, motion: 'orbit', spin: -1.7 })),
    cue(0, caster(c, 'shard', '出膛棱镜齿', { count: c.rage ? 8 : 6, spread: 1.35, width: .14, height: .65, y: 1.6, color: '#f0d7a4', gain: .48, life: .42, motion: 'expand' })),
  ] };
}

function impact(c) {
  if (c.shape === 'line') {
    const length = c.length ?? 28, width = c.width ?? 1.204;
    return { cues: [
      cue(0, effect(c, 'decal', '真实光束双轨', { shape: 'lane', length, width, pattern: 'rail', color: '#b9873e', gain: .46, life: .48, chargeTime: .04 })),
      cue(0, effect(c, 'ribbon', '琥珀束壳', { length, width: width * .78, y: .16, color: '#d4a04a', gain: .43, life: .34, chargeTime: .04 })),
      cue(0, effect(c, 'ribbon', '白金窄芯', { length, width: width * .12, y: .19, color: '#f5dfab', gain: .63, life: .23, chargeTime: .04 })),
      cue(0, effect(c, 'shield', '近端光学门', { offset: [length * .15, .45, 0], radius: width * .5, height: 1.2, color: '#bb8d4c', gain: .37, life: .38 })),
      cue(0, effect(c, 'shield', '远端光学门', { offset: [length * .72, .45, 0], radius: width * .5, height: 1.2, color: '#f0cb81', gain: .32, life: .35 })),
    ] };
  }
  const radius = c.radius ?? 1.96;
  return { cues: [
    cue(0, effect(c, 'decal', '轰击光学分度盘', { radius, pattern: 'rail', color: '#a87a39', gain: .44, life: .48, chargeTime: .04 })),
    cue(0, effect(c, 'pillar', '金芯短轰击', { radius: radius * .12, height: 2.9, color: '#e2be73', gain: .53, life: .26 })),
    cue(0, effect(c, 'shard', '轰击折射棱片', { count: c.rage ? 8 : 6, spread: radius * .65, width: .18, height: .8, color: '#dfbc75', gain: .48, life: .42, motion: 'expand' })),
    cue(0, effect(c, 'arc', '金属门环余辉', { radius, width: .05, halfAngle: Math.PI, color: '#bc9555', gain: .38, life: .36, motion: 'expand' })),
  ] };
}
function enrage(c) {
  return { cues: [
    cue(0, caster(c, 'orb', '狂暴光学球壳', { radius: 2.7, y: 1.4, color: '#8e703d', gain: .3, life: .9, motion: 'collapse' })),
    cue(0, caster(c, 'arc', '高位分光环', { radius: 2.65, width: .06, halfAngle: Math.PI, y: 1.8, tilt: .8, color: '#efc96e', gain: .44, life: .8, motion: 'orbit', spin: 2 })),
    cue(0, caster(c, 'arc', '反转分光环', { radius: 2.25, width: .04, halfAngle: Math.PI, y: .8, tilt: -.8, color: '#bd9659', gain: .38, life: .8, motion: 'orbit', spin: -2 })),
    cue(0, caster(c, 'shard', '狂暴棱镜尖齿', { count: 8, spread: 1.8, width: .13, height: 1.1, y: 1.3, color: '#ead5a4', gain: .49, life: .75, motion: 'rise' })),
  ] };
}
export default { boss: 4, name: BOSS_NAMES[4], attack, impact, charge: () => ({ cues: [] }), enrage, zone: () => ({ cues: [] }),
  projectile: { shape: 'lumen', color: '#f4c76c', core: '#f6e3b9', tail: '#8b612e', size: .28, length: 1.02, gain: .6 } };
