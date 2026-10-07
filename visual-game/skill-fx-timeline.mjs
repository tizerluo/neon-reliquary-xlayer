// 技能表现使用游戏时间；暂停、补帧或审图拖动时间轴都不会重复结算战斗。
export const FX_TIMING = Object.freeze({ fps: 26, castContact: 14 / 26, channelEnter: 13 / 26, channelHold: 28 / 26 });
export const FX_COLORS = Object.freeze(['#70e5dc', '#ffab52', '#79adff', '#c293f4', '#f477b5', '#c2f4ff']);
export const FX_KINDS = Object.freeze(['decal', 'arc', 'lance', 'pillar', 'petals', 'shield', 'orb', 'shard', 'dome', 'bolt', 'ribbon', 'wing', 'feedback']);
export const FX_PATTERNS = Object.freeze(['sigil', 'fault', 'rail', 'void', 'rose', 'frost']);
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
const smooth = v => { v = clamp(v, 0, 1); return v * v * (3 - 2 * v); };

export function normalizeEffect(input = {}) {
  if (!FX_KINDS.includes(input.kind)) throw new TypeError('未知技能特效类型');
  const number = (key, value, lo, hi) => {
    const n = input[key] ?? value;
    if (!Number.isFinite(n) || n < lo || n > hi) throw new RangeError(`特效 ${key} 超出范围`);
    return n;
  };
  const life = number('life', .7, .04, 12), fadeIn = number('fadeIn', Math.min(.08, life), 0, life), fadeOut = number('fadeOut', Math.min(.24, life * .4), 0, life);
  const offset = input.offset ?? [0, 0, 0];
  if (!Array.isArray(offset) || offset.length !== 3 || offset.some(n => !Number.isFinite(n) || Math.abs(n) > 32)) throw new RangeError('特效 offset 必须是三个有限米制坐标');
  const color = input.color ?? FX_COLORS[input.hero ?? 0];
  if (typeof color !== 'string' || !/^#[0-9a-f]{6}$/i.test(color)) throw new TypeError('特效颜色必须是六位十六进制');
  const owner = input.owner ?? null;
  if (owner !== null && (!Number.isSafeInteger(owner) || owner < 0)) throw new TypeError('特效主人必须是 uid');
  if (input.attach && owner === null) throw new TypeError('跟随特效需要主人 uid');
  const shape = input.shape ?? 'seal';
  if (!['seal', 'lane', 'sector'].includes(shape)) throw new TypeError('未知地面贴花形状');
  const pattern = input.pattern ?? 'sigil', motion = input.motion ?? 'still';
  if (!FX_PATTERNS.includes(pattern)) throw new TypeError('未知技能纹样');
  if (!['still', 'expand', 'collapse', 'rise', 'fall', 'sweep', 'orbit'].includes(motion)) throw new TypeError('未知技能运动');
  const end = input.end ?? null;
  if (end !== null && (!Array.isArray(end) || end.length !== 3 || end.some(n => !Number.isFinite(n) || Math.abs(n) > 128))) throw new RangeError('电弧终点必须为三个有限坐标');
  const target = input.target ?? null, generation = input.generation ?? null;
  const boss = input.boss ?? null;
  if (boss !== null && (!Number.isInteger(boss) || boss < 0 || boss > 7)) throw new TypeError('Boss 特效需要有效图鉴索引');
  if (target !== null && (!Number.isSafeInteger(target) || target < 0)) throw new TypeError('敌人锚点必须是池索引');
  if (generation !== null && (!Number.isSafeInteger(generation) || generation < 0)) throw new TypeError('敌人锚点需要有效代次');
  return Object.freeze({ kind: input.kind, shape, color, owner, attach: !!input.attach,
    pattern, motion, end: end && Object.freeze([...end]), target, generation, requireFreeze: !!input.requireFreeze, requireStun: !!input.requireStun, decoration: !!input.decoration,
    hero: number('hero', 0, 0, 5) | 0, boss, label: String(input.label ?? input.kind).slice(0, 64),
    cancelOnOwnerLoss: input.cancelOnOwnerLoss ?? !!input.attach, channel: !!input.channel,
    channelDuration: number('channelDuration', 4.2, .01, 12),
    x: number('x', 0, -128, 128), y: number('y', .07, -4, 24), z: number('z', 0, -128, 128),
    angle: number('angle', 0, -Math.PI * 8, Math.PI * 8), tilt: number('tilt', 0, -Math.PI, Math.PI),
    aimOffset: number('aimOffset', 0, -Math.PI*8, Math.PI*8),
    radius: number('radius', 1.5, .02, 20), width: number('width', .14, .01, 12),
    length: number('length', 3, .02, 32), height: number('height', 3, .02, 18),
    halfAngle: number('halfAngle', Math.PI / 2, .025, Math.PI), spin: number('spin', 0, -8, 8),
    count: number('count', 1, 1, 12) | 0, spread: number('spread', 0, 0, 8),
    gain: number('gain', input.kind === 'feedback' ? .10 : .75, 0, input.kind === 'feedback' ? .12 : 1.6),
    seed: number('seed', 1, 0, 2147483647), chargeTime: number('chargeTime', input.kind==='decal'?life:Math.min(.18,life), .01, 12),
    petals: number('petals', 8, 3, 12) | 0, offset: Object.freeze([...offset]), life, fadeIn, fadeOut });
}

export function sampleEffect(spec, start, now) {
  const age = now - start;
  if (age < 0 || age >= spec.life) return null;
  return { age, phase: age / spec.life, progress: clamp(age / spec.chargeTime, 0, 1),
    opacity: spec.gain * Math.min(spec.fadeIn ? smooth(age / spec.fadeIn) : 1, spec.fadeOut ? smooth((spec.life - age) / spec.fadeOut) : 1),
    dissolve: spec.fadeOut ? smooth((age - spec.life + spec.fadeOut) / spec.fadeOut) : 0 };
}

// 先编译全部 cue，再一次预约；容量不足不会只画半个招式。
export function compilePreset(definition, context = {}) {
  if (!Array.isArray(definition?.cues) || definition.cues.length > 24) throw new TypeError('技能配方需要至多 24 个 cue');
  return definition.cues.map(cue => {
    const at = typeof cue.at === 'string' ? FX_TIMING[cue.at] : cue.at ?? 0;
    if (!Number.isFinite(at) || at < 0 || at > 12) throw new RangeError('无效技能 cue 时间');
    return { at, spec: normalizeEffect({ ...context, ...cue.effect,
      aimOffset: cue.effect.attach && Number.isFinite(context.angle) ? (cue.effect.angle ?? context.angle)-context.angle : cue.effect.aimOffset ?? 0 }) };
  });
}

export function createEffectTimeline(capacity = 128) {
  const entries = [];
  let accepted = 0, dropped = 0;
  return {
    add(compiled, now) {
      if (!Number.isFinite(now)) throw new TypeError('技能表现时间必须有限');
      if (entries.length + compiled.length > capacity) { dropped += compiled.length; return false; }
      for (const cue of compiled) entries.push({ spec: cue.spec, start: now + cue.at, origin: now });
      accepted += compiled.length; return true;
    },
    visit(now, visitor, cancel = () => false) {
      for (let i = entries.length - 1; i >= 0; i--) {
        const entry = entries[i];
        if (now >= entry.start + entry.spec.life || cancel(entry.spec, entry.start, entry.origin)) { entries.splice(i, 1); continue; }
        const sample = sampleEffect(entry.spec, entry.start, now);
        if (sample) visitor(entry.spec, sample, entry.start, entry.origin);
      }
    },
    clear() { entries.length = 0; accepted = dropped = 0; },
    removeWhere(predicate) { for(let i=entries.length-1;i>=0;i--)if(predicate(entries[i].spec))entries.splice(i,1); },
    metrics: () => ({ scheduled: entries.length, accepted, dropped, capacity }),
  };
}

// 通用施法提示只围绕角色，后续六英雄的专属攻击由各自配方替换，原生攻击仍保留。
export const COMMON_SKILL_PRESETS = Object.freeze({
  cast: { cues: [
    { at: 0, effect: { kind: 'decal', shape: 'seal', radius: 1.65, life: 1.02, chargeTime: FX_TIMING.castContact, gain: .62, attach: true } },
    { at: 'castContact', effect: { kind: 'arc', radius: 1.2, width: .16, y: .7, tilt: .35, life: .25, gain: .75, attach: true } },
  ] },
  channel: { cues: [
    { at: 0, effect: { kind: 'decal', shape: 'seal', radius: 2.15, life: 4.35, chargeTime: 4.2, gain: .55, attach: true, channel: true } },
    { at: 'channelEnter', effect: { kind: 'pillar', radius: .18, height: 2.8, life: .32, gain: .7, attach: true, channel: true } },
    { at: 'channelHold', effect: { kind: 'petals', radius: 1.0, length: .7, height: .35, life: .42, gain: .62, attach: true, channel: true } },
    { at: 0, effect: { kind: 'feedback', life: .28, fadeIn: .055, fadeOut: .20, gain: .10 } },
  ] },
});
