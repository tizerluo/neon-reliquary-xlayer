import { FX_TIMING, FX_COLORS } from '../skill-fx-timeline.mjs';

const CYAN = FX_COLORS[0], WHITE = '#d9ffff', DEEP = '#3198b3';
const cue = (at, effect) => ({ at, effect });
const origin = c => ({ x: c.x, z: c.z, angle: c.angle, owner: c.owner, seed: c.seed ?? 1 });
const attached = c => ({ ...origin(c), attach: true, cancelOnOwnerLoss: true });

export default {
  hero: 0,
  key: 'aurelian',
  name: '圣盾破阵 / 天坠之枪',
  cast(c) {
    const root = origin(c), hand = attached(c);
    // 蓄势只聚焦手臂与盾脊；地面的真实扇面在接触帧才显现。
    const cues = [
      cue(0, { ...hand, kind: 'shield', color: DEEP, offset: [.75, .75, -.35], radius: .52, height: 1.28, motion: 'rise', life: .64, fadeIn: .16, fadeOut: .12, chargeTime: FX_TIMING.castContact, gain: .35 }),
      cue(0, { ...hand, kind: 'ribbon', color: WHITE, offset: [.32, 1.18, -.36], length: 1.32, width: .055, motion: 'sweep', pattern: 'rail', life: .57, fadeIn: .14, fadeOut: .12, chargeTime: FX_TIMING.castContact, gain: .55 }),
      // 第14帧举起六角盾：双层外框与暗青格架承载材质感。
      cue('castContact', { ...hand, kind: 'shield', color: CYAN, angle:c.angle+.5, offset: [1.12, 1.04, 0], radius: 1.12, height: 2.45, motion: 'rise', pattern: 'sigil', life: .49, fadeIn: .025, fadeOut: .32, gain: .72 }),
      cue('castContact', { ...hand, kind: 'shield', color: WHITE, angle:c.angle+.5, offset: [1.16, 1.08, 0], radius: .91, height: 2.02, life: .26, fadeIn: .02, fadeOut: .18, gain: .44 }),
      cue('castContact', { ...root, kind: 'decal', shape: 'sector', pattern: 'sigil', color: DEEP, radius: 9.94, halfAngle: .58, y: .055, life: .57, fadeIn: .025, fadeOut: .43, chargeTime: .12, gain: .3 }),
      // 宽薄主刃、白色刃口与稍迟的低位残影形成横扫，而非完整圆环。
      cue('castContact', { ...root, kind: 'arc', color: CYAN, radius: 9.94, halfAngle: .58, width: .27, y: 1.0, tilt: .07, motion: 'expand', life: .36, fadeIn: .02, fadeOut: .21, chargeTime: .19, gain: .68 }),
      cue('castContact', { ...root, kind: 'arc', color: WHITE, radius: 9.82, halfAngle: .57, width: .06, y: 1.08, tilt: .07, motion: 'expand', life: .29, fadeIn: .015, fadeOut: .17, chargeTime: .18, gain: .81 }),
      cue(FX_TIMING.castContact + .055, { ...root, kind: 'arc', color: DEEP, radius: 8.84, halfAngle: .55, width: .13, y: .31, motion: 'expand', life: .42, fadeIn: .02, fadeOut: .29, chargeTime: .21, gain: .34 }),
      cue('castContact', { ...hand, kind: 'shard', color: CYAN, offset: [1.4, 1.15, 0], width: .13, height: .42, count: 6, spread: .72, motion: 'expand', life: .35, fadeIn: .01, fadeOut: .25, gain: .52 }),
    ];
    // 七条放射枪脊保留枪群的方向性，全部止于真实破阵扇面以内。
    for (let j = 0; j < 7; j++) {
      cues.push(cue('castContact', { ...root, kind: 'ribbon', color: j % 2 ? CYAN : WHITE, angle: c.angle + (j - 3) * .145, offset: [1.3, .48 + (j % 2) * .19, 0], length: 8.35, width: j === 3 ? .115 : .058, pattern: 'rail', motion: 'expand', life: .31 + (j % 2) * .04, fadeIn: .015, fadeOut: .2, chargeTime: .13, gain: j === 3 ? .68 : .44 }));
    }
    return { cues };
  },
  channel(c) {
    const root = origin(c), body = attached(c), duration = c.channelDuration ?? 4.2;
    const sustaining = { ...body, channel: true, channelDuration: duration };
    // 背盾先被抬起，第13帧在头后建立轮廓，第28帧收束为稳定的圣盾冠。
    return { cues: [
      cue(0, { ...sustaining, kind: 'shield', color: DEEP, offset: [-.4, 1.43, 0], radius: .74, height: 1.85, motion: 'rise', life: FX_TIMING.channelHold + .12, fadeIn: .16, fadeOut: .25, chargeTime: FX_TIMING.channelEnter, gain: .39 }),
      cue('channelEnter', { ...sustaining, kind: 'shield', color: CYAN, angle:c.angle+.65, offset: [-.38, 3.18, 0], radius: 1.38, height: 2.7, motion: 'rise', pattern: 'sigil', life: Math.max(.4, duration - FX_TIMING.channelEnter), fadeIn: .18, fadeOut: .3, chargeTime: FX_TIMING.channelHold - FX_TIMING.channelEnter, gain: .59 }),
      cue('channelHold', { ...sustaining, kind: 'shield', color: WHITE, angle:c.angle+.65, offset: [-.34, 3.26, 0], radius: 1.16, height: 2.3, pattern: 'sigil', life: Math.max(.4, duration - FX_TIMING.channelHold), fadeIn: .15, fadeOut: .3, gain: .36 }),
      cue('channelEnter', { ...sustaining, kind: 'wing', color: DEEP, offset: [-.52, 2.84, 0], radius: 1.95, height: .52, length: .88, petals: 3, motion: 'expand', life: Math.max(.4, duration - FX_TIMING.channelEnter), fadeIn: .2, fadeOut: .3, gain: .3 }),
      // 原点圣印固定；持盾者移动时不会拖着整片战场纹样移动。
      cue('channelHold', { ...root, kind: 'decal', shape: 'seal', pattern: 'sigil', color: DEEP, radius: 2.14, y: .05, life: Math.max(.4, duration - FX_TIMING.channelHold), fadeIn: .22, fadeOut: .4, chargeTime: .48, gain: .27, channel: true, channelDuration: duration }),
      cue(0, { ...root, kind: 'feedback', color: CYAN, life: .26, fadeIn: .045, fadeOut: .2, gain: .085 }),
    ] };
  },
  pulse(c) {
    const cues = [];
    // 仅接收本次真实三落点；每处四层，枪尖、刻印与碎屑共用同一触地点。
    for (const [i, point] of (c.points ?? []).slice(0, 3).entries()) {
      const root = { ...origin(c), x: point.x, z: point.z, seed: (c.seed ?? 1) + i * 17 }, radius = point.radius ?? 2.016;
      cues.push(
        cue(0, { ...root, kind: 'lance', color: CYAN, height: 9.3, length: 4.45, width: .17, life: .27, fadeIn: .012, fadeOut: .09, chargeTime: .14, gain: .74 }),
        cue(0, { ...root, kind: 'decal', shape: 'seal', pattern: 'sigil', color: CYAN, radius, y: .055, angle: c.angle + i * Math.PI / 3, life: .48, fadeIn: .025, fadeOut: .37, chargeTime: .07, gain: .56 }),
        cue(0, { ...root, kind: 'decal', shape: 'seal', pattern: 'sigil', color: WHITE, radius: radius * .49, y: .065, angle: c.angle + Math.PI / 6, life: .3, fadeIn: .015, fadeOut: .23, chargeTime: .045, gain: .5 }),
        cue(0, { ...root, kind: 'shard', color: CYAN, y: .12, width: .085, height: .46, count: 5, spread: radius * .4, motion: 'rise', life: .31, fadeIn: .02, fadeOut: .22, gain: .42 }),
      );
    }
    return { cues };
  },
};
