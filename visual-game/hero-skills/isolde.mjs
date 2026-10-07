import { FX_TIMING, FX_COLORS } from '../skill-fx-timeline.mjs';

const ICE = FX_COLORS[5], EDGE = '#e5fbff', DEEP = '#246475';
const cue = (at, label, effect) => ({ at, effect: { ...effect, label } });
const origin = c => ({ x: c.x, z: c.z, angle: c.angle, owner: c.owner, seed: c.seed ?? 1 });
const attached = c => ({ ...origin(c), attach: true, cancelOnOwnerLoss: true });

export default {
  hero: 5,
  key: 'isolde',
  name: '绝对封锁 / 零度开尔文',
  cast(c) {
    const root = origin(c), hand = attached(c);
    // 手边先聚起暗青刻面；第14帧前不提前铺满真实攻击扇面。
    const cues = [
      cue(0, '霜晶蓄势', { ...hand, kind: 'shard', color: DEEP, offset: [.43, 1.18, -.25], count: 3, spread: .26, width: .2, height: .64, motion: 'rise', life: .63, fadeIn: .14, fadeOut: .17, chargeTime: FX_TIMING.castContact, gain: .45 }),
      cue(0, '掌心冰魄', { ...hand, kind: 'orb', color: ICE, pattern: 'frost', offset: [.43, 1.38, -.25], radius: .34, motion: 'collapse', life: .57, fadeIn: .14, fadeOut: .11, chargeTime: FX_TIMING.castContact, gain: .48 }),
      // 扇面只刻雪花细线；暗色晶面与白色断口提供层次，红色预警仍可读。
      cue('castContact', '封锁雪纹', { ...root, kind: 'decal', color: DEEP, shape: 'sector', pattern: 'frost', radius: 9.52, halfAngle: .78, life: .5, fadeIn: .025, fadeOut: .36, chargeTime: .12, gain: .32 }),
      cue('castContact', '前沿冰断口', { ...root, kind: 'arc', color: EDGE, radius: 9.52, halfAngle: .78, width: .065, y: .23, motion: 'expand', life: .32, fadeIn: .015, fadeOut: .21, chargeTime: .16, gain: .58 }),
      cue('castContact', '近前碎冰', { ...root, kind: 'shard', color: DEEP, offset: [1.75, .14, 0], width: .31, height: 1.02, count: 7, spread: 1.05, motion: 'rise', spin: .2, life: .46, fadeIn: .025, fadeOut: .29, gain: .47 }),
      cue('castContact', '起晶雪花刻印', { ...root, kind: 'decal', color: ICE, offset: [1.65, .035, 0], shape: 'seal', pattern: 'frost', radius: .88, life: .4, fadeIn: .02, fadeOut: .29, gain: .48 }),
    ];
    // 七条方向与真实战技一致（±.57）；冰脊止于9.52米，碎片并非虚构冻结目标。
    for (let i = 0; i < 7; i++) {
      const angle = c.angle + (i - 3) * .19;
      cues.push(
        cue('castContact', `冰棱射线${i + 1}`, { ...root, angle, kind: 'ribbon', color: ICE, pattern: 'frost', offset: [1.54, .17, 0], length: 7.98, width: i === 3 ? .12 : .065, motion: 'expand', chargeTime: .13, life: .35, fadeIn: .015, fadeOut: .24, gain: .58 }),
        cue('castContact', `射线${i + 1}断裂冰棱`, { ...root, angle, kind: 'shard', color: i % 2 ? DEEP : ICE, offset: [4.15 + (i % 3) * 1.2, .15, 0], count: 3, spread: .34, width: .18, height: .82 + (i % 2) * .25, motion: 'rise', spin: (i - 3) * .05, life: .42, fadeIn: .02, fadeOut: .27, gain: .44 }),
      );
    }
    return { cues };
  },
  channel(c) {
    const root = origin(c), duration = c.channelDuration ?? 4.2;
    const body = { ...attached(c), channel: true, channelDuration: duration };
    const enterLife = Math.max(.04, duration - FX_TIMING.channelEnter);
    const holdLife = Math.max(.04, duration - FX_TIMING.channelHold);
    // 第13帧霜穹从举手动作展开，第28帧建立环绕冠；仅贴身形随主人移动。
    return { cues: [
      cue(0, '零度掌心凝核', { ...body, kind: 'shard', color: DEEP, offset: [.24, 1.42, -.28], width: .34, height: .82, count: 3, spread: .2, motion: 'rise', life: .65, fadeIn: .16, fadeOut: .17, gain: .47 }),
      cue(0, '零度凝神', { ...root, kind: 'feedback', color: ICE, life: .26, fadeIn: .04, fadeOut: .19, gain: .08 }),
      cue('channelEnter', '13帧霜穹展开', { ...body, kind: 'dome', color: DEEP, pattern: 'frost', radius: 2.7, height: 3.3, y: .08, motion: 'expand', chargeTime: FX_TIMING.channelHold - FX_TIMING.channelEnter, life: enterLife, fadeIn: .28, fadeOut: .34, gain: .31 }),
      cue('channelEnter', '13帧浮冰王冠', { ...body, kind: 'shard', color: DEEP, offset: [0, 2.92, 0], count: 6, spread: 1.22, width: .29, height: .95, motion: 'orbit', spin: -.38, life: enterLife, fadeIn: .35, fadeOut: .3, gain: .43 }),
      cue('channelHold', '28帧霜穹亮棱', { ...body, kind: 'dome', color: ICE, pattern: 'frost', radius: 2.58, height: 3.12, y: .1, motion: 'still', life: holdLife, fadeIn: .16, fadeOut: .34, gain: .29 }),
      cue('channelHold', '28帧冠顶雪花', { ...body, kind: 'arc', color: EDGE, pattern: 'frost', radius: 1.17, width: .04, halfAngle: Math.PI, y: 3.56, tilt: .08, motion: 'orbit', spin: -.38, life: holdLife, fadeIn: .18, fadeOut: .3, gain: .43 }),
      cue('channelHold', '释放地霜纹', { ...root, kind: 'decal', color: DEEP, shape: 'seal', pattern: 'frost', radius: 2.7, channel: true, channelDuration: duration, life: holdLife, fadeIn: .2, fadeOut: .35, gain: .27 }),
    ] };
  },
  pulse(c) {
    const cues = [];
    // 只呈现本次三个真实陨冰落点；.5秒内收尽刻印与碎屑，避免持续蓝色覆盖。
    for (const [i, point] of (c.points ?? []).slice(0, 3).entries()) {
      if (!Number.isFinite(point.x) || !Number.isFinite(point.z)) continue;
      const root = { ...origin(c), x: point.x, z: point.z, seed: (c.seed ?? 1) + i * 23 };
      const radius = point.radius ?? 2.016;
      cues.push(
        cue(0, `冰陨${i + 1}刻面`, { ...root, kind: 'shard', color: DEEP, y: 5.7, width: .88, height: 2.3, count: 1, motion: 'fall', spin: .6, chargeTime: .15, life: .24, fadeIn: .01, fadeOut: .065, gain: .63 }),
        cue(0, `冰陨${i + 1}雪花落印`, { ...root, kind: 'decal', color: ICE, shape: 'seal', pattern: 'frost', radius, life: .48, fadeIn: .035, fadeOut: .35, chargeTime: .08, gain: .48 }),
        cue(.12, `冰陨${i + 1}碎晶`, { ...root, kind: 'shard', color: ICE, y: .12, width: .17, height: .64, count: 7, spread: radius * .55, motion: 'expand', spin: -.4, life: .32, fadeIn: .015, fadeOut: .24, gain: .53 }),
        cue(.12, `冰陨${i + 1}断口`, { ...root, kind: 'arc', color: EDGE, radius, halfAngle: Math.PI, width: .04, y: .16, motion: 'expand', chargeTime: .1, life: .26, fadeIn: .01, fadeOut: .2, gain: .47 }),
      );
    }
    return { cues };
  },
  freeze(c) {
    const cues = [];
    // 冻结时长来自战斗（Boss可更短）；索引、代次与requireFreeze共同防止池复用伪壳。
    for (const [i, point] of (c.points ?? []).slice(0, 12).entries()) {
      if (!Number.isSafeInteger(point.target) || point.target < 0 || !Number.isSafeInteger(point.generation) || point.generation < 0 || !Number.isFinite(point.duration) || point.duration < .04 || !Number.isFinite(point.x) || !Number.isFinite(point.z)) continue;
      const shell = { ...origin(c), x: point.x, z: point.z, target: point.target, generation: point.generation, requireFreeze: true, duration: point.duration, life: point.duration, seed: (c.seed ?? 1) + i * 11, kind: 'dome', pattern: 'frost', motion: 'still', fadeIn: Math.min(.07, point.duration / 4), fadeOut: Math.min(.2, point.duration / 3) };
      const radius = Math.max(.7, Math.min(1.8, (point.radius ?? .48) + .16));
      cues.push(
        cue(0, `冻结${i + 1}暗晶壳`, { ...shell, color: DEEP, radius, height: Math.max(2.15,radius * 2.3), gain: .45 }),
        cue(0, `冻结${i + 1}霜白棱`, { ...shell, color: ICE, radius: radius * 1.035, height: Math.max(2.18,radius * 2.34), gain: .38 }),
      );
    }
    return { cues };
  },
};
