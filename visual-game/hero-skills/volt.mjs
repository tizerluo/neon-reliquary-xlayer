import { FX_TIMING } from '../skill-fx-timeline.mjs';

const BLUE = '#79adff', VIOLET = '#9978e9', WHITE = '#edf5ff';
const LENGTH = 12.04, WIDTH = 4.424;
const cue = (at, effect) => ({ at, effect });
const origin = c => ({ x: c.x, z: c.z, angle: c.angle, owner: c.owner, seed: c.seed });

export default {
  hero: 2,
  key: 'volt',
  name: '雷霆轨道 · 风暴裁决',
  cast(c) {
    const o = origin(c);
    // 全宽只由稀疏贴花界定；两条细轨形成可读剪影，不覆盖红色预警。
    const cues = [
      cue(0, { ...o, kind: 'decal', shape: 'lane', pattern: 'rail', color: VIOLET,
        length: LENGTH, width: WIDTH, life: 1.03, chargeTime: FX_TIMING.castContact,
        fadeIn: .09, fadeOut: .34, gain: .34 }),
      cue(0, { ...o, kind: 'orb', pattern: 'rail', color: BLUE, attach: true,
        offset: [.42, 1.24, -.23], radius: .32, life: .57, chargeTime: .5,
        motion: 'collapse', gain: .48, fadeIn: .14, fadeOut: .08 }),
    ];
    for (const side of [-1, 1]) cues.push(cue(0, {
      ...o, kind: 'ribbon', pattern: 'rail', color: BLUE, offset: [0, .12, side * 1.42],
      length: LENGTH, width: .055, life: 1.0, chargeTime: FX_TIMING.castContact,
      motion: 'expand', gain: .58, fadeIn: .12, fadeOut: .32,
    }));
    // 三道竖直符文门与直轨正交；接触帧只点亮门边，留下空心中央。
    for (const distance of [2.9, 6.45, 10.0]) {
      const x = c.x + Math.cos(c.angle) * distance;
      const z = c.z + Math.sin(c.angle) * distance;
      cues.push(cue(0, { ...o, x, z, kind: 'arc', pattern: 'rail', color: VIOLET,
        angle: c.angle + Math.PI / 2, tilt: Math.PI / 2, y: 1.1, radius: 1.14,
        width: .045, halfAngle: Math.PI, life: 1.0, chargeTime: FX_TIMING.castContact,
        fadeIn: .2, fadeOut: .3, gain: .44 }));
      cues.push(cue('castContact', { ...o, x, z, kind: 'arc', pattern: 'rail', color: BLUE,
        angle: c.angle + Math.PI / 2, tilt: Math.PI / 2, y: 1.1, radius: 1.03,
        width: .035, halfAngle: Math.PI, life: .28, fadeIn: .02, fadeOut: .22, gain: .67 }));
    }
    // 第14帧：直线亮芯与两侧电鞘同时放电；这些端点只是战技真实轨道末端。
    cues.push(cue('castContact', { ...o, kind: 'ribbon', pattern: 'rail', color: BLUE,
      y: .33, length: LENGTH, width: .19, life: .27, motion: 'sweep',
      chargeTime: .08, gain: .67, fadeIn: .01, fadeOut: .23 }));
    for (const side of [-1, 0, 1]) cues.push(cue('castContact', {
      ...o, kind: 'bolt', pattern: 'rail', color: side === 0 ? WHITE : VIOLET,
      offset: [0, .48, side * .58], length: LENGTH,
      width: side === 0 ? .027 : .04, spread: side === 0 ? .13 : .29,
      life: .24, fadeIn: .01, fadeOut: .19, gain: side === 0 ? .83 : .5,
    }));
    return { cues };
  },
  stun(c) {
    // 即时结算事件独立于第14帧轨道；亮芯与电鞘只锚定真实存活目标。
    const points = (c.points ?? []).filter(p => Number.isFinite(p.x) && Number.isFinite(p.z)
      && Number.isSafeInteger(p.target) && p.target >= 0 && Number.isSafeInteger(p.generation)
      && p.generation >= 0 && Number.isFinite(p.duration) && p.duration >= .04).slice(0, 8);
    const cues = [];
    for (const p of points) {
      const radius = Math.max(.28, Math.min(1.15, p.radius || .4));
      const target = { ...origin(c), x: p.x, z: p.z, target: p.target, generation: p.generation,
        requireStun: true, cancelOnOwnerLoss: false, life: p.duration,
        fadeIn: .008, fadeOut: Math.min(.12, p.duration * .3), chargeTime: .04,
        seed: ((c.seed ?? 0) + p.target * 17) % 2147483647 };
      // 两条共形蓝鞘/白芯即使关闭辉光也可读；侧向紫叉仅在高画质完整动态下添加。
      for (const [color, width, gain] of [[BLUE, .048, .56], [WHITE, .014, .78]]) cues.push(cue(0, {
        ...target, kind: 'bolt', pattern: 'rail', color, width, gain, y: .65,
        offset: [-radius * .6, 0, 0], length: radius * 1.2, spread: .12,
        angle: c.angle + .8, motion: 'orbit', spin: 2.1,
      }));
      cues.push(cue(0, { ...target, kind: 'bolt', pattern: 'rail', color: VIOLET,
        decoration: true, y: 1.02, offset: [-radius * .5, 0, 0], length: radius,
        width: .025, spread: .1, gain: .45, angle: c.angle - .7, motion: 'orbit', spin: -1.7 }));
    }
    return { cues };
  },
  channel(c) {
    const o = origin(c), duration = c.channelDuration ?? 4.2;
    const enterLife = Math.max(.04, duration - FX_TIMING.channelEnter);
    const holdLife = Math.max(.04, duration - FX_TIMING.channelHold);
    const sustained = { ...o, attach: true, channel: true, cancelOnOwnerLoss: true,
      channelDuration: duration, fadeOut: .25 };
    // 手中蓄电与头顶云盘分属两种尺度；13帧开始举盘，28帧建立内圈。
    return { cues: [
      cue(0, { ...sustained, kind: 'orb', pattern: 'rail', color: BLUE,
        offset: [.25, 1.45, -.25], radius: .35, motion: 'collapse', life: .65,
        chargeTime: .5, fadeIn: .15, fadeOut: .15, gain: .48 }),
      cue(0, { ...o, kind: 'feedback', color: BLUE, life: .26,
        fadeIn: .045, fadeOut: .19, gain: .08 }),
      cue('channelEnter', { ...sustained, kind: 'arc', pattern: 'rail', color: VIOLET,
        y: 3.75, radius: 2.3, width: .095, halfAngle: Math.PI, motion: 'orbit', spin: -.8,
        life: enterLife, chargeTime: FX_TIMING.channelHold - FX_TIMING.channelEnter,
        fadeIn: .3, gain: .4 }),
      cue('channelEnter', { ...sustained, kind: 'shard', pattern: 'rail', color: BLUE,
        offset: [0, 3.65, 0], count: 6, spread: 1.7, width: .42, height: .12,
        motion: 'orbit', spin: -.8, life: enterLife, fadeIn: .4, gain: .32 }),
      cue('channelHold', { ...sustained, kind: 'arc', pattern: 'rail', color: BLUE,
        y: 3.62, radius: 1.65, width: .055, halfAngle: Math.PI, tilt: -.08,
        motion: 'orbit', spin: -.8, life: holdLife, fadeIn: .14, gain: .54 }),
      cue('channelHold', { ...sustained, kind: 'orb', pattern: 'rail', color: WHITE,
        offset: [0, 3.66, 0], radius: .26, life: holdLife,
        fadeIn: .14, gain: .46 }),
    ] };
  },
  pulse(c) {
    // 每次真实命中一根分叉落雷；空扇面不伪造落点、不预约后续攻击。
    const points = (c.points ?? []).filter(p => Number.isFinite(p.x) && Number.isFinite(p.z)).slice(0, 10);
    if (!points.length) return { cues: [] };
    const o = origin(c);
    const cues = points.map((p, i) => cue(0, {
      ...o, kind: 'bolt', pattern: 'rail', color: BLUE, y: 3.7,
      end: [p.x, .18, p.z], width: .045, spread: .38,
      life: .23, fadeIn: .008, fadeOut: .18, gain: .78,
      seed: (c.seed ?? 0) + i, target: p.target, generation: p.generation,
    }));
    cues.push(cue(0, { ...o, kind: 'arc', pattern: 'rail', color: WHITE,
      y: 3.7, radius: 1.18, width: .035, halfAngle: Math.PI,
      motion: 'expand', life: .2, fadeIn: .015, fadeOut: .16, gain: .4 }));
    return { cues };
  },
};
