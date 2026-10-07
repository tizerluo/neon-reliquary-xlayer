import { FX_TIMING } from '../skill-fx-timeline.mjs';

const FIRE = '#ffab52';
const CORE = '#fff0cf';
const COAL = '#51362c';
const HOT = '#ed7837';

// 配方只描述真实事件；坐标是米，熔缝落点与持续时间由战斗层传入。
function effect(c, kind, label, fields) {
  return { kind, label, x: c.x, z: c.z, angle: c.angle, owner: c.owner,
    seed: c.seed ?? 1, color: FIRE, ...fields };
}

function cast(c) {
  const cues = [
    { at: 0, effect: effect(c, 'shard', '举锤炉屑', {
      attach: true, offset: [.65, 1.65, 0], width: .13, height: .42,
      count: 4, spread: .55, motion: 'rise', life: FX_TIMING.castContact,
      fadeIn: .14, fadeOut: .09, gain: .36,
    }) },
    // 第 14 帧锤头触地：低矮空心冲击弧，避免用发光圆盘遮住脚下。
    { at: 'castContact', effect: effect(c, 'arc', '锤触地白热弧', {
      offset: [.85, .08, 0], radius: 1.45, halfAngle: 1.35, width: .075,
      color: CORE, motion: 'expand', life: .26, fadeIn: .015, fadeOut: .21, gain: .82,
    }) },
    { at: 'castContact', effect: effect(c, 'decal', '断层暗边', {
      shape: 'lane', pattern: 'fault', length: 12.18, width: 3.808,
      color: COAL, life: .62, fadeIn: .025, fadeOut: .38, gain: .44,
    }) },
    { at: 'castContact', effect: effect(c, 'ribbon', '纵贯熔脊', {
      pattern: 'fault', length: 12.18, width: .12, y: .085, spread: .22,
      color: CORE, motion: 'expand', life: .38, fadeIn: .025, fadeOut: .29, gain: .76,
    }) },
    { at: 'castContact', effect: effect(c, 'feedback', '重锤反馈', {
      life: .22, fadeIn: .025, fadeOut: .18, gain: .075,
    }) },
  ];

  // 三个实际灼烧区各含暗裂边、细熔芯、两条叉缝、刻面岩屑；不预约额外落点。
  for (const [i, point] of (c.points ?? []).slice(0, 3).entries()) {
    const radius = point.radius ?? 1.736;
    const life = Math.max(.04, (point.duration ?? 2.5) - FX_TIMING.castContact);
    const co = Math.cos(c.angle), si = Math.sin(c.angle);
    const origin = { ...c, x: point.x, z: point.z, seed: (c.seed ?? 1) + i * 17 };
    cues.push({ at: 'castContact', effect: effect(origin, 'decal', `熔缝${i + 1}冷却边`, {
      shape: 'seal', pattern: 'fault', radius, width: .14, color: HOT,
      life, fadeIn: .035, fadeOut: Math.min(1.6, life), gain: .46,
    }) });
    cues.push({ at: 'castContact', effect: effect(origin, 'ribbon', `熔缝${i + 1}白热芯`, {
      x: point.x - co * radius * .8, z: point.z - si * radius * .8,
      pattern: 'fault', length: radius * 1.6, width: .065, y: .09, spread: .13,
      color: CORE, life: Math.min(1.3, life), fadeIn: .025,
      fadeOut: Math.min(1.1, life), gain: .86,
    }) });
    for (const side of [-1, 1]) {
      cues.push({ at: 'castContact', effect: effect(origin, 'ribbon', `熔缝${i + 1}叉缝${side}`, {
        angle: c.angle + side * .82, pattern: 'fault', length: radius * .92,
        width: .055, y: .08, spread: .12, color: HOT,
        life, fadeIn: .04, fadeOut: Math.min(1.6, life), gain: .54,
      }) });
    }
    cues.push({ at: 'castContact', effect: effect(origin, 'shard', `熔缝${i + 1}岩屑`, {
      color: COAL, count: 4, spread: radius * .72, width: .28,
      height: .62, y: .11, motion: 'rise', life: .48,
      fadeIn: .025, fadeOut: .27, gain: .38,
    }) });
  }
  return { cues };
}

function channel(c) {
  const duration = c.channelDuration ?? 4.2;
  const heldLife = Math.max(.04, duration - FX_TIMING.channelHold);
  const crown = (kind, label, fields) => effect(c, kind, label, {
    attach: true, channel: true, channelDuration: duration, cancelOnOwnerLoss: true,
    ...fields,
  });
  return { cues: [
    { at: 0, effect: crown('shard', '炉冠聚合', {
      offset: [0, 1.7, 0], count: 5, spread: .72, width: .1, height: .5,
      motion: 'rise', life: FX_TIMING.channelEnter, fadeIn: .12, fadeOut: .12, gain: .4,
    }) },
    // 第 13 帧举手，前后两层竖立断环接住手势，轮廓与地面熔缝有明确区别。
    { at: 'channelEnter', effect: crown('arc', '举手日冕外环', {
      offset: [-.24, 3.35, 0], radius: 1.45, halfAngle: 2.6,
      width: .15, tilt: Math.PI / 2, motion: 'expand',
      life: FX_TIMING.channelHold - FX_TIMING.channelEnter + .18,
      fadeIn: .12, fadeOut: .2, gain: .62,
    }) },
    { at: 'channelEnter', effect: crown('arc', '举手白热线', {
      offset: [-.2, 3.35, 0], radius: 1.25, halfAngle: 2.6,
      width: .045, tilt: Math.PI / 2, color: CORE,
      life: FX_TIMING.channelHold - FX_TIMING.channelEnter + .18,
      fadeIn: .16, fadeOut: .2, gain: .74,
    }) },
    // 第 28 帧定形：保留缺口的日冕与短炉齿，在整个真实引导内跟随并可取消。
    { at: 'channelHold', effect: crown('arc', '保持炉冠暗边', {
      offset: [-.25, 3.35, 0], radius: 1.46, halfAngle: 2.6,
      width: .22, tilt: Math.PI / 2, color: COAL,
      life: heldLife, fadeIn: .1, fadeOut: Math.min(.32, heldLife), gain: .5,
    }) },
    { at: 'channelHold', effect: crown('arc', '保持炉冠熔边', {
      offset: [-.2, 3.35, 0], radius: 1.4, halfAngle: 2.6,
      width: .09, tilt: Math.PI / 2, spin: .18,
      life: heldLife, fadeIn: .08, fadeOut: Math.min(.3, heldLife), gain: .58,
    }) },
    { at: 'channelHold', effect: crown('arc', '保持内日冕白芯', {
      offset: [-.14, 3.35, 0], radius: .99, halfAngle: 2.4,
      width: .035, tilt: Math.PI / 2, spin: -.24, color: CORE,
      life: heldLife, fadeIn: .1, fadeOut: Math.min(.3, heldLife), gain: .72,
    }) },
    { at: 'channelHold', effect: crown('shard', '炉冠刻面齿', {
      offset: [-.21, 3.62, 0], color: COAL, count: 7, spread: 1.75,
      width: .15, height: .55, life: heldLife, fadeIn: .12,
      fadeOut: Math.min(.3, heldLife), gain: .42,
    }) },
    { at: 0, effect: effect(c, 'feedback', '烈日蓄势反馈', {
      life: .28, fadeIn: .045, fadeOut: .22, gain: .09,
    }) },
  ] };
}

function pulse(c) {
  // c.angle 已是真实 laneDamage 的 sweep。弧端横宽锁在 3.808m 内，不扩成大扇面。
  const travel = 12.74, radius = 2.6, halfAngle = Math.asin(1.904 / radius);
  return { cues: [
    { at: 0, effect: effect(c, 'arc', '推进月牙暗背', {
      radius, halfAngle, length: travel, offset: [-radius,0,0], width: .34, y: .32, color: COAL,
      motion: 'sweep', chargeTime: .24, life: .32, fadeIn: .02, fadeOut: .18, gain: .48,
    }) },
    { at: 0, effect: effect(c, 'arc', '推进月牙熔刃', {
      radius, halfAngle, length: travel, offset: [-radius,0,0], width: .2, y: .36, color: FIRE,
      motion: 'sweep', chargeTime: .24, life: .32, fadeIn: .02, fadeOut: .18, gain: .7,
    }) },
    { at: 0, effect: effect(c, 'arc', '推进月牙白热锋', {
      radius, halfAngle, length: travel, offset: [-radius,0,0], width: .045, y: .4, color: CORE,
      motion: 'sweep', chargeTime: .24, life: .3, fadeIn: .015, fadeOut: .17, gain: .9,
    }) },
    ...[-1, 1].map(side => ({ at: 0, effect: effect(c, 'ribbon', `月牙热浪${side}`, {
      offset: [0, .45, side * 1.45], pattern: 'fault',
      length: travel, width: .075, spread: .18, motion: 'expand',
      color: FIRE, life: .28, fadeIn: .025, fadeOut: .21, gain: .23,
    }) })),
  ] };
}

export default { hero: 1, key: 'mordred', name: '莫德雷德 · 断层重击 / 烈日处决', cast, channel, pulse };
