import { FX_TIMING } from '../skill-fx-timeline.mjs';

const ROSE = '#f477b5', CRIMSON = '#c54879', GOLD = '#e9ac91', WHITE = '#fff1d5';
const cue = (at, effect) => ({ at, effect });
const origin = c => ({ x: c.x, z: c.z, angle: c.angle, owner: c.owner, seed: c.seed ?? 1 });
const attached = c => ({ ...origin(c), attach: true, cancelOnOwnerLoss: true });
const actualPoints = c => (c.points ?? []).filter(p => Number.isFinite(p.x) && Number.isFinite(p.z));

export default {
  hero: 4,
  key: 'seraph',
  name: '祝祷 / 赤红圣餐',
  cast(c) {
    const root = origin(c), body = attached(c);
    // 手中小光冠蓄势；接触帧的三层空心波纹严格止于9.1米、半角.68。
    return { cues: [
      cue(0, { ...body, kind: 'arc', label: '掌心祝祷冠', color: GOLD,
        offset: [.44, 1.42, -.22], radius: .34, width: .035, halfAngle: Math.PI,
        tilt: .65, motion: 'collapse', life: .59, chargeTime: FX_TIMING.castContact,
        fadeIn: .15, fadeOut: .1, gain: .48 }),
      cue(0, { ...body, kind: 'shard', label: '玫金蓄势羽', color: ROSE,
        offset: [.4, 1.1, -.22], count: 3, spread: .22, width: .065, height: .28,
        motion: 'rise', life: .56, fadeIn: .14, fadeOut: .1, gain: .38 }),
      cue('castContact', { ...root, kind: 'decal', label: '祝祷真实扇面', shape: 'sector',
        pattern: 'rose', color: CRIMSON, radius: 9.1, halfAngle: .68,
        life: .49, fadeIn: .02, fadeOut: .37, chargeTime: .16, gain: .27 }),
      cue('castContact', { ...root, kind: 'arc', label: '绯红击退波', color: ROSE,
        radius: 9.1, halfAngle: .68, width: .18, y: .48, tilt: .035,
        motion: 'expand', life: .38, chargeTime: .23, fadeIn: .015, fadeOut: .22, gain: .62 }),
      cue('castContact', { ...root, kind: 'arc', label: '玫金波刃', color: GOLD,
        radius: 9.04, halfAngle: .68, width: .052, y: .53, tilt: .035,
        motion: 'expand', life: .34, chargeTime: .23, fadeIn: .01, fadeOut: .2, gain: .76 }),
      cue(FX_TIMING.castContact + .055, { ...root, kind: 'arc', label: '低位祝祷余波', color: CRIMSON,
        radius: 8.7, halfAngle: .66, width: .08, y: .17,
        motion: 'expand', life: .39, chargeTime: .24, fadeIn: .02, fadeOut: .28, gain: .36 }),
      // 第14帧短促展开机械羽扇，暗玫骨架与金色羽尖分开，避免一整块亮翼。
      cue('castContact', { ...body, kind: 'wing', label: '祝祷机械羽扇', color: CRIMSON,
        offset: [-.32, 1.7, 0], radius: 2.15, height: .52, length: 1.07,
        petals: 5, motion: 'expand', life: .44, chargeTime: .12, fadeIn: .025, fadeOut: .3, gain: .46 }),
      cue('castContact', { ...body, kind: 'wing', label: '机械羽金边', color: GOLD,
        offset: [-.31, 1.75, 0], radius: 2.09, height: .49, length: .78,
        petals: 5, motion: 'expand', life: .36, chargeTime: .12, fadeIn: .025, fadeOut: .24, gain: .56 }),
      cue('castContact', { ...body, kind: 'arc', label: '自身祝祷环', color: GOLD,
        offset: [0, .9, 0], radius: .65, width: .035, halfAngle: Math.PI,
        motion: 'rise', life: .45, fadeIn: .025, fadeOut: .32, gain: .42 }),
      cue('castContact', { ...body, kind: 'shard', label: '自身疗愈星光', color: WHITE,
        offset: [0, .3, 0], count: 4, spread: .45, width: .035, height: .16,
        motion: 'rise', life: .47, fadeIn: .03, fadeOut: .31, gain: .51 }),
    ] };
  },
  channel(c) {
    const root = origin(c), duration = c.channelDuration ?? 4.2;
    const body = { ...attached(c), channel: true, channelDuration: duration };
    const enterLife = Math.max(.04, duration - FX_TIMING.channelEnter);
    const holdLife = Math.max(.04, duration - FX_TIMING.channelHold);
    // 第13帧展翼，第28帧白金细冠锁定；地面玫瑰圣印固定在施放原点。
    return { cues: [
      cue(0, { ...body, kind: 'arc', label: '圣餐举手光环', color: GOLD,
        offset: [.4, 1.45, -.2], radius: .4, width: .035, halfAngle: Math.PI,
        motion: 'rise', life: .67, fadeIn: .16, fadeOut: .15, gain: .4 }),
      cue(0, { ...root, kind: 'feedback', color: CRIMSON, life: .26,
        fadeIn: .045, fadeOut: .19, gain: .08 }),
      cue('channelEnter', { ...body, kind: 'wing', label: '圣餐绯红机械翼', color: CRIMSON,
        offset: [-.42, 2.1, 0], radius: 2.8, height: .84, length: 1.2, petals: 5,
        motion: 'expand', chargeTime: FX_TIMING.channelHold - FX_TIMING.channelEnter,
        life: enterLife, fadeIn: .2, fadeOut: .3, gain: .41 }),
      cue('channelEnter', { ...body, kind: 'arc', label: '玫金升冠', color: GOLD,
        offset: [0, 3.16, 0], radius: .89, width: .045, halfAngle: Math.PI,
        tilt: .16, motion: 'rise', life: enterLife, fadeIn: .25, fadeOut: .28,
        chargeTime: FX_TIMING.channelHold - FX_TIMING.channelEnter, gain: .57 }),
      cue('channelHold', { ...body, kind: 'wing', label: '圣餐羽尖金饰', color: GOLD,
        offset: [-.4, 2.17, 0], radius: 2.73, height: .78, length: .68, petals: 5,
        motion: 'still', life: holdLife, fadeIn: .15, fadeOut: .3, gain: .4 }),
      cue('channelHold', { ...body, kind: 'arc', label: '白金圣餐冠', color: WHITE,
        offset: [0, 3.22, 0], radius: .71, width: .026, halfAngle: Math.PI,
        tilt: .16, motion: 'orbit', spin: .22, life: holdLife, fadeIn: .15, fadeOut: .28, gain: .48 }),
      cue('channelHold', { ...root, kind: 'decal', label: '圣餐原点玫瑰纹', shape: 'seal',
        pattern: 'rose', color: CRIMSON, radius: 1.36, y: .055, channel: true,
        channelDuration: duration, life: holdLife, fadeIn: .25, fadeOut: .3, gain: .25 }),
    ] };
  },
  pulse(c) {
    const point = actualPoints(c)[0];
    if (!point) return { cues: [] };
    const root = { ...origin(c), x: point.x, z: point.z };
    const radius = point.radius ?? 2.744;
    const angle = c.angle + Math.sin((c.age ?? 0) * 1.7) * .14;
    // 本次只有真实落点绽放。两层莲瓣保持空心花心；白金细瓣对应上层脉线。
    return { cues: [
      cue(0, { ...root, kind: 'decal', label: '真实圣餐落点', shape: 'seal', pattern: 'rose',
        color: CRIMSON, radius, angle, y: .055, life: .46, fadeIn: .02, fadeOut: .34, gain: .31 }),
      cue(0, { ...root, kind: 'petals', label: '绯红外莲瓣', color: CRIMSON,
        petals: 10, radius: radius * .67, length: .94, width: .42, height: .35, angle,
        y: .1, motion: 'expand', life: .44, chargeTime: .15, fadeIn: .025, fadeOut: .28, gain: .55 }),
      cue(.035, { ...root, kind: 'petals', label: '玫金内莲瓣', color: GOLD,
        petals: 8, radius: radius * .42, length: .69, width: .31, height: .55,
        angle: angle + Math.PI / 8, y: .16, motion: 'expand',
        life: .4, chargeTime: .14, fadeIn: .02, fadeOut: .26, gain: .53 }),
      cue(.035, { ...root, kind: 'petals', label: '白金莲瓣脉线', color: WHITE,
        petals: 8, radius: radius * .42, length: .62, width: .035, height: .56,
        angle: angle + Math.PI / 8, y: .18, motion: 'expand',
        life: .29, chargeTime: .14, fadeIn: .02, fadeOut: .19, gain: .42 }),
      cue(0, { ...root, kind: 'arc', label: '圣餐花缘金圈', color: GOLD,
        radius, width: .035, halfAngle: Math.PI, y: .085, motion: 'expand',
        life: .33, chargeTime: .18, fadeIn: .015, fadeOut: .22, gain: .45 }),
      cue(.04, { ...root, kind: 'shard', label: '圣餐稀疏花粉', color: ROSE,
        count: 5, spread: radius * .48, y: .38, width: .045, height: .2,
        motion: 'rise', life: .32, fadeIn: .02, fadeOut: .21, gain: .4 }),
    ] };
  },
  heal(c) {
    const cues = [];
    // 只跟随事件中实际接受治疗的队友 uid，不从施法者或半径猜测接收者。
    for (const [i, point] of actualPoints(c).filter(p => Number.isSafeInteger(p.owner) && p.owner >= 0).slice(0, 6).entries()) {
      const root = { x: point.x, z: point.z, angle: c.angle, owner: point.owner,
        attach: true, cancelOnOwnerLoss: true, seed: (c.seed ?? 1) + i * 11 };
      cues.push(
        cue('castContact', { ...root, kind: 'shard', label: '队友真实疗愈光点', color: WHITE,
          offset: [0, .24, 0], count: 4, spread: .36, width: .035, height: .15,
          motion: 'rise', life: .48, fadeIn: .03, fadeOut: .29, gain: .53 }),
        cue('castContact', { ...root, kind: 'arc', label: '队友玫金疗愈环', color: GOLD,
          offset: [0, .42, 0], radius: .48, width: .022, halfAngle: Math.PI,
          motion: 'rise', life: .4, fadeIn: .03, fadeOut: .27, gain: .38 }),
      );
    }
    return { cues };
  },
};
