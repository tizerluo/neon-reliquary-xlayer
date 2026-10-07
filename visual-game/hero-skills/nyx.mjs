import { FX_TIMING, FX_COLORS } from '../skill-fx-timeline.mjs';

const VIOLET = FX_COLORS[3], DEEP = '#7150ad', LIGHT = '#e5caff';
const cue = (at, label, effect) => ({ at, effect: { label, ...effect } });
const origin = c => ({ hero: 3, x: c.x, z: c.z, angle: c.angle, owner: c.owner, seed: c.seed });
const points = c => (c.points ?? []).filter(p => Number.isFinite(p.x) && Number.isFinite(p.z));

export default {
  hero: 3,
  key: 'nyx',
  name: '虚空炸药 · 黑障协议',
  cast(c) {
    const o = origin(c);
    const hand = { ...o, attach: true, cancelOnOwnerLoss: true };
    // 炸药先按真实引信显形；第14帧只补投掷手势，不预约第二轮爆炸。
    const cues = [
      cue(0, 'nyx-cast-hand-charge', { ...hand, kind: 'orb', pattern: 'void', color: VIOLET,
        offset: [.35, 1.15, -.36], radius: .26, life: .60, motion: 'collapse',
        chargeTime: FX_TIMING.castContact, fadeIn: .13, fadeOut: .08, gain: .48 }),
      cue(0, 'nyx-cast-wrist-silhouette', { ...hand, kind: 'shard', pattern: 'void', color: DEEP,
        offset: [.38, 1.16, -.36], count: 3, spread: .22, width: .12, height: .43,
        tilt: .5, spin: 1.1, motion: 'orbit', life: .63, fadeIn: .11, fadeOut: .16, gain: .36 }),
      cue(0, 'nyx-cast-real-near-fan', { ...o, kind: 'arc', pattern: 'void', color: DEEP,
        radius: 3.92, halfAngle: .62, width: .05, motion: 'expand', life: .28,
        chargeTime: .12, fadeIn: .02, fadeOut: .19, gain: .34 }),
      cue('castContact', 'nyx-cast14-throw-release', { ...hand, kind: 'ribbon', pattern: 'void', color: LIGHT,
        offset: [.45, 1.16, -.36], length: 1.62, width: .045, life: .26,
        motion: 'sweep', chargeTime: .13, fadeIn: .01, fadeOut: .22, gain: .64 }),
      cue('castContact', 'nyx-cast14-release-shell', { ...hand, kind: 'orb', pattern: 'void', color: VIOLET,
        offset: [.74, 1.14, -.36], radius: .38, life: .25, motion: 'expand',
        chargeTime: .12, fadeIn: .01, fadeOut: .20, gain: .44 }),
    ];
    points(c).slice(0, 4).forEach((p, i) => {
      const fuse = Math.max(.04, p.duration ?? (.12 + i * .12));
      const root = { ...o, x: p.x, z: p.z, seed: (c.seed ?? 0) + i };
      cues.push(cue(0, `nyx-fuse-${i + 1}-hollow-shell`, { ...root, kind: 'orb', pattern: 'void', color: VIOLET,
        y: .65, radius: .68, life: fuse, motion: 'collapse', chargeTime: fuse,
        fadeIn: Math.min(.035, fuse / 4), fadeOut: Math.min(.045, fuse / 3), gain: .58 }));
      cues.push(cue(0, `nyx-fuse-${i + 1}-void-sparks`, { ...root, kind: 'shard', pattern: 'void', color: LIGHT,
        y: .55, count: 4, spread: .53, width: .045, height: .19, life: fuse,
        motion: 'collapse', spin: -1.4, chargeTime: fuse, fadeIn: .02,
        fadeOut: Math.min(.04, fuse / 3), gain: .42 }));
    });
    return { cues };
  },
  bomb(c) {
    // 仅实际爆点触发内塌壳、断环与碎光；四个引信由战斗事件逐一结算。
    const p = points(c)[0];
    if (!p) return { cues: [] };
    const o = { ...origin(c), x: p.x, z: p.z }, radius = p.radius ?? 2.24;
    return { cues: [
      cue(0, 'nyx-bomb-real-implosion-shell', { ...o, kind: 'orb', pattern: 'void', color: VIOLET,
        y: .72, radius: radius * .75, motion: 'collapse', life: .33, chargeTime: .25,
        fadeIn: .015, fadeOut: .12, gain: .69 }),
      cue(0, 'nyx-bomb-real-shock-ring', { ...o, kind: 'arc', pattern: 'void', color: LIGHT,
        y: .11, radius, halfAngle: Math.PI, width: .045, motion: 'expand',
        life: .39, chargeTime: .25, fadeIn: .01, fadeOut: .25, gain: .55 }),
      cue(0, 'nyx-bomb-tilted-void-ring', { ...o, kind: 'arc', pattern: 'void', color: DEEP,
        y: .5, radius: radius * .68, halfAngle: 2.55, width: .07, tilt: .55,
        motion: 'collapse', spin: -.6, life: .31, chargeTime: .22, fadeIn: .015, fadeOut: .19, gain: .45 }),
      cue(0, 'nyx-bomb-void-sparks', { ...o, kind: 'shard', pattern: 'void', color: VIOLET,
        y: .32, count: 7, spread: radius * .68, width: .065, height: .34,
        motion: 'expand', life: .37, chargeTime: .24, fadeIn: .01, fadeOut: .25, gain: .51 }),
    ] };
  },
  channel(c) {
    const o = origin(c), duration = c.channelDuration ?? 4.2;
    const enterLife = Math.max(.04, duration - FX_TIMING.channelEnter);
    const holdLife = Math.max(.04, duration - FX_TIMING.channelHold);
    const held = { ...o, attach: true, channel: true, cancelOnOwnerLoss: true, channelDuration: duration };
    // 地面电路固定在释放地点；头顶黑障随举手在13到28帧逐层建立。
    return { cues: [
      cue(0, 'nyx-channel-hand-key', { ...held, kind: 'orb', pattern: 'void', color: VIOLET,
        offset: [.28, 1.42, -.26], radius: .28, motion: 'collapse', life: .64,
        chargeTime: .50, fadeIn: .15, fadeOut: .15, gain: .43 }),
      cue(0, 'nyx-channel-blackout-feedback', { ...o, kind: 'feedback', color: DEEP,
        life: .26, fadeIn: .05, fadeOut: .19, gain: .08 }),
      cue('channelEnter', 'nyx-channel13-purple-circuit-grid', { ...o, kind: 'decal', shape: 'lane',
        pattern: 'void', color: DEEP, length: 9.6, width: 4.3, y: .04,
        life: enterLife, channel: true, channelDuration: duration, cancelOnOwnerLoss: true,
        chargeTime: FX_TIMING.channelHold - FX_TIMING.channelEnter, fadeIn: .26, fadeOut: .32, gain: .28 }),
      cue('channelEnter', 'nyx-channel13-blackout-canopy', { ...held, kind: 'orb', pattern: 'void', color: DEEP,
        offset: [0, 3.1, 0], radius: 1.56, motion: 'rise', spin: -.22,
        life: enterLife, chargeTime: .58, fadeIn: .32, fadeOut: .3, gain: .28 }),
      cue('channelEnter', 'nyx-channel13-canopy-fragments', { ...held, kind: 'shard', pattern: 'void', color: VIOLET,
        offset: [0, 3.1, 0], count: 6, spread: 1.28, width: .12, height: .51,
        motion: 'orbit', spin: -.38, life: enterLife, fadeIn: .4, fadeOut: .32, gain: .37 }),
      cue('channelHold', 'nyx-channel28-canopy-rim', { ...held, kind: 'arc', pattern: 'void', color: VIOLET,
        offset: [0, 3.3, 0], radius: 1.73, halfAngle: 2.55, width: .045,
        motion: 'orbit', spin: -.38, life: holdLife, fadeIn: .18, fadeOut: .27, gain: .46 }),
      cue('channelHold', 'nyx-channel28-hand-command', { ...held, kind: 'ribbon', pattern: 'void', color: LIGHT,
        offset: [.25, 1.55, -.27], length: .55, width: .022,
        life: holdLife, fadeIn: .14, fadeOut: .25, gain: .36 }),
    ] };
  },
  pulse(c) {
    const o = origin(c);
    // 两组各八针严格复用本次真实16针扇面；只表现出膛，不伪造伤害或落点。
    // 单组角距 .045，外缘总半角 .3375；实际出膛侧偏为每针 .14米。
    const cues = [-1, 1].map(side => cue(0, `nyx-pulse-real-eight-needles-${side < 0 ? 'left' : 'right'}`, {
      ...o, kind: 'ribbon', pattern: 'void', color: side < 0 ? VIOLET : LIGHT,
      angle: c.angle + side * .18, offset: [.24, .79, side * .56],
      count: 8, halfAngle: .1575, spread: .49, length: 4.8, width: .023,
      motion: 'sweep', life: .16, chargeTime: .11, fadeIn: .008, fadeOut: .09, gain: .5,
    }));
    // age 是真实终结技经过时间，不能将每次 pulse 当作重新举手。
    if ((c.age ?? 0) >= FX_TIMING.channelEnter) cues.push(cue(0, 'nyx-pulse-held-canopy-needle-glint', {
      ...o, kind: 'shard', pattern: 'void', color: VIOLET, offset: [.12, 2.75, 0],
      count: 5, spread: 1.04, width: .025, height: .45, motion: 'fall',
      life: .14, fadeIn: .008, fadeOut: .1, gain: .29,
    }));
    return { cues };
  },
};
