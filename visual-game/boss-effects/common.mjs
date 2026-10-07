// Boss 的表现配方只读取真实事件；颜色沿用战斗数据，预警另由原生红色层绘制。
export const BOSS_COLORS = Object.freeze(['#ff8969','#91e6ff','#efcf8c','#c5a1f4','#f4c76c','#eba1f6','#8ceab9','#ffad8c']);
export const BOSS_NAMES = Object.freeze(['余烬之王','苍白巨龙','钢铁巨兽','空壳元帅','机械神祇','零域先知','剧毒三位体','灰烬炽天使']);
export const cue = (at, effect) => ({ at, effect });
export function effect(c, kind, label, fields = {}) {
  return { kind, label, hero: 0, boss: c.boss, owner: c.owner ?? null,
    x: c.x, z: c.z, angle: c.angle ?? 0, seed: c.seed ?? 1,
    color: BOSS_COLORS[c.boss], cancelOnOwnerLoss: false, ...fields };
}
export function caster(c, kind, label, fields = {}) {
  return effect(c, kind, label, { attach: true, cancelOnOwnerLoss: true, ...fields });
}
