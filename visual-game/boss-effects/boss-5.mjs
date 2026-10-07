import { BOSS_NAMES, cue, effect, caster } from './common.mjs';

function attack(c) {
  const cues = [
    cue(0, caster(c, 'orb', '先知空心逆流', { radius: 1.65, y: 1.35, color: '#5b2a79', gain: .38, life: .7, motion: 'collapse' })),
    cue(0, caster(c, 'arc', '棱轨左瓣', { radius: 2.2, width: .045, halfAngle: .78, y: 1.55, tilt: .85, color: '#d17cdd', gain: .46, life: .58, motion: 'orbit', spin: 1.4 })),
    cue(0, caster(c, 'arc', '棱轨右瓣', { radius: 2.2, width: .045, halfAngle: .78, angle: (c.angle ?? 0) + Math.PI, y: 1.55, tilt: -.85, color: '#9360b4', gain: .4, life: .58, motion: 'orbit', spin: -1.4 })),
    cue(0, caster(c, 'shard', '幽灵返流棱芯', { count: c.rage ? 6 : 4, spread: .9, width: .12, height: 1.05, y: 1, color: '#e1a5ee', gain: .47, life: .4, motion: 'rise' })),
  ];
  // 每三次生成的八个灵体只在成功的真实坐标出现，不画假目标或装饰弹。
  for (const p of (c.summons ?? []).slice(0, 8)) {
    cues.push(cue(0, effect(c, 'shard', '真实灵体返流', { x: p.x, z: p.z, count: 3, spread: (p.radius ?? .6) * .55, width: .1, height: 1.3, y: .12, color: '#b88adc', gain: .46, life: .62, motion: 'rise' })));
  }
  return { cues };
}
function impact(c) {
  const radius = c.radius ?? 2.408;
  return { cues: [
    cue(0, effect(c, 'orb', '虚空井内塌', { radius, y: .3, color: '#583071', gain: .32, life: .46, motion: 'collapse' })),
    cue(0, effect(c, 'decal', '真实井口碎符', { radius, pattern: 'void', color: '#a759b6', gain: .48, life: .42, chargeTime: .04 })),
    cue(0, effect(c, 'shard', '井沿棱形返流', { count: c.rage ? 6 : 4, spread: radius * .62, width: .12, height: .95, color: '#cb82d9', gain: .5, life: .43, motion: 'fall' })),
  ] };
}
function zone(c) {
  const radius = c.radius ?? 2.408, life = c.duration ?? 3.4;
  // 生命周期与危险区完全一致。使用世界锚点，不随 Boss 移动或因 Boss 死亡取消。
  return { cues: [
    cue(0, effect(c, 'decal', '活虚空井稀疏裂符', { radius, pattern: 'void', color: '#743d92', gain: .39, life, chargeTime: .14, fadeIn: .1, fadeOut: .28, cancelOnOwnerLoss: false })),
    cue(0, effect(c, 'arc', '活井玫紫外沿', { radius, width: .055, halfAngle: .9, color: '#c575d2', y: .12, gain: .44, life, fadeOut: .28, motion: 'orbit', spin: .7, cancelOnOwnerLoss: false })),
    cue(0, effect(c, 'arc', '活井深紫反轨', { radius: radius * .72, width: .035, halfAngle: .7, angle: (c.angle ?? 0) + Math.PI, color: '#8b54ae', y: .16, gain: .36, life, fadeOut: .28, motion: 'orbit', spin: -.8, cancelOnOwnerLoss: false })),
    cue(0, effect(c, 'orb', '活井低空空壳', { radius: radius * .46, y: .18, color: '#5e2b7a', gain: .25, life, fadeOut: .28, pattern: 'void', cancelOnOwnerLoss: false })),
  ] };
}
function enrage(c) {
  return { cues: [
    cue(0, caster(c, 'orb', '先知狂暴收束壳', { radius: 2.8, y: 1.25, color: '#673282', gain: .33, life: .9, motion: 'collapse' })),
    cue(0, caster(c, 'shard', '先知悬浮棱冠', { count: 8, spread: 1.6, width: .14, height: 1.35, y: 1.8, color: '#dda0e8', gain: .48, life: .75, motion: 'rise' })),
    cue(0, caster(c, 'arc', '狂暴逆向棱轨', { radius: 2.7, width: .045, halfAngle: 1.2, y: 1, tilt: .72, color: '#b965cb', gain: .43, life: .82, motion: 'orbit', spin: -1.6 })),
  ] };
}
export default { boss: 5, name: BOSS_NAMES[5], attack, impact, charge: () => ({ cues: [] }), enrage, zone,
  projectile: { shape: 'void', color: '#d38ee5', core: '#edbdf3', tail: '#5b2c78', size: .33, length: .72, gain: .59 } };
